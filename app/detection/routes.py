from flask import Blueprint, jsonify, request
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
from models import db, Detection, Report


detection_bp = Blueprint("detection", __name__)


def error_response(
    message: str,
    status_code: int,
    code: str,
):
    """
    Return errors using one consistent JSON structure.
    """
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }), status_code


@detection_bp.route("/api/detect", methods=["POST"])
def detect_api():
    """
    Run road-damage detection on an existing image path.

    Expected JSON:
    {
        "image_path": "test_images/road1.png",
        "report_id": 1
    }

    report_id is optional. When supplied, the detection result is saved
    to the database and linked to the matching report.
    """

    if not request.is_json:
        return error_response(
            "Content-Type must be application/json.",
            415,
            "UNSUPPORTED_MEDIA_TYPE",
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "Request body must contain valid JSON.",
            400,
            "INVALID_JSON",
        )

    image_path = data.get("image_path")
    report_id = data.get("report_id")

    if not isinstance(image_path, str) or not image_path.strip():
        return error_response(
            "image_path is required and must be a non-empty string.",
            400,
            "MISSING_IMAGE_PATH",
        )

    image_path = image_path.strip()

    if report_id is not None:
        if isinstance(report_id, bool):
            return error_response(
                "report_id must be an integer.",
                400,
                "INVALID_REPORT_ID",
            )

        try:
            report_id = int(report_id)
        except (TypeError, ValueError):
            return error_response(
                "report_id must be an integer.",
                400,
                "INVALID_REPORT_ID",
            )

        if report_id <= 0:
            return error_response(
                "report_id must be a positive integer.",
                400,
                "INVALID_REPORT_ID",
            )

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