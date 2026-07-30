"""Fine-tune the existing YOLO road-damage model safely."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, NoReturn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "road_damage.pt"
DATA_YAML_PATH = PROJECT_ROOT / "dataset" / "road_damage.yaml"
RUNS_PROJECT = PROJECT_ROOT / "runs" / "fine_tune"
RUN_NAME = "road_damage_v2"
LAST_WEIGHTS_PATH = RUNS_PROJECT / RUN_NAME / "weights" / "last.pt"

EXPECTED_CLASS_NAMES = {
    0: "Longitudinal Crack",
    1: "Transverse Crack",
    2: "Alligator Crack",
    3: "Potholes",
}

TRAINING_ARGS = {
    "imgsz": 640,
    "epochs": 50,
    "batch": 8,
    "patience": 15,
}


def fail(message: str) -> NoReturn:
    """Print a beginner-friendly error and exit with failure."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path, description: str) -> None:
    """Raise a clear error when a required file is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"{description} was not found: {path}")


def normalize_names(names: Any) -> dict[int, str]:
    """Convert Ultralytics/YAML class names to a stable dict format."""
    if isinstance(names, dict):
        return {int(class_id): str(name) for class_id, name in names.items()}

    if isinstance(names, (list, tuple)):
        return {class_id: str(name) for class_id, name in enumerate(names)}

    raise ValueError("Class names must be a dict, list, or tuple.")


def validate_dataset_yaml() -> None:
    """Confirm the dataset YAML exists and contains the expected classes."""
    require_file(DATA_YAML_PATH, "Dataset YAML")

    try:
        import yaml
    except ImportError as error:
        raise RuntimeError(
            "PyYAML is required. Install the project requirements first."
        ) from error

    with DATA_YAML_PATH.open("r", encoding="utf-8") as yaml_file:
        data = yaml.safe_load(yaml_file) or {}

    if "train" not in data or "val" not in data:
        raise ValueError("Dataset YAML must contain both 'train' and 'val' paths.")

    names = normalize_names(data.get("names"))
    if names != EXPECTED_CLASS_NAMES:
        raise ValueError(
            "Dataset YAML class names do not match the expected road-damage classes."
        )


def check_training_args_supported() -> None:
    """Check that the installed Ultralytics version accepts our train args."""
    try:
        from ultralytics.cfg import DEFAULT_CFG_DICT
    except ImportError as error:
        raise RuntimeError(
            "Ultralytics is required. Install the project requirements first."
        ) from error

    required_args = {
        "data",
        "imgsz",
        "epochs",
        "batch",
        "patience",
        "project",
        "name",
        "exist_ok",
        "device",
    }
    missing_args = sorted(arg for arg in required_args if arg not in DEFAULT_CFG_DICT)
    if missing_args:
        raise RuntimeError(
            "The installed Ultralytics version does not support these training "
            f"arguments: {', '.join(missing_args)}"
        )


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


def load_model(weights_path: Path) -> Any:
    """Load YOLO weights from disk."""
    require_file(weights_path, "Model weights")

    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError(
            "Ultralytics is required. Install the project requirements first."
        ) from error

    try:
        model = YOLO(str(weights_path))
    except Exception as error:
        raise RuntimeError(
            f"The model could not be loaded by Ultralytics YOLO: {weights_path}"
        ) from error

    model_names = normalize_names(getattr(model, "names", None))
    if model_names != EXPECTED_CLASS_NAMES:
        raise ValueError(
            "The model class names do not match the dataset class names. "
            "Stop and fix the dataset/model mismatch before training."
        )

    return model


def get_resume_checkpoint() -> Path | None:
    """Return the latest interrupted fine-tuning checkpoint, if one exists."""
    if LAST_WEIGHTS_PATH.is_file():
        return LAST_WEIGHTS_PATH
    return None


def main() -> None:
    """Run fine-tuning. This does not replace the production model."""
    try:
        validate_dataset_yaml()
        check_training_args_supported()
        device = select_device()
        resume_checkpoint = get_resume_checkpoint()
        weights_path = resume_checkpoint or MODEL_PATH
        model = load_model(weights_path)

        if resume_checkpoint is not None:
            print(f"Resuming fine-tuning from: {resume_checkpoint}")
        else:
            print(f"Starting fine-tuning from: {MODEL_PATH}")
        print(f"Using dataset YAML: {DATA_YAML_PATH}")
        print(f"Results directory: {RUNS_PROJECT / RUN_NAME}")

        if resume_checkpoint is not None:
            model.train(
                resume=True,
                imgsz=TRAINING_ARGS["imgsz"],
                batch=TRAINING_ARGS["batch"],
                device=device,
                plots=False,
            )
        else:
            model.train(
                data=str(DATA_YAML_PATH),
                imgsz=TRAINING_ARGS["imgsz"],
                epochs=TRAINING_ARGS["epochs"],
                batch=TRAINING_ARGS["batch"],
                patience=TRAINING_ARGS["patience"],
                project=str(RUNS_PROJECT),
                name=RUN_NAME,
                exist_ok=True,
                device=device,
                amp=False,
                plots=False,
                workers=2,
            )

        print("Fine-tuning complete.")
        print(
            "Best weights should be saved at: "
            f"{RUNS_PROJECT / RUN_NAME / 'weights' / 'best.pt'}"
        )
        print(f"Production model was not modified: {MODEL_PATH}")
    except KeyboardInterrupt:
        fail("Fine-tuning was interrupted by the user.")
    except Exception as error:
        traceback.print_exc()
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
