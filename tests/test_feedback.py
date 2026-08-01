import pytest

from app import create_app
from models import FeedbackMessage, db


@pytest.fixture()
def app(tmp_path):
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"

    flask_app = create_app(
        {
            "TESTING": True,
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


def test_contact_modal_has_email_faq_and_feedback_form(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"tariqlb.contact@gmail.com" in response.data
    assert b"Quick answers" in response.data
    assert b"Report Problem" in response.data
    assert b"Contact and feedback form" in response.data
    assert b'aria-haspopup="dialog"' in response.data
    assert b'aria-controls="about-modal"' in response.data
    assert b'aria-expanded="false"' in response.data
    assert b'aria-describedby="home-feedback-help"' in response.data
    assert b'name="name"' in response.data
    assert b'name="email"' in response.data
    assert b'name="message"' in response.data
    assert b'name="report_id"' in response.data


def test_feedback_submission_saves_message(app, client):
    response = client.post(
        "/feedback",
        data={
            "name": "Test User",
            "email": "tester@example.com",
            "message": "The map marker needs a small adjustment.",
            "report_id": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/#support-modal")

    with app.app_context():
        saved_message = FeedbackMessage.query.one()
        assert saved_message.name == "Test User"
        assert saved_message.email == "tester@example.com"
        assert saved_message.message == "The map marker needs a small adjustment."
        assert saved_message.report_id is None


def test_feedback_submission_can_return_to_upload_page(app, client):
    response = client.post(
        "/feedback",
        data={
            "name": "Test User",
            "email": "tester@example.com",
            "message": "The report page FAQ button was not opening.",
            "report_id": "",
            "next": "/upload",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/upload#support-modal")

    with app.app_context():
        assert FeedbackMessage.query.count() == 1


def test_feedback_rejects_unknown_report_id(app, client):
    response = client.post(
        "/feedback",
        data={
            "name": "Test User",
            "email": "tester@example.com",
            "message": "Please check this report.",
            "report_id": "999",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"That report ID does not exist" in response.data

    with app.app_context():
        assert FeedbackMessage.query.count() == 0
