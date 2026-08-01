"""Security and response-hardening helpers for Tariq.lb."""

from __future__ import annotations

from collections import defaultdict, deque
from functools import wraps
from hmac import compare_digest
from secrets import token_urlsafe
from time import monotonic
from typing import Callable

from flask import abort, current_app, jsonify, request, session


CSRF_SESSION_KEY = "_csrf_token"
RATE_LIMIT_STATE: dict[str, deque[float]] = defaultdict(deque)


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


def _client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.remote_addr or "unknown"


def _rate_limit_response(retry_after: int):
    message = "Too many requests. Please try again shortly."

    wants_json = request.accept_mimetypes.best == "application/json"
    if request.path.startswith("/api/") or wants_json:
        response = jsonify({"error": message})
    else:
        response = current_app.response_class(
            message,
            status=429,
            mimetype="text/plain",
        )

    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def rate_limit(
    limit_config: str,
    window_config: str,
    key_prefix: str,
    methods: set[str] | None = None,
) -> Callable:
    """Protect a route with a small per-client in-memory rate limit."""

    limited_methods = (
        {method.upper() for method in methods}
        if methods
        else None
    )

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if (
                current_app.config.get("TESTING")
                or not current_app.config.get("RATE_LIMIT_ENABLED", True)
                or (
                    limited_methods is not None
                    and request.method.upper() not in limited_methods
                )
            ):
                return view(*args, **kwargs)

            limit = int(current_app.config.get(limit_config, 60))
            window_seconds = int(current_app.config.get(window_config, 60))

            if limit <= 0 or window_seconds <= 0:
                return view(*args, **kwargs)

            now = monotonic()
            bucket_key = f"{key_prefix}:{_client_ip()}"
            bucket = RATE_LIMIT_STATE[bucket_key]

            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return _rate_limit_response(retry_after)

            bucket.append(now)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def reset_rate_limits() -> None:
    """Clear in-memory rate limit counters, mainly for tests."""
    RATE_LIMIT_STATE.clear()


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
