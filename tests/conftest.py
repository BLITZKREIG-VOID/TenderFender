"""Temporary stand-ins for api.auth / api.users (owned by feat/accounts-auth).

api.main includes api.llm_routes, which imports both modules. Until feat/accounts-auth merges they do not exist on
feat/byok-llm, so minimal stand-ins are installed ONLY when the real modules are absent; the BYOK tests override
every dependency themselves, and the stand-ins only refuse. Delete this file once accounts-auth is merged.
"""

import importlib.util
import sys
import types

if importlib.util.find_spec("api.auth") is None:
    from fastapi import HTTPException

    def _unauthenticated():
        raise HTTPException(401, detail={"error": "Sign in required.", "code": "unauthenticated"})

    def _no_store():
        raise HTTPException(503, detail={"error": "users table not configured", "code": "unavailable"})

    def _consume(user_id, kind, store=None):
        raise HTTPException(503, detail={"error": "usage counters not configured", "code": "unavailable"})

    class _ItemTooLarge(ValueError):
        pass

    _auth = types.ModuleType("api.auth")
    _auth.require_user = _unauthenticated
    _users = types.ModuleType("api.users")
    _users.users_store = _no_store
    _users.consume = _consume
    _users.ItemTooLarge = _ItemTooLarge
    _users.MAX_USER_TENDERS = 20
    sys.modules["api.auth"] = _auth
    sys.modules["api.users"] = _users
