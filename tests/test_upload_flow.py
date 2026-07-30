import io
import os

import pytest
from PIL import Image

from app import create_app
from models import Detection, Report, db


def image_bytes(fmt="PNG"):
    """Create a small valid image in memory for upload tests."""
    stream = io.BytesIO()

    Image.new(
        "RGB",
        (4, 4),
        "white",
    ).save(
        stream,
        format=fmt,
    )

    stream.seek(0)

    return stream


@pytest.fixture()
def app(tmp_path):
    """Create an isolated Flask application for every test."""
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(static_folder),
            "UPLOAD_FOLDER": str(upload_folder),
            "ANNOTATED_FOLDER": str(annotated_folder),
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Create a Flask test client."""
    return app.test_client()


def test_valid_exif_upload_creates_report_and_redirects(
    app,
    client,
    monkeypatch,
):
    """A valid GPS image should create a report and detection."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (33.8938, 35.5018),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: {
            "status": "completed",
            "damage_type": "None",
            "confidence": 0.99,
            "severity_score": 0,
            "severity_label": "Low",
            "annotated_image_path": None,
        },
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    assert response.headers["Location"].endswith(
        "/reports/1"
    )

    with app.app_context():
        report = db.session.get(Report, 1)

        assert report is not None
        assert report.location_source == "gps"
        assert report.lat == pytest.approx(33.8938)
        assert report.lng == pytest.approx(35.5018)
        assert report.image_path.startswith("uploads/")

        saved_file = os.path.join(
            app.config["UPLOAD_FOLDER"],
            os.path.basename(report.image_path),
        )

        assert os.path.exists(saved_file)

        assert Detection.query.filter_by(
            report_id=report.id
        ).count() == 1


def test_invalid_file_is_rejected_without_report(
    app,
    client,
):
    """A fake image file should not create a report."""
    response = client.post(
        "/upload",
        data={
            "image": (
                io.BytesIO(b"not an image"),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    assert response.headers["Location"].endswith(
        "/upload"
    )

    with app.app_context():
        assert Report.query.count() == 0


def test_manual_location_is_used_when_exif_is_missing(
    app,
    client,
    monkeypatch,
):
    """Manual coordinates should be used when EXIF GPS is absent."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: {
            "status": "pending",
            "error": "Detector unavailable in test.",
        },
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
            "lat": "33.9001",
            "lng": "35.5002",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    assert response.headers["Location"].endswith(
        "/reports/1"
    )

    with app.app_context():
        report = db.session.get(Report, 1)

        assert report is not None
        assert report.location_source == "manual"
        assert report.lat == pytest.approx(33.9001)
        assert report.lng == pytest.approx(35.5002)
        assert report.detections == []


def test_missing_manual_location_keeps_image_and_does_not_create_report(
    app,
    client,
    monkeypatch,
):
    """
    When GPS and manual coordinates are missing, keep the uploaded
    image and show the form again without creating a report.
    """
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 200

    assert (
        b"Your uploaded image has been kept"
        in response.data
    )

    assert (
        b"Select the road location on the map"
        in response.data
    )

    assert b'name="saved_image_path"' in response.data

    with app.app_context():
        assert Report.query.count() == 0

    uploaded_items = os.listdir(
        app.config["UPLOAD_FOLDER"]
    )

    saved_images = [
        filename
        for filename in uploaded_items
        if filename != "annotated"
    ]

    assert len(saved_images) == 1
    assert saved_images[0].endswith(".png")


def test_report_detail_page_renders_after_redirect(
    app,
    client,
    monkeypatch,
):
    """A successful upload should render the redesigned report page."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (33.0, 35.0),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: {
            "status": "pending",
            "error": "Not integrated",
        },
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"Report submitted successfully."
        in response.data
    )

    assert b"Detection Pending" in response.data
    assert b"Report Information" in response.data
    assert b"Original Road Image" in response.data

def test_browser_location_source_is_saved_when_exif_is_missing(
    app,
    client,
    monkeypatch,
):
    """Browser coordinates should be stored with their own source."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: {
            "status": "pending",
            "error": "Detector unavailable in test.",
        },
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
            "lat": "33.8938",
            "lng": "35.5018",
            "location_source": "browser",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        report = db.session.get(Report, 1)

        assert report is not None
        assert report.location_source == "browser"
        assert report.lat == pytest.approx(33.8938)
        assert report.lng == pytest.approx(35.5018)

