"""
config.py — Shared constants for Tariq.lb
"""

import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# Flask and database
SQLALCHEMY_DATABASE_URI = (
    f"sqlite:///{os.path.join(BASE_DIR, 'tariq.db')}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-secret-change-me",
)


# File uploads
UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads",
)

ANNOTATED_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "annotated",
)

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
}

MAX_CONTENT_LENGTH = 5 * 1024 * 1024


# Detection API
DETECTION_API_URL = os.environ.get(
    "DETECTION_API_URL",
    "http://127.0.0.1:5000/api/detect",
)

DETECTION_API_TIMEOUT = float(
    os.environ.get(
        "DETECTION_API_TIMEOUT",
        "15",
    )
)

DETECTION_STATUSES = [
    "pending",
    "completed",
]


# Damage classification
DAMAGE_TYPES = [
    "Pothole",
    "Road Crack",
    "Surface Wear",
    "Other",
    "None",
]


# Severity
SEVERITY_LEVELS = [
    "Low",
    "Medium",
    "High",
    "Critical",
]

SEVERITY_COLORS = {
    "Low": "green",
    "Medium": "yellow",
    "High": "orange",
    "Critical": "red",
}


# Report workflow
REPORT_STATUSES = [
    "pending",
    "reviewed",
    "resolved",
]

LOCATION_SOURCES = [
    "gps",
    "manual",
]


# Admin authentication
ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin",
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "changeme",
)


# Map defaults centered on Lebanon
MAP_DEFAULT_LAT = 33.85
MAP_DEFAULT_LNG = 35.86
MAP_DEFAULT_ZOOM = 9

# Detection API
DETECTION_API_URL = os.environ.get(
    "DETECTION_API_URL",
    "http://127.0.0.1:5000/api/detect",
)

DETECTION_API_TIMEOUT = float(
    os.environ.get(
        "DETECTION_API_TIMEOUT",
        "15",
    )
)
DETECTION_ESTIMATED_WAIT_SECONDS = int(
    os.environ.get(
        "DETECTION_ESTIMATED_WAIT_SECONDS",
        "15",
    )
)

DETECTION_STATUSES = [
    "pending",
    "completed",
]