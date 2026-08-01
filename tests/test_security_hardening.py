import re

import pytest

from app import create_app
from models import db


@pytest.fixture()
def app(tmp_path):
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"

    flask_app = create_app(
        {
            "TESTING": False,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(static_folder),
            "UPLOAD_FOLDER": str(upload_folder),
            "ANNOTATED_FOLDER": str(annotated_folder),
            "ENABLE_COMPRESSION": False,
        }
    )

    with flask_app.app_context():
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_from_response(response):
    match = re.search(
        rb'name="_csrf_token" value="([^"]+)"',
        response.data,
    )
    assert match is not None
    return match.group(1).decode("utf-8")


def test_security_headers_are_sent(client):
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "https://server.arcgisonline.com" in response.headers["Content-Security-Policy"]
    assert "geolocation=(self)" in response.headers["Permissions-Policy"]


def test_admin_login_rejects_missing_csrf_token(client):
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "changeme"},
    )

    assert response.status_code == 400


def test_admin_login_accepts_valid_csrf_token(client):
    login_page = client.get("/admin/login")
    token = _csrf_from_response(login_page)

    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "changeme",
            "_csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")
