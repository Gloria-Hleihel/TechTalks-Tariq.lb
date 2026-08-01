from pathlib import Path
import sys

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

CONFIGURED_MODEL_PATH = Path(config.DETECTION_MODEL_PATH)
MODEL_PATH = (
    CONFIGURED_MODEL_PATH
    if CONFIGURED_MODEL_PATH.is_absolute()
    else PROJECT_ROOT / CONFIGURED_MODEL_PATH
).resolve()
TEST_IMAGES_DIR = Path("test_images")

model = YOLO(str(MODEL_PATH))

for image_path in TEST_IMAGES_DIR.glob("*"):
    if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
        continue

    print(f"\nTesting image: {image_path}")

    results = model(str(image_path), conf=0.3)

    for result in results:
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            print("No damage detected.")
            continue

        for box in boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            damage_type = model.names[class_id]
            bbox = box.xyxy[0].tolist()

            print({
                "damage_type": damage_type,
                "confidence": round(confidence, 3),
                "bounding_box": [round(value, 2) for value in bbox]
            })
