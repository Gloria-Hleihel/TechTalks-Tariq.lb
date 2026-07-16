from typing import Any, Dict

import config


def _load_detector():
    """Load Majd's detector from either supported package location."""
    try:
        from app.detection.detector import detect_damage

        return detect_damage
    except ImportError:
        try:
            from app.detect.detector import detect_damage

            return detect_damage
        except ImportError:
            return None


def _failed(message: str) -> Dict[str, Any]:
    return {
        "status": "failed",
        "error": message,
    }


def trigger_detection(
    report,
    image_path: str,
) -> Dict[str, Any]:
    """
    Trigger road-damage detection without inventing a result.

    Possible statuses:
    - completed
    - pending
    - failed
    """
    try:
        detect_damage = _load_detector()
    except Exception as exc:
        return _failed(
            f"Detection module could not be loaded: {exc}"
        )

    if detect_damage is None:
        return {
            "status": "pending",
            "error": "Detection module is not available yet.",
        }

    try:
        result = detect_damage(image_path)
    except Exception as exc:
        return _failed(f"Detection failed: {exc}")

    if not isinstance(result, dict):
        return _failed(
            "Detection returned no usable result."
        )

    if result.get("status") in {"pending", "failed"}:
        return {
            "status": result["status"],
            "error": result.get(
                "error",
                "Detection did not complete.",
            ),
        }

    required_fields = {
        "damage_type",
        "confidence",
        "severity_score",
        "severity_label",
    }

    if not required_fields.issubset(result):
        return _failed(
            "Detection result is missing required fields."
        )

    damage_type = str(result["damage_type"])
    severity_label = str(result["severity_label"])

    if damage_type not in config.DAMAGE_TYPES:
        return _failed(
            f"Unsupported damage type: {damage_type}"
        )

    if severity_label not in config.SEVERITY_LEVELS:
        return _failed(
            f"Unsupported severity label: {severity_label}"
        )

    try:
        confidence = float(result["confidence"])
        severity_score = int(result["severity_score"])
    except (TypeError, ValueError):
        return _failed(
            "Detection returned invalid numeric values."
        )

    if not 0.0 <= confidence <= 1.0:
        return _failed(
            "Detection confidence must be between 0 and 1."
        )

    if not 0 <= severity_score <= 100:
        return _failed(
            "Detection severity score must be between 0 and 100."
        )

    return {
        "status": "completed",
        "damage_type": damage_type,
        "confidence": confidence,
        "severity_score": severity_score,
        "severity_label": severity_label,
        "annotated_image_path": result.get(
            "annotated_image_path"
        ),
    }