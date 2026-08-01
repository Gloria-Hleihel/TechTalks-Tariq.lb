from functools import wraps
from hmac import compare_digest

from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from werkzeug.security import check_password_hash

import config
from app.security import require_csrf, validate_csrf_token
from models import Detection, Report, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def login_required(view):
    @wraps(view)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return decorated_function


def _valid_admin_credentials(username: str | None, password: str | None) -> bool:
    """Validate admin credentials without leaking timing differences."""
    submitted_username = username or ""
    submitted_password = password or ""
    username_ok = compare_digest(submitted_username, config.ADMIN_USERNAME)

    if config.ADMIN_PASSWORD_HASH:
        password_ok = check_password_hash(
            config.ADMIN_PASSWORD_HASH,
            submitted_password,
        )
    else:
        password_ok = compare_digest(submitted_password, config.ADMIN_PASSWORD)

    return username_ok and password_ok


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


def _count_by_column(model, column, expected_values):
    counts = {value: 0 for value in expected_values}
    rows = db.session.query(column, func.count(model.id)).group_by(column).all()

    for value, count in rows:
        if value in counts:
            counts[value] = count

    return counts


def _get_report_or_404(report_id: int, with_detections: bool = False) -> Report:
    options = [selectinload(Report.detections)] if with_detections else None
    report = db.session.get(Report, report_id, options=options)

    if report is None:
        abort(404)

    return report


@admin_bp.route("")
@admin_bp.route("/")
def admin_root():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        validate_csrf_token()
        username = request.form.get("username")
        password = request.form.get("password")

        if _valid_admin_credentials(username, password):
            session.clear()
            session.permanent = True
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))

        error = "Invalid credentials"

    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    reports = (
        Report.query.options(selectinload(Report.detections))
        .order_by(Report.created_at.desc())
        .all()
    )

    for report in reports:
        report.best_detection = _best_detection(report)

    total_reports = len(reports)
    latest_report = reports[0] if reports else None
    severity_counts = _count_by_column(
        Detection,
        Detection.severity_label,
        config.SEVERITY_LEVELS,
    )
    damage_counts = _count_by_column(
        Detection,
        Detection.damage_type,
        config.DAMAGE_TYPES,
    )
    status_counts = _count_by_column(
        Report,
        Report.status,
        config.REPORT_STATUSES,
    )

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
    status_filter = (request.args.get("status") or "").strip()

    if status_filter and status_filter not in config.REPORT_STATUSES:
        return {
            "error": f"Invalid status. Must be one of: {config.REPORT_STATUSES}"
        }, 400

    query = Report.query.options(selectinload(Report.detections))

    if status_filter:
        query = query.filter_by(status=status_filter)

    reports = query.order_by(Report.created_at.desc()).all()
    return {"reports": [_report_payload(report) for report in reports]}


@admin_bp.route("/reports/<int:report_id>", methods=["PATCH"])
@login_required
@require_csrf
def update_report_status(report_id):
    report = _get_report_or_404(report_id, with_detections=True)
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
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
@require_csrf
def update_status(report_id):
    report = _get_report_or_404(report_id)
    new_status = request.form.get("status")

    if new_status in config.REPORT_STATUSES:
        report.status = new_status
        db.session.commit()

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete/<int:report_id>", methods=["POST"])
@login_required
@require_csrf
def delete_report(report_id):
    report = _get_report_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/reports/<int:report_id>")
@login_required
def report_detail(report_id):
    report = _get_report_or_404(report_id, with_detections=True)
    detection = _best_detection(report)
    return render_template(
        "admin/report_detail.html",
        report=report,
        detection=detection,
    )
