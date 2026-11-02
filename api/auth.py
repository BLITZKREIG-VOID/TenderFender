"""
Cognito id-token verification for the API (SoT §13 D38).

``require_user`` is the FastAPI dependency for authenticated endpoints. It accepts
``Authorization: Bearer <Cognito id token>`` and verifies, locally:

- the RS256 signature against the user pool's JWKS (fetched once per Lambda container,
  re-fetched on an unknown ``kid`` at most once per ``JWKS_MIN_REFRESH_SECONDS``);
- ``iss`` = ``https://cognito-idp.<region>.amazonaws.com/<pool id>``;
- ``aud`` = the app client id; ``token_use`` = ``id``; ``exp`` (no leeway).

Failures are 401 ``{"error", "code": "unauthenticated"}``; the token is never echoed or logged.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from collections.abc import Callable
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, Request

JWKS_TIMEOUT_SECONDS = 5
JWKS_MIN_REFRESH_SECONDS = 60
JWKS_FAILURE_BACKOFF_SECONDS = 30

class AuthError(Exception):
    """A token that must be rejected with 401. ``message`` is safe to show the caller."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class JwksUnavailable(Exception):
    """The pool's JWKS could not be fetched; the request cannot be verified (503)."""


def issuer_for(user_pool_id: str) -> str:
    """The ``iss`` claim of a user pool: the region is the pool id's prefix (``ap-south-1_AbC``)."""
    region = user_pool_id.split("_", 1)[0]
    return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"


def _fetch_url_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=JWKS_TIMEOUT_SECONDS) as resp:  # noqa: S310 (fixed https URL)
            return json.loads(resp.read())
    except (OSError, ValueError) as exc:
        raise JwksUnavailable(f"could not fetch JWKS: {type(exc).__name__}") from exc


class JwksCache:
    """Signing keys by ``kid``. Fetched lazily, kept for the container's life, refreshed on an unknown kid."""

    def __init__(self, fetch: Callable[[], dict[str, Any]], clock: Callable[[], float] = time.monotonic):
        self._fetch = fetch
        self._clock = clock
        self._keys: dict[str, Any] = {}
        self._fetched_at: float | None = None
        self._failed_at: float | None = None
        self._lock = threading.Lock()

    def _refresh(self) -> None:
        try:
            jwks = self._fetch()
        except Exception:
            self._failed_at = self._clock()
            raise
        keys: dict[str, Any] = {}
        for jwk in jwks.get("keys", []):
            if jwk.get("kty") == "RSA" and jwk.get("kid"):
                keys[jwk["kid"]] = jwt.PyJWK(jwk, algorithm="RS256").key
        self._keys = keys
        self._fetched_at = self._clock()
        self._failed_at = None
    def get(self, kid: str) -> Any | None:
        with self._lock:
            if kid not in self._keys:
                now = self._clock()
                if self._failed_at is not None and now - self._failed_at < JWKS_FAILURE_BACKOFF_SECONDS:
                    raise JwksUnavailable("JWKS fetch recently failed; backing off")
                stale = self._fetched_at is None or now - self._fetched_at >= JWKS_MIN_REFRESH_SECONDS
                if stale:
                    self._refresh()
            return self._keys.get(kid)


class TokenVerifier:
    def __init__(self, user_pool_id: str, client_id: str, jwks: JwksCache):
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.issuer = issuer_for(user_pool_id)
        self.jwks = jwks

    def verify(self, token: str) -> dict[str, Any]:
        """Return the verified claims of a Cognito id token, else raise ``AuthError``."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise AuthError("Malformed token") from exc
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise AuthError("Unsupported token")
        key = self.jwks.get(header["kid"])
        if key is None:
            raise AuthError("Unknown signing key")
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "token_use"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthError("Invalid token") from exc
        if claims.get("token_use") != "id":
            raise AuthError("An id token is required")
        return claims


_verifier: TokenVerifier | None = None
_verifier_lock = threading.Lock()


def auth_settings() -> dict[str, str]:
    pool = os.environ.get("COGNITO_USER_POOL_ID", "")
    return {
        "region": pool.split("_", 1)[0] if "_" in pool else os.environ.get("AWS_REGION", ""),
        "user_pool_id": pool,
        "client_id": os.environ.get("COGNITO_CLIENT_ID", ""),
        "domain": os.environ.get("COGNITO_DOMAIN", ""),
    }


def get_verifier() -> TokenVerifier:
    """Per-container verifier (and so per-container JWKS cache) built from the environment."""
    global _verifier
    settings = auth_settings()
    pool, client = settings["user_pool_id"], settings["client_id"]
    if not pool or not client:
        raise HTTPException(
            status_code=503,
            detail={"error": "Sign-in is not configured on this server", "code": "auth_not_configured"},
        )
    with _verifier_lock:
        if _verifier is None or (_verifier.user_pool_id, _verifier.client_id) != (pool, client):
            url = f"{issuer_for(pool)}/.well-known/jwks.json"
            _verifier = TokenVerifier(pool, client, JwksCache(lambda: _fetch_url_json(url)))
        return _verifier


def _unauthenticated(message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"error": message, "code": "unauthenticated"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_user(
    authorization: str | None = Header(default=None),
    verifier: TokenVerifier = Depends(get_verifier),
) -> dict[str, Any]:
    """FastAPI dependency: ``{"user_id", "email", "name", "username"}`` of the verified caller, else 401."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthenticated("Sign-in required")
    try:
        claims = verifier.verify(token.strip())
    except AuthError as exc:
        raise _unauthenticated(exc.message) from None
    except JwksUnavailable:
        raise HTTPException(
            status_code=503,
            detail={"error": "Sign-in keys are temporarily unavailable", "code": "auth_unavailable"},
        ) from None
    return {
        "user_id": claims["sub"],
        "email": claims.get("email"),
        "name": claims.get("name"),
        # Cognito's username (the sub for email users, "google_<id>" for Google users): AdminDeleteUser needs it.
        "username": claims.get("cognito:username") or claims["sub"],
    }

def optional_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | None:
    """FastAPI dependency: user dict if valid Bearer token, None if no token, 401 if invalid token."""
    if not authorization or not authorization.strip():
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthenticated("Sign-in required")
    if request is not None and get_verifier in request.app.dependency_overrides:
        verifier = request.app.dependency_overrides[get_verifier]()
    else:
        verifier = get_verifier()
    try:
        claims = verifier.verify(token.strip())
    except AuthError as exc:
        raise _unauthenticated(exc.message) from None
    except JwksUnavailable:
        raise HTTPException(
            status_code=503,
            detail={"error": "Sign-in keys are temporarily unavailable", "code": "auth_unavailable"},
        ) from None
    return {
        "user_id": claims["sub"],
        "email": claims.get("email"),
        "name": claims.get("name"),
        "username": claims.get("cognito:username") or claims["sub"],
    }


require_user.optional = optional_user
