import os
from typing import Any, Dict

import requests
from flask import current_app

import config


def _setting(
    name: str,
    default,
):
    """Read a Flask setting or fall back to config.py."""
    try:
        return current_app.config.get(
            name,
            default,
        )
    except RuntimeError:
        return getattr(
            config,
            name,
            default,
        )


def _pending(
    error: str,
    user_message: str,
) -> Dict[str, Any]:
    """Return a retryable failed-detection result."""
    return {
        "status": "pending",
        "error": error,
        "user_message": user_message,
    }


def _normalize_result(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate the detection API response."""
    result = payload.get(
        "detection",
        payload,
    )

    if not isinstance(result, dict):
        return _pending(
            "Detection API returned an invalid JSON structure.",
            (
                "Your report was saved, but the detection "
                "response was invalid. "
                "Please retry detection later."
            ),
        )

    if result.get("status") in {
        "pending",
        "failed",
        "error",
    }:
        api_error = str(
            result.get("error")
            or result.get("message")
            or "Detection did not complete."
        )

        return _pending(
            api_error,
            (
                "Your report was saved, but detection "
                "did not complete. "
                "Please retry detection later."
            ),
        )

    required_fields = {
        "damage_type",
        "confidence",
        "severity_score",
        "severity_label",
    }

    if not required_fields.issubset(result):
        return _pending(
            "Detection API response is missing required fields.",
            (
                "Your report was saved, but the detection "
                "response was incomplete. "
                "Please retry detection later."
            ),
        )

    damage_type = str(
        result["damage_type"]
    )

    severity_label = str(
        result["severity_label"]
    )

    if damage_type not in config.DAMAGE_TYPES:
        return _pending(
            (
                "Unsupported damage type returned: "
                f"{damage_type}"
            ),
            (
                "Your report was saved, but detection returned "
                "an unsupported result. "
                "Please retry detection later."
            ),
        )

    if severity_label not in config.SEVERITY_LEVELS:
        return _pending(
            (
                "Unsupported severity label returned: "
                f"{severity_label}"
            ),
            (
                "Your report was saved, but detection returned "
                "an unsupported severity. "
                "Please retry detection later."
            ),
        )

    try:
        confidence = float(
            result["confidence"]
        )

        severity_score = int(
            result["severity_score"]
        )

    except (TypeError, ValueError):
        return _pending(
            "Detection API returned invalid numeric values.",
            (
                "Your report was saved, but detection "
                "returned invalid values. "
                "Please retry detection later."
            ),
        )

    if not 0.0 <= confidence <= 1.0:
        return _pending(
            "Detection confidence must be between 0 and 1.",
            (
                "Your report was saved, but detection returned "
                "invalid confidence. "
                "Please retry detection later."
            ),
        )

    if not 0 <= severity_score <= 100:
        return _pending(
            (
                "Detection severity score must be "
                "between 0 and 100."
            ),
            (
                "Your report was saved, but detection returned "
                "an invalid severity score. "
                "Please retry detection later."
            ),
        )

    return {
        "status": "completed",
        "damage_type": damage_type,
        "confidence": confidence,
        "severity_score": severity_score,
        "severity_label": severity_label,
        "annotated_image_path": (
            result.get("annotated_image_path")
            or result.get("annotated_path")
        ),
    }


def trigger_detection(
    report,
    image_path: str,
) -> Dict[str, Any]:
    """
    Send the saved image path to POST /api/detect.

    Any API or network failure returns pending so the Report
    remains saved and detection can be retried.
    """
    api_url = _setting(
        "DETECTION_API_URL",
        config.DETECTION_API_URL,
    )

    timeout = float(
        _setting(
            "DETECTION_API_TIMEOUT",
            config.DETECTION_API_TIMEOUT,
        )
    )

    if not os.path.isfile(image_path):
        return _pending(
            "Saved upload is missing from disk.",
            (
                "The report was saved, but its image "
                "could not be sent for detection."
            ),
        )

    try:
        response = requests.post(
            api_url,
            json={
                "report_id": report.id,
                "image_path": image_path,
            },
            timeout=timeout,
        )

    except requests.Timeout:
        return _pending(
            (
                "Detection API timed out after "
                f"{timeout:g} seconds."
            ),
            (
                "Your report was saved, but detection "
                "timed out. Please retry detection later."
            ),
        )

    except requests.ConnectionError:
        return _pending(
            "Detection API is unavailable.",
            (
                "Your report was saved, but the detection "
                "service is unavailable. "
                "Please retry detection later."
            ),
        )

    except requests.RequestException as exc:
        return _pending(
            f"Detection API request failed: {exc}",
            (
                "Your report was saved, but detection "
                "could not be started. "
                "Please retry detection later."
            ),
        )

    if not response.ok:
        detail = ""

        try:
            body = response.json()

            detail = str(
                body.get("error")
                or body.get("message")
                or ""
            )

        except (ValueError, AttributeError):
            detail = response.text.strip()[:200]

        error = (
            "Detection API returned HTTP "
            f"{response.status_code}."
        )

        if detail:
            error = f"{error} {detail}"

        return _pending(
            error,
            (
                "Your report was saved, but the detection "
                "service returned an error. "
                "Please retry detection later."
            ),
        )

    try:
        payload = response.json()

    except ValueError:
        return _pending(
            "Detection API returned non-JSON data.",
            (
                "Your report was saved, but the detection "
                "response could not be read. "
                "Please retry detection later."
            ),
        )

    return _normalize_result(
        payload
    )