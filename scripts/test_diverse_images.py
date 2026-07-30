import csv
import os
from pathlib import Path
from time import perf_counter

from app.detection.detector import detect_damage


IMAGE_FOLDER = Path("test_images/diverse_set")
OUTPUT_FILE = Path("detection_test_results.csv")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def main():
    images = sorted(
        [
            path
            for path in IMAGE_FOLDER.iterdir()
            if path.suffix.lower() in SUPPORTED_EXTENSIONS
        ],
        key=lambda path: path.name.lower(),
    )

    if not images:
        print("No supported images were found.")
        return

    results = []

    for index, image_path in enumerate(images, start=1):
        print("=" * 60)
        print(f"[{index}/{len(images)}] Testing: {image_path.name}")

        started = perf_counter()

        try:
            result = detect_damage(str(image_path))
            elapsed_ms = round(
                (perf_counter() - started) * 1000,
                2,
            )

            row = {
                "image_file": image_path.name,
                "detected_result": result.get(
                    "damage_type",
                    "None",
                ),
                "confidence": result.get(
                    "confidence",
                    0.0,
                ),
                "severity_score": result.get(
                    "severity_score",
                    0,
                ),
                "severity_label": result.get(
                    "severity_label",
                    "None",
                ),
                "processing_time_ms": elapsed_ms,
                "bounding_box_count": len(
                    result.get("bounding_boxes", [])
                ),
                "annotated_image_path": result.get(
                    "annotated_image_path",
                    "",
                ),
                "error": "",
            }

            print(
                f"Detected: {row['detected_result']} | "
                f"Confidence: {row['confidence']} | "
                f"Time: {elapsed_ms} ms"
            )

        except Exception as exc:
            elapsed_ms = round(
                (perf_counter() - started) * 1000,
                2,
            )

            row = {
                "image_file": image_path.name,
                "detected_result": "",
                "confidence": "",
                "severity_score": "",
                "severity_label": "",
                "processing_time_ms": elapsed_ms,
                "bounding_box_count": "",
                "annotated_image_path": "",
                "error": str(exc),
            }

            print(f"Error: {exc}")

        results.append(row)

    fieldnames = [
        "image_file",
        "detected_result",
        "confidence",
        "severity_score",
        "severity_label",
        "processing_time_ms",
        "bounding_box_count",
        "annotated_image_path",
        "error",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(results)

    print("=" * 60)
    print(f"Finished testing {len(results)} images.")
    print(f"Results saved to: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()