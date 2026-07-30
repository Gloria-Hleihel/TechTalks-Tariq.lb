"""
app.py — Tariq.lb Flask application (Gloria's Week 2 dev version)
"""
from flask import Flask, jsonify, request, render_template, abort

import config
from models import db, Report, Detection

app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)


@app.route("/api/reports")
def api_reports():
    severity = request.args.get("severity")
    damage_type = request.args.get("damage_type")

    query = db.session.query(Report, Detection).join(
        Detection, Detection.report_id == Report.id
    )

    if severity:
        query = query.filter(Detection.severity_label == severity)
    if damage_type:
        query = query.filter(Detection.damage_type == damage_type)

    results = []
    for report, detection in query.all():
        results.append({
            "id": report.id,
            "lat": report.lat,
            "lng": report.lng,
            "damage_type": detection.damage_type,
            "severity_label": detection.severity_label,
            "date": report.created_at.isoformat(),
        })

    return jsonify(results)


@app.route("/api/reports/<int:report_id>")
def api_report_detail(report_id):
    report = Report.query.get(report_id)
    if report is None:
        abort(404, description="Report not found")

    detection = report.detections[0] if report.detections else None

    data = {
        "id": report.id,
        "lat": report.lat,
        "lng": report.lng,
        "image_path": report.image_path,
        "location_source": report.location_source,
        "status": report.status,
        "date": report.created_at.isoformat(),
        "damage_type": detection.damage_type if detection else None,
        "confidence": detection.confidence if detection else None,
        "severity_score": detection.severity_score if detection else None,
        "severity_label": detection.severity_label if detection else None,
        "annotated_image_path": detection.annotated_image_path if detection else None,
    }

    return jsonify(data)


@app.route("/reports/<int:report_id>")
def report_detail_page(report_id):
    report = Report.query.get(report_id)
    if report is None:
        abort(404, description="Report not found")

    detection = report.detections[0] if report.detections else None
    return render_template("report_detail.html", report=report, detection=detection)


@app.route("/")
def home():
    return "Tariq.lb API running"


@app.route("/map")
def map_page():
    return render_template("map.html")


if __name__ == "__main__":
    app.run(debug=True)