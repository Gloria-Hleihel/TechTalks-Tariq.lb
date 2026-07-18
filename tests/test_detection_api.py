from app import create_app


def test_detect_rejects_missing_json():
    app = create_app({"TESTING": True})

    with app.test_client() as client:
        response = client.post("/api/detect")

    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_detect_rejects_missing_image_path():
    app = create_app({"TESTING": True})

    with app.test_client() as client:
        response = client.post(
            "/api/detect",
            json={},
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "MISSING_IMAGE_PATH"


def test_detect_rejects_invalid_report_id():
    app = create_app({"TESTING": True})

    with app.test_client() as client:
        response = client.post(
            "/api/detect",
            json={
                "image_path": "test_images/road1.png",
                "report_id": "abc",
            },
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_REPORT_ID"