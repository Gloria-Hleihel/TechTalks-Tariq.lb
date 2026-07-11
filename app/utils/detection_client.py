def trigger_detection(report, image_path: str) -> dict | None:
    """
    Temporary Week 2 detection trigger.

    Later, this should call Majd's real POST /api/detect endpoint
    or Majd's detect_damage() function.

    For now:
    - Try to import Majd's detector if it exists.
    - If not available, return a mock detection result.
    - Never crash the upload flow.
    """

    try:
        detect_damage = None

        try:
            from app.detection.detector import detect_damage
        except ImportError:
            try:
                from app.detect.detector import detect_damage
            except ImportError:
                detect_damage = None

        if detect_damage:
            result = detect_damage(image_path)

            if result:
                return {
                    "damage_type": result.get("damage_type", "Other"),
                    "confidence": float(result.get("confidence", 0.0)),
                    "severity_score": int(result.get("severity_score", 50)),
                    "severity_label": result.get("severity_label", "Medium"),
                    "annotated_image_path": result.get("annotated_image_path"),
                }

    except Exception:
        return None

    # Mock result so Malek's Week 2 upload flow works before Majd's
    # real detection module is integrated.
    return {
        "damage_type": "Pothole",
        "confidence": 0.85,
        "severity_score": 70,
        "severity_label": "High",
        "annotated_image_path": None,
    }