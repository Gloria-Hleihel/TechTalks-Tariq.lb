"""Stream a small YOLO subset from the Hugging Face unified road-defect dataset."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = PROJECT_ROOT / "dataset"

SOURCE_NAME = "TamAko783/Unified_Road_Defect_Dataset"
SOURCE_URL = "https://huggingface.co/datasets/TamAko783/Unified_Road_Defect_Dataset"
TRAIN_SHARD_URL = (
    "https://huggingface.co/datasets/TamAko783/Unified_Road_Defect_Dataset/"
    "resolve/main/data/train_a.tar.gz?download=true"
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
CLASS_NAMES = {
    0: "Longitudinal Crack",
    1: "Transverse Crack",
    2: "Alligator Crack",
    3: "Potholes",
}


@dataclass(frozen=True)
class Sample:
    """One streamed image plus its YOLO label text."""

    stem: str
    image_suffix: str
    image_bytes: bytes
    label_text: str


def fail(message: str) -> NoReturn:
    """Print a clear error and exit with failure."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description=(
            "Stream a practical YOLO subset from "
            "TamAko783/Unified_Road_Defect_Dataset into dataset/."
        )
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=500,
        help="Number of image/label pairs to stream before splitting.",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio. Use 0.2 for an 80/20 split.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Output dataset directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing files under dataset/images and dataset/labels.",
    )
    return parser.parse_args()


def resolve_project_path(path: Path) -> Path:
    """Resolve relative paths from the project root."""
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def validate_label_text(label_text: str, stem: str) -> dict[int, int]:
    """Validate YOLO labels and return per-class counts."""
    class_counts = {class_id: 0 for class_id in CLASS_NAMES}

    for line_number, raw_line in enumerate(label_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"{stem}.txt line {line_number} is not YOLO format.")

        try:
            class_id = int(parts[0])
            values = [float(value) for value in parts[1:]]
        except ValueError as error:
            raise ValueError(
                f"{stem}.txt line {line_number} contains non-numeric values."
            ) from error

        if class_id not in CLASS_NAMES:
            raise ValueError(
                f"{stem}.txt line {line_number} has unsupported class id {class_id}."
            )

        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError(
                f"{stem}.txt line {line_number} has coordinates outside 0..1."
            )

        class_counts[class_id] += 1

    return class_counts


def sample_key(member_name: str) -> str:
    """Return the filename stem used to match streamed image/label pairs."""
    return Path(member_name).stem


def stream_samples(max_images: int) -> tuple[list[Sample], dict[int, int]]:
    """Stream image/label pairs from the first Hugging Face train shard."""
    if max_images <= 1:
        raise ValueError("--max-images must be greater than 1.")

    pending_images: dict[str, tuple[str, bytes]] = {}
    pending_labels: dict[str, str] = {}
    samples: list[Sample] = []
    class_totals = {class_id: 0 for class_id in CLASS_NAMES}

    print(f"Streaming source: {SOURCE_NAME}")
    print(f"Shard URL: {TRAIN_SHARD_URL}")
    print(f"Target samples: {max_images}")

    with urllib.request.urlopen(TRAIN_SHARD_URL, timeout=60) as response:
        with tarfile.open(fileobj=response, mode="r|gz") as archive:
            for member in archive:
                if len(samples) >= max_images:
                    break

                if not member.isfile():
                    continue

                member_path = Path(member.name)
                suffix = member_path.suffix.lower()
                stem = sample_key(member.name)

                if "images" in member_path.parts and suffix in IMAGE_EXTENSIONS:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        continue
                    pending_images[stem] = (suffix, extracted.read())
                elif "labels" in member_path.parts and suffix == ".txt":
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        continue
                    pending_labels[stem] = extracted.read().decode("utf-8").strip()
                else:
                    continue

                if stem not in pending_images or stem not in pending_labels:
                    continue

                image_suffix, image_bytes = pending_images.pop(stem)
                label_text = pending_labels.pop(stem)
                class_counts = validate_label_text(label_text, stem)

                for class_id, count in class_counts.items():
                    class_totals[class_id] += count

                samples.append(
                    Sample(
                        stem=stem,
                        image_suffix=image_suffix,
                        image_bytes=image_bytes,
                        label_text=label_text,
                    )
                )

                if len(samples) % 50 == 0:
                    print(f"Streamed {len(samples)} image/label pairs...")

    if len(samples) < max_images:
        print(
            f"WARNING: Requested {max_images} samples but only streamed {len(samples)}."
        )

    if not samples:
        raise RuntimeError("No image/label pairs were streamed.")

    return samples, class_totals


def ensure_output_dirs(dataset_dir: Path, overwrite: bool) -> dict[str, Path]:
    """Create output directories and protect existing labels/images by default."""
    paths = {
        "train_images": dataset_dir / "images" / "train",
        "val_images": dataset_dir / "images" / "val",
        "train_labels": dataset_dir / "labels" / "train",
        "val_labels": dataset_dir / "labels" / "val",
    }

    existing_files = [
        path
        for directory in paths.values()
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file()
    ]

    if existing_files and not overwrite:
        raise FileExistsError(
            "dataset/images or dataset/labels already contains files. "
            "Use --overwrite only if you intentionally want to replace them."
        )

    if overwrite:
        for directory in paths.values():
            if directory.exists():
                shutil.rmtree(directory)

    for directory in paths.values():
        directory.mkdir(parents=True, exist_ok=True)

    return paths


def write_dataset_yaml(dataset_dir: Path) -> None:
    """Write the YOLO dataset YAML used by training and validation."""
    yaml_text = """# Paths are relative to this YAML file.
train: images/train
val: images/val

names:
  0: Longitudinal Crack
  1: Transverse Crack
  2: Alligator Crack
  3: Potholes
"""
    (dataset_dir / "road_damage.yaml").write_text(yaml_text, encoding="utf-8")


def split_samples(samples: list[Sample], val_ratio: float) -> tuple[list[Sample], list[Sample]]:
    """Split samples in blocks to reduce adjacent-frame train/val leakage."""
    if not 0.0 < val_ratio < 1.0:
        raise ValueError("--val-ratio must be between 0 and 1.")

    val_count = max(1, round(len(samples) * val_ratio))
    if val_count >= len(samples):
        val_count = len(samples) - 1

    train_count = len(samples) - val_count
    return samples[:train_count], samples[train_count:]


def write_samples(
    samples: list[Sample],
    image_dir: Path,
    label_dir: Path,
) -> dict[int, int]:
    """Write one split of image and label files."""
    class_totals = {class_id: 0 for class_id in CLASS_NAMES}

    for sample in samples:
        image_path = image_dir / f"{sample.stem}{sample.image_suffix}"
        label_path = label_dir / f"{sample.stem}.txt"

        image_path.write_bytes(sample.image_bytes)
        if sample.label_text:
            label_path.write_text(sample.label_text + "\n", encoding="utf-8")
        else:
            label_path.write_text("", encoding="utf-8")

        class_counts = validate_label_text(sample.label_text, sample.stem)
        for class_id, count in class_counts.items():
            class_totals[class_id] += count

    return class_totals


def class_count_summary(class_counts: dict[int, int]) -> dict[str, int]:
    """Return class counts with readable class labels."""
    return {
        f"{class_id} {CLASS_NAMES[class_id]}": class_counts.get(class_id, 0)
        for class_id in CLASS_NAMES
    }


def write_summary(
    dataset_dir: Path,
    samples: list[Sample],
    train_samples: list[Sample],
    val_samples: list[Sample],
    streamed_class_counts: dict[int, int],
    train_class_counts: dict[int, int],
    val_class_counts: dict[int, int],
) -> None:
    """Write a machine-readable preparation summary."""
    summary = {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "streamed_from": TRAIN_SHARD_URL,
        "total_images": len(samples),
        "train_images": len(train_samples),
        "val_images": len(val_samples),
        "empty_label_files": sum(1 for sample in samples if not sample.label_text),
        "streamed_instances_by_class": class_count_summary(streamed_class_counts),
        "train_instances_by_class": class_count_summary(train_class_counts),
        "val_instances_by_class": class_count_summary(val_class_counts),
        "split_note": (
            "Samples are split in one ordered block for train and one ordered block "
            "for validation to reduce adjacent-frame leakage."
        ),
    }
    summary_path = dataset_dir / "hf_unified_preparation_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Preparation summary: {summary_path}")


def main() -> None:
    """Prepare the local YOLO dataset from a streamed Hugging Face subset."""
    try:
        args = parse_args()
        dataset_dir = resolve_project_path(args.dataset_dir)

        samples, streamed_class_counts = stream_samples(args.max_images)
        train_samples, val_samples = split_samples(samples, args.val_ratio)
        output_dirs = ensure_output_dirs(dataset_dir, args.overwrite)
        write_dataset_yaml(dataset_dir)

        train_class_counts = write_samples(
            train_samples,
            output_dirs["train_images"],
            output_dirs["train_labels"],
        )
        val_class_counts = write_samples(
            val_samples,
            output_dirs["val_images"],
            output_dirs["val_labels"],
        )
        write_summary(
            dataset_dir,
            samples,
            train_samples,
            val_samples,
            streamed_class_counts,
            train_class_counts,
            val_class_counts,
        )

        print("Dataset preparation complete.")
        print(f"Train images: {len(train_samples)}")
        print(f"Validation images: {len(val_samples)}")
        print(f"Train instances: {class_count_summary(train_class_counts)}")
        print(f"Validation instances: {class_count_summary(val_class_counts)}")
        print(f"Dataset YAML: {dataset_dir / 'road_damage.yaml'}")
    except KeyboardInterrupt:
        fail("Dataset preparation was interrupted by the user.")
    except Exception as error:
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
