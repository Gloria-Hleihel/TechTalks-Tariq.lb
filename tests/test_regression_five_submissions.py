import io

import pytest
from PIL import ExifTags, Image

from app import create_app
from models import Detection, Report, db


def make_image(fmt="JPEG", gps=None):
    stream = io.BytesIO()
    exif = None

    if gps:
        exif = Image.Exif()
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps_ifd[1] = "N" if gps[0] >= 0 else "S"
        gps_ifd[2] = (abs(gps[0]), 0.0, 0.0)
        gps_ifd[3] = "E" if gps[1] >= 0 else "W"
        gps_ifd[4] = (abs(gps[1]), 0.0, 0.0)

    image = Image.new("RGB", (14, 14), "white")
    if exif is None:
        image.save(stream, format=fmt)
    else:
        image.save(stream, format=fmt, exif=exif)
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
            "MAX_CONTENT_LENGTH": 5 * 1024 * 1024,
        }
    )

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_complete_submission_flow_five_times(app, client, monkeypatch):
    calls = {"count": 0}

    def detection_result(_report, _path):
        calls["count"] += 1
        if calls["count"] in {2, 5}:
            return {
                "status": "pending",
                "error": "Temporary detector failure.",
                "user_message": "Report saved; detection can be retried.",
            }

        return {
            "status": "completed",
            "damage_type": "Pothole" if calls["count"] != 4 else "None",
            "confidence": 0.90,
            "severity_score": 65 if calls["count"] != 4 else 0,
            "severity_label": "High" if calls["count"] != 4 else "Low",
            "annotated_image_path": None,
        }

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        detection_result,
    )

    cases = [
        {
            "filename": "gps-beirut.jpg",
            "stream": make_image("JPEG", gps=(33.8938, 35.5018)),
        },
        {
            "filename": "manual-hamra.jpg",
            "stream": make_image("JPEG"),
            "lat": "33.8959",
            "lng": "35.4784",
        },
        {
            "filename": "manual-baabda.png",
            "stream": make_image("PNG"),
            "lat": "33.8203",
            "lng": "35.4878",
        },
        {
            "filename": "gps-tripoli.jpg",
            "stream": make_image("JPEG", gps=(34.4346, 35.8362)),
        },
        {
            "filename": "manual-sidon.jpg",
            "stream": make_image("JPEG"),
            "lat": "33.5571",
            "lng": "35.3729",
        },
    ]

    for expected_id, case in enumerate(cases, start=1):
        form_data = {"image": (case["stream"], case["filename"])}
        if "lat" in case:
            form_data["lat"] = case["lat"]
            form_data["lng"] = case["lng"]

        response = client.post(
            "/api/reports",
            data=form_data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        payload = response.get_json()
        assert payload["report"]["id"] == expected_id

        detail_response = client.get(payload["redirect_url"])
        assert detail_response.status_code == 200
        assert f"Report #{expected_id}".encode() in detail_response.data

    with app.app_context():
        assert Report.query.count() == 5
        assert Detection.query.count() == 3
        assert Report.query.filter_by(detection_status="completed").count() == 3
        assert Report.query.filter_by(detection_status="pending").count() == 2
        assert {report.location_source for report in Report.query.all()} == {
            "gps",
            "manual",
        }
