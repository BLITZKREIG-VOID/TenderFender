"""
Accounts API: Cognito id-token verification, profile, account deletion, daily limits (SoT §13 D38).

No AWS and no network: tokens are signed with an RSA key generated here, the JWKS is served from memory,
and DynamoDB / Cognito are fakes injected through FastAPI dependency overrides.
"""

import os
import time
from datetime import UTC, datetime
from decimal import Decimal

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

os.environ["MOCK"] = "1"

from api import auth, users  # noqa: E402
from api.main import app  # noqa: E402

POOL_ID = "ap-south-1_TestPool1"
CLIENT_ID = "testclientid123"
ISSUER = f"https://cognito-idp.ap-south-1.amazonaws.com/{POOL_ID}"
KID = "test-kid-1"


def _rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SIGNING_KEY = _rsa_key()
OTHER_KEY = _rsa_key()


def _jwks(*pairs):
    keys = []
    for kid, key in pairs:
        jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
        keys.append({**jwk, "kid": kid, "alg": "RS256", "use": "sig"})
    return {"keys": keys}


def _pem(key):
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())


def make_token(*, key=SIGNING_KEY, kid=KID, sub="user-1", **overrides):
    now = int(time.time())
    claims = {
        "sub": sub,
        "aud": CLIENT_ID,
        "iss": ISSUER,
        "token_use": "id",
        "iat": now,
        "exp": now + 3600,
        "email": f"{sub}@example.org",
        "name": "Test User",
        "cognito:username": f"google_{sub}",
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, _pem(key), algorithm="RS256", headers={"kid": kid})


class CountingFetch:
    def __init__(self, jwks):
        self.jwks = jwks
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.jwks


def make_verifier(fetch=None):
    fetch = fetch or CountingFetch(_jwks((KID, SIGNING_KEY)))
    return auth.TokenVerifier(POOL_ID, CLIENT_ID, auth.JwksCache(fetch))


# ── Fakes for DynamoDB and Cognito ───────────────────────────────────────────


class FakeClientError(Exception):
    """Shape of botocore's ClientError: ``.response["Error"]["Code"]``."""

    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeBatchWriter:
    def __init__(self, table):
        self.table = table

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def delete_item(self, Key):
        self.table.items.pop((Key["pk"], Key["sk"]), None)


class FakeTable:
    """In-memory stand-in for the boto3 Table resource, covering exactly the calls api/users.py makes."""

    PAGE_SIZE = 2  # small, so query pagination is exercised

    def __init__(self):
        self.items = {}

    def get_item(self, Key):
        item = self.items.get((Key["pk"], Key["sk"]))
        return {"Item": dict(item)} if item is not None else {}

    def put_item(self, Item):
        self.items[(Item["pk"], Item["sk"])] = dict(Item)

    def delete_item(self, Key, ReturnValues="NONE"):
        old = self.items.pop((Key["pk"], Key["sk"]), None)
        return {"Attributes": old} if old is not None and ReturnValues == "ALL_OLD" else {}

    def query(self, KeyConditionExpression, ExpressionAttributeValues, Select=None,
              ProjectionExpression=None, ExclusiveStartKey=None):
        assert KeyConditionExpression == "pk = :pk AND begins_with(sk, :prefix)"
        pk, prefix = ExpressionAttributeValues[":pk"], ExpressionAttributeValues[":prefix"]
        matched = sorted((k, v) for k, v in self.items.items() if k[0] == pk and k[1].startswith(prefix))
        if ExclusiveStartKey is not None:
            start = (ExclusiveStartKey["pk"], ExclusiveStartKey["sk"])
            matched = [(k, v) for k, v in matched if k > start]
        page, rest = matched[: self.PAGE_SIZE], matched[self.PAGE_SIZE:]
        out = {"Count": len(page)}
        if Select != "COUNT":
            if ProjectionExpression == "pk, sk":
                out["Items"] = [{"pk": k[0], "sk": k[1]} for k, _ in page]
            else:
                out["Items"] = [dict(v) for _, v in page]
        if rest:
            out["LastEvaluatedKey"] = {"pk": page[-1][0][0], "sk": page[-1][0][1]}
        return out

    def update_item(self, Key, UpdateExpression, ConditionExpression, ExpressionAttributeNames,
                    ExpressionAttributeValues, ReturnValues):
        assert UpdateExpression == "SET expires_at = if_not_exists(expires_at, :exp) ADD #k :one"
        assert ConditionExpression == "attribute_not_exists(#k) OR #k < :limit"
        assert ReturnValues == "UPDATED_NEW"
        attr = ExpressionAttributeNames["#k"]
        values = ExpressionAttributeValues
        item = self.items.setdefault((Key["pk"], Key["sk"]), {"pk": Key["pk"], "sk": Key["sk"]})
        if attr in item and not item[attr] < values[":limit"]:
            raise FakeClientError("ConditionalCheckFailedException")
        item.setdefault("expires_at", Decimal(values[":exp"]))
        item[attr] = Decimal(item.get(attr, 0)) + values[":one"]
        return {"Attributes": {attr: item[attr], "expires_at": item["expires_at"]}}

    def batch_writer(self):
        return FakeBatchWriter(self)


class FakeCognitoClient:
    def __init__(self, missing=False):
        self.deleted = []
        self.missing = missing

    def admin_delete_user(self, UserPoolId, Username):
        if self.missing:
            raise FakeClientError("UserNotFoundException")
        self.deleted.append((UserPoolId, Username))


@pytest.fixture
def env(monkeypatch):
    table = FakeTable()
    cognito = FakeCognitoClient()
    verifier = make_verifier()
    app.dependency_overrides[auth.get_verifier] = lambda: verifier
    app.dependency_overrides[users.users_store] = lambda: users.UsersStore(table)
    app.dependency_overrides[users.cognito_admin] = lambda: users.CognitoAdmin(cognito, POOL_ID)
    for kind in users.KINDS:
        monkeypatch.delenv(f"DAILY_LIMIT_{kind.upper()}", raising=False)
    try:
        yield {"client": TestClient(app), "table": table, "cognito": cognito}
    finally:
        app.dependency_overrides.clear()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


VALID_PROFILE = {
    "role": "journalist",
    "org_type": "ngo_media",
    "state": "Karnataka",
    "purpose": "research",
    "experience": "some",
    "consent": True,
}


# ── JWT verification ─────────────────────────────────────────────────────────


def test_valid_token_is_accepted():
    claims = make_verifier().verify(make_token())
    assert claims["sub"] == "user-1" and claims["token_use"] == "id"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"exp": int(time.time()) - 10, "iat": int(time.time()) - 3700}, "Token expired"),
        ({"aud": "someone-elses-client"}, "Invalid token"),
        ({"iss": "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_OtherPool"}, "Invalid token"),
        ({"token_use": "access"}, "An id token is required"),
        ({"exp": None}, "Invalid token"),
    ],
    ids=["expired", "wrong-aud", "wrong-issuer", "access-token", "no-exp"],
)
def test_bad_claims_are_rejected(overrides, message):
    with pytest.raises(auth.AuthError) as err:
        make_verifier().verify(make_token(**overrides))
    assert err.value.message == message


def test_signature_from_another_key_is_rejected():
    with pytest.raises(auth.AuthError, match="Invalid token"):
        make_verifier().verify(make_token(key=OTHER_KEY))


def test_hs256_token_is_rejected():
    token = jwt.encode({"sub": "x"}, "a-shared-secret-of-sufficient-length-32b", algorithm="HS256", headers={"kid": KID})
    with pytest.raises(auth.AuthError, match="Unsupported token"):
        make_verifier().verify(token)


def test_jwks_is_cached_and_unknown_kid_refresh_is_rate_limited():
    fetch = CountingFetch(_jwks((KID, SIGNING_KEY)))
    clock = [1000.0]
    verifier = auth.TokenVerifier(POOL_ID, CLIENT_ID, auth.JwksCache(fetch, clock=lambda: clock[0]))
    for _ in range(3):
        verifier.verify(make_token())
    assert fetch.calls == 1

    # Unknown kid: refetched once, then not again within the refresh window.
    for _ in range(3):
        with pytest.raises(auth.AuthError, match="Unknown signing key"):
            verifier.verify(make_token(key=OTHER_KEY, kid="rotated"))
    assert fetch.calls == 1  # the first fetch is younger than JWKS_MIN_REFRESH_SECONDS

    # After the window, a rotated key is picked up.
    fetch.jwks = _jwks((KID, SIGNING_KEY), ("rotated", OTHER_KEY))
    clock[0] += auth.JWKS_MIN_REFRESH_SECONDS
    assert verifier.verify(make_token(key=OTHER_KEY, kid="rotated"))["sub"] == "user-1"
    assert fetch.calls == 2


def test_issuer_is_derived_from_pool_id():
    assert auth.issuer_for(POOL_ID) == ISSUER


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer "}, bearer("not.a.jwt")])
def test_me_without_valid_token_is_401(env, headers):
    resp = env["client"].get("/api/me", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "unauthenticated"
    assert resp.headers["www-authenticate"] == "Bearer"


def test_expired_token_is_401_and_not_echoed(env):
    token = make_token(exp=int(time.time()) - 10, iat=int(time.time()) - 3700)
    resp = env["client"].get("/api/me", headers=bearer(token))
    assert resp.status_code == 401
    assert resp.json()["detail"] == {"error": "Token expired", "code": "unauthenticated"}
    assert token not in resp.text


def test_unconfigured_server_reports_503(monkeypatch):
    monkeypatch.delenv("COGNITO_USER_POOL_ID", raising=False)
    monkeypatch.delenv("COGNITO_CLIENT_ID", raising=False)
    resp = TestClient(app).get("/api/me", headers=bearer(make_token()))
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "auth_not_configured"


# ── Public auth config ───────────────────────────────────────────────────────


def test_auth_config_is_public(monkeypatch):
    monkeypatch.setenv("COGNITO_USER_POOL_ID", POOL_ID)
    monkeypatch.setenv("COGNITO_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("COGNITO_DOMAIN", "tf-test.auth.ap-south-1.amazoncognito.com")
    resp = TestClient(app).get("/api/auth/config")
    assert resp.status_code == 200
    assert resp.json() == {
        "region": "ap-south-1",
        "user_pool_id": POOL_ID,
        "client_id": CLIENT_ID,
        "domain": "tf-test.auth.ap-south-1.amazoncognito.com",
        "redirect_path": "/auth/callback",
    }


# ── Profile ──────────────────────────────────────────────────────────────────


def test_profile_roundtrip_and_me(env):
    client = env["client"]
    me = client.get("/api/me", headers=bearer(make_token())).json()
    assert me["user_id"] == "user-1" and me["email"] == "user-1@example.org"
    assert me["profile"] is None
    assert me["usage"] == {"regen": 0, "compile": 0, "chat": 0}
    assert me["limits"] == {"regen": 20, "compile": 10, "chat": 50}

    resp = client.put("/api/me/profile", json=VALID_PROFILE, headers=bearer(make_token()))
    assert resp.status_code == 200
    assert {k: resp.json()[k] for k in VALID_PROFILE} == VALID_PROFILE

    me = client.get("/api/me", headers=bearer(make_token())).json()
    assert {k: me["profile"][k] for k in VALID_PROFILE} == VALID_PROFILE
    assert set(me["profile"]) == set(VALID_PROFILE) | {"updated_at"}


@pytest.mark.parametrize(
    "change",
    [
        {"role": "spy"},
        {"org_type": "government"},
        {"state": "karnataka"},
        {"state": "Atlantis"},
        {"purpose": "fun"},
        {"experience": "guru"},
        {"unexpected": "field"},
    ],
)
def test_profile_rejects_unknown_values(env, change):
    resp = env["client"].put("/api/me/profile", json={**VALID_PROFILE, **change}, headers=bearer(make_token()))
    assert resp.status_code == 422
    assert env["table"].items == {}


@pytest.mark.parametrize("consent", [False, "true", 1, None])
def test_profile_requires_consent_true(env, consent):
    body = {**VALID_PROFILE, "consent": consent}
    resp = env["client"].put("/api/me/profile", json=body, headers=bearer(make_token()))
    assert resp.status_code == 422
    assert env["table"].items == {}


def test_profile_requires_consent_field(env):
    body = {k: v for k, v in VALID_PROFILE.items() if k != "consent"}
    resp = env["client"].put("/api/me/profile", json=body, headers=bearer(make_token()))
    assert resp.status_code == 422


def test_profile_accepts_outside_india_and_union_territory(env):
    for state in ("outside_india", "Dadra and Nagar Haveli and Daman and Diu"):
        resp = env["client"].put("/api/me/profile", json={**VALID_PROFILE, "state": state}, headers=bearer(make_token()))
        assert resp.status_code == 200, resp.text
    assert len(users.STATES) == 28 + 8 + 1


def test_profile_requires_auth(env):
    resp = env["client"].put("/api/me/profile", json=VALID_PROFILE)
    assert resp.status_code == 401


# ── Account deletion ─────────────────────────────────────────────────────────


def test_delete_me_removes_every_item_and_the_cognito_user(env):
    table = env["table"]
    store = users.UsersStore(table)
    store.put_item("user-1", "PROFILE", VALID_PROFILE)
    for i in range(3):
        store.put_item("user-1", f"TENDER#{i}", {"title": f"t{i}"})
    store.put_item("user-1", "REGEN#T-001", {"reasoning": "r"})
    users.consume("user-1", "chat", store)
    store.put_item("user-2", "PROFILE", VALID_PROFILE)
    assert sum(1 for pk, _ in table.items if pk == "USER#user-1") == 6

    resp = env["client"].delete("/api/me", headers=bearer(make_token()))
    assert resp.status_code == 204
    assert resp.content == b""
    assert [k for k in table.items if k[0] == "USER#user-1"] == []
    assert list(table.items) == [("USER#user-2", "PROFILE")]
    assert env["cognito"].deleted == [(POOL_ID, "google_user-1")]


def test_delete_me_is_retryable_when_cognito_user_is_gone(env):
    app.dependency_overrides[users.cognito_admin] = lambda: users.CognitoAdmin(FakeCognitoClient(missing=True), POOL_ID)
    resp = env["client"].delete("/api/me", headers=bearer(make_token()))
    assert resp.status_code == 204


def test_delete_me_requires_auth(env):
    users.UsersStore(env["table"]).put_item("user-1", "PROFILE", VALID_PROFILE)
    assert env["client"].delete("/api/me").status_code == 401
    assert len(env["table"].items) == 1


# ── Store items and daily limits ─────────────────────────────────────────────


def test_store_items_crud_count_and_size_limit(env):
    store = users.UsersStore(env["table"])
    for i in range(5):
        store.put_item("u", f"TENDER#{i}", {"n": i, "score": 0.5})
    store.put_item("u", "REGEN#T-001", {"x": 1})
    assert store.count_items("u", "TENDER#") == 5
    assert [d["n"] for d in store.query_items("u", "TENDER#")] == [0, 1, 2, 3, 4]
    assert store.get_item("u", "TENDER#3") == {"n": 3, "score": 0.5}
    assert store.delete_item("u", "TENDER#3") is True
    assert store.delete_item("u", "TENDER#3") is False
    assert store.get_item("u", "TENDER#3") is None
    with pytest.raises(users.ItemTooLarge):
        store.put_item("u", "TENDER#big", {"text": "x" * users.MAX_ITEM_BYTES})


def test_consume_counts_with_ttl_then_429(env, monkeypatch):
    monkeypatch.setenv("DAILY_LIMIT_CHAT", "2")
    store = users.UsersStore(env["table"])
    now = datetime(2026, 11, 1, 18, 30, tzinfo=UTC)
    assert users.consume("u", "chat", store, now=now) == 1
    assert users.consume("u", "chat", store, now=now) == 2
    with pytest.raises(HTTPException) as err:
        users.consume("u", "chat", store, now=now)
    assert err.value.status_code == 429
    assert err.value.detail["code"] == "daily_limit"
    assert err.value.detail["limit"] == 2
    assert err.value.detail["reset_at"] == "2026-11-02T00:00:00+00:00"
    assert err.value.headers["Retry-After"] == str(5 * 3600 + 30 * 60)

    item = env["table"].items[("USER#u", "USAGE#2026-11-01")]
    assert item["chat"] == 2  # the rejected call did not count
    assert item["expires_at"] == int(datetime(2026, 11, 4, tzinfo=UTC).timestamp())
    # Other kinds and the next UTC day have their own counters.
    assert users.consume("u", "regen", store, now=now) == 1
    assert users.consume("u", "chat", store, now=datetime(2026, 11, 2, 0, 0, 1, tzinfo=UTC)) == 1


def test_zero_limit_blocks_the_first_call(env, monkeypatch):
    monkeypatch.setenv("DAILY_LIMIT_COMPILE", "0")
    with pytest.raises(HTTPException) as err:
        users.consume("u", "compile", users.UsersStore(env["table"]))
    assert err.value.status_code == 429 and err.value.detail["limit"] == 0
    assert env["table"].items == {}


def test_consume_rejects_unknown_kind(env):
    with pytest.raises(ValueError):
        users.consume("u", "images", users.UsersStore(env["table"]))


def test_daily_limit_429_response_and_me_usage(env, monkeypatch):
    """An LLM-style route gated by consume() answers 429 with the documented body once over the limit."""
    monkeypatch.setenv("DAILY_LIMIT_REGEN", "1")
    gated = FastAPI()

    @gated.post("/gated")
    def gated_route(user: dict = Depends(auth.require_user), store: users.UsersStore = Depends(users.users_store)):
        return {"count": users.consume(user["user_id"], "regen", store)}

    gated.dependency_overrides = app.dependency_overrides
    client = TestClient(gated)
    assert client.post("/gated", headers=bearer(make_token())).json() == {"count": 1}
    resp = client.post("/gated", headers=bearer(make_token()))
    assert resp.status_code == 429
    detail = resp.json()["detail"]
    assert detail["code"] == "daily_limit" and detail["limit"] == 1
    assert datetime.fromisoformat(detail["reset_at"]) > datetime.now(UTC)
    assert "retry-after" in resp.headers

    me = env["client"].get("/api/me", headers=bearer(make_token())).json()
    assert me["usage"]["regen"] == 1 and me["limits"]["regen"] == 1
