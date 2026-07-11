"""
config.py — Shared constants for Tariq.lb

Every teammate imports from this file instead of redefining these
values locally. If a constant needs to change, open a PR to Zahraa
rather than editing your own copy.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- Flask / Database -------------------------------------------------
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'tariq.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# --- File uploads -------------------------------------------------------
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ANNOTATED_FOLDER = os.path.join(UPLOAD_FOLDER, "annotated")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB, per the Week 3 validation task

# --- Damage classification ----------------------------------------------
# Matches Section 11 delivery checklist exactly.
DAMAGE_TYPES = ["Pothole", "Road Crack", "Surface Wear", "Other"]

# --- Severity ------------------------------------------------------------
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Used by Gloria's getMarkerColor() (JS) and the severity badge styling.
SEVERITY_COLORS = {
    "Low": "green",
    "Medium": "yellow",
    "High": "orange",
    "Critical": "red",
}

# --- Report workflow -----------------------------------------------------
REPORT_STATUSES = ["pending", "reviewed", "resolved"]
LOCATION_SOURCES = ["gps", "manual"]

# --- Admin auth ------------------------------------------------------------
# Simple Flask session-based auth per project assumptions — no role
# management needed for the 5-week scope.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

# --- Map defaults (centered on Lebanon) -----------------------------------
MAP_DEFAULT_LAT = 33.85
MAP_DEFAULT_LNG = 35.86
MAP_DEFAULT_ZOOM = 9 