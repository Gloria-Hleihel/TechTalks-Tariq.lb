DAMAGE_BASE_SCORES = {
    "longitudinal crack": 45,
    "transverse crack": 55,
    "alligator crack": 75,
    "potholes": 90,
}


def severity_score(damage_type: str, confidence: float) -> dict:
    """
    Calculates a severity score and label based on damage type and confidence.
    """

    normalized_damage_type = damage_type.lower().strip()

    base_score = DAMAGE_BASE_SCORES.get(normalized_damage_type, 40)

    score = int(base_score * confidence)

    if score < 25:
        label = "Low"
    elif score < 50:
        label = "Medium"
    elif score < 75:
        label = "High"
    else:
        label = "Critical"

    return {
        "severity_score": score,
        "severity_label": label
    }