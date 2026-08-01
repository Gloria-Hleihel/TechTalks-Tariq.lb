import io

import pytest
from PIL import ExifTags, Image

from app import create_app
from models import Detection, Report, db


def image_bytes(fmt="PNG"):
    stream = io.BytesIO()

    Image.new(
        "RGB",
        (12, 12),
        "white",
    ).save(
        stream,
        format=fmt,
    )

    stream.seek(0)

    return stream


def jpeg_with_gps_bytes():
    stream = io.BytesIO()
    exif = Image.Exif()

    gps_ifd = {
        1: "N",
        2: (33.0, 53.0, 37.68),
        3: "E",
        4: (35.0, 30.0, 6.48),
    }

    exif[ExifTags.IFD.GPSInfo] = gps_ifd

    Image.new(
        "RGB",
        (12, 12),
        "white",
    ).save(
        stream,
        format="JPEG",
        exif=exif,
    )

    stream.seek(0)

    return stream


@pytest.fixture()
def app(tmp_path):
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(static_folder),
            "UPLOAD_FOLDER": str(upload_folder),
            "ANNOTATED_FOLDER": str(annotated_folder),
            "MAX_CONTENT_LENGTH": 2048,
            "DETECTION_API_URL": "http://detector.test/api/detect",
            "DETECTION_API_TIMEOUT": 0.1,
        }
    )

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def pending_detection(monkeypatch):
    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: {
            "status": "pending",
            "error": "Detector unavailable in integration test.",
            "user_message": (
                "Your report was saved, but detection is pending. "
                "Please retry detection later."
            ),
        },
    )


def assert_single_report(app, *, source, lat, lng):
    with app.app_context():
        assert Report.query.count() == 1

        report = Report.query.one()

        assert report.location_source == source
        assert report.lat == pytest.approx(
            lat,
            abs=0.0001,
        )
        assert report.lng == pytest.approx(
            lng,
            abs=0.0001,
        )
        assert report.detection_status == "pending"
        assert Detection.query.count() == 0


def test_post_api_reports_accepts_valid_jpg_with_gps(app, client):
    response = client.post(
        "/api/reports",
        data={
            "image": (
                jpeg_with_gps_bytes(),
                "gps-road.jpg",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    payload = response.get_json()

    assert payload["ok"] is True
    assert payload["report"]["location_source"] == "gps"
    assert payload["redirect_url"].endswith("/reports/1")

    assert_single_report(
        app,
        source="gps",
        lat=33.8938,
        lng=35.5018,
    )


def test_post_api_reports_returns_single_completed_detection(
    app,
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )
    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: {
            "status": "completed",
            "damage_type": "Alligator Crack",
            "confidence": 0.8275,
            "severity_score": 78,
            "severity_label": "High",
            "annotated_image_path": "static/uploads/annotated/road.jpg",
            "user_message": "Report submitted and detection completed.",
        },
    )

    response = client.post(
        "/api/reports",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
            "lat": "33.8938",
            "lng": "35.5018",
            "location_source": "search",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    payload = response.get_json()
    detection = payload["report"]["detection"]

    assert payload["ok"] is True
    assert payload["report"]["detection_status"] == "completed"
    assert detection["damage_type"] == "Alligator Crack"
    assert detection["confidence"] == pytest.approx(0.8275)

    with app.app_context():
        report = Report.query.one()
        assert Detection.query.filter_by(report_id=report.id).count() == 1


def test_post_api_reports_accepts_valid_jpg_without_gps_using_manual_pin(
    app,
    client,
):
    response = client.post(
        "/api/reports",
        data={
            "image": (
                image_bytes("JPEG"),
                "manual-road.jpg",
            ),
            "lat": "33.9001",
            "lng": "35.5002",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    payload = response.get_json()

    assert payload["report"]["location_source"] == "manual"

    assert_single_report(
        app,
        source="manual",
        lat=33.9001,
        lng=35.5002,
    )


def test_post_api_reports_accepts_png_file(app, client):
    response = client.post(
        "/api/reports",
        data={
            "image": (
                image_bytes("PNG"),
                "road.png",
            ),
            "lat": "33.8203",
            "lng": "35.4878",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json()["report"]["image_path"].endswith(".png")

    assert_single_report(
        app,
        source="manual",
        lat=33.8203,
        lng=35.4878,
    )


def test_post_api_reports_rejects_oversized_file_and_keeps_db_empty(
    app,
    client,
):
    response = client.post(
        "/api/reports",
        data={
            "image": (
                io.BytesIO(b"x" * 4096),
                "large.jpg",
            ),
            "lat": "33.8",
            "lng": "35.9",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 413

    payload = response.get_json()

    assert payload["ok"] is False
    assert "larger than 5MB" in payload["error"]

    with app.app_context():
        assert Report.query.count() == 0
        assert Detection.query.count() == 0


def test_post_api_reports_rejects_wrong_type_and_keeps_db_empty(
    app,
    client,
):
    response = client.post(
        "/api/reports",
        data={
            "image": (
                io.BytesIO(b"hello"),
                "road.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400

    payload = response.get_json()

    assert payload["ok"] is False
    assert payload["field"] == "image"
    assert "Unsupported file type" in payload["error"]

    with app.app_context():
        assert Report.query.count() == 0
        assert Detection.query.count() == 0
