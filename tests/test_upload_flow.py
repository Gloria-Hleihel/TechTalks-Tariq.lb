import io
import os

import pytest
import requests
from PIL import Image

from app import create_app
from app.utils.detection_client import trigger_detection
from app.utils.exif import GPSExtractionError
from models import Detection, Report, db


def image_bytes(fmt="PNG"):
    """Create a small valid image in memory for upload tests."""
    stream = io.BytesIO()

    Image.new(
        "RGB",
        (8, 8),
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

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(static_folder),
            "UPLOAD_FOLDER": str(upload_folder),
            "ANNOTATED_FOLDER": str(annotated_folder),
            "MAX_CONTENT_LENGTH": 2048,
            "DETECTION_API_URL": (
                "http://detector.test/api/detect"
            ),
            "DETECTION_API_TIMEOUT": 0.1,
        }
    )

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Create a Flask test client."""
    return app.test_client()


def completed_result():
    return {
        "status": "completed",
        "damage_type": "Pothole",
        "confidence": 0.91,
        "severity_score": 72,
        "severity_label": "High",
        "annotated_image_path": None,
    }


def pending_result(
    error="Detection API timed out.",
):
    return {
        "status": "pending",
        "error": error,
        "user_message": (
            "Your report was saved, but detection timed out. "
            "Please retry detection later."
        ),
    }


def test_completed_upload_saves_report_detection_and_redirects(
    app,
    client,
    monkeypatch,
):
    """A valid GPS image should create a report and detection."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (
            33.8938,
            35.5018,
        ),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: completed_result(),
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
        report = db.session.get(
            Report,
            1,
        )

        detection = Detection.query.filter_by(
            report_id=1
        ).one()

        assert report.location_source == "gps"
        assert report.detection_status == "completed"
        assert report.detection_error is None
        assert report.image_path.startswith("uploads/")
        assert detection.damage_type == "Pothole"

        saved_file = os.path.join(
            app.config["UPLOAD_FOLDER"],
            os.path.basename(report.image_path),
        )

        assert os.path.exists(saved_file)

        assert Detection.query.filter_by(
            report_id=report.id
        ).count() == 1


def test_wrong_file_type_has_actionable_error_and_no_report(
    app,
    client,
):
    """A fake image file should not create a report."""
    response = client.post(
        "/upload",
        data={
            "image": (
                io.BytesIO(b"hello"),
                "road.txt",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"Unsupported file type"
        in response.data
    )

    with app.app_context():
        assert Report.query.count() == 0


def test_corrupted_image_has_actionable_error_and_no_report(
    app,
    client,
):
    response = client.post(
        "/upload",
        data={
            "image": (
                io.BytesIO(b"not-an-image"),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"not a valid JPG or PNG image"
        in response.data
    )

    with app.app_context():
        assert Report.query.count() == 0


def test_oversized_upload_has_actionable_error_and_no_report(
    app,
    client,
):
    response = client.post(
        "/upload",
        data={
            "image": (
                io.BytesIO(
                    b"x" * 4096
                ),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"larger than 5MB"
        in response.data
    )

    with app.app_context():
        assert Report.query.count() == 0


def test_manual_location_is_used_when_photo_has_no_gps(
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
        lambda _report, _path: pending_result(
            "Detector unavailable."
        ),
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
        report = db.session.get(
            Report,
            1,
        )

        assert report is not None
        assert report.location_source == "manual"

        assert report.lat == pytest.approx(
            33.9001
        )

        assert report.lng == pytest.approx(
            35.5002
        )

        assert report.detection_status == "pending"


def test_gps_exception_uses_manual_location_and_warns_user(
    app,
    client,
    monkeypatch,
):
    def raise_gps_error(_path):
        raise GPSExtractionError(
            "The photo contains damaged GPS metadata."
        )

    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        raise_gps_error,
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: pending_result(),
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
            "lat": "33.8",
            "lng": "35.9",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"selected location was used"
        in response.data
    )

    with app.app_context():
        report = Report.query.one()

        assert report.location_source == "manual"
        assert report.lat == pytest.approx(33.8)
        assert report.lng == pytest.approx(35.9)


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

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: pending_result(),
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"Your uploaded image has been kept"
        in response.data
    )

    assert (
        b'name="saved_image_path"'
        in response.data
    )

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


def test_gps_exception_without_manual_location_keeps_image_and_no_report(
    app,
    client,
    monkeypatch,
):
    def raise_gps_error(_path):
        raise GPSExtractionError(
            "The photo contains damaged GPS metadata."
        )

    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        raise_gps_error,
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
        b"Select the road location on the map"
        in response.data
    )

    assert (
        b'name="saved_image_path"'
        in response.data
    )

    with app.app_context():
        assert Report.query.count() == 0


def test_detection_timeout_does_not_lose_report(
    app,
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (
            33.0,
            35.0,
        ),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: pending_result(
            "Detection API timed out."
        ),
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
        b"report was saved"
        in response.data.lower()
    )

    assert (
        b"Retry Detection"
        in response.data
    )

    with app.app_context():
        report = Report.query.one()

        assert report.detection_status == "pending"

        assert (
            "timed out"
            in report.detection_error
        )

        assert Detection.query.count() == 0


def test_retry_detection_completes_existing_report(
    app,
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (
            33.0,
            35.0,
        ),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: pending_result(),
    )

    client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        lambda _report, _path: completed_result(),
    )

    response = client.post(
        "/reports/1/retry-detection",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"detection completed"
        in response.data.lower()
    )

    with app.app_context():
        report = db.session.get(
            Report,
            1,
        )

        assert report.detection_status == "completed"
        assert report.detection_error is None

        assert Detection.query.filter_by(
            report_id=1
        ).count() == 1


def test_report_detail_renders_redesigned_page(
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
        lambda _report, _path: pending_result(),
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
        lambda _report, _path: pending_result(
            "Detector unavailable in test."
        ),
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


def test_detection_client_timeout_returns_pending(
    app,
    tmp_path,
    monkeypatch,
):
    image_path = (
        tmp_path
        / "road.png"
    )

    image_path.write_bytes(
        image_bytes().getvalue()
    )

    class ExampleReport:
        id = 42

    def raise_timeout(
        *_args,
        **_kwargs,
    ):
        raise requests.Timeout()

    monkeypatch.setattr(
        "app.utils.detection_client.requests.post",
        raise_timeout,
    )

    with app.app_context():
        result = trigger_detection(
            ExampleReport(),
            str(image_path),
        )

    assert result["status"] == "pending"

    assert (
        "timed out"
        in result["error"]
    )


def test_detection_client_http_error_returns_pending(
    app,
    tmp_path,
    monkeypatch,
):
    image_path = (
        tmp_path
        / "road.png"
    )

    image_path.write_bytes(
        image_bytes().getvalue()
    )

    class ExampleReport:
        id = 42

    class FakeResponse:
        ok = False
        status_code = 503
        text = "service unavailable"

        @staticmethod
        def json():
            return {
                "error": "model unavailable"
            }

    monkeypatch.setattr(
        "app.utils.detection_client.requests.post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    with app.app_context():
        result = trigger_detection(
            ExampleReport(),
            str(image_path),
        )

    assert result["status"] == "pending"

    assert (
        "HTTP 503"
        in result["error"]
    )