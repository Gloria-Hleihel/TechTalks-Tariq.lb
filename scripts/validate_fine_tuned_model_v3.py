"""Validate road_damage_v3."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, NoReturn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_YAML_PATH = PROJECT_ROOT / "dataset_v3" / "road_damage.yaml"
BEST_WEIGHTS_PATH = PROJECT_ROOT / "runs" / "fine_tune" / "road_damage_v3" / "weights" / "best.pt"


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


def metric(value: Any) -> float | None:
    if callable(value):
        value = value()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def print_metric(label: str, value: Any) -> None:
    value = metric(value)
    print(f"{label}: {value:.4f}" if value is not None else f"{label}: unavailable")


def main() -> None:
    try:
        if not BEST_WEIGHTS_PATH.is_file():
            raise FileNotFoundError(f"v3 best.pt not found: {BEST_WEIGHTS_PATH}")
        if not DATA_YAML_PATH.is_file():
            raise FileNotFoundError(f"v3 dataset YAML not found: {DATA_YAML_PATH}")

        from ultralytics import YOLO

        model = YOLO(str(BEST_WEIGHTS_PATH))
        metrics = model.val(
            data=str(DATA_YAML_PATH),
            imgsz=640,
            device=select_device(),
            workers=0,
            project=str(PROJECT_ROOT / "runs" / "validation"),
            name="road_damage_v3",
            exist_ok=True,
        )
        results = getattr(metrics, "results_dict", {})
        print_metric("Precision", results.get("metrics/precision(B)"))
        print_metric("Recall", results.get("metrics/recall(B)"))
        print_metric("mAP50", results.get("metrics/mAP50(B)"))
        print_metric("mAP50-95", results.get("metrics/mAP50-95(B)"))
    except Exception as error:
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
