"""Build the local Lebanese populated-places gazetteer for Tariq.lb.

The generated JSON is used by the report upload search bar so users can find
cities, towns, villages, municipalities, and localities across Lebanon without
maintaining a small hardcoded list.
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GEONAMES_BASE_URL = "https://download.geonames.org/export/dump"
COUNTRY_ZIP_URL = f"{GEONAMES_BASE_URL}/LB.zip"
ALT_NAMES_ZIP_URL = f"{GEONAMES_BASE_URL}/alternatenames/LB.zip"
ADMIN1_URL = f"{GEONAMES_BASE_URL}/admin1CodesASCII.txt"
ADMIN2_URL = f"{GEONAMES_BASE_URL}/admin2Codes.txt"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "lebanon_localities.json"
USER_AGENT = "Tariq.lb localities builder (student civic-tech project)"

POPULATED_FEATURE_CODES = {
    "PPLC",   # capital of a political entity
    "PPLA",   # seat of a first-order administrative division
    "PPLA2",  # seat of a second-order administrative division
    "PPLA3",  # seat of a third-order administrative division
    "PPLA4",  # seat of a fourth-order administrative division
    "PPL",    # populated place: city, town, village, or settlement
    "PPLL",   # populated locality
    "PPLS",   # populated places
    "PPLX",   # section of populated place
}

FEATURE_TYPE_LABELS = {
    "PPLC": "capital",
    "PPLA": "governorate center",
    "PPLA2": "district center",
    "PPLA3": "municipality center",
    "PPLA4": "local administrative center",
    "PPL": "populated place",
    "PPLL": "locality",
    "PPLS": "populated places",
    "PPLX": "locality",
}

BLOCKED_ALT_LANGUAGE_CODES = {
    "abbr",
    "fr_1793",
    "iata",
    "icao",
    "link",
    "post",
    "wkdt",
}

GEONAME_COLUMNS = [
    "geoname_id",
    "name",
    "ascii_name",
    "alternate_names",
    "latitude",
    "longitude",
    "feature_class",
    "feature_code",
    "country_code",
    "cc2",
    "admin1_code",
    "admin2_code",
    "admin3_code",
    "admin4_code",
    "population",
    "elevation",
    "dem",
    "timezone",
    "modification_date",
]


def download(url: str, destination: Path) -> None:
    """Download one GeoNames file with a clear User-Agent."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def read_zip_text(zip_path: Path, member_name: str) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member_name) as file:
            return file.read().decode("utf-8")


def load_admin_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter="\t")
        for row in reader:
            if len(row) >= 2:
                mapping[row[0]] = row[1]

    return mapping


def clean_name(value: str | None) -> str | None:
    text = (value or "").strip()

    if not text or text.startswith("http://") or text.startswith("https://"):
        return None

    return text


def unique_names(values: list[str | None], *, limit: int = 80) -> list[str]:
    seen = set()
    names = []

    for value in values:
        name = clean_name(value)
        if not name:
            continue

        key = name.casefold()
        if key in seen:
            continue

        seen.add(key)
        names.append(name)

        if len(names) >= limit:
            break

    return names


def parse_alternate_names(text: str, wanted_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Parse GeoNames alternate names for Lebanese populated places only."""
    records: dict[str, dict[str, Any]] = defaultdict(lambda: {"aliases": [], "ar": [], "en": []})
    reader = csv.reader(text.splitlines(), delimiter="\t")

    for row in reader:
        if len(row) < 4:
            continue

        geoname_id = row[1]
        if geoname_id not in wanted_ids:
            continue

        language = row[2].casefold()
        name = clean_name(row[3])
        if not name or language in BLOCKED_ALT_LANGUAGE_CODES:
            continue

        records[geoname_id]["aliases"].append(name)

        if language == "ar":
            records[geoname_id]["ar"].append(name)
        elif language == "en":
            records[geoname_id]["en"].append(name)

    return records


def parse_population(value: str) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def build_places(
    country_text: str,
    admin1: dict[str, str],
    admin2: dict[str, str],
    alternate_records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    places: list[dict[str, Any]] = []
    reader = csv.DictReader(
        country_text.splitlines(),
        delimiter="\t",
        fieldnames=GEONAME_COLUMNS,
    )

    for row in reader:
        if row["country_code"] != "LB":
            continue

        if row["feature_class"] != "P":
            continue

        feature_code = row["feature_code"]
        if feature_code not in POPULATED_FEATURE_CODES:
            continue

        geoname_id = row["geoname_id"]
        alternate_record = alternate_records.get(geoname_id, {})
        alternates_from_country = (row["alternate_names"] or "").split(",")
        aliases = unique_names(
            [
                row["name"],
                row["ascii_name"],
                *alternates_from_country,
                *alternate_record.get("aliases", []),
            ]
        )

        admin1_key = f"LB.{row['admin1_code']}"
        admin2_key = f"LB.{row['admin1_code']}.{row['admin2_code']}"
        governorate = admin1.get(admin1_key)
        district = admin2.get(admin2_key)
        name_en = clean_name((alternate_record.get("en") or [None])[0]) or clean_name(row["ascii_name"]) or row["name"]
        name_ar = clean_name((alternate_record.get("ar") or [None])[0])

        places.append(
            {
                "geoname_id": int(geoname_id),
                "name": row["name"],
                "name_en": name_en,
                "name_ar": name_ar,
                "ascii_name": row["ascii_name"],
                "alternate_names": aliases,
                "district": district,
                "governorate": governorate,
                "lat": float(row["latitude"]),
                "lng": float(row["longitude"]),
                "type": FEATURE_TYPE_LABELS.get(feature_code, "populated place"),
                "feature_code": feature_code,
                "population": parse_population(row["population"]),
            }
        )

    places.sort(
        key=lambda item: (
            -int(item.get("population") or 0),
            str(item.get("name_en") or item.get("name") or "").casefold(),
            int(item["geoname_id"]),
        )
    )
    return places


def build(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    with tempfile.TemporaryDirectory(prefix="tariq_geonames_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        country_zip = tmp_dir / "LB.zip"
        alt_zip = tmp_dir / "LB_alternate_names.zip"
        admin1_path = tmp_dir / "admin1CodesASCII.txt"
        admin2_path = tmp_dir / "admin2Codes.txt"

        print("Downloading GeoNames Lebanon country dump...")
        download(COUNTRY_ZIP_URL, country_zip)
        print("Downloading GeoNames Lebanon alternate names...")
        download(ALT_NAMES_ZIP_URL, alt_zip)
        print("Downloading GeoNames admin maps...")
        download(ADMIN1_URL, admin1_path)
        download(ADMIN2_URL, admin2_path)

        country_text = read_zip_text(country_zip, "LB.txt")
        wanted_ids = {
            row.split("\t", 1)[0]
            for row in country_text.splitlines()
            if "\tP\t" in row
        }
        alternate_text = read_zip_text(alt_zip, "LB.txt")
        alternate_records = parse_alternate_names(alternate_text, wanted_ids)
        places = build_places(
            country_text=country_text,
            admin1=load_admin_map(admin1_path),
            admin2=load_admin_map(admin2_path),
            alternate_records=alternate_records,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "GeoNames",
        "license": "Creative Commons Attribution 4.0",
        "source_urls": {
            "country_dump": COUNTRY_ZIP_URL,
            "alternate_names": ALT_NAMES_ZIP_URL,
            "admin1": ADMIN1_URL,
            "admin2": ADMIN2_URL,
        },
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "country_code": "LB",
        "feature_codes": sorted(POPULATED_FEATURE_CODES),
        "count": len(places),
        "places": places,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(places)} Lebanese populated places to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build data/lebanon_localities.json from GeoNames Lebanon populated places."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination JSON file. Defaults to data/lebanon_localities.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(args.output)


if __name__ == "__main__":
    main()