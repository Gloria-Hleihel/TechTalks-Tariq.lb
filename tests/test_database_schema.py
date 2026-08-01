"""Regression tests for local SQLite schema upgrades."""

import sqlite3
from pathlib import Path

from app import create_app


def _create_old_report_database(database_path: Path) -> None:
    """Create the pre-detection-status schema used by older local installs."""
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE reports (
                id INTEGER NOT NULL,
                image_path VARCHAR(255) NOT NULL,
                lat FLOAT NOT NULL,
                lng FLOAT NOT NULL,
                location_source VARCHAR(10) NOT NULL,
                status VARCHAR(20) NOT NULL,
                created_at DATETIME NOT NULL,
                PRIMARY KEY (id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE detections (
                id INTEGER NOT NULL,
                report_id INTEGER NOT NULL,
                damage_type VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                severity_score INTEGER NOT NULL,
                severity_label VARCHAR(20) NOT NULL,
                annotated_image_path VARCHAR(255),
                PRIMARY KEY (id),
                FOREIGN KEY(report_id) REFERENCES reports (id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO reports (
                id,
                image_path,
                lat,
                lng,
                location_source,
                status,
                created_at
            )
            VALUES (
                1,
                'static/uploads/example.jpg',
                33.9001,
                35.5018,
                'manual',
                'pending',
                '2026-08-01 10:15:00.000000'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO detections (
                id,
                report_id,
                damage_type,
                confidence,
                severity_score,
                severity_label,
                annotated_image_path
            )
            VALUES (
                1,
                1,
                'Transverse Crack',
                0.82,
                55,
                'Medium',
                NULL
            )
            """
        )


def test_old_sqlite_database_is_upgraded_on_startup(tmp_path: Path) -> None:
    database_path = tmp_path / "old_tariq.db"
    _create_old_report_database(database_path)

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "ANNOTATED_FOLDER": str(tmp_path / "uploads" / "annotated"),
            "WTF_CSRF_ENABLED": False,
        }
    )

    with sqlite3.connect(database_path) as connection:
        report_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(reports)")
        }
        upgraded_values = connection.execute(
            """
            SELECT detection_status, detection_error
            FROM reports
            WHERE id = 1
            """
        ).fetchone()

    assert "detection_status" in report_columns
    assert "detection_error" in report_columns
    assert upgraded_values == ("completed", None)

    response = app.test_client().get("/api/reports")

    assert response.status_code == 200
    assert response.get_json()[0]["id"] == 1
