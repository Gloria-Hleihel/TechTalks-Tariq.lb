"""Security and response-hardening helpers for Tariq.lb."""

from __future__ import annotations

from functools import wraps
from hmac import compare_digest
from secrets import token_urlsafe
from typing import Callable

from flask import abort, current_app, request, session


CSRF_SESSION_KEY = "_csrf_token"


def csrf_protection_enabled() -> bool:
    """Return whether CSRF checks should run for this request."""
    if current_app.config.get("TESTING"):
        return False
    if current_app.config.get("WTF_CSRF_ENABLED") is False:
        return False
    return bool(current_app.config.get("CSRF_ENABLED", True))


def generate_csrf_token() -> str:
    """Create or reuse the current session CSRF token."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _submitted_csrf_token() -> str:
    """Read a CSRF token from form data, JSON, or headers."""
    token = request.form.get("_csrf_token") or request.headers.get(
        "X-CSRF-Token",
        "",
    )

    if not token and request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            token = str(data.get("_csrf_token") or "")

    return str(token or "")


def validate_csrf_token() -> None:
    """Abort the request when the submitted CSRF token is missing or invalid."""
    if not csrf_protection_enabled():
        return

    expected = str(session.get(CSRF_SESSION_KEY) or "")
    submitted = _submitted_csrf_token()

    if not expected or not submitted or not compare_digest(expected, submitted):
        abort(400, description="Invalid CSRF token.")


def require_csrf(view: Callable) -> Callable:
    """Decorator for state-changing views that need CSRF protection."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        validate_csrf_token()
        return view(*args, **kwargs)

    return wrapped


def _security_header_policy() -> str:
    """Compatibility CSP for the current inline-style/template-heavy app."""
    return "; ".join(
        [
            "default-src 'self'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "object-src 'none'",
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://server.arcgisonline.com",
            "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com",
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com",
            "font-src 'self' data: https://cdnjs.cloudflare.com",
            "connect-src 'self'",
        ]
    )


def init_security(app) -> None:
    """Attach security headers, CSRF context, and optional compression."""
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_SECURE", False)

    @app.context_processor
    def csrf_context() -> dict[str, Callable[[], str]]:
        return {"csrf_token": generate_csrf_token}

    @app.after_request
    def add_security_headers(response):
        if not app.config.get("SECURITY_HEADERS_ENABLED", True):
            return response

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(self), camera=(), microphone=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            _security_header_policy(),
        )

        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        if request.path.startswith("/static/"):
            max_age = int(app.config.get("STATIC_CACHE_SECONDS", 86_400))
            response.cache_control.public = True
            response.cache_control.max_age = max_age
        elif request.path.startswith("/admin"):
            response.cache_control.no_store = True

        return response

    if app.config.get("ENABLE_COMPRESSION", True):
        try:
            from flask_compress import Compress
        except ImportError:
            app.logger.info(
                "Flask-Compress is not installed; compression is disabled."
            )
        else:
            Compress(app)
