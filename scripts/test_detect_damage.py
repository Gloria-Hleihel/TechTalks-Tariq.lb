from pathlib import Path
import sys

# Add project root to Python path so "app" can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.detection.detector import detect_damage


TEST_IMAGES_DIR = Path("test_images")

for image_path in TEST_IMAGES_DIR.glob("*"):
    if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
        continue

    print(f"\nTesting: {image_path}")

    result = detect_damage(str(image_path))

    print("Damage type:", result["damage_type"])
    print("Confidence:", result["confidence"])
    print("Severity score:", result["severity_score"])
    print("Severity label:", result["severity_label"])
    print("Bounding boxes:", result["bounding_boxes"])
    print("Annotated image:", result["annotated_image_path"])