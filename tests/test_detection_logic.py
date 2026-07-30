from app.detection.severity import calculate_severity


def test_pothole_severity_is_high():
    result = calculate_severity(
        damage_type="Potholes",
        confidence=0.6814,
    )

    assert result["severity_score"] == 61
    assert result["severity_label"] == "High"


def test_low_confidence_crack_is_low():
    result = calculate_severity(
        damage_type="Longitudinal Crack",
        confidence=0.4,
    )

    assert result["severity_score"] == 18
    assert result["severity_label"] == "Low"


def test_no_damage_returns_none():
    result = calculate_severity(
        damage_type="None",
        confidence=0.9,
    )

    assert result["severity_score"] == 0
    assert result["severity_label"] == "None"


def test_unknown_damage_uses_default_score():
    result = calculate_severity(
        damage_type="Unknown Damage",
        confidence=0.5,
    )

    assert result["severity_score"] == 20
    assert result["severity_label"] == "Low"