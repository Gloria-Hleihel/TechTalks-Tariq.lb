"""
tests/test_admin.py — Admin module tests
Owner: Zahraa · Week 5
"""
import os

import pytest
from app import create_app
from models import db, Report, Detection, FeedbackMessage


@pytest.fixture
def app(tmp_path):
    """Create test app with in-memory database."""
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "STATIC_FOLDER": str(static_folder),
        "UPLOAD_FOLDER": str(upload_folder),
        "ANNOTATED_FOLDER": str(annotated_folder),
    }
    app = create_app(test_config)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def seed_report(app):
    """Insert one report with a detection for testing."""
    with app.app_context():
        report = Report(
            image_path="static/uploads/test.jpg",
            lat=33.89,
            lng=35.50,
            location_source="gps",
            status="pending",
        )
        db.session.add(report)
        db.session.flush()

        detection = Detection(
            report_id=report.id,
            damage_type="Potholes",
            confidence=0.85,
            severity_score=70,
            severity_label="High",
            annotated_image_path="static/uploads/annotated/test.jpg",
        )
        db.session.add(detection)
        db.session.commit()
        return report.id


def login(client):
    """Helper to log in as admin."""
    return client.post("/admin/login", data={
        "username": "admin",
        "password": "changeme"
    }, follow_redirects=True)


# --- Login tests ---

def test_login_correct_credentials(client):
    """Login with correct credentials redirects to dashboard."""
    response = login(client)
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_wrong_credentials(client):
    """Login with wrong credentials shows error."""
    response = client.post("/admin/login", data={
        "username": "admin",
        "password": "wrongpassword"
    }, follow_redirects=True)
    assert b"Invalid credentials" in response.data


def test_admin_login_has_accessible_fields(client):
    """Login inputs should have labels, autocomplete, and alert semantics."""
    response = client.get("/admin/login")

    assert response.status_code == 200
    assert b'<label for="username">Username</label>' in response.data
    assert b'id="username"' in response.data
    assert b'autocomplete="username"' in response.data
    assert b'<label for="password">Password</label>' in response.data
    assert b'autocomplete="current-password"' in response.data
    assert b'aria-label="Show password"' in response.data


# --- Authentication redirect tests ---

def test_dashboard_requires_login(client):
    """Dashboard redirects to login if not authenticated."""
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert b"Sign in" in response.data


def test_reports_api_requires_login(client):
    """GET /admin/reports requires login."""
    response = client.get("/admin/reports")
    assert response.status_code == 302


# --- Dashboard tests ---

def test_dashboard_loads_after_login(client):
    """Dashboard loads correctly after login."""
    login(client)
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Road Damage Control Center" in response.data
    assert b'data-section="live"' in response.data
    assert b'data-section="review"' in response.data
    assert b'data-section="done"' in response.data
    assert b'<option value="search">Search</option>' in response.data


def test_dashboard_has_accessible_tabs_rows_and_map(client, seed_report):
    """Dashboard management controls should be usable without only a mouse."""
    login(client)
    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b'href="#admin-main"' in response.data
    assert b'aria-controls="table-view"' in response.data
    assert b'aria-controls="map-view"' in response.data
    assert b'aria-labelledby="map-view-tab"' in response.data
    assert b'id="admin-map"' in response.data
    assert b'role="region"' in response.data
    assert b'Open report 1 on the management map' in response.data
    assert b'aria-label="Update status for report 1"' in response.data
    assert b'aria-label="Delete report 1"' in response.data


def test_dashboard_shows_site_feedback_messages(client, app):
    """Dashboard shows messages sent from the public feedback form."""
    with app.app_context():
        feedback = FeedbackMessage(
            name="Citizen User",
            email="citizen@example.com",
            message="The report form needs help text.",
        )
        db.session.add(feedback)
        db.session.commit()

    login(client)
    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b"Site Messages" in response.data
    assert b"Citizen User" in response.data
    assert b"citizen@example.com" in response.data
    assert b"The report form needs help text." in response.data


# --- Status update tests ---

def test_update_status_valid(client, seed_report):
    """Update report status to reviewed."""
    login(client)
    response = client.post(
        f"/admin/update/{seed_report}",
        data={"status": "reviewed"},
        follow_redirects=True
    )
    assert response.status_code == 200
    with client.application.app_context():
        report = db.session.get(Report, seed_report)
        assert report.status == "reviewed"


def test_update_status_invalid(client, seed_report):
    """Update report with invalid status keeps original status."""
    login(client)
    client.post(
        f"/admin/update/{seed_report}",
        data={"status": "invalid_status"},
        follow_redirects=True
    )
    with client.application.app_context():
        report = db.session.get(Report, seed_report)
        assert report.status == "pending"


# --- Delete tests ---

def test_delete_report(client, seed_report):
    """Delete report removes it from database."""
    login(client)
    response = client.post(
        f"/admin/delete/{seed_report}",
        follow_redirects=True
    )
    assert response.status_code == 200
    with client.application.app_context():
        report = db.session.get(Report, seed_report)
        assert report is None


def test_cascade_delete(client, seed_report):
    """Deleting report also deletes its detection."""
    login(client)
    client.post(f"/admin/delete/{seed_report}", follow_redirects=True)
    with client.application.app_context():
        detection = Detection.query.filter_by(report_id=seed_report).first()
        assert detection is None


def test_delete_report_removes_saved_images(client, app, seed_report):
    """Deleting a report removes uploaded and annotated files."""
    with app.app_context():
        upload_path = app.config["UPLOAD_FOLDER"] + "/test.jpg"
        annotated_path = app.config["ANNOTATED_FOLDER"] + "/test.jpg"

    with open(upload_path, "wb") as file:
        file.write(b"uploaded")

    with open(annotated_path, "wb") as file:
        file.write(b"annotated")

    login(client)
    response = client.post(
        f"/admin/delete/{seed_report}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert not os.path.exists(upload_path)
    assert not os.path.exists(annotated_path)


# --- Filter tests ---

def test_filter_reports_by_status(client, seed_report):
    """GET /admin/reports?status=pending returns only pending reports."""
    login(client)
    response = client.get("/admin/reports?status=pending")
    assert response.status_code == 200
    data = response.get_json()
    assert all(r["status"] == "pending" for r in data["reports"])


# --- Report detail tests ---

def test_report_detail_exists(client, seed_report):
    """Report detail page loads for existing report."""
    login(client)
    response = client.get(f"/admin/reports/{seed_report}")
    assert response.status_code == 200


def test_report_detail_not_found(client):
    """Report detail returns 404 for non-existent report."""
    login(client)
    response = client.get("/admin/reports/9999")
    assert response.status_code == 404
