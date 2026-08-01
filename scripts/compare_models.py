"""Compare production and fine-tuned YOLO road-damage models on test images."""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

TEST_IMAGES_DIR = PROJECT_ROOT / "test_images"
CONFIGURED_MODEL_PATH = Path(config.DETECTION_MODEL_PATH)
PRODUCTION_MODEL_PATH = (
    CONFIGURED_MODEL_PATH
    if CONFIGURED_MODEL_PATH.is_absolute()
    else PROJECT_ROOT / CONFIGURED_MODEL_PATH
).resolve()
FINE_TUNED_MODEL_PATH = (
    PROJECT_ROOT / "runs" / "fine_tune" / "road_damage_v2" / "weights" / "best.pt"
)
OUTPUT_ROOT = PROJECT_ROOT / "runs" / "model_comparison"

CONFIDENCE_THRESHOLD = 0.30
IMAGE_SIZE = 640
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

PREDICTION_FIELDS = [
    "model_name",
    "model_path",
    "image_filename",
    "detected_damage_type",
    "confidence",
    "number_of_bounding_boxes",
    "processing_time_seconds",
    "error",
]

SUMMARY_FIELDS = [
    "image_filename",
    "production_damage_type",
    "production_confidence",
    "production_bounding_boxes",
    "production_processing_time_seconds",
    "production_error",
    "fine_tuned_damage_type",
    "fine_tuned_confidence",
    "fine_tuned_bounding_boxes",
    "fine_tuned_processing_time_seconds",
    "fine_tuned_error",
    "damage_type_changed",
    "confidence_delta_fine_tuned_minus_production",
    "box_count_delta_fine_tuned_minus_production",
]


def fail(message: str) -> NoReturn:
    """Print a clear error and exit with failure."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path, description: str) -> None:
    """Raise a clear error when a required file is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"{description} was not found: {path}")


def select_device() -> int | str:
    """Use GPU 0 when CUDA is available; otherwise use CPU."""
    try:
        import torch
    except ImportError as error:
        raise RuntimeError(
            "PyTorch is required. Install the project requirements first."
        ) from error

    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"Using device: CUDA GPU 0 ({device_name})")
        return 0

    print("Using device: CPU")
    return "cpu"


def collect_test_images() -> list[Path]:
    """Return all supported test images under test_images/."""
    if not TEST_IMAGES_DIR.is_dir():
        raise FileNotFoundError(f"Test image folder was not found: {TEST_IMAGES_DIR}")

    images = sorted(
        path
        for path in TEST_IMAGES_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise FileNotFoundError(f"No test images were found in: {TEST_IMAGES_DIR}")

    return images


def load_yolo_model(model_path: Path) -> Any:
    """Load one YOLO model from disk."""
    require_file(model_path, "Model weights")

    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError(
            "Ultralytics is required. Install the project requirements first."
        ) from error

    try:
        return YOLO(str(model_path))
    except Exception as error:
        raise RuntimeError(f"Could not load model weights at {model_path}") from error


def class_name(model: Any, class_id: int) -> str:
    """Resolve a YOLO class id to a readable class name."""
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def summarize_prediction(result: Any, model: Any) -> tuple[str, float, int]:
    """Return best damage type, confidence, and box count for one result."""
    boxes = getattr(result, "boxes", None)
    box_count = 0 if boxes is None else len(boxes)

    if box_count == 0:
        return "None", 0.0, 0

    confidences = boxes.conf.detach().cpu().tolist()
    classes = boxes.cls.detach().cpu().tolist()
    best_index = max(range(len(confidences)), key=lambda index: confidences[index])
    best_class_id = int(classes[best_index])
    best_confidence = round(float(confidences[best_index]), 4)

    return class_name(model, best_class_id), best_confidence, box_count


def run_predictions(
    model_name: str,
    model_path: Path,
    images: list[Path],
    device: int | str,
) -> list[dict[str, object]]:
    """Run one model over all test images and return CSV-ready rows."""
    model = load_yolo_model(model_path)
    rows: list[dict[str, object]] = []

    for image_path in images:
        image_filename = image_path.relative_to(TEST_IMAGES_DIR).as_posix()
        start_time = time.perf_counter()

        try:
            results = model.predict(
                source=str(image_path),
                imgsz=IMAGE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                device=device,
                verbose=False,
            )
            elapsed = round(time.perf_counter() - start_time, 4)
            damage_type, confidence, box_count = summarize_prediction(results[0], model)
            error = ""
        except Exception as exc:
            elapsed = round(time.perf_counter() - start_time, 4)
            damage_type = "Error"
            confidence = 0.0
            box_count = 0
            error = f"{type(exc).__name__}: {exc}"

        rows.append(
            {
                "model_name": model_name,
                "model_path": str(model_path),
                "image_filename": image_filename,
                "detected_damage_type": damage_type,
                "confidence": confidence,
                "number_of_bounding_boxes": box_count,
                "processing_time_seconds": elapsed,
                "error": error,
            }
        )

    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    """Write rows to a UTF-8 CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: object) -> float:
    """Convert a CSV value to float for summary calculations."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_int(value: object) -> int:
    """Convert a CSV value to int for summary calculations."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_summary(
    production_rows: list[dict[str, object]],
    fine_tuned_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build one side-by-side comparison row for each image."""
    fine_tuned_by_image = {
        str(row["image_filename"]): row for row in fine_tuned_rows
    }
    summary_rows: list[dict[str, object]] = []

    for production_row in production_rows:
        image_filename = str(production_row["image_filename"])
        fine_tuned_row = fine_tuned_by_image[image_filename]

        production_confidence = to_float(production_row["confidence"])
        fine_tuned_confidence = to_float(fine_tuned_row["confidence"])
        production_boxes = to_int(production_row["number_of_bounding_boxes"])
        fine_tuned_boxes = to_int(fine_tuned_row["number_of_bounding_boxes"])

        summary_rows.append(
            {
                "image_filename": image_filename,
                "production_damage_type": production_row["detected_damage_type"],
                "production_confidence": production_confidence,
                "production_bounding_boxes": production_boxes,
                "production_processing_time_seconds": production_row[
                    "processing_time_seconds"
                ],
                "production_error": production_row["error"],
                "fine_tuned_damage_type": fine_tuned_row["detected_damage_type"],
                "fine_tuned_confidence": fine_tuned_confidence,
                "fine_tuned_bounding_boxes": fine_tuned_boxes,
                "fine_tuned_processing_time_seconds": fine_tuned_row[
                    "processing_time_seconds"
                ],
                "fine_tuned_error": fine_tuned_row["error"],
                "damage_type_changed": production_row["detected_damage_type"]
                != fine_tuned_row["detected_damage_type"],
                "confidence_delta_fine_tuned_minus_production": round(
                    fine_tuned_confidence - production_confidence,
                    4,
                ),
                "box_count_delta_fine_tuned_minus_production": fine_tuned_boxes
                - production_boxes,
            }
        )

    return summary_rows


def main() -> None:
    """Compare both models and save CSV outputs."""
    try:
        require_file(PRODUCTION_MODEL_PATH, "Production model")
        require_file(FINE_TUNED_MODEL_PATH, "Fine-tuned best.pt")

        images = collect_test_images()
        device = select_device()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_ROOT / timestamp

        print(f"Comparing {len(images)} images from: {TEST_IMAGES_DIR}")
        print(f"Writing comparison CSVs to: {output_dir}")

        production_rows = run_predictions(
            "production",
            PRODUCTION_MODEL_PATH,
            images,
            device,
        )
        fine_tuned_rows = run_predictions(
            "fine_tuned",
            FINE_TUNED_MODEL_PATH,
            images,
            device,
        )
        summary_rows = build_summary(production_rows, fine_tuned_rows)

        production_csv = output_dir / "production_model_predictions.csv"
        fine_tuned_csv = output_dir / "fine_tuned_model_predictions.csv"
        summary_csv = output_dir / "model_comparison_summary.csv"

        write_csv(production_csv, production_rows, PREDICTION_FIELDS)
        write_csv(fine_tuned_csv, fine_tuned_rows, PREDICTION_FIELDS)
        write_csv(summary_csv, summary_rows, SUMMARY_FIELDS)

        print(f"Production model CSV: {production_csv}")
        print(f"Fine-tuned model CSV: {fine_tuned_csv}")
        print(f"Summary CSV: {summary_csv}")
        print(f"Production model was not modified: {PRODUCTION_MODEL_PATH}")
    except KeyboardInterrupt:
        fail("Model comparison was interrupted by the user.")
    except Exception as error:
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
