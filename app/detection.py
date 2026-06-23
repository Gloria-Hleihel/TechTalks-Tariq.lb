"""
Detection module -- MOCKED for this MVP.

The PRD calls for YOLOv8 (ultralytics) using pretrained weights from
oracl4/RoadDamageDetection trained on RDD2022 (see Section 12, Tech Stack).
That model is NOT wired up here -- this MVP validates the full upload ->
detect -> score -> map pipeline end-to-end first, with the AI step
replaced by a random-but-realistic stand-in.

TO REPLACE WITH REAL YOLOv8 LATER:
    1. `pip install ultralytics opencv-python`
    2. Load the pretrained weights once at module level:
           from ultralytics import YOLO
           model = YOLO("path/to/weights.pt")
    3. Replace the body of `run_detection()` with a real inference call:
           results = model(image_path)
           # map results -> damage_type, confidence_score
    4. Keep the function signature identical so app.py needs no changes.
"""
import random

# Matches PRD Section 8: Damage Types
DAMAGE_TYPES = ["Pothole", "Road Crack", "Surface Wear", "Other / Unclear Damage"]

# Matches PRD Section 9: Severity Levels
SEVERITY_LEVELS = [
    ("Low", (0.0, 0.25)),
    ("Medium", (0.25, 0.5)),
    ("High", (0.5, 0.75)),
    ("Critical", (0.75, 1.0)),
]


def run_detection(image_path):
    """
    MOCK detection. Ignores image_path entirely and returns a plausible,
    randomized result shaped exactly like what a real YOLOv8 integration
    would return.

    Returns:
        dict with keys: damage_type, confidence_score, severity_level,
        severity_score
    """
    damage_type = random.choice(DAMAGE_TYPES)
    confidence_score = round(random.uniform(0.55, 0.97), 2)

    severity_level, (low, high) = random.choice(SEVERITY_LEVELS)
    severity_score = round(random.uniform(low, high), 2)

    return {
        "damage_type": damage_type,
        "confidence_score": confidence_score,
        "severity_level": severity_level,
        "severity_score": severity_score,
    }
