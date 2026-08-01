"""Regression tests for public live-map report visibility."""

import pytest

from app import create_app
from models import Detection, Report, db


@pytest.fixture
def app():
    """Create a test app with an in-memory database."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_FOLDER": "/tmp/test_uploads",
        "ANNOTATED_FOLDER": "/tmp/test_annotated",
    }
    flask_app = create_app(test_config)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Return a Flask test client."""
    return app.test_client()


def _add_report(status: str, latitude: float) -> Report:
    """Insert one report and its detection result."""
    report = Report(
        image_path=f"static/uploads/{status}.jpg",
        lat=latitude,
        lng=35.50,
        location_source="manual",
        status=status,
    )
    db.session.add(report)
    db.session.flush()

    detection = Detection(
        report_id=report.id,
        damage_type="Potholes",
        confidence=0.82,
        severity_score=70,
        severity_label="High",
        annotated_image_path=f"static/uploads/annotated/{status}.jpg",
    )
    db.session.add(detection)
    return report


def test_public_live_map_hides_done_reports(app, client):
    """Done reports stay in admin history but do not appear on /api/reports."""
    with app.app_context():
        pending_report = _add_report("pending", 33.89)
        reviewed_report = _add_report("reviewed", 33.90)
        completed_report = _add_report("resolved", 33.91)
        rejected_report = _add_report("rejected", 33.92)
        db.session.commit()

        pending_id = pending_report.id
        reviewed_id = reviewed_report.id
        completed_id = completed_report.id
        rejected_id = rejected_report.id

    response = client.get("/api/reports")

    assert response.status_code == 200
    visible_ids = {item["id"] for item in response.get_json()}
    assert pending_id in visible_ids
    assert reviewed_id in visible_ids
    assert completed_id not in visible_ids
    assert rejected_id not in visible_ids


def test_public_reports_reject_invalid_filters(client):
    response = client.get("/api/reports?severity=Severe")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid severity filter."

    response = client.get("/api/reports?damage_type=Unknown")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid damage_type filter."


def test_public_reports_support_bounds_and_limit(app, client):
    with app.app_context():
        first = _add_report("pending", 33.89)
        second = _add_report("pending", 34.40)
        db.session.commit()
        first_id = first.id
        second_id = second.id

    response = client.get(
        "/api/reports?north=34&south=33.5&east=36&west=35&limit=1"
    )

    assert response.status_code == 200
    data = response.get_json()
    visible_ids = {item["id"] for item in data}

    assert len(data) == 1
    assert first_id in visible_ids
    assert second_id not in visible_ids


def test_public_reports_reject_bad_bounds(client):
    response = client.get("/api/reports?north=34&south=33")
    assert response.status_code == 400
    assert "north, south, east, and west" in response.get_json()["error"]

    response = client.get("/api/reports?north=33&south=34&east=36&west=35")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid map bounds."
