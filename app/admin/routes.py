from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps
import config
from models import Report, Detection, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.all()
    return render_template("admin/dashboard.html", reports=reports)


@admin_bp.route("/api/admin/reports", methods=["GET"])
@login_required
def get_reports():
    status_filter = request.args.get("status")
    if status_filter:
        reports = Report.query.filter_by(status=status_filter).all()
    else:
        reports = Report.query.all()
    result = []
    for report in reports:
        report_data = report.to_dict()
        if report.detections:
            report_data["damage_type"] = report.detections[0].damage_type
            report_data["severity_label"] = report.detections[0].severity_label
            report_data["confidence"] = report.detections[0].confidence
        else:
            report_data["damage_type"] = "No detection yet"
            report_data["severity_label"] = "—"
            report_data["confidence"] = None
        result.append(report_data)
    return {"reports": result}


@admin_bp.route("/api/admin/reports/<int:report_id>", methods=["PATCH"])
@login_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    data = request.get_json()
    new_status = data.get("status")
    if new_status not in config.REPORT_STATUSES:
        return {"error": f"Invalid status. Must be one of: {config.REPORT_STATUSES}"}, 400
    report.status = new_status
    db.session.commit()
    return report.to_dict()


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
    detection = report.detections[0] if report.detections else None
    return render_template("admin/report_detail.html", report=report, detection=detection)