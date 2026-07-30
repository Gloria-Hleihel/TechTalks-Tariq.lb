"""Validate the fine-tuned YOLO road-damage model."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, NoReturn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_YAML_PATH = PROJECT_ROOT / "dataset" / "road_damage.yaml"
BEST_WEIGHTS_PATH = (
    PROJECT_ROOT / "runs" / "fine_tune" / "road_damage_v2" / "weights" / "best.pt"
)
VALIDATION_PROJECT = PROJECT_ROOT / "runs" / "validation"
VALIDATION_RUN_NAME = "road_damage_v2"


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


def numeric_metric(value: Any) -> float | None:
    """Return a float metric value when Ultralytics exposes one."""
    if callable(value):
        value = value()

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def print_metric(label: str, value: Any) -> None:
    """Print one metric in a consistent format."""
    metric = numeric_metric(value)
    if metric is None:
        print(f"{label}: unavailable")
    else:
        print(f"{label}: {metric:.4f}")


def print_validation_metrics(metrics: Any) -> None:
    """Print the main object-detection validation metrics."""
    results_dict = getattr(metrics, "results_dict", None)

    if isinstance(results_dict, dict) and results_dict:
        key_labels = {
            "metrics/precision(B)": "Precision",
            "metrics/recall(B)": "Recall",
            "metrics/mAP50(B)": "mAP50",
            "metrics/mAP50-95(B)": "mAP50-95",
            "fitness": "Fitness",
        }
        for key, label in key_labels.items():
            if key in results_dict:
                print_metric(label, results_dict[key])
    else:
        box_metrics = getattr(metrics, "box", None)
        print_metric("Precision", getattr(box_metrics, "mp", None))
        print_metric("Recall", getattr(box_metrics, "mr", None))
        print_metric("mAP50", getattr(box_metrics, "map50", None))
        print_metric("mAP50-95", getattr(box_metrics, "map", None))

    speed = getattr(metrics, "speed", None)
    if isinstance(speed, dict):
        print("Speed:")
        for name, milliseconds in speed.items():
            print_metric(f"  {name} (ms/image)", milliseconds)


def main() -> None:
    """Validate the fine-tuned model against the validation dataset."""
    try:
        require_file(BEST_WEIGHTS_PATH, "Fine-tuned best.pt")
        require_file(DATA_YAML_PATH, "Dataset YAML")

        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError(
                "Ultralytics is required. Install the project requirements first."
            ) from error

        device = select_device()
        model = YOLO(str(BEST_WEIGHTS_PATH))

        print(f"Validating model: {BEST_WEIGHTS_PATH}")
        print(f"Using dataset YAML: {DATA_YAML_PATH}")

        metrics = model.val(
            data=str(DATA_YAML_PATH),
            imgsz=640,
            device=device,
            workers=0,
            project=str(VALIDATION_PROJECT),
            name=VALIDATION_RUN_NAME,
            exist_ok=True,
        )
        print_validation_metrics(metrics)
    except KeyboardInterrupt:
        fail("Validation was interrupted by the user.")
    except Exception as error:
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
