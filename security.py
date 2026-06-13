"""Security middleware: headers + CSRF protection for FastAPI.

Adds to every response:
  - Content-Security-Policy
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - Strict-Transport-Security (if HTTPS)
  - Referrer-Policy

CSRF protection:
  - JSON API calls with JWT Bearer token are exempt (Bearer token cannot
    be auto-submitted by a form).
  - Form POSTs (Content-Type: application/x-www-form-urlencoded) validate
    the Origin or Referer header matches the app origin.
  - SameSite=Lax on auth cookies prevents cross-site form submission.
"""

import os
import re
import logging
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("cbse.security")

# Permissive CSP that allows KaTeX CDN and inline styles/scripts needed
# for the server-rendered content. The app has inline <style> and <script>
# because templates have no separate asset pipeline yet.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "img-src 'self' data: https:; "
    "font-src 'self' https://fonts.gstatic.com; "
    "connect-src 'self' https://sehntpqydngyqvfyumpp.supabase.co; "
    "frame-src 'none'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

# Origins allowed for CSRF checks (derived from env or default)
_ALLOWED_ORIGINS = set()


def _get_allowed_origins():
    if not _ALLOWED_ORIGINS:
        raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:9090,http://localhost:9095")
        for o in raw.split(","):
            o = o.strip()
            if o:
                _ALLOWED_ORIGINS.add(o.rstrip("/"))
        # Also derive from common deployment setups
        _ALLOWED_ORIGINS.add("https://cbse.app")
        _ALLOWED_ORIGINS.add("https://www.cbse.app")
    return _ALLOWED_ORIGINS


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"  # deprecated but harmless
        # Only add HSTS if HTTPS (detected by header or scheme)
        scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
        if scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response


class CSRFSafeMiddleware(BaseHTTPMiddleware):
    """CSRF protection for form POSTs.

    Exempts:
      - GET, HEAD, OPTIONS, TRACE
      - JSON API calls (Content-Type: application/json) — these require
        JWT Bearer token which cannot be auto-submitted cross-origin.
      - Auth endpoints (they use JWT exclusively).
      - Requests with valid Origin/Referer matching allowed origins.
    """

    # Path prefixes that are always exempt (auth uses JWT, not session cookies)
    EXEMPT_PREFIXES = ("/api/auth/", "/api/tutor/")

    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return await call_next(request)

        # Check exempt paths
        path = request.url.path
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # JSON API calls are exempt (they need JWT Bearer, not cookies)
        content_type = request.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await call_next(request)

        # Check for Bearer token — if present, the request is authenticated
        # via JWT and CSRF doesn't apply
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Validate Origin or Referer header
        origin = request.headers.get("Origin", "")
        referer = request.headers.get("Referer", "")

        if origin:
            if not self._is_allowed(origin):
                log.warning("CSRF blocked: origin=%s method=%s path=%s", origin, request.method, path)
                return Response("Forbidden", status_code=403)
            return await call_next(request)

        if referer:
            parsed = urlparse(referer)
            ref_origin = f"{parsed.scheme}://{parsed.netloc}"
            if self._is_allowed(ref_origin):
                return await call_next(request)
            log.warning("CSRF blocked: referer=%s method=%s path=%s", ref_origin, request.method, path)
            return Response("Forbidden", status_code=403)

        # No Origin, no Referer, no Bearer, not JSON — block it
        log.warning("CSRF blocked: no origin/referer method=%s path=%s", request.method, path)
        return Response("Forbidden", status_code=403)

    @staticmethod
    def _is_allowed(origin: str) -> bool:
        origin = origin.rstrip("/")
        for allowed in _get_allowed_origins():
            if origin == allowed:
                return True
            # Allow localhost variants
            if "localhost" in origin and "localhost" in allowed:
                return True
        return False
