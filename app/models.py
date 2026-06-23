"""
Database layer for Tariq.lb -- plain sqlite3 (no ORM).

NOTE: The PRD's suggested tech stack (Section 12) calls for
Flask-SQLAlchemy. This sandbox has no network access to install it,
so this module re-implements the same schema and operations directly
on top of Python's built-in sqlite3. The data model matches the PRD's
"Basic Data Requirements" (Section 10) exactly: report id, image,
damage type, severity score, GPS lat/lon, manual location flag,
detection result, confidence score, and timestamp.

If Flask-SQLAlchemy becomes available later, this module can be
swapped for a real `db.Model` class without changing any callers --
every function here returns plain dicts shaped like Report.to_dict().
"""
import sqlite3
from datetime import datetime, timezone

DB_PATH = None  # set by init_db()


def init_db(db_path):
    """Create the reports table if it doesn't exist."""
    global DB_PATH
    DB_PATH = db_path
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_filename TEXT NOT NULL,
            damage_type TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            severity_level TEXT NOT NULL,
            severity_score REAL NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row):
    return {
        "id": row["id"],
        "image_filename": row["image_filename"],
        "image_url": f"/static/uploads/{row['image_filename']}",
        "damage_type": row["damage_type"],
        "confidence_score": round(row["confidence_score"], 2),
        "severity_level": row["severity_level"],
        "severity_score": round(row["severity_score"], 2),
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "location_source": row["location_source"],
        "created_at": row["created_at"],
    }


def create_report(image_filename, damage_type, confidence_score,
                   severity_level, severity_score,
                   latitude, longitude, location_source):
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    conn = _connect()
    cur = conn.execute("""
        INSERT INTO reports (
            image_filename, damage_type, confidence_score,
            severity_level, severity_score,
            latitude, longitude, location_source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        image_filename, damage_type, confidence_score,
        severity_level, severity_score,
        latitude, longitude, location_source, created_at
    ))
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return get_report(report_id)


def get_report(report_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def list_reports():
    conn = _connect()
    rows = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]
