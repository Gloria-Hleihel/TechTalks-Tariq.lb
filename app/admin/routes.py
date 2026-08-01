from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

import config
from models import Detection, Report, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)

    return decorated_function


def _best_detection(report):
    if not report.detections:
        return None
    return max(report.detections, key=lambda detection: detection.confidence)


def _asset_url(path):
    if not path:
        return None

    normalized = path.replace("\\", "/").lstrip("/")
    if normalized.startswith("static/"):
        normalized = normalized[len("static/"):]

    return url_for("static", filename=normalized)


def _report_payload(report):
    detection = _best_detection(report)
    created_at = report.created_at

    payload = {
        "id": report.id,
        "lat": report.lat,
        "lng": report.lng,
        "location": f"{report.lat:.5f}, {report.lng:.5f}",
        "location_source": report.location_source,
        "status": report.status,
        "created_at": created_at.isoformat() if created_at else None,
        "date_label": created_at.strftime("%Y-%m-%d") if created_at else "",
        "image_path": report.image_path,
        "image_url": _asset_url(report.image_path),
        "detail_url": url_for("admin.report_detail", report_id=report.id),
        "damage_type": "No detection yet",
        "severity_label": "Unrated",
        "severity_score": None,
        "confidence": None,
        "annotated_image_path": None,
        "annotated_image_url": None,
    }

    if detection:
        payload.update(
            {
                "damage_type": detection.damage_type,
                "severity_label": detection.severity_label,
                "severity_score": detection.severity_score,
                "confidence": detection.confidence,
                "annotated_image_path": detection.annotated_image_path,
                "annotated_image_url": _asset_url(
                    detection.annotated_image_path
                ),
            }
        )

    return payload


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        error = "Invalid credentials"
    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.order_by(Report.created_at.desc()).all()

    for report in reports:
        report.best_detection = _best_detection(report)

    total_reports = Report.query.count()
    latest_report = Report.query.order_by(Report.created_at.desc()).first()

    severity_counts = {
        "Low": Detection.query.filter_by(severity_label="Low").count(),
        "Medium": Detection.query.filter_by(severity_label="Medium").count(),
        "High": Detection.query.filter_by(severity_label="High").count(),
        "Critical": Detection.query.filter_by(severity_label="Critical").count(),
    }

    damage_counts = {
        "Longitudinal Crack": Detection.query.filter_by(
            damage_type="Longitudinal Crack"
        ).count(),
        "Transverse Crack": Detection.query.filter_by(
            damage_type="Transverse Crack"
        ).count(),
        "Alligator Crack": Detection.query.filter_by(
            damage_type="Alligator Crack"
        ).count(),
        "Potholes": Detection.query.filter_by(damage_type="Potholes").count(),
        "None": Detection.query.filter_by(damage_type="None").count(),
    }

    status_counts = {
        status: Report.query.filter_by(status=status).count()
        for status in config.REPORT_STATUSES
    }

    return render_template(
        "admin/dashboard.html",
        reports=reports,
        reports_payload=[_report_payload(report) for report in reports],
        total_reports=total_reports,
        severity_counts=severity_counts,
        damage_counts=damage_counts,
        status_counts=status_counts,
        report_statuses=config.REPORT_STATUSES,
        latest_report=latest_report,
    )


@admin_bp.route("/reports", methods=["GET"])
@login_required
def get_reports():
    status_filter = request.args.get("status")
    if status_filter:
        reports = Report.query.filter_by(status=status_filter).all()
    else:
        reports = Report.query.all()

    return {"reports": [_report_payload(report) for report in reports]}


@admin_bp.route("/reports/<int:report_id>", methods=["PATCH"])
@login_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    data = request.get_json(silent=True)
    if not data:
        return {"error": "Invalid or missing JSON body"}, 400

    new_status = data.get("status")
    if new_status not in config.REPORT_STATUSES:
        return {
            "error": f"Invalid status. Must be one of: {config.REPORT_STATUSES}"
        }, 400

    report.status = new_status
    db.session.commit()
    return _report_payload(report)


@admin_bp.route("/update/<int:report_id>", methods=["POST"])
@login_required
def update_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get("status")
    if new_status in config.REPORT_STATUSES:
        report.status = new_status
        db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete/<int:report_id>", methods=["POST"])
@login_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/reports/<int:report_id>")
@login_required
def report_detail(report_id):
    report = Report.query.get_or_404(report_id)
    detection = _best_detection(report)
    return render_template(
        "admin/report_detail.html",
        report=report,
        detection=detection,
    )
