"""
app.py — Tariq.lb Flask application (Gloria's Week 2 dev version)
This is a self-contained app so the map/API work can be built and tested
against Zahraa's real models + seed data, without waiting on Malek's
final bootstrap. The /api/reports route here is the deliverable; it can
later be merged into the team's shared app.py.
"""
from flask import Flask, jsonify, request, render_template
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


@app.route("/")
def home():
    return "Tariq.lb API running"


@app.route("/map")
def map_page():
    return render_template("map.html")


if __name__ == "__main__":
    app.run(debug=True)