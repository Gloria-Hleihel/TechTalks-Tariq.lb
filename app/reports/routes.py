import os
from dataclasses import dataclass

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.reports import bp
from app.utils.detection_client import trigger_detection
from app.utils.exif import GPSExtractionError, extract_gps
from app.utils.storage import (
    allowed_file,
    delete_image,
    get_file_size,
    save_image,
)
from models import Detection, Report, db


@dataclass
class SubmissionError(Exception):
    """A user-correctable report-submission failure."""

    message: str
    status_code: int = 400
    field: str | None = None
    saved_image_path: str | None = None

    def __str__(self) -> str:
        return self.message


def _manual_coordinates():
    """Parse and validate manual coordinates."""
    lat_value = (
        request.form.get("lat")
        or ""
    ).strip()

    lng_value = (
        request.form.get("lng")
        or ""
    ).strip()

    if not lat_value or not lng_value:
        return None

    try:
        lat = float(lat_value)
        lng = float(lng_value)
    except ValueError:
        return None

    if not (
        -90 <= lat <= 90
        and -180 <= lng <= 180
    ):
        return None

    return lat, lng


def _absolute_upload_path(
    relative_path: str,
) -> str:
    """Convert a stored upload path into an absolute file path."""
    return os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        os.path.basename(relative_path),
    )


def _location_source_from_form() -> str:
    """Return whether fallback coordinates came from the browser or map."""
    source = (
        request.form.get("location_source")
        or "manual"
    ).strip().lower()

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

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
    }

    extension = os.path.splitext(filename)[1].lower()

    return extension in allowed_extensions


def _mark_detection_pending(
    report: Report,
    error: str,
) -> None:
    """Store a retryable detection failure."""
    report.detection_status = "pending"

    report.detection_error = (
        error
        or "Detection did not complete."
    )[:500]

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Could not save pending detection "
            "state for report %s",
            report.id,
        )


def _save_detection(
    report: Report,
    result: dict,
) -> bool:
    """Create or update a Detection result."""
    if report.detections:
        detection = report.detections[0]
    else:
        detection = Detection(
            report_id=report.id,
        )

    detection.damage_type = result[
        "damage_type"
    ]

    detection.confidence = result[
        "confidence"
    ]

    detection.severity_score = result[
        "severity_score"
    ]

    detection.severity_label = result[
        "severity_label"
    ]

    detection.annotated_image_path = result.get(
        "annotated_image_path"
    )

    report.detection_status = "completed"
    report.detection_error = None

    try:
        db.session.add(detection)
        db.session.commit()

        return True

    except Exception as exc:
        db.session.rollback()

        current_app.logger.exception(
            "Report %s was saved but its detection "
            "could not be stored",
            report.id,
        )

        _mark_detection_pending(
            report,
            f"Detection result could not be stored: {exc}",
        )

        return False


def _process_detection(
    report: Report,
    image_path: str,
) -> dict:
    """Run detection and always preserve the Report."""
    try:
        result = trigger_detection(
            report,
            image_path,
        )

    except Exception as exc:
        current_app.logger.exception(
            "Unexpected detection integration error "
            "for report %s",
            report.id,
        )

        result = {
            "status": "pending",
            "error": (
                "Unexpected detection integration error: "
                f"{exc}"
            ),
            "user_message": (
                "Your report was saved, but detection "
                "could not be started. "
                "Please retry detection later."
            ),
        }

    if (
        result.get("status") == "completed"
        and _save_detection(report, result)
    ):
        return {
            "status": "completed",
            "user_message": (
                "Report submitted and detection completed."
            ),
        }

    error = str(
        result.get("error")
        or "Detection did not complete."
    )

    _mark_detection_pending(
        report,
        error,
    )

    return {
        "status": "pending",
        "user_message": (
            result.get("user_message")
            or (
                "Your report was saved, but detection "
                "is pending. Please retry detection later."
            )
        ),
    }


def _validate_and_save_upload():
    """
    Validate and save the uploaded image.

    Supports two cases:
    1. New image uploaded by the user.
    2. Previously saved image reused after missing-location fallback.
    """
    file = request.files.get("image")

    saved_image_path = (
        request.form.get("saved_image_path")
        or ""
    ).strip()

    using_saved_image = False

    if file and file.filename:
        if not allowed_file(file.filename):
            raise SubmissionError(
                "Unsupported file type. "
                "Choose a JPG, JPEG, or PNG image.",
                field="image",
            )

        file_size = get_file_size(file)

        max_size = current_app.config[
            "MAX_CONTENT_LENGTH"
        ]

        if file_size <= 0:
            raise SubmissionError(
                "The selected file is empty or unreadable. "
                "Choose another image.",
                field="image",
            )

        if file_size > max_size:
            raise SubmissionError(
                "The image is larger than 5MB. "
                "Compress it or choose a smaller image.",
                status_code=413,
                field="image",
            )

        try:
            saved_rel_path = save_image(file)

        except OSError as exc:
            current_app.logger.exception(
                "Could not save uploaded image"
            )

            raise SubmissionError(
                "The image could not be saved. "
                "Check storage permissions and try again.",
                status_code=500,
                field="image",
            ) from exc

        if not saved_rel_path:
            raise SubmissionError(
                "The file is not a valid JPG or PNG image. "
                "Choose a different file.",
                field="image",
            )

    elif saved_image_path:
        if not _saved_image_is_allowed(saved_image_path):
            raise SubmissionError(
                "The previously uploaded image path is invalid. "
                "Please choose the image again.",
                field="image",
            )

        saved_rel_path = saved_image_path.replace("\\", "/")
        using_saved_image = True

    else:
        raise SubmissionError(
            "Please choose a JPG, JPEG, or PNG road image.",
            field="image",
        )

    saved_abs_path = _absolute_upload_path(
        saved_rel_path
    )

    if using_saved_image and not os.path.isfile(saved_abs_path):
        raise SubmissionError(
            "The previously uploaded image could not be found. "
            "Please choose it again.",
            field="image",
        )

    return (
        saved_rel_path,
        saved_abs_path,
        using_saved_image,
    )


def _resolve_location(
    saved_rel_path: str,
    saved_abs_path: str,
):
    """Use GPS first and manual/browser coordinates as fallback."""
    manual = _manual_coordinates()
    gps_warning = None

    try:
        gps = extract_gps(
            saved_abs_path
        )

    except GPSExtractionError as exc:
        gps = None
        gps_warning = str(exc)

        current_app.logger.warning(
            "GPS extraction failed for %s: %s",
            saved_rel_path,
            exc,
        )

    if gps:
        lat, lng = gps

        return (
            lat,
            lng,
            "gps",
            gps_warning,
        )

    if manual:
        lat, lng = manual

        return (
            lat,
            lng,
            _location_source_from_form(),
            gps_warning,
        )

    if gps_warning:
        message = (
            f"{gps_warning} "
            "Select the road location on the map "
            "and submit again. Your uploaded image "
            "has been kept."
        )
    else:
        message = (
            "No GPS location was found. "
            "Click the map to select the road location, "
            "then submit again. Your uploaded image "
            "has been kept."
        )

    raise SubmissionError(
        message,
        field="location",
        saved_image_path=saved_rel_path,
    )


def _create_report_submission():
    """Create a report from the current multipart request."""
    (
        saved_rel_path,
        saved_abs_path,
        using_saved_image,
    ) = _validate_and_save_upload()

    try:
        (
            lat,
            lng,
            location_source,
            gps_warning,
        ) = _resolve_location(
            saved_rel_path,
            saved_abs_path,
        )

    except SubmissionError:
        raise

    except Exception as exc:
        if not using_saved_image:
            delete_image(
                saved_rel_path
            )

        current_app.logger.exception(
            "Unexpected location processing failure"
        )

        raise SubmissionError(
            "The image location could not be processed. "
            "Select a map location and try again.",
            status_code=500,
            field="location",
        ) from exc

    report = Report(
        image_path=saved_rel_path,
        lat=lat,
        lng=lng,
        location_source=location_source,
        status="pending",
        detection_status="pending",
        detection_error=None,
    )

    try:
        db.session.add(report)
        db.session.commit()

    except Exception as exc:
        db.session.rollback()

        if not using_saved_image:
            delete_image(
                saved_rel_path
            )

        current_app.logger.exception(
            "Could not create report"
        )

        raise SubmissionError(
            "The report could not be saved. "
            "Please try again.",
            status_code=500,
        ) from exc

    detection_result = _process_detection(
        report,
        saved_abs_path,
    )

    return (
        report,
        detection_result,
        gps_warning,
    )


def _report_api_payload(
    report: Report,
) -> dict:
    """Return the JSON representation for the API."""
    if report.detections:
        detection = report.detections[0]
    else:
        detection = None

    return {
        "id": report.id,
        "image_path": report.image_path,
        "lat": report.lat,
        "lng": report.lng,
        "location_source": report.location_source,
        "status": report.status,
        "detection_status": report.detection_status,
        "detection_error": report.detection_error,
        "detection": (
            detection.to_dict()
            if detection
            else None
        ),
        "detail_url": url_for(
            "reports.report_detail",
            report_id=report.id,
        ),
    }


@bp.route("/")
def index():
    return redirect(
        url_for("reports.upload")
    )


@bp.route(
    "/upload",
    methods=["GET"],
)
def upload():
    return render_template(
        "upload.html",
        estimated_wait_seconds=(
            current_app.config.get(
                "DETECTION_ESTIMATED_WAIT_SECONDS",
                15,
            )
        ),
    )


@bp.route(
    "/upload",
    methods=["POST"],
)
def create_report():
    """
    Normal HTML fallback when JavaScript is disabled.
    """
    try:
        (
            report,
            detection_result,
            gps_warning,
        ) = _create_report_submission()

    except SubmissionError as exc:
        flash(
            exc.message,
            "error",
        )

        if (
            exc.field == "location"
            and exc.saved_image_path
        ):
            return render_template(
                "upload.html",
                saved_image_path=exc.saved_image_path,
                saved_image_name=os.path.basename(
                    exc.saved_image_path
                ),
                estimated_wait_seconds=(
                    current_app.config.get(
                        "DETECTION_ESTIMATED_WAIT_SECONDS",
                        15,
                    )
                ),
            )

        return redirect(
            url_for("reports.upload")
        )

    if (
        gps_warning
        and report.location_source != "gps"
    ):
        flash(
            "The photo GPS metadata could not be read, "
            "so your selected location was used.",
            "info",
        )

    category = (
        "success"
        if detection_result["status"] == "completed"
        else "info"
    )

    flash(
        detection_result["user_message"],
        category,
    )

    return redirect(
        url_for(
            "reports.report_detail",
            report_id=report.id,
        )
    )


@bp.route(
    "/api/reports",
    methods=["POST"],
)
def api_create_report():
    """Create a Report and return a JSON result."""
    try:
        (
            report,
            detection_result,
            gps_warning,
        ) = _create_report_submission()

    except SubmissionError as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": exc.message,
                    "field": exc.field,
                    "saved_image_path": exc.saved_image_path,
                }
            ),
            exc.status_code,
        )

    warning = None

    if (
        gps_warning
        and report.location_source != "gps"
    ):
        warning = (
            "The photo GPS metadata could not be read, "
            "so your selected location was used."
        )

    return (
        jsonify(
            {
                "ok": True,
                "message": detection_result[
                    "user_message"
                ],
                "warning": warning,
                "estimated_wait_seconds": (
                    current_app.config.get(
                        "DETECTION_ESTIMATED_WAIT_SECONDS",
                        15,
                    )
                ),
                "report": _report_api_payload(report),
                "redirect_url": url_for(
                    "reports.report_detail",
                    report_id=report.id,
                ),
            }
        ),
        201,
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


@bp.route("/map", methods=["GET"])
def map_page():
    return render_template("map.html")


@bp.route("/api/reports", methods=["GET"])
def api_reports():
    severity = (
        request.args.get("severity")
        or ""
    ).strip()

    damage_type = (
        request.args.get("damage_type")
        or ""
    ).strip()

    query = db.session.query(
        Report,
        Detection,
    ).outerjoin(
        Detection,
        Detection.report_id == Report.id,
    )

    if severity:
        query = query.filter(
            Detection.severity_label == severity
        )

    if damage_type:
        query = query.filter(
            Detection.damage_type == damage_type
        )

    results = []

    for report, detection in query.all():
        results.append(
            {
                "id": report.id,
                "lat": report.lat,
                "lng": report.lng,
                "status": report.status,
                "location_source": report.location_source,
                "damage_type": (
                    detection.damage_type
                    if detection
                    else None
                ),
                "severity_label": (
                    detection.severity_label
                    if detection
                    else None
                ),
                "date": (
                    report.created_at.isoformat()
                    if report.created_at
                    else None
                ),
            }
        )

    return jsonify(results)


@bp.route(
    "/api/reports/<int:report_id>",
    methods=["GET"],
)
def api_report_detail(report_id):
    report = db.get_or_404(
        Report,
        report_id,
    )

    detection = (
        report.detections[0]
        if report.detections
        else None
    )

    return jsonify(
        {
            "id": report.id,
            "lat": report.lat,
            "lng": report.lng,
            "image_path": report.image_path,
            "location_source": report.location_source,
            "status": report.status,
            "date": (
                report.created_at.isoformat()
                if report.created_at
                else None
            ),
            "damage_type": (
                detection.damage_type
                if detection
                else None
            ),
            "confidence": (
                detection.confidence
                if detection
                else None
            ),
            "severity_score": (
                detection.severity_score
                if detection
                else None
            ),
            "severity_label": (
                detection.severity_label
                if detection
                else None
            ),
            "annotated_image_path": (
                detection.annotated_image_path
                if detection
                else None
            ),
        }
    )


@bp.route(
    "/reports/<int:report_id>/retry-detection",
    methods=["POST"],
)
def retry_detection(report_id):
    """Retry a pending detection."""
    report = db.get_or_404(
        Report,
        report_id,
    )

    if (
        report.detection_status == "completed"
        and report.detections
    ):
        flash(
            "Detection has already completed "
            "for this report.",
            "info",
        )

        return redirect(
            url_for(
                "reports.report_detail",
                report_id=report.id,
            )
        )

    image_path = _absolute_upload_path(
        report.image_path
    )

    if not os.path.isfile(image_path):
        _mark_detection_pending(
            report,
            "Uploaded image is missing from storage.",
        )

        flash(
            "Detection cannot be retried because "
            "the uploaded image is missing.",
            "error",
        )

        return redirect(
            url_for(
                "reports.report_detail",
                report_id=report.id,
            )
        )

    result = _process_detection(
        report,
        image_path,
    )

    category = (
        "success"
        if result["status"] == "completed"
        else "info"
    )

    flash(
        result["user_message"],
        category,
    )

    return redirect(
        url_for(
            "reports.report_detail",
            report_id=report.id,
        )
    )