"""Compare production, v2, and v3 models on test_images."""

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
ACTIVE_MODEL_PATH = (
    CONFIGURED_MODEL_PATH
    if CONFIGURED_MODEL_PATH.is_absolute()
    else PROJECT_ROOT / CONFIGURED_MODEL_PATH
).resolve()
MODELS = {
    "active_app_model": ACTIVE_MODEL_PATH,
    "v2": PROJECT_ROOT / "runs" / "fine_tune" / "road_damage_v2" / "weights" / "best.pt",
    "v3": PROJECT_ROOT / "runs" / "fine_tune" / "road_damage_v3" / "weights" / "best.pt",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def select_device() -> int | str:
    import torch

    if torch.cuda.is_available():
        print(f"Using device: CUDA GPU 0 ({torch.cuda.get_device_name(0)})")
        return 0
    print("Using device: CPU")
    return "cpu"


def collect_images() -> list[Path]:
    images = sorted(
        path
        for path in TEST_IMAGES_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise FileNotFoundError(f"No test images found in {TEST_IMAGES_DIR}")
    return images


def summarize(result: Any, model: Any) -> tuple[str, float, int]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return "None", 0.0, 0
    confs = boxes.conf.detach().cpu().tolist()
    classes = boxes.cls.detach().cpu().tolist()
    best_index = max(range(len(confs)), key=lambda index: confs[index])
    class_id = int(classes[best_index])
    return str(model.names[class_id]), round(float(confs[best_index]), 4), len(boxes)


def main() -> None:
    try:
        from ultralytics import YOLO

        for name, path in MODELS.items():
            if not path.is_file():
                raise FileNotFoundError(f"{name} model not found: {path}")

        device = select_device()
        images = collect_images()
        output_dir = PROJECT_ROOT / "runs" / "model_comparison" / datetime.now().strftime("%Y%m%d_%H%M%S_v3")
        output_dir.mkdir(parents=True, exist_ok=True)

        all_rows = []
        for model_name, model_path in MODELS.items():
            model = YOLO(str(model_path))
            model_rows = []
            for image_path in images:
                started = time.perf_counter()
                try:
                    result = model.predict(
                        str(image_path),
                        imgsz=640,
                        conf=0.30,
                        device=device,
                        verbose=False,
                    )[0]
                    damage_type, confidence, box_count = summarize(result, model)
                    error = ""
                except Exception as exc:
                    damage_type, confidence, box_count = "Error", 0.0, 0
                    error = f"{type(exc).__name__}: {exc}"
                elapsed = round(time.perf_counter() - started, 4)
                row = {
                    "model_name": model_name,
                    "image_filename": image_path.relative_to(TEST_IMAGES_DIR).as_posix(),
                    "detected_damage_type": damage_type,
                    "confidence": confidence,
                    "number_of_bounding_boxes": box_count,
                    "processing_time_seconds": elapsed,
                    "error": error,
                }
                model_rows.append(row)
                all_rows.append(row)

            with (output_dir / f"{model_name}_predictions.csv").open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=list(model_rows[0]))
                writer.writeheader()
                writer.writerows(model_rows)

        with (output_dir / "all_model_predictions.csv").open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"Comparison saved to: {output_dir}")
        print(f"Active app model was not modified: {ACTIVE_MODEL_PATH}")
    except Exception as error:
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
