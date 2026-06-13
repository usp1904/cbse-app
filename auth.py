"""Supabase Auth — JWT-based authentication for FastAPI.

Requires env vars:
  SUPABASE_URL        — https://xxxxx.supabase.co
  SUPABASE_SERVICE_KEY — service_role key (backend admin)
  SUPABASE_ANON_KEY   — anon/public key (JWT verification)

Usage:
  from auth import require_user, get_current_user

  @app.get("/profile")
  async def profile(user: dict = Depends(require_user)):
      return user
"""

import os
import json
import logging
import urllib.request
from typing import Optional

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

log = logging.getLogger("cbse.auth")

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
_SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

_supabase_client = None
_security_scheme = HTTPBearer(auto_error=False)


def _get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if not _SUPABASE_URL or not _SUPABASE_SERVICE_KEY:
        log.warning("Supabase not configured: set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(_SUPABASE_URL, _SUPABASE_SERVICE_KEY)
        log.info("Supabase client initialized (DB ready)")
        return _supabase_client
    except Exception as e:
        log.error("Failed to init Supabase client: %s", e)
        return None


def _supabase_headers(use_service_role=False):
    key = _SUPABASE_SERVICE_KEY if use_service_role else _SUPABASE_ANON_KEY
    return {
        "Content-Type": "application/json",
        "apikey": key,
    }


def is_configured() -> bool:
    return bool(_SUPABASE_URL and _SUPABASE_SERVICE_KEY and _SUPABASE_ANON_KEY)


def _extract_token(request: Request, credentials) -> Optional[str]:
    token = None
    if credentials:
        token = credentials.credentials
    if not token and request:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif request.cookies.get("access_token"):
            token = request.cookies["access_token"]
    return token


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security_scheme),
) -> Optional[dict]:
    """Extract authenticated user from JWT via Supabase. Returns None if not authenticated."""
    token = _extract_token(request, credentials)
    if not token:
        return None

    try:
        req = urllib.request.Request(
            f"{_SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": _SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data and data.get("id"):
                return {
                    "id": data["id"],
                    "email": data.get("email", ""),
                    "username": (data.get("user_metadata") or {}).get("username", data.get("email", "")),
                    "aud": data.get("aud", ""),
                    "role": data.get("role", ""),
                }
    except urllib.error.HTTPError as e:
        if e.code != 401:
            log.warning("Supabase user fetch failed: %s", e.code)
    except Exception as e:
        log.warning("JWT verification failed: %s", e)
    return None


async def require_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security_scheme),
) -> dict:
    """Require authenticated user. Returns 401 if not authenticated."""
    user = await get_current_user(request, credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def signup(email: str, password: str, username: str = "") -> dict:
    """Register a new user via Supabase Auth (admin API — no email confirmation needed)."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    payload = json.dumps({
        "email": email,
        "password": password,
        "user_metadata": {"username": username or email.split("@")[0]},
        "email_confirm": True,
    }).encode()
    req = urllib.request.Request(
        f"{_SUPABASE_URL}/auth/v1/admin/users",
        data=payload,
        headers={
            **_supabase_headers(use_service_role=True),
            "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {"success": True, "user_id": data["id"], "email": data["email"]}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def login(email: str, password: str) -> dict:
    """Authenticate user via Supabase Auth. Returns session with JWT."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    payload = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{_SUPABASE_URL}/auth/v1/token?grant_type=password",
        data=payload,
        headers=_supabase_headers(use_service_role=False),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get("access_token") and data.get("user"):
                user_data = data["user"]
                return {
                    "success": True,
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token", ""),
                    "user": {
                        "id": user_data["id"],
                        "email": user_data.get("email", ""),
                        "username": (user_data.get("user_metadata") or {}).get(
                            "username", user_data.get("email", "")
                        ),
                    },
                }
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        if e.code == 400:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        raise HTTPException(status_code=e.code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


async def logout(access_token: str) -> bool:
    """Revoke the current session."""
    if not access_token:
        return False
    try:
        req = urllib.request.Request(
            f"{_SUPABASE_URL}/auth/v1/logout",
            data=b"",
            headers={
                "apikey": _SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {access_token}",
            },
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        return True
    except Exception as e:
        log.warning("Logout failed: %s", e)
        return False


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Admin: get user details by ID (requires service_role key)."""
    try:
        req = urllib.request.Request(
            f"{_SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={
                **_supabase_headers(use_service_role=True),
                "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data and data.get("id"):
                return {
                    "id": data["id"],
                    "email": data.get("email", ""),
                    "username": (data.get("user_metadata") or {}).get("username", ""),
                    "created_at": data.get("created_at", ""),
                }
    except Exception as e:
        log.warning("get_user_by_id failed: %s", e)
    return None
