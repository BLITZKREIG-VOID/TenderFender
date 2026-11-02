"""
User accounts: profile, daily usage counters, per-user items in DynamoDB (SoT §13 D38).

Table ``USERS_TABLE`` (PK ``pk`` = ``USER#<sub>``, SK ``sk``) items:
``PROFILE``, ``USAGE#<yyyy-mm-dd>`` (counters, TTL ``expires_at`` 3 days), ``TENDER#<uuid>``, ``REGEN#<tender_id>``.
Non-usage items keep their payload as one JSON string attribute ``data`` (< ``MAX_ITEM_BYTES``).

Dependencies (override in tests via ``app.dependency_overrides``):
``users_store`` -> ``UsersStore`` over the DynamoDB table; ``cognito_admin`` -> ``CognitoAdmin``.
boto3 is provided by the Lambda Python runtime and imported only when these build real clients.

``consume(user_id, kind, store)`` is the daily-limit gate for the LLM routes: one conditional atomic
``ADD`` per call; over the limit it raises 429 ``{"error", "code": "daily_limit", "limit", "reset_at"}``.
"""

from __future__ import annotations

import functools
import json
import os
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from api.auth import auth_settings, require_user

KINDS = ("regen", "compile", "chat", "detect")
DEFAULT_DAILY_LIMITS = {"regen": 10, "compile": 5, "chat": 30, "detect": 20}
DEFAULT_GLOBAL_LIMITS = {"llm_total": 150, "detect_total": 300}
GLOBAL_PK = "GLOBAL"
USAGE_TTL_DAYS = 3
TOMBSTONE_TTL_SECONDS = 7200  # 2 hours
MAX_ITEM_BYTES = 100_000
MAX_USER_TENDERS = 20
ROLES = ("procurement_officer", "auditor_vigilance", "journalist", "researcher_student",
         "vendor_contractor", "citizen", "other")
ORG_TYPES = ("central_govt", "state_govt", "psu", "private", "ngo_media", "academic", "individual")
# 28 states and 8 union territories, official names, plus "outside_india".
STATES = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
    "outside_india",
)
PURPOSES = ("check_my_tenders", "audit_oversight", "research", "learning", "other")
EXPERIENCE = ("new", "some", "expert")


class ItemTooLarge(ValueError):
    pass


class DailyLimitExceeded(Exception):
    pass


class GlobalDailyLimitExceeded(Exception):
    pass


class UserDeletedError(Exception):
    pass


class TenderLimitExceeded(Exception):
    pass

def _pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _is_conditional_failure(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return isinstance(response, dict) and response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def _is_transaction_canceled(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return isinstance(response, dict) and response.get("Error", {}).get("Code") in (
        "TransactionCanceledException",
        "ConditionalCheckFailedException",
    )


def _serialize(val: Any) -> dict[str, Any]:
    try:
        from boto3.dynamodb.types import TypeSerializer
        return TypeSerializer().serialize(val)
    except Exception:
        if isinstance(val, str):
            return {"S": val}
        if isinstance(val, (int, float)):
            return {"N": str(val)}
        if isinstance(val, bool):
            return {"BOOL": val}
        if val is None:
            return {"NULL": True}
        return {"S": str(val)}


def _serialize_map(d: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize(v) for k, v in d.items()}


def check_llm_enabled() -> None:
    """Kill switch helper: raises 503 llm_disabled if LLM_FEATURES_ENABLED is false."""
    val = os.environ.get("LLM_FEATURES_ENABLED", "true").lower()
    if val not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=503,
            detail={"error": "LLM features are currently disabled", "code": "llm_disabled"},
        )

def daily_limits() -> dict[str, int]:
    return {k: int(os.environ.get(f"DAILY_LIMIT_{k.upper()}", v)) for k, v in DEFAULT_DAILY_LIMITS.items()}


def global_daily_limits() -> dict[str, int]:
    return {
        "llm_total": int(os.environ.get("GLOBAL_DAILY_LIMIT_LLM", DEFAULT_GLOBAL_LIMITS["llm_total"])),
        "detect_total": int(os.environ.get("GLOBAL_DAILY_LIMIT_DETECT", DEFAULT_GLOBAL_LIMITS["detect_total"])),
    }

def _utc_day(now: datetime) -> date:
    return now.astimezone(UTC).date()


def _next_midnight(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=UTC)


class UsersStore:
    """Per-user items in one DynamoDB table (any object with the boto3 ``Table`` resource methods)."""

    def __init__(self, table: Any, client: Any = None):
        self.table = table
        self.client = client
        self.table_name = getattr(table, "name", "") or os.environ.get("USERS_TABLE", "users")

    def write_tombstone(self, user_id: str, ttl_seconds: int = TOMBSTONE_TTL_SECONDS) -> None:
        expires_at = int(datetime.now(UTC).timestamp() + ttl_seconds)
        self.table.put_item(Item={
            "pk": _pk(user_id),
            "sk": "DELETED",
            "expires_at": expires_at,
            "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        })

    def is_deleted(self, user_id: str) -> bool:
        item = self.table.get_item(Key={"pk": _pk(user_id), "sk": "DELETED"}).get("Item")
        return item is not None

    # ── JSON payload items (PROFILE, TENDER#, REGEN#) ────────────────────────
    def get_item(self, user_id: str, sk: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key={"pk": _pk(user_id), "sk": sk}).get("Item")
        return None if item is None else json.loads(item["data"])

    def put_item(self, user_id: str, sk: str, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(body.encode("utf-8")) > MAX_ITEM_BYTES:
            raise ItemTooLarge(f"item {sk.split('#', 1)[0]} exceeds {MAX_ITEM_BYTES} bytes")
        raw_item = {
            "pk": _pk(user_id),
            "sk": sk,
            "data": body,
            "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if hasattr(self.table, "transact_write_items"):
            try:
                self.table.transact_write_items(TransactItems=[
                    {
                        "ConditionCheck": {
                            "TableName": self.table_name,
                            "Key": {"pk": _pk(user_id), "sk": "DELETED"},
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": raw_item,
                        }
                    },
                ])
            except Exception as exc:
                if _is_transaction_canceled(exc) or _is_conditional_failure(exc):
                    raise UserDeletedError(f"User {user_id} has been deleted") from exc
                raise
        else:
            client = getattr(getattr(self.table, "meta", None), "client", None)
            if client is not None and hasattr(client, "transact_write_items"):
                try:
                    client.transact_write_items(TransactItems=[
                        {
                            "ConditionCheck": {
                                "TableName": self.table_name,
                                "Key": {"pk": {"S": _pk(user_id)}, "sk": {"S": "DELETED"}},
                                "ConditionExpression": "attribute_not_exists(pk)",
                            }
                        },
                        {
                            "Put": {
                                "TableName": self.table_name,
                                "Item": _serialize_map(raw_item),
                            }
                        },
                    ])
                except Exception as exc:
                    if _is_transaction_canceled(exc) or _is_conditional_failure(exc):
                        raise UserDeletedError(f"User {user_id} has been deleted") from exc
                    raise
            else:
                if self.is_deleted(user_id):
                    raise UserDeletedError(f"User {user_id} has been deleted")
                self.table.put_item(Item=raw_item)
    def delete_item(self, user_id: str, sk: str) -> bool:
        resp = self.table.delete_item(Key={"pk": _pk(user_id), "sk": sk}, ReturnValues="ALL_OLD")
        return bool(resp.get("Attributes"))

    def _query(self, user_id: str, sk_prefix: str = "", **extra: Any):
        expr_vals: dict[str, Any] = {":pk": _pk(user_id)}
        if sk_prefix:
            key_cond = "pk = :pk AND begins_with(sk, :prefix)"
            expr_vals[":prefix"] = sk_prefix
        else:
            key_cond = "pk = :pk"
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": key_cond,
            "ExpressionAttributeValues": expr_vals,
            **extra,
        }
        while True:
            page = self.table.query(**kwargs)
            yield page
            if "LastEvaluatedKey" not in page:
                return
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    def query_items(self, user_id: str, sk_prefix: str) -> list[dict[str, Any]]:
        return [json.loads(item["data"]) for page in self._query(user_id, sk_prefix) for item in page.get("Items", [])]

    def count_items(self, user_id: str, sk_prefix: str) -> int:
        return sum(int(page.get("Count", 0)) for page in self._query(user_id, sk_prefix, Select="COUNT"))

    def delete_all(self, user_id: str) -> int:
        """Delete every item of the user, whatever its kind, skipping DELETED tombstone. Returns the number deleted."""
        keys = [
            {"pk": item["pk"], "sk": item["sk"]}
            for page in self._query(user_id, "", ProjectionExpression="pk, sk")
            for item in page.get("Items", [])
            if item["sk"] != "DELETED"
        ]
        if keys:
            with self.table.batch_writer() as batch:
                for key in keys:
                    batch.delete_item(Key=key)
        return len(keys)

    # ── Tender items, summaries, and counter ─────────────────────────────────
    def get_tender_count(self, user_id: str) -> int:
        item = self.table.get_item(Key={"pk": _pk(user_id), "sk": "TENDERCOUNT"}).get("Item")
        return int(item.get("count", 0)) if item else 0

    def increment_tender_count(self, user_id: str, limit: int = MAX_USER_TENDERS) -> int:
        try:
            resp = self.table.update_item(
                Key={"pk": _pk(user_id), "sk": "TENDERCOUNT"},
                UpdateExpression="ADD #c :one",
                ConditionExpression="attribute_not_exists(#c) OR #c < :limit",
                ExpressionAttributeNames={"#c": "count"},
                ExpressionAttributeValues={":one": 1, ":limit": limit},
                ReturnValues="UPDATED_NEW",
            )
            return int(resp["Attributes"]["count"])
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise TenderLimitExceeded(f"User {user_id} has reached maximum of {limit} tenders") from None
            raise

    def decrement_tender_count(self, user_id: str) -> int:
        try:
            resp = self.table.update_item(
                Key={"pk": _pk(user_id), "sk": "TENDERCOUNT"},
                UpdateExpression="ADD #c :minus_one",
                ConditionExpression="attribute_not_exists(#c) OR #c > :zero",
                ExpressionAttributeNames={"#c": "count"},
                ExpressionAttributeValues={":minus_one": -1, ":zero": 0},
                ReturnValues="UPDATED_NEW",
            )
            return int(resp["Attributes"]["count"])
        except Exception as exc:
            if _is_conditional_failure(exc):
                return 0
            raise

    def put_tender(self, user_id: str, tender_id: str, data: dict[str, Any], summary: dict[str, Any]) -> None:
        if self.is_deleted(user_id):
            raise UserDeletedError(f"User {user_id} has been deleted")
        self.increment_tender_count(user_id)
        try:
            self.put_item(user_id, f"TENDER#{tender_id}", data)
            self.put_item(user_id, f"TENDERSUM#{tender_id}", summary)
        except Exception:
            self.decrement_tender_count(user_id)
            raise

    def delete_tender(self, user_id: str, tender_id: str) -> bool:
        deleted_main = self.delete_item(user_id, f"TENDER#{tender_id}")
        self.delete_item(user_id, f"TENDERSUM#{tender_id}")
        if deleted_main:
            self.decrement_tender_count(user_id)
        return deleted_main

    def list_tender_summaries(self, user_id: str) -> list[dict[str, Any]]:
        return self.query_items(user_id, "TENDERSUM#")

    # ── Daily usage counters (USAGE#<yyyy-mm-dd>) ────────────────────────────
    def get_usage(self, user_id: str, day: date) -> dict[str, int]:
        item = self.table.get_item(Key={"pk": _pk(user_id), "sk": f"USAGE#{day.isoformat()}"}).get("Item") or {}
        return {k: int(item.get(k, 0)) for k in KINDS}

    def increment_usage(self, user_id: str, kind: str, limit: int, day: date) -> int:
        """Atomically add 1 to today's ``kind`` counter unless it already reached ``limit``."""
        if limit <= 0:  # attribute_not_exists would otherwise admit the first call of the day
            raise DailyLimitExceeded(kind)
        expires_at = int(datetime.combine(day + timedelta(days=USAGE_TTL_DAYS), time.min, tzinfo=UTC).timestamp())
        try:
            resp = self.table.update_item(
                Key={"pk": _pk(user_id), "sk": f"USAGE#{day.isoformat()}"},
                UpdateExpression="SET expires_at = if_not_exists(expires_at, :exp) ADD #k :one",
                ConditionExpression="attribute_not_exists(#k) OR #k < :limit",
                ExpressionAttributeNames={"#k": kind},
                ExpressionAttributeValues={":one": 1, ":limit": limit, ":exp": expires_at},
                ReturnValues="UPDATED_NEW",
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise DailyLimitExceeded(kind) from None
            raise
        return int(resp["Attributes"][kind])

    def increment_global_usage(self, counter_name: str, limit: int, day: date) -> int:
        """Atomically add 1 to today's global counter unless it already reached limit."""
        if limit <= 0:
            raise GlobalDailyLimitExceeded(counter_name)
        expires_at = int(datetime.combine(day + timedelta(days=USAGE_TTL_DAYS), time.min, tzinfo=UTC).timestamp())
        try:
            resp = self.table.update_item(
                Key={"pk": GLOBAL_PK, "sk": f"USAGE#{day.isoformat()}"},
                UpdateExpression="SET expires_at = if_not_exists(expires_at, :exp) ADD #k :one",
                ConditionExpression="attribute_not_exists(#k) OR #k < :limit",
                ExpressionAttributeNames={"#k": counter_name},
                ExpressionAttributeValues={":one": 1, ":limit": limit, ":exp": expires_at},
                ReturnValues="UPDATED_NEW",
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise GlobalDailyLimitExceeded(counter_name) from None
            raise
        return int(resp["Attributes"][counter_name])

    # ── Site AI monthly spend tracking (SPEND#<yyyy-mm>) ─────────────────────
    def get_site_ai_spend(self, month: str | None = None) -> int:
        """Return the month's spend in integer micro-dollars."""
        m = month or datetime.now(UTC).strftime("%Y-%m")
        item = self.table.get_item(Key={"pk": GLOBAL_PK, "sk": f"SPEND#{m}"}).get("Item") or {}
        return int(item.get("spend_micro_usd", 0))

    def record_site_ai_spend(self, cost_micro_usd: int, month: str | None = None) -> int:
        """Atomically add cost_micro_usd to the month's spend item."""
        if cost_micro_usd <= 0:
            return self.get_site_ai_spend(month)
        m = month or datetime.now(UTC).strftime("%Y-%m")
        resp = self.table.update_item(
            Key={"pk": GLOBAL_PK, "sk": f"SPEND#{m}"},
            UpdateExpression="ADD #s :cost",
            ExpressionAttributeNames={"#s": "spend_micro_usd"},
            ExpressionAttributeValues={":cost": cost_micro_usd},
            ReturnValues="UPDATED_NEW",
        )
        return int(resp["Attributes"]["spend_micro_usd"])


@functools.cache
def _dynamodb_table() -> Any:
    name = os.environ.get("USERS_TABLE", "")
    if not name:
        raise HTTPException(status_code=503, detail={"error": "User storage is not configured", "code": "store_not_configured"})
    import boto3  # provided by the Lambda Python runtime

    return boto3.resource("dynamodb").Table(name)


def users_store() -> UsersStore:
    """FastAPI dependency: the store over this container's (cached) DynamoDB table."""
    return UsersStore(_dynamodb_table())


class CognitoAdmin:
    def __init__(self, client: Any, user_pool_id: str):
        self.client = client
        self.user_pool_id = user_pool_id

    def delete_user(self, username: str) -> None:
        """AdminDeleteUser; an already deleted user is not an error (DELETE /api/me is retryable)."""
        try:
            self.client.admin_delete_user(UserPoolId=self.user_pool_id, Username=username)
        except Exception as exc:
            response = getattr(exc, "response", None)
            if isinstance(response, dict) and response.get("Error", {}).get("Code") == "UserNotFoundException":
                return
            raise


@functools.cache
def _cognito_client() -> Any:
    import boto3  # provided by the Lambda Python runtime

    return boto3.client("cognito-idp")


def cognito_admin() -> CognitoAdmin:
    pool = auth_settings()["user_pool_id"]
    if not pool:
        raise HTTPException(status_code=503, detail={"error": "Sign-in is not configured on this server", "code": "auth_not_configured"})
    return CognitoAdmin(_cognito_client(), pool)


def consume(user_id: str, kind: str, store: UsersStore | None = None, now: datetime | None = None) -> int:
    """Count one ``kind`` request against today's (UTC) limit; return the new count or raise 429.

    Pass the store from ``Depends(users_store)`` so dependency overrides apply.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown usage kind {kind!r}")
    store = store if store is not None else users_store()
    now = now or datetime.now(UTC)
    day = _utc_day(now)
    reset_at = _next_midnight(day)
    retry_after = str(max(1, int((reset_at - now).total_seconds())))

    limit = daily_limits()[kind]
    if limit <= 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Daily {kind} limit of {limit} reached; it resets at {reset_at.isoformat()}",
                "code": "daily_limit",
                "limit": limit,
                "reset_at": reset_at.isoformat(),
            },
            headers={"Retry-After": retry_after},
        ) from None

    # Global daily cap check
    global_counter = "detect_total" if kind == "detect" else "llm_total"
    global_limit = global_daily_limits().get(global_counter, 0)
    try:
        store.increment_global_usage(global_counter, global_limit, day)
    except GlobalDailyLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Global daily limit for {global_counter} reached ({global_limit}/day); it resets at {reset_at.isoformat()}",
                "code": "global_daily_limit",
                "limit": global_limit,
                "reset_at": reset_at.isoformat(),
            },
            headers={"Retry-After": retry_after},
        ) from None

    # Per-user daily cap check
    try:
        return store.increment_usage(user_id, kind, limit, day)
    except DailyLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Daily {kind} limit of {limit} reached; it resets at {reset_at.isoformat()}",
                "code": "daily_limit",
                "limit": limit,
                "reset_at": reset_at.isoformat(),
            },
            headers={"Retry-After": retry_after},
        ) from None

# ── Endpoints ────────────────────────────────────────────────────────────────

router = APIRouter()


class ProfileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal[ROLES]
    org_type: Literal[ORG_TYPES]
    state: Literal[STATES]
    purpose: Literal[PURPOSES]
    experience: Literal[EXPERIENCE]
    consent: StrictBool = Field(description="Must be true: the user agrees to the privacy note.")

    @field_validator("consent")
    @classmethod
    def _consent_given(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("consent must be true")
        return value


@router.get("/api/auth/config")
def auth_config() -> dict[str, str]:
    """Public: what the UI needs to start the PKCE sign-in. Empty strings when sign-in is not configured."""
    settings = auth_settings()
    return {**settings, "redirect_path": "/auth/callback"}


@router.get("/api/me")
def me(user: dict = Depends(require_user), store: UsersStore = Depends(users_store)) -> dict[str, Any]:
    day = _utc_day(datetime.now(UTC))
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "profile": store.get_item(user["user_id"], "PROFILE"),
        "usage": store.get_usage(user["user_id"], day),
        "limits": daily_limits(),
        "reset_at": _next_midnight(day).isoformat(),
    }


@router.put("/api/me/profile")
def put_profile(
    body: ProfileBody, user: dict = Depends(require_user), store: UsersStore = Depends(users_store)
) -> dict[str, Any]:
    profile = {**body.model_dump(), "updated_at": datetime.now(UTC).isoformat(timespec="seconds")}
    try:
        store.put_item(user["user_id"], "PROFILE", profile)
    except UserDeletedError:
        raise HTTPException(
            status_code=403,
            detail={"error": "User account has been deleted", "code": "account_deleted"},
        ) from None
    return profile


@router.delete("/api/me", status_code=204)
def delete_me(
    user: dict = Depends(require_user),
    store: UsersStore = Depends(users_store),
    admin: CognitoAdmin = Depends(cognito_admin),
) -> Response:
    """Delete every stored item of the caller, then the Cognito user. Safe to retry."""
    store.write_tombstone(user["user_id"], ttl_seconds=TOMBSTONE_TTL_SECONDS)
    store.delete_all(user["user_id"])
    try:
        admin.delete_user(user["username"])
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Failed to delete user in identity provider; data was removed and deletion is safe to retry",
                "code": "partial_delete_retry_safe",
            },
        ) from exc
    store.delete_all(user["user_id"])
    return Response(status_code=204)
