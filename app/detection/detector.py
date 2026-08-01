import os
from pathlib import Path

import cv2

# PyTorch 2.6+ defaults torch.load() to weights_only=True. Ultralytics
# checkpoints are trusted app assets here, loaded only from MODEL_PATH below.
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

from ultralytics import YOLO

import config
from app.detection.severity import severity_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "road_damage_v3.pt"
ANNOTATED_DIR = PROJECT_ROOT / "static" / "uploads" / "annotated"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

_model = None


class DetectionError(Exception):
    """Base exception for detection-related failures."""


class InvalidImagePathError(DetectionError):
    """Raised when the supplied image path is invalid."""


class ImageNotFoundError(DetectionError):
    """Raised when the requested image does not exist."""


class UnsupportedImageTypeError(DetectionError):
    """Raised when the image extension is unsupported."""


class InvalidImageError(DetectionError):
    """Raised when OpenCV cannot read the image."""


class ModelNotFoundError(DetectionError):
    """Raised when the YOLO weights file cannot be found."""


class ModelLoadError(DetectionError):
    """Raised when the YOLO model cannot be loaded."""


class InferenceError(DetectionError):
    """Raised when YOLO inference fails."""


def _allowed_detection_roots() -> tuple[Path, ...]:
    roots = []
    for raw_root in getattr(config, "DETECTION_ALLOWED_ROOTS", []):
        root = Path(raw_root)
        if not root.is_absolute():
            root = PROJECT_ROOT / root
        roots.append(root.resolve())
    return tuple(roots)


def _is_under_allowed_root(path: Path) -> bool:
    for root in _allowed_detection_roots():
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def get_model():
    """Load the YOLO model once and reuse it."""
    global _model

    if _model is not None:
        return _model

    if not MODEL_PATH.is_file():
        raise ModelNotFoundError(
            f"Model weights were not found at: {MODEL_PATH}"
        )

    try:
        _model = YOLO(str(MODEL_PATH))
    except Exception as error:
        raise ModelLoadError(
            "The detection model could not be loaded."
        ) from error

    return _model


def validate_image(image_path: str) -> Path:
    """Validate the image path and check that the image is readable."""
    if not isinstance(image_path, str) or not image_path.strip():
        raise InvalidImagePathError(
            "A valid image path is required."
        )

    path = Path(image_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    path = path.resolve()

    if not _is_under_allowed_root(path):
        raise InvalidImagePathError(
            "The image path is outside the allowed detection folders."
        )

    if not path.is_file():
        raise ImageNotFoundError(
            "The image file does not exist."
        )

    if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise UnsupportedImageTypeError(
            "Only JPG, JPEG, and PNG images are supported."
        )

    image = cv2.imread(str(path))

    if image is None:
        raise InvalidImageError(
            "The file is not a valid or readable image."
        )

    return path


def detect_damage(
    image_path: str,
    confidence_threshold: float = 0.30,
) -> dict:
    """Run YOLOv8 road-damage detection on one image."""
    validated_path = validate_image(image_path)
    model = get_model()

    try:
        results = model(
            str(validated_path),
            conf=confidence_threshold,
            imgsz=640,
        )
    except Exception as error:
        raise InferenceError(
            "The model failed while analyzing the image."
        ) from error

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
                "bounding_box": [
                    round(value, 2)
                    for value in bbox
                ],
            }

            detections.append(detection)

            if (
                best_detection is None
                or detection["confidence"]
                > best_detection["confidence"]
            ):
                best_detection = detection

    if best_detection is None:
        return {
            "damage_type": "None",
            "confidence": 0.0,
            "bounding_boxes": [],
            "severity_score": 0,
            "severity_label": "Low",
            "annotated_image_path": None,
            "message": "No damage detected.",
        }

    severity = severity_score(
        best_detection["damage_type"],
        best_detection["confidence"],
    )

    annotated_image_path = save_annotated_result(
        results,
        validated_path,
    )

    return {
        "damage_type": best_detection["damage_type"],
        "confidence": best_detection["confidence"],
        "bounding_boxes": detections,
        "severity_score": severity["severity_score"],
        "severity_label": severity["severity_label"],
        "annotated_image_path": annotated_image_path,
        "message": "Detection completed.",
    }


def save_annotated_result(
    results,
    image_path: Path,
) -> str:
    """Save the first annotated YOLO result."""
    output_path = (
        ANNOTATED_DIR
        / f"{image_path.stem}_annotated.jpg"
    )

    for result in results:
        annotated_image = result.plot()

        saved = cv2.imwrite(
            str(output_path),
            annotated_image,
        )

        if not saved:
            raise DetectionError(
                "The annotated image could not be saved."
            )

        break

    try:
        relative_path = output_path.relative_to(
            PROJECT_ROOT
        )
        return str(relative_path).replace("\\", "/")
    except ValueError:
        return str(output_path)
