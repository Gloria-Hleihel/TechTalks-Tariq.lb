from pathlib import Path

import cv2
from ultralytics import YOLO

from app.detection.severity import severity_score


MODEL_PATH = "models/road_damage.pt"
ANNOTATED_DIR = Path("static/uploads/annotated")

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

model = YOLO(MODEL_PATH)


def detect_damage(image_path: str, confidence_threshold: float = 0.3) -> dict:
    """
    Runs YOLOv8 road damage detection on an image.

    Returns:
        A dictionary containing damage type, confidence, bounding boxes,
        severity score, severity label, and annotated image path.
    """

    results = model(image_path, conf=confidence_threshold)

    detections = []
    best_detection = None

    for result in results:
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            continue

        for box in boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            damage_type = model.names[class_id]
            bbox = box.xyxy[0].tolist()

            detection = {
                "damage_type": damage_type,
                "confidence": round(confidence, 4),
                "bounding_box": [round(value, 2) for value in bbox],
            }

            detections.append(detection)

            if best_detection is None or confidence > best_detection["confidence"]:
                best_detection = detection

    if best_detection is None:
        return {
            "damage_type": "None",
            "confidence": 0.0,
            "bounding_boxes": [],
            "severity_score": 0,
            "severity_label": "None",
            "annotated_image_path": None,
            "message": "No damage detected."
        }

    severity = severity_score(
        best_detection["damage_type"],
        best_detection["confidence"]
    )

    annotated_image_path = save_annotated_result(results, image_path)

    return {
        "damage_type": best_detection["damage_type"],
        "confidence": best_detection["confidence"],
        "bounding_boxes": detections,
        "severity_score": severity["severity_score"],
        "severity_label": severity["severity_label"],
        "annotated_image_path": annotated_image_path,
        "message": "Detection completed."
    }


def save_annotated_result(results, image_path: str) -> str:
    """
    Saves the YOLO annotated image with bounding boxes.
    """

    original_name = Path(image_path).stem
    output_path = ANNOTATED_DIR / f"{original_name}_annotated.jpg"

    for result in results:
        annotated_image = result.plot()
        cv2.imwrite(str(output_path), annotated_image)
        break

    return str(output_path)