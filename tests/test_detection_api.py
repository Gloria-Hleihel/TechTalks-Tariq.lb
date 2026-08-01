import pytest

from app import create_app
from models import Detection, Report, db


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
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
    return app.test_client()


def test_detect_rejects_missing_json(client):
    response = client.post("/api/detect")

    assert response.status_code == 415

    result = response.get_json()

    assert result["success"] is False
    assert (
        result["error"]["code"]
        == "UNSUPPORTED_MEDIA_TYPE"
    )


def test_detect_rejects_missing_image_path(client):
    response = client.post(
        "/api/detect",
        json={},
    )

    assert response.status_code == 400

    result = response.get_json()

    assert result["success"] is False
    assert (
        result["error"]["code"]
        == "MISSING_IMAGE_PATH"
    )


def test_detect_rejects_invalid_report_id(client):
    response = client.post(
        "/api/detect",
        json={
            "image_path": "test_images/road1.png",
            "report_id": "abc",
        },
    )

    assert response.status_code == 400

    result = response.get_json()

    assert result["success"] is False
    assert (
        result["error"]["code"]
        == "INVALID_REPORT_ID"
    )


def test_detection_model_preload_uses_cached_loader(monkeypatch):
    from app.detection import detector

    calls = []

    def fake_get_model():
        calls.append("loaded")
        return object()

    monkeypatch.setattr(detector, "get_model", fake_get_model)

    assert detector.preload_model() is True
    assert calls == ["loaded"]


def test_detect_returns_successful_result(
    client,
    monkeypatch,
):
    fake_result = {
        "damage_type": "Potholes",
        "confidence": 0.87,
        "severity_score": 78,
        "severity_label": "Critical",
        "bounding_boxes": [
            {
                "damage_type": "Potholes",
                "confidence": 0.87,
                "bounding_box": [
                    100.0,
                    120.0,
                    300.0,
                    280.0,
                ],
            }
        ],
        "annotated_image_path": (
            "uploads/annotated/road_annotated.jpg"
        ),
        "message": "Road damage detected.",
    }

    monkeypatch.setattr(
        "app.detection.routes.detect_damage",
        lambda _image_path: fake_result,
    )

    response = client.post(
        "/api/detect",
        json={
            "image_path": "test_images/road1.png",
        },
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["success"] is True
    assert result["report_id"] is None
    assert result["damage_type"] == "Potholes"
    assert result["confidence"] == pytest.approx(0.87)
    assert result["severity_score"] == 78
    assert result["severity_label"] == "Critical"
    assert len(result["bounding_boxes"]) == 1
    assert result["saved_to_db"] is False


def test_detect_saves_result_when_report_id_is_given(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        report = Report(
            image_path="uploads/test-road.png",
            lat=33.8938,
            lng=35.5018,
            location_source="manual",
            status="Pending",
        )

        db.session.add(report)
        db.session.commit()

        report_id = report.id

    fake_result = {
        "damage_type": "Longitudinal Crack",
        "confidence": 0.76,
        "severity_score": 34,
        "severity_label": "Medium",
        "bounding_boxes": [],
        "annotated_image_path": (
            "uploads/annotated/test-road.jpg"
        ),
        "message": "Road damage detected.",
    }

    monkeypatch.setattr(
        "app.detection.routes.detect_damage",
        lambda _image_path: fake_result,
    )

    response = client.post(
        "/api/detect",
        json={
            "image_path": "uploads/test-road.png",
            "report_id": report_id,
        },
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["success"] is True
    assert result["report_id"] == report_id
    assert result["saved_to_db"] is True
    assert result["detection_id"] is not None

    with app.app_context():
        detection = Detection.query.filter_by(
            report_id=report_id
        ).first()

        assert detection is not None
        assert (
            detection.damage_type
            == "Longitudinal Crack"
        )
        assert detection.confidence == pytest.approx(
            0.76
        )
        assert detection.severity_score == 34
        assert detection.severity_label == "Medium"


def test_detect_updates_existing_result_for_same_report(
    app,
    client,
    monkeypatch,
):
    with app.app_context():
        report = Report(
            image_path="uploads/test-road.png",
            lat=33.8938,
            lng=35.5018,
            location_source="manual",
            status="pending",
        )
        db.session.add(report)
        db.session.flush()

        detection = Detection(
            report_id=report.id,
            damage_type="Longitudinal Crack",
            confidence=0.31,
            severity_score=22,
            severity_label="Low",
            annotated_image_path="uploads/annotated/old.jpg",
        )
        db.session.add(detection)
        db.session.commit()

        report_id = report.id
        detection_id = detection.id

    fake_result = {
        "damage_type": "Potholes",
        "confidence": 0.91,
        "severity_score": 82,
        "severity_label": "Critical",
        "bounding_boxes": [],
        "annotated_image_path": "uploads/annotated/new.jpg",
        "message": "Road damage detected.",
    }

    monkeypatch.setattr(
        "app.detection.routes.detect_damage",
        lambda _image_path: fake_result,
    )

    response = client.post(
        "/api/detect",
        json={
            "image_path": "uploads/test-road.png",
            "report_id": report_id,
        },
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["detection_id"] == detection_id

    with app.app_context():
        detections = Detection.query.filter_by(report_id=report_id).all()
        report = db.session.get(Report, report_id)

        assert len(detections) == 1
        assert detections[0].damage_type == "Potholes"
        assert detections[0].confidence == pytest.approx(0.91)
        assert report.detection_status == "completed"
        assert report.detection_error is None


def test_detect_rejects_missing_report(
    client,
    monkeypatch,
):
    fake_result = {
        "damage_type": "None",
        "confidence": 0.0,
        "severity_score": 0,
        "severity_label": "Low",
        "bounding_boxes": [],
        "annotated_image_path": None,
        "message": "No road damage detected.",
    }

    monkeypatch.setattr(
        "app.detection.routes.detect_damage",
        lambda _image_path: fake_result,
    )

    response = client.post(
        "/api/detect",
        json={
            "image_path": "test_images/road1.png",
            "report_id": 999,
        },
    )

    assert response.status_code == 404

    result = response.get_json()

    assert result["success"] is False
    assert result["error"]["code"] == "REPORT_NOT_FOUND"
