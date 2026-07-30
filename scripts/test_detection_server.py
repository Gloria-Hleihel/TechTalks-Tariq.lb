from flask import Flask

from app.detection.routes import detection_bp
from models import db, Report


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tariq_test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(detection_bp)


@app.route("/")
def home():
    return {
        "message": "Detection test server is running"
    }


with app.app_context():
    db.create_all()

    if not Report.query.get(1):
        report_1 = Report(
            id=1,
            image_path="test_images/road1.png",
            lat=33.8938,
            lng=35.5018,
            location_source="manual"
        )
        db.session.add(report_1)

    if not Report.query.get(2):
        report_2 = Report(
            id=2,
            image_path="test_images/good.png",
            lat=33.8938,
            lng=35.5018,
            location_source="manual"
        )
        db.session.add(report_2)

    db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)