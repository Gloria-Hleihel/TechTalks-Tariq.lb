from flask import Flask

from app.detection.routes import detection_bp


app = Flask(__name__)
app.register_blueprint(detection_bp)


@app.route("/")
def home():
    return {
        "message": "Detection test server is running"
    }


if __name__ == "__main__":
    app.run(debug=True)