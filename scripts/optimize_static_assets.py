"""Create lightweight WebP copies for large static images.

This script is intentionally non-destructive: it never replaces the original
PNG/JPEG files. Run it from the project root after installing Pillow.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_MAX_WIDTH = 1800
DEFAULT_QUALITY = 82


def format_size(num_bytes: int) -> str:
    """Return a readable file size."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def optimize_image(path: Path, max_width: int, quality: int) -> Path | None:
    """Create or refresh a WebP version of one image."""
    target = path.with_suffix(".webp")

    with Image.open(path) as image:
        image = image.convert("RGB")
        if image.width > max_width:
            ratio = max_width / image.width
            image = image.resize(
                (max_width, int(image.height * ratio)),
                Image.Resampling.LANCZOS,
            )

        image.save(target, "WEBP", quality=quality, method=6)

    return target


def main() -> None:
    project_root = Path.cwd()
    image_root = project_root / "static" / "images"

    if not image_root.is_dir():
        raise SystemExit(f"Static image folder not found: {image_root}")

    candidates = [
        path
        for path in image_root.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not candidates:
        print("No JPG/PNG images found to optimize.")
        return

    for source in candidates:
        target = optimize_image(source, DEFAULT_MAX_WIDTH, DEFAULT_QUALITY)
        before = source.stat().st_size
        after = target.stat().st_size if target else 0
        savings = 100 - ((after / before) * 100) if before else 0
        print(
            f"{source.name}: {format_size(before)} -> "
            f"{target.name}: {format_size(after)} ({savings:.1f}% smaller)"
        )


if __name__ == "__main__":
    main()
