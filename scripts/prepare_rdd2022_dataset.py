"""Download and convert an official RDD2022 subset into YOLO format."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = PROJECT_ROOT / "dataset"
DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "work" / "rdd2022"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
CLASS_MAP = {
    "D00": 0,
    "D10": 1,
    "D20": 2,
    "D40": 3,
}
CLASS_NAMES = {
    0: "Longitudinal Crack",
    1: "Transverse Crack",
    2: "Alligator Crack",
    3: "Potholes",
}


@dataclass(frozen=True)
class DatasetSource:
    """Metadata for one downloadable RDD2022 source archive."""

    key: str
    description: str
    url: str
    size_mb: float


SOURCES = {
    "china_motorbike": DatasetSource(
        key="china_motorbike",
        description="RDD2022 China MotorBike subset (train and test)",
        url=(
            "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/"
            "CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/"
            "RDD2022_China_MotorBike.zip"
        ),
        size_mb=183.1,
    ),
    "china_drone": DatasetSource(
        key="china_drone",
        description="RDD2022 China Drone subset (train only)",
        url=(
            "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/"
            "CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/"
            "RDD2022_China_Drone.zip"
        ),
        size_mb=152.8,
    ),
    "czech": DatasetSource(
        key="czech",
        description="RDD2022 Czech subset (train and test)",
        url=(
            "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/"
            "CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/"
            "RDD2022_Czech.zip"
        ),
        size_mb=245.2,
    ),
    "united_states": DatasetSource(
        key="united_states",
        description="RDD2022 United States subset (train and test)",
        url=(
            "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/"
            "CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/"
            "RDD2022_United_States.zip"
        ),
        size_mb=423.8,
    ),
}


@dataclass(frozen=True)
class ConvertedItem:
    """One image and its converted YOLO label lines."""

    image_path: Path
    output_stem: str
    yolo_lines: list[str]
    class_counts: dict[int, int]
    ignored_objects: int


def fail(message: str) -> NoReturn:
    """Print a clear error and exit with failure."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description=(
            "Download an official RDD2022 subset, convert Pascal VOC XML labels "
            "to YOLO labels, and split into dataset/images + dataset/labels."
        )
    )
    parser.add_argument(
        "--source",
        choices=sorted(SOURCES),
        default="china_motorbike",
        help="RDD2022 subset to download and convert.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Output dataset directory.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=DEFAULT_DOWNLOAD_DIR,
        help="Directory for downloaded and extracted raw data.",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio. Use 0.2 for an 80/20 split.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic splitting.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Optional cap for quick experiments. By default, all converted images are used.",
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


def download_file(url: str, destination: Path) -> None:
    """Download a file if it does not already exist."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_file() and destination.stat().st_size > 0:
        print(f"Using existing download: {destination}")
        return

    temporary_path = destination.with_suffix(destination.suffix + ".part")
    if temporary_path.exists():
        temporary_path.unlink()

    print(f"Downloading: {url}")
    print(f"Destination: {destination}")

    with urllib.request.urlopen(url, timeout=60) as response:
        total_bytes = int(response.headers.get("Content-Length") or 0)
        downloaded_bytes = 0

        with temporary_path.open("wb") as output_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break

                output_file.write(chunk)
                downloaded_bytes += len(chunk)

                if total_bytes:
                    percent = downloaded_bytes / total_bytes * 100
                    print(
                        f"\rDownloaded {downloaded_bytes / (1024 ** 2):.1f} MB "
                        f"of {total_bytes / (1024 ** 2):.1f} MB ({percent:.1f}%)",
                        end="",
                    )

    if total_bytes:
        print()

    temporary_path.replace(destination)


def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    """Extract a zip file while preventing path traversal."""
    marker_file = extract_dir / ".extract_complete"
    if marker_file.is_file():
        print(f"Using existing extraction: {extract_dir}")
        return

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target_path = (extract_dir / member.filename).resolve()
            try:
                target_path.relative_to(extract_dir.resolve())
            except ValueError as error:
                raise RuntimeError(
                    f"Unsafe archive member path blocked: {member.filename}"
                ) from error

        archive.extractall(extract_dir)

    marker_file.write_text("ok\n", encoding="utf-8")


def build_image_indexes(extract_dir: Path) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    """Index extracted images by filename and stem."""
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}

    for image_path in sorted(extract_dir.rglob("*")):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        by_name.setdefault(image_path.name.lower(), []).append(image_path)
        by_stem.setdefault(image_path.stem.lower(), []).append(image_path)

    return by_name, by_stem


def choose_best_image_match(xml_path: Path, candidates: list[Path]) -> Path:
    """Choose the most likely train image for a Pascal VOC annotation file."""
    xml_parts = {part.lower() for part in xml_path.parts}

    def score(candidate: Path) -> tuple[int, int, str]:
        candidate_parts = {part.lower() for part in candidate.parts}
        value = 0
        if "train" in candidate_parts:
            value -= 100
        if "test" in candidate_parts:
            value += 100
        value -= len(xml_parts.intersection(candidate_parts))
        return value, len(str(candidate)), str(candidate)

    return sorted(candidates, key=score)[0]


def find_image_for_xml(
    xml_path: Path,
    xml_root: ElementTree.Element,
    images_by_name: dict[str, list[Path]],
    images_by_stem: dict[str, list[Path]],
) -> Path | None:
    """Find the image file referenced by a Pascal VOC XML annotation."""
    filename = (xml_root.findtext("filename") or "").strip()
    candidates: list[Path] = []

    if filename:
        candidates.extend(images_by_name.get(filename.lower(), []))

    if not candidates:
        candidates.extend(images_by_stem.get(xml_path.stem.lower(), []))

    if not candidates:
        return None

    return choose_best_image_match(xml_path, candidates)


def read_image_size_from_xml(xml_root: ElementTree.Element) -> tuple[int, int] | None:
    """Read image width and height from a Pascal VOC XML annotation."""
    size = xml_root.find("size")
    if size is None:
        return None

    try:
        width = int(float(size.findtext("width") or "0"))
        height = int(float(size.findtext("height") or "0"))
    except ValueError:
        return None

    if width <= 0 or height <= 0:
        return None

    return width, height


def read_image_size(image_path: Path, xml_root: ElementTree.Element) -> tuple[int, int]:
    """Read image size from XML, falling back to Pillow if needed."""
    xml_size = read_image_size_from_xml(xml_root)
    if xml_size is not None:
        return xml_size

    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError(
            "Pillow is required when XML files do not contain image dimensions."
        ) from error

    with Image.open(image_path) as image:
        return image.size


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value to a range."""
    return max(minimum, min(maximum, value))


def parse_bbox(
    box: ElementTree.Element,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float] | None:
    """Convert a Pascal VOC bbox to normalized YOLO coordinates."""
    try:
        xmin = float(box.findtext("xmin") or "0")
        ymin = float(box.findtext("ymin") or "0")
        xmax = float(box.findtext("xmax") or "0")
        ymax = float(box.findtext("ymax") or "0")
    except ValueError:
        return None

    xmin = clamp(xmin, 0.0, float(image_width))
    xmax = clamp(xmax, 0.0, float(image_width))
    ymin = clamp(ymin, 0.0, float(image_height))
    ymax = clamp(ymax, 0.0, float(image_height))

    if xmax <= xmin or ymax <= ymin:
        return None

    x_center = ((xmin + xmax) / 2.0) / image_width
    y_center = ((ymin + ymax) / 2.0) / image_height
    width = (xmax - xmin) / image_width
    height = (ymax - ymin) / image_height

    values = (x_center, y_center, width, height)
    if any(value < 0.0 or value > 1.0 for value in values):
        return None

    return values


def sanitize_stem(value: str) -> str:
    """Make a filesystem-safe output stem."""
    safe_chars = []
    for character in value:
        if character.isalnum() or character in {"-", "_"}:
            safe_chars.append(character)
        else:
            safe_chars.append("_")
    return "".join(safe_chars).strip("_")


def make_output_stem(
    source_key: str,
    extract_dir: Path,
    image_path: Path,
    used_stems: set[str],
) -> str:
    """Create a stable unique stem for the converted image and label."""
    relative_stem = image_path.relative_to(extract_dir).with_suffix("").as_posix()
    base_stem = sanitize_stem(f"rdd2022_{source_key}_{relative_stem}")
    output_stem = base_stem
    counter = 2

    while output_stem in used_stems:
        output_stem = f"{base_stem}_{counter}"
        counter += 1

    used_stems.add(output_stem)
    return output_stem


def convert_annotation(
    source_key: str,
    extract_dir: Path,
    xml_path: Path,
    images_by_name: dict[str, list[Path]],
    images_by_stem: dict[str, list[Path]],
    used_stems: set[str],
) -> ConvertedItem | None:
    """Convert one Pascal VOC XML annotation to YOLO label lines."""
    xml_root = ElementTree.parse(xml_path).getroot()
    image_path = find_image_for_xml(xml_path, xml_root, images_by_name, images_by_stem)
    if image_path is None:
        return None

    image_width, image_height = read_image_size(image_path, xml_root)
    yolo_lines: list[str] = []
    class_counts = {class_id: 0 for class_id in CLASS_NAMES}
    ignored_objects = 0

    for object_node in xml_root.findall("object"):
        raw_name = (object_node.findtext("name") or "").strip()
        class_id = CLASS_MAP.get(raw_name)
        if class_id is None:
            ignored_objects += 1
            continue

        box = object_node.find("bndbox")
        if box is None:
            ignored_objects += 1
            continue

        converted_box = parse_bbox(box, image_width, image_height)
        if converted_box is None:
            ignored_objects += 1
            continue

        x_center, y_center, width, height = converted_box
        yolo_lines.append(
            f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
        )
        class_counts[class_id] += 1

    output_stem = make_output_stem(source_key, extract_dir, image_path, used_stems)
    return ConvertedItem(
        image_path=image_path,
        output_stem=output_stem,
        yolo_lines=yolo_lines,
        class_counts=class_counts,
        ignored_objects=ignored_objects,
    )


def collect_converted_items(
    source_key: str,
    extract_dir: Path,
    max_images: int | None,
    seed: int,
) -> tuple[list[ConvertedItem], int]:
    """Convert all XML annotations that can be matched to images."""
    images_by_name, images_by_stem = build_image_indexes(extract_dir)
    xml_paths = sorted(extract_dir.rglob("*.xml"))

    if not xml_paths:
        raise FileNotFoundError(f"No Pascal VOC XML annotations found in {extract_dir}")

    used_stems: set[str] = set()
    converted_items: list[ConvertedItem] = []
    missing_image_count = 0

    for xml_path in xml_paths:
        item = convert_annotation(
            source_key,
            extract_dir,
            xml_path,
            images_by_name,
            images_by_stem,
            used_stems,
        )
        if item is None:
            missing_image_count += 1
            continue

        converted_items.append(item)

    if max_images is not None:
        if max_images <= 0:
            raise ValueError("--max-images must be greater than zero.")
        randomizer = random.Random(seed)
        randomizer.shuffle(converted_items)
        converted_items = converted_items[:max_images]

    if not converted_items:
        raise RuntimeError("No annotations were converted.")

    return converted_items, missing_image_count


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


def split_items(
    items: list[ConvertedItem],
    val_ratio: float,
    seed: int,
) -> tuple[list[ConvertedItem], list[ConvertedItem]]:
    """Create a deterministic train/validation split."""
    if not 0.0 < val_ratio < 1.0:
        raise ValueError("--val-ratio must be between 0 and 1.")

    shuffled_items = items[:]
    random.Random(seed).shuffle(shuffled_items)

    val_count = max(1, round(len(shuffled_items) * val_ratio))
    if val_count >= len(shuffled_items):
        val_count = len(shuffled_items) - 1

    val_items = shuffled_items[:val_count]
    train_items = shuffled_items[val_count:]
    return train_items, val_items


def copy_converted_items(
    items: list[ConvertedItem],
    image_dir: Path,
    label_dir: Path,
) -> dict[int, int]:
    """Copy images and write YOLO labels for one split."""
    class_totals = {class_id: 0 for class_id in CLASS_NAMES}

    for item in items:
        output_image = image_dir / f"{item.output_stem}{item.image_path.suffix.lower()}"
        output_label = label_dir / f"{item.output_stem}.txt"

        shutil.copy2(item.image_path, output_image)
        if item.yolo_lines:
            output_label.write_text(
                "\n".join(item.yolo_lines) + "\n",
                encoding="utf-8",
            )
        else:
            output_label.write_text("", encoding="utf-8")

        for class_id, count in item.class_counts.items():
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
    source: DatasetSource,
    train_items: list[ConvertedItem],
    val_items: list[ConvertedItem],
    train_class_counts: dict[int, int],
    val_class_counts: dict[int, int],
    missing_image_count: int,
) -> None:
    """Write a machine-readable preparation summary."""
    all_items = train_items + val_items
    summary = {
        "source": source.description,
        "source_url": source.url,
        "source_size_mb": source.size_mb,
        "total_images": len(all_items),
        "train_images": len(train_items),
        "val_images": len(val_items),
        "empty_label_files": sum(1 for item in all_items if not item.yolo_lines),
        "ignored_objects": sum(item.ignored_objects for item in all_items),
        "annotations_missing_matching_image": missing_image_count,
        "train_instances_by_class": class_count_summary(train_class_counts),
        "val_instances_by_class": class_count_summary(val_class_counts),
    }
    summary_path = dataset_dir / "rdd2022_preparation_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Preparation summary: {summary_path}")


def main() -> None:
    """Prepare the local YOLO dataset from an official RDD2022 subset."""
    try:
        args = parse_args()
        source = SOURCES[args.source]
        dataset_dir = resolve_project_path(args.dataset_dir)
        download_dir = resolve_project_path(args.download_dir)
        zip_path = download_dir / f"{source.key}.zip"
        extract_dir = download_dir / source.key

        print(f"Selected source: {source.description}")
        print(f"Expected download size: {source.size_mb:.1f} MB")

        download_file(source.url, zip_path)
        safe_extract_zip(zip_path, extract_dir)

        converted_items, missing_image_count = collect_converted_items(
            source.key,
            extract_dir,
            args.max_images,
            args.seed,
        )
        train_items, val_items = split_items(
            converted_items,
            args.val_ratio,
            args.seed,
        )
        output_dirs = ensure_output_dirs(dataset_dir, args.overwrite)
        write_dataset_yaml(dataset_dir)

        train_class_counts = copy_converted_items(
            train_items,
            output_dirs["train_images"],
            output_dirs["train_labels"],
        )
        val_class_counts = copy_converted_items(
            val_items,
            output_dirs["val_images"],
            output_dirs["val_labels"],
        )

        write_summary(
            dataset_dir,
            source,
            train_items,
            val_items,
            train_class_counts,
            val_class_counts,
            missing_image_count,
        )

        print("Dataset preparation complete.")
        print(f"Train images: {len(train_items)}")
        print(f"Validation images: {len(val_items)}")
        print(f"Train instances: {class_count_summary(train_class_counts)}")
        print(f"Validation instances: {class_count_summary(val_class_counts)}")
        print(f"Dataset YAML: {dataset_dir / 'road_damage.yaml'}")
    except KeyboardInterrupt:
        fail("Dataset preparation was interrupted by the user.")
    except Exception as error:
        fail(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
