"""Fine-tune road_damage_v3 from the current best v2 weights."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, NoReturn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

CONFIGURED_MODEL_PATH = Path(config.DETECTION_MODEL_PATH)
ACTIVE_MODEL_PATH = (
    CONFIGURED_MODEL_PATH
    if CONFIGURED_MODEL_PATH.is_absolute()
    else PROJECT_ROOT / CONFIGURED_MODEL_PATH
).resolve()
V2_BEST_PATH = PROJECT_ROOT / "runs" / "fine_tune" / "road_damage_v2" / "weights" / "best.pt"
DATA_YAML_PATH = PROJECT_ROOT / "dataset_v3" / "road_damage.yaml"
RUNS_PROJECT = PROJECT_ROOT / "runs" / "fine_tune"
RUN_NAME = "road_damage_v3"
LAST_WEIGHTS_PATH = RUNS_PROJECT / RUN_NAME / "weights" / "last.pt"

EXPECTED_CLASS_NAMES = {
    0: "Longitudinal Crack",
    1: "Transverse Crack",
    2: "Alligator Crack",
    3: "Potholes",
}


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_names(names: Any) -> dict[int, str]:
    if isinstance(names, dict):
        return {int(class_id): str(name) for class_id, name in names.items()}
    if isinstance(names, (list, tuple)):
        return {class_id: str(name) for class_id, name in enumerate(names)}
    raise ValueError("Class names must be a dict, list, or tuple.")


def select_device() -> int | str:
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("PyTorch is required.") from error

    if torch.cuda.is_available():
        print(f"Using device: CUDA GPU 0 ({torch.cuda.get_device_name(0)})")
        return 0

    print("Using device: CPU")
    return "cpu"


def load_model(weights_path: Path) -> Any:
    if not weights_path.is_file():
        raise FileNotFoundError(f"Model weights not found: {weights_path}")

    from ultralytics import YOLO

    model = YOLO(str(weights_path))
    if normalize_names(model.names) != EXPECTED_CLASS_NAMES:
        raise ValueError("Model class names do not match the expected classes.")
    return model


def main() -> None:
    try:
        if not DATA_YAML_PATH.is_file():
            raise FileNotFoundError(f"Dataset YAML not found: {DATA_YAML_PATH}")

        device = select_device()

        if LAST_WEIGHTS_PATH.is_file():
            weights_path = LAST_WEIGHTS_PATH
            print(f"Resuming v3 training from: {weights_path}")
            model = load_model(weights_path)
            model.train(resume=True, batch=4, device=device, plots=False)
        else:
            weights_path = V2_BEST_PATH if V2_BEST_PATH.is_file() else ACTIVE_MODEL_PATH
            print(f"Starting v3 training from: {weights_path}")
            model = load_model(weights_path)
            model.train(
                data=str(DATA_YAML_PATH),
                imgsz=640,
                epochs=50,
                batch=4,
                patience=15,
                project=str(RUNS_PROJECT),
                name=RUN_NAME,
                exist_ok=True,
                device=device,
                amp=False,
                plots=False,
                workers=2,
            )

        print("v3 fine-tuning complete.")
        print(f"Best weights: {RUNS_PROJECT / RUN_NAME / 'weights' / 'best.pt'}")
        print(f"Active app model was not modified: {ACTIVE_MODEL_PATH}")
    except KeyboardInterrupt:
        fail("Training interrupted by user.")
    except Exception as error:
        traceback.print_exc()
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
