"""
Tariq.lb -- Flask application entry point.

MVP scope (per PRD Section 5), with AI detection mocked (see detection.py):
  - Upload road photo
  - "YOLOv8" detection (mocked -- see detection.py for why and how to swap in)
  - Damage classification (mocked)
  - Severity score (mocked)
  - EXIF GPS extraction (real, via Pillow)
  - Manual map-pin fallback (real)
  - Save report to database (real, plain SQLite -- see models.py)
  - Leaflet map display (real)
  - View report details (real)

NOTE on tech stack: the PRD suggests Flask-SQLAlchemy and Flask-CORS
(Section 12). This environment has no package-install access, so the
app uses Flask's built-in capabilities plus Python's stdlib sqlite3
instead (see models.py). Functionally equivalent for this MVP; CORS
middleware isn't needed since the frontend and API are served from
the same Flask app (same origin).
"""
import os
import uuid
from flask import Flask, render_template, request, jsonify, abort
from werkzeug.utils import secure_filename

import models
from detection import run_detection
from gps_utils import extract_gps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DB_PATH = os.path.join(BASE_DIR, "tariq.db")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# Default map center: Beirut, Lebanon
DEFAULT_LAT = 33.8938
DEFAULT_LON = 35.5018


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    models.init_db(DB_PATH)

    register_routes(app)
    return app


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def register_routes(app):

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            default_lat=DEFAULT_LAT,
            default_lon=DEFAULT_LON,
        )

    @app.route("/report/<int:report_id>")
    def report_detail(report_id):
        report = models.get_report(report_id)
        if not report:
            abort(404)
        return render_template("report.html", report=report)

    # ---------- API ----------

    @app.route("/api/reports", methods=["GET"])
    def api_list_reports():
        return jsonify(models.list_reports())

    @app.route("/api/reports/<int:report_id>", methods=["GET"])
    def api_get_report(report_id):
        report = models.get_report(report_id)
        if not report:
            return jsonify({"error": "Report not found."}), 404
        return jsonify(report)

    @app.route("/api/reports", methods=["POST"])
    def api_create_report():
        if "image" not in request.files:
            return jsonify({"error": "No image file provided."}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No image selected."}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Unsupported file type. Use JPG or PNG."}), 400

        # If this is a retry after a manual-pin prompt, reuse the
        # already-uploaded file instead of saving a duplicate.
        existing_filename = request.form.get("existing_image_filename")

        if existing_filename:
            unique_name = secure_filename(existing_filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        else:
            ext = file.filename.rsplit(".", 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)

        # Try EXIF GPS extraction first
        gps_coords = extract_gps(save_path)

        if gps_coords:
            latitude, longitude = gps_coords
            location_source = "exif"
        else:
            manual_lat = request.form.get("manual_lat")
            manual_lon = request.form.get("manual_lon")
            if manual_lat is None or manual_lon is None:
                # No GPS in image and no manual pin given yet --
                # tell the client so it can prompt for manual placement.
                return jsonify({
                    "error": "no_gps",
                    "message": "No GPS data found in image. Please select a location manually.",
                    "image_filename": unique_name,
                }), 422
            try:
                latitude = float(manual_lat)
                longitude = float(manual_lon)
            except ValueError:
                return jsonify({"error": "Invalid manual coordinates."}), 400
            location_source = "manual"

        # Run (mocked) detection -- see detection.py
        detection_result = run_detection(save_path)

        report = models.create_report(
            image_filename=unique_name,
            damage_type=detection_result["damage_type"],
            confidence_score=detection_result["confidence_score"],
            severity_level=detection_result["severity_level"],
            severity_score=detection_result["severity_score"],
            latitude=latitude,
            longitude=longitude,
            location_source=location_source,
        )

        return jsonify(report), 201


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
