"""Application configuration for Tariq.lb."""

from datetime import timedelta
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable safely."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a safe fallback."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float environment variable with a safe fallback."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


# --- Flask / Database -------------------------------------------------
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'tariq.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
AUTO_CREATE_DATABASE = _env_bool("AUTO_CREATE_DATABASE", True)

# --- File uploads -------------------------------------------------------
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ANNOTATED_FOLDER = os.path.join(UPLOAD_FOLDER, "annotated")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = _env_int("MAX_IMAGE_PIXELS", 24_000_000)

# --- Detection API ------------------------------------------------------
DETECTION_API_URL = os.environ.get(
    "DETECTION_API_URL",
    "http://127.0.0.1:5000/api/detect",
)
DETECTION_API_TIMEOUT = _env_float("DETECTION_API_TIMEOUT", 15.0)
DETECTION_ESTIMATED_WAIT_SECONDS = _env_int(
    "DETECTION_ESTIMATED_WAIT_SECONDS",
    15,
)
DETECTION_STATUSES = ["pending", "completed"]

# --- Damage classification ----------------------------------------------
DAMAGE_TYPES = [
    "Longitudinal Crack",
    "Transverse Crack",
    "Alligator Crack",
    "Potholes",
    "None",
]

# --- Severity ------------------------------------------------------------
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

SEVERITY_COLORS = {
    "Low": "green",
    "Medium": "yellow",
    "High": "orange",
    "Critical": "red",
}

# --- Report workflow -----------------------------------------------------
REPORT_STATUSES = ["pending", "reviewed", "resolved", "rejected"]
LOCATION_SOURCES = ["gps", "browser", "manual", "search"]

# --- Admin auth ----------------------------------------------------------
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

# --- Security ------------------------------------------------------------
CSRF_ENABLED = _env_bool("CSRF_ENABLED", True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
PERMANENT_SESSION_LIFETIME = timedelta(
    hours=_env_int("SESSION_LIFETIME_HOURS", 2)
)
SECURITY_HEADERS_ENABLED = _env_bool("SECURITY_HEADERS_ENABLED", True)

# --- Static files / compression -----------------------------------------
STATIC_CACHE_SECONDS = _env_int("STATIC_CACHE_SECONDS", 86_400)
SEND_FILE_MAX_AGE_DEFAULT = STATIC_CACHE_SECONDS
ENABLE_COMPRESSION = _env_bool("ENABLE_COMPRESSION", True)
COMPRESS_MIMETYPES = [
    "text/html",
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/json",
    "image/svg+xml",
]

# --- Map defaults (centered on Lebanon) ---------------------------------
MAP_DEFAULT_LAT = 33.85
MAP_DEFAULT_LNG = 35.86
MAP_DEFAULT_ZOOM = 9

# --- API safety limits ---------------------------------------------------
PUBLIC_REPORT_LIMIT = _env_int("PUBLIC_REPORT_LIMIT", 1000)
SEARCH_QUERY_MAX_LENGTH = _env_int("SEARCH_QUERY_MAX_LENGTH", 80)

# Inference endpoints may only read images from these project-relative roots.
DETECTION_ALLOWED_ROOTS = [
    os.path.join(BASE_DIR, "static", "uploads"),
    os.path.join(BASE_DIR, "test_images"),
]
