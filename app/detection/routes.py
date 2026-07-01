from flask import Blueprint, request, jsonify

from app.detection.detector import detect_damage
from app.detection.severity import calculate_severity


detection_bp = Blueprint("detection", __name__)


@detection_bp.route("/api/detect", methods=["POST"])
def detect_api():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body must be JSON."
        }), 400

    image_path = data.get("image_path")
    report_id = data.get("report_id")

    if not image_path:
        return jsonify({
            "error": "image_path is required."
        }), 400

    try:
        detection_result = detect_damage(image_path)

        damage_type = detection_result.get("damage_type", "None")
        confidence = detection_result.get("confidence", 0)

        severity_result = calculate_severity(damage_type, confidence)

        response = {
            "report_id": report_id,
            "damage_type": damage_type,
            "confidence": confidence,
            "severity_score": severity_result["severity_score"],
            "severity_label": severity_result["severity_label"],
            "bounding_boxes": detection_result.get("bounding_boxes", []),
            "annotated_image_path": detection_result.get("annotated_image_path"),
            "message": detection_result.get("message", "Detection completed.")
        }

        return jsonify(response), 200

    except Exception as error:
        return jsonify({
            "error": "Detection failed.",
            "reason": str(error)
        }), 500