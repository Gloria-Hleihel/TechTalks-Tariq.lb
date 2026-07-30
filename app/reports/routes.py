import os

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.reports import bp
from app.utils.detection_client import trigger_detection
from app.utils.exif import extract_gps
from app.utils.storage import delete_image, get_file_size, save_image
from models import Detection, Report, db


def _manual_coordinates():
    """Parse and validate manual coordinates from the upload form."""
    lat_value = (request.form.get("lat") or "").strip()
    lng_value = (request.form.get("lng") or "").strip()

    if not lat_value or not lng_value:
        return None

    try:
        lat = float(lat_value)
        lng = float(lng_value)
    except ValueError:
        return None

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None

    return lat, lng


def _location_source_from_form() -> str:
    """Return whether fallback coordinates came from the browser or map."""
    source = (request.form.get("location_source") or "manual").strip().lower()

    if source == "browser":
        return "browser"

    return "manual"


def _saved_image_is_allowed(saved_image_path: str) -> bool:
    """
    Validate a previously uploaded image path.

    save_image() returns paths such as uploads/abc123.jpg.
    """
    if not saved_image_path:
        return False

    normalized_path = saved_image_path.replace("\\", "/")

    if not normalized_path.startswith("uploads/"):
        return False

    filename = os.path.basename(normalized_path)

    if not filename:
        return False

    allowed_extensions = {".jpg", ".jpeg", ".png"}
    extension = os.path.splitext(filename)[1].lower()

    return extension in allowed_extensions


@bp.route("/")
def index():
    return redirect(url_for("reports.upload"))


@bp.route("/upload", methods=["GET"])
def upload():
    return render_template("upload.html")


@bp.route("/upload", methods=["POST"])
def create_report():
    """
    Validate an upload, preserve it when location is missing,
    create its Report, run detection, and redirect.
    """
    file = request.files.get("image")
    saved_image_path = (
        request.form.get("saved_image_path") or ""
    ).strip()

    using_saved_image = False

    if file and file.filename:
        file_size = get_file_size(file)
        max_size = current_app.config["MAX_CONTENT_LENGTH"]

        if file_size <= 0:
            flash(
                "The selected file is empty or unreadable.",
                "error",
            )
            return redirect(url_for("reports.upload"))

        if file_size > max_size:
            flash(
                "File is too large. Maximum size is 5MB.",
                "error",
            )
            return redirect(url_for("reports.upload"))

        saved_rel_path = save_image(file)

        if not saved_rel_path:
            flash(
                "Invalid image. Please upload a JPG, JPEG, "
                "or PNG file.",
                "error",
            )
            return redirect(url_for("reports.upload"))

    elif saved_image_path:
        if not _saved_image_is_allowed(saved_image_path):
            flash(
                "The previously uploaded image path is invalid. "
                "Please choose the image again.",
                "error",
            )
            return redirect(url_for("reports.upload"))

        saved_rel_path = saved_image_path.replace("\\", "/")
        using_saved_image = True

    else:
        flash(
            "Please choose an image to upload.",
            "error",
        )
        return redirect(url_for("reports.upload"))

    saved_abs_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        os.path.basename(saved_rel_path),
    )

    if using_saved_image and not os.path.isfile(saved_abs_path):
        flash(
            "The previously uploaded image could not be found. "
            "Please choose it again.",
            "error",
        )
        return redirect(url_for("reports.upload"))

    gps = extract_gps(saved_abs_path)

    if gps:
        lat, lng = gps
        location_source = "gps"

    else:
        manual = _manual_coordinates()

        if manual is None:
            flash(
                "No GPS was found. Select a valid location on "
                "the map and submit again. Your uploaded image "
                "has been kept.",
                "error",
            )

            return render_template(
                "upload.html",
                saved_image_path=saved_rel_path,
                saved_image_name=os.path.basename(
                    saved_rel_path
                ),
            )

        lat, lng = manual
        location_source = _location_source_from_form()

    report = Report(
        image_path=saved_rel_path,
        lat=lat,
        lng=lng,
        location_source=location_source,
        status="pending",
    )

    try:
        db.session.add(report)
        db.session.commit()

    except Exception:
        db.session.rollback()

        if not using_saved_image:
            delete_image(saved_rel_path)

        current_app.logger.exception(
            "Could not create report"
        )

        flash(
            "The report could not be saved. Please try again.",
            "error",
        )

        return render_template(
            "upload.html",
            saved_image_path=saved_rel_path,
            saved_image_name=os.path.basename(
                saved_rel_path
            ),
        )

    detection_result = trigger_detection(
        report,
        saved_abs_path,
    )

    detection_status = detection_result.get("status")

    if detection_status == "completed":
        detection = Detection(
            report_id=report.id,
            damage_type=detection_result["damage_type"],
            confidence=detection_result["confidence"],
            severity_score=detection_result["severity_score"],
            severity_label=detection_result["severity_label"],
            annotated_image_path=detection_result.get(
                "annotated_image_path"
            ),
        )

        try:
            db.session.add(detection)
            db.session.commit()

            flash(
                "Report submitted and detection completed.",
                "success",
            )

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Report %s was saved but its detection "
                "was not",
                report.id,
            )

            flash(
                "Report saved, but the detection result "
                "could not be stored and is pending.",
                "info",
            )

    elif detection_status == "failed":
        current_app.logger.warning(
            "Detection failed for report %s: %s",
            report.id,
            detection_result.get("error"),
        )

        flash(
            "Report saved, but detection failed and remains "
            "pending: "
            f"{detection_result.get('error', 'Unknown error')}",
            "info",
        )

    else:
        flash(
            "Report saved. Detection is pending until the "
            "detector is available.",
            "info",
        )

    return redirect(
        url_for(
            "reports.report_detail",
            report_id=report.id,
        )
    )


@bp.route(
    "/reports/<int:report_id>",
    methods=["GET"],
)
def report_detail(report_id):
    report = db.get_or_404(
        Report,
        report_id,
    )

    detection = (
        report.detections[0]
        if report.detections
        else None
    )

    return render_template(
        "report_detail.html",
        report=report,
        detection=detection,
    )