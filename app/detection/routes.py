from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.detection.detector import (
    DetectionError,
    ImageNotFoundError,
    InferenceError,
    InvalidImageError,
    InvalidImagePathError,
    ModelLoadError,
    ModelNotFoundError,
    UnsupportedImageTypeError,
    detect_damage,
)
from app.detection.jobs import (
    create_detection_job,
    get_detection_job,
)
from models import Detection, Report, db


detection_bp = Blueprint("detection", __name__)


def error_response(
    message: str,
    status_code: int,
    code: str,
):
    """
    Return API errors using one consistent JSON structure.
    """
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }), status_code


def parse_detection_request():
    """
    Validate and extract image_path and report_id from a JSON request.

    Returns:
        A tuple containing:
            - image_path
            - report_id
            - error response, or None when validation succeeds
    """
    if not request.is_json:
        return None, None, error_response(
            "Content-Type must be application/json.",
            415,
            "UNSUPPORTED_MEDIA_TYPE",
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, None, error_response(
            "Request body must contain valid JSON.",
            400,
            "INVALID_JSON",
        )

    image_path = data.get("image_path")
    report_id = data.get("report_id")

    if not isinstance(image_path, str) or not image_path.strip():
        return None, None, error_response(
            "image_path is required and must be a non-empty string.",
            400,
            "MISSING_IMAGE_PATH",
        )

    image_path = image_path.strip()

    if report_id is not None:
        if isinstance(report_id, bool):
            return None, None, error_response(
                "report_id must be an integer.",
                400,
                "INVALID_REPORT_ID",
            )

        try:
            report_id = int(report_id)
        except (TypeError, ValueError):
            return None, None, error_response(
                "report_id must be an integer.",
                400,
                "INVALID_REPORT_ID",
            )

        if report_id <= 0:
            return None, None, error_response(
                "report_id must be a positive integer.",
                400,
                "INVALID_REPORT_ID",
            )

    return image_path, report_id, None


@detection_bp.route("/api/detect", methods=["POST"])
def detect_api():
    """
    Run road-damage detection synchronously.

    Expected JSON:
    {
        "image_path": "test_images/road1.png",
        "report_id": 1
    }

    report_id is optional. When included, the result is saved to the
    database and linked to that report.
    """
    image_path, report_id, validation_error = (
        parse_detection_request()
    )

    if validation_error is not None:
        return validation_error

    try:
        detection_result = detect_damage(image_path)

    except InvalidImagePathError:
        return error_response(
            "The supplied image path is invalid.",
            400,
            "INVALID_IMAGE_PATH",
        )

    except ImageNotFoundError:
        return error_response(
            "The requested image could not be found.",
            404,
            "IMAGE_NOT_FOUND",
        )

    except UnsupportedImageTypeError:
        return error_response(
            "Only JPG, JPEG, and PNG images are supported.",
            415,
            "UNSUPPORTED_IMAGE_TYPE",
        )

    except InvalidImageError:
        return error_response(
            "The supplied file is not a valid or readable image.",
            422,
            "INVALID_IMAGE",
        )

    except ModelNotFoundError:
        return error_response(
            "The detection model is currently unavailable.",
            503,
            "MODEL_NOT_FOUND",
        )

    except ModelLoadError:
        return error_response(
            "The detection model could not be initialized.",
            503,
            "MODEL_LOAD_FAILED",
        )

    except InferenceError:
        return error_response(
            "The image could not be analyzed.",
            500,
            "INFERENCE_FAILED",
        )

    except DetectionError:
        return error_response(
            "Detection could not be completed.",
            500,
            "DETECTION_FAILED",
        )

    except Exception:
        return error_response(
            "An unexpected server error occurred.",
            500,
            "INTERNAL_SERVER_ERROR",
        )

    response = {
        "success": True,
        "report_id": report_id,
        "damage_type": detection_result.get(
            "damage_type",
            "None",
        ),
        "confidence": detection_result.get(
            "confidence",
            0.0,
        ),
        "severity_score": detection_result.get(
            "severity_score",
            0,
        ),
        "severity_label": detection_result.get(
            "severity_label",
            "Low",
        ),
        "bounding_boxes": detection_result.get(
            "bounding_boxes",
            [],
        ),
        "annotated_image_path": detection_result.get(
            "annotated_image_path",
        ),
        "message": detection_result.get(
            "message",
            "Detection completed.",
        ),
        "saved_to_db": False,
    }

    if report_id is not None:
        report = db.session.get(Report, report_id)

        if report is None:
            return error_response(
                "The specified report does not exist.",
                404,
                "REPORT_NOT_FOUND",
            )

        try:
            detection = Detection(
                report_id=report_id,
                damage_type=response["damage_type"],
                confidence=response["confidence"],
                severity_score=response["severity_score"],
                severity_label=response["severity_label"],
                annotated_image_path=response[
                    "annotated_image_path"
                ],
            )

            db.session.add(detection)
            db.session.commit()

            response["detection_id"] = detection.id
            response["saved_to_db"] = True

        except SQLAlchemyError:
            db.session.rollback()

            return error_response(
                "Detection completed, but the result could not be saved.",
                500,
                "DATABASE_SAVE_FAILED",
            )

    return jsonify(response), 200


@detection_bp.route("/api/detect/jobs", methods=["POST"])
def create_detect_job_api():
    """
    Create an asynchronous road-damage detection job.

    The request returns immediately with HTTP 202 and a job ID.
    The frontend can then poll the status URL until the job finishes.

    Expected JSON:
    {
        "image_path": "test_images/road1.png",
        "report_id": 1
    }
    """
    image_path, report_id, validation_error = (
        parse_detection_request()
    )

    if validation_error is not None:
        return validation_error

    app = current_app._get_current_object()

    job = create_detection_job(
        app=app,
        image_path=image_path,
        report_id=report_id,
    )

    return jsonify({
        "success": True,
        "message": "Detection job accepted.",
        "job": job,
        "status_url": f"/api/detect/jobs/{job['job_id']}",
    }), 202


@detection_bp.route(
    "/api/detect/jobs/<string:job_id>",
    methods=["GET"],
)
def get_detect_job_api(job_id: str):
    """
    Return the current state and result of a detection job.

    Possible statuses:
        queued
        processing
        completed
        failed
    """
    job = get_detection_job(job_id)

    if job is None:
        return error_response(
            "The requested detection job does not exist.",
            404,
            "JOB_NOT_FOUND",
        )

    return jsonify({
        "success": True,
        "job": job,
    }), 200