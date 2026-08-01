from __future__ import annotations

import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests


LEBANON_BOUNDS = {
    "south": 33.03,
    "west": 35.09,
    "north": 34.72,
    "east": 36.66,
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCALITIES_DATA_PATH = PROJECT_ROOT / "data" / "lebanon_localities.json"
LOCALITIES_DATA_PATH = DEFAULT_LOCALITIES_DATA_PATH

ARABIC_NORMALIZATION = str.maketrans(
    {
        "\u0622": "\u0627",
        "\u0623": "\u0627",
        "\u0625": "\u0627",
        "\u0649": "\u064a",
        "\u0629": "\u0647",
        "\u0624": "\u0648",
        "\u0626": "\u064a",
    }
)
SEARCH_TOKEN_PATTERN = re.compile(r"[^0-9a-z\u0600-\u06ff]+")

# Approximate national outline used for backend validation. The browser uses
# the same polygon for immediate feedback, but the server remains authoritative.
LEBANON_POLYGON = [
    [34.69, 35.98],
    [34.62, 36.32],
    [34.38, 36.55],
    [34.10, 36.63],
    [33.78, 36.55],
    [33.58, 36.36],
    [33.33, 35.92],
    [33.10, 35.67],
    [33.05, 35.20],
    [33.24, 35.17],
    [33.52, 35.32],
    [33.78, 35.38],
    [33.91, 35.44],
    [34.08, 35.56],
    [34.20, 35.65],
    [34.32, 35.58],
    [34.50, 35.74],
]

SETTLEMENT_CLASSES = {"place", "boundary"}
SETTLEMENT_TYPES = {
    "city",
    "town",
    "village",
    "hamlet",
    "locality",
    "municipality",
    "administrative",
    "suburb",
    "neighbourhood",
    "quarter",
}

REJECTED_TYPES = {
    "road",
    "street",
    "highway",
    "shop",
    "amenity",
    "building",
    "commercial",
    "industrial",
    "tourism",
    "leisure",
}

LOCATION_SOURCE_ALIASES = {
    "browser": "browser",
    "gps": "gps",
    "manual": "manual",
    "search": "search",
}

SEARCH_RESULT_LIMIT = 50
NOMINATIM_RESULT_LIMIT = 50
SEARCH_MIN_REMOTE_LENGTH = 2
NEAR_DUPLICATE_DEGREES = 0.003

LOCAL_LEBANESE_LOCALITIES = [
    {"name": "Beirut", "governorate": "Beirut Governorate", "lat": 33.8938, "lng": 35.5018, "type": "city"},
    {"name": "Byblos", "governorate": "Mount Lebanon", "lat": 34.1230, "lng": 35.6519, "type": "city"},
    {"name": "Batroun", "governorate": "North Lebanon", "lat": 34.2553, "lng": 35.6581, "type": "city"},
    {"name": "Bater", "governorate": "Mount Lebanon", "lat": 33.60207, "lng": 35.61731, "type": "village"},
    {"name": "Baalbek", "governorate": "Baalbek-Hermel", "lat": 34.0058, "lng": 36.2181, "type": "city"},
    {"name": "Bsharri", "governorate": "North Lebanon", "lat": 34.2503, "lng": 36.0106, "type": "town"},
    {"name": "Bhamdoun", "governorate": "Mount Lebanon", "lat": 33.7956, "lng": 35.6525, "type": "town"},
    {"name": "Bint Jbeil", "governorate": "Nabatieh", "lat": 33.1197, "lng": 35.4336, "type": "town"},
    {"name": "Bteghrine", "governorate": "Mount Lebanon", "lat": 33.9256, "lng": 35.7464, "type": "village"},
    {"name": "Barouk", "governorate": "Mount Lebanon", "lat": 33.6975, "lng": 35.6961, "type": "village"},
    {"name": "Beit Mery", "governorate": "Mount Lebanon", "lat": 33.8617, "lng": 35.5958, "type": "town"},
    {"name": "Beit ed-Dine", "governorate": "Mount Lebanon", "lat": 33.6956, "lng": 35.5808, "type": "town"},
    {"name": "Tripoli", "governorate": "North Lebanon", "lat": 34.4367, "lng": 35.8497, "type": "city"},
    {"name": "Jounieh", "governorate": "Mount Lebanon", "lat": 33.9808, "lng": 35.6178, "type": "city"},
    {"name": "Zahle", "governorate": "Bekaa", "lat": 33.8467, "lng": 35.9020, "type": "city"},
    {"name": "Saida", "governorate": "South Lebanon", "lat": 33.5571, "lng": 35.3715, "type": "city"},
    {"name": "Tyre", "governorate": "South Lebanon", "lat": 33.2705, "lng": 35.2038, "type": "city"},
    {"name": "Aley", "governorate": "Mount Lebanon", "lat": 33.8106, "lng": 35.5972, "type": "city"},
    {"name": "Jezzine", "governorate": "South Lebanon", "lat": 33.5418, "lng": 35.5847, "type": "town"},
    {"name": "Nabatieh", "governorate": "Nabatieh", "lat": 33.3772, "lng": 35.4839, "type": "city"},
    {"name": "Jbeil", "governorate": "Mount Lebanon", "lat": 34.1230, "lng": 35.6519, "type": "city"},
    {"name": "Dbayeh", "governorate": "Mount Lebanon", "lat": 33.9470, "lng": 35.5886, "type": "town"},
    {"name": "Antelias", "governorate": "Mount Lebanon", "lat": 33.9181, "lng": 35.5894, "type": "town"},
    {"name": "Bikfaya", "governorate": "Mount Lebanon", "lat": 33.9206, "lng": 35.6794, "type": "town"},
    {"name": "Zgharta", "governorate": "North Lebanon", "lat": 34.3975, "lng": 35.8953, "type": "city"},
    {"name": "Ehden", "governorate": "North Lebanon", "lat": 34.3083, "lng": 35.9786, "type": "town"},
    {"name": "Halba", "governorate": "Akkar", "lat": 34.5428, "lng": 36.0797, "type": "town"},
    {"name": "Hermel", "governorate": "Baalbek-Hermel", "lat": 34.3942, "lng": 36.3847, "type": "city"},
    {"name": "Rashaya", "governorate": "Bekaa", "lat": 33.5008, "lng": 35.8397, "type": "town"},
    {"name": "Marjayoun", "governorate": "Nabatieh", "lat": 33.3603, "lng": 35.5911, "type": "town"},
    {"name": "Hasbaya", "governorate": "Nabatieh", "lat": 33.3975, "lng": 35.6858, "type": "town"},
]


class LocationValidationError(ValueError):
    """Raised when submitted coordinates cannot be accepted."""


class GeocoderError(RuntimeError):
    """Raised when the locality search provider fails."""


def is_valid_coordinate_pair(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180


def is_inside_lebanon_bounds(lat: float, lng: float) -> bool:
    return (
        LEBANON_BOUNDS["south"] <= lat <= LEBANON_BOUNDS["north"]
        and LEBANON_BOUNDS["west"] <= lng <= LEBANON_BOUNDS["east"]
    )


def is_inside_polygon(lat: float, lng: float) -> bool:
    inside = False
    point_x = lng
    point_y = lat
    vertices = LEBANON_POLYGON
    previous = vertices[-1]

    for current in vertices:
        current_y, current_x = current
        previous_y, previous_x = previous

        intersects = (current_y > point_y) != (previous_y > point_y)
        if intersects:
            slope_x = (previous_x - current_x) * (
                point_y - current_y
            ) / (previous_y - current_y) + current_x
            if point_x < slope_x:
                inside = not inside

        previous = current

    return inside


def is_inside_lebanon(lat: float, lng: float) -> bool:
    if not is_valid_coordinate_pair(lat, lng):
        return False

    if not is_inside_lebanon_bounds(lat, lng):
        return False

    return is_inside_polygon(lat, lng)


def validate_lebanon_coordinates(lat: float, lng: float) -> None:
    if not is_valid_coordinate_pair(lat, lng):
        raise LocationValidationError(
            "Please select valid latitude and longitude values."
        )

    if not is_inside_lebanon(lat, lng):
        raise LocationValidationError(
            "Please select a location inside Lebanon."
        )


def normalize_location_source(source: str | None) -> str:
    normalized = (source or "manual").strip().lower()
    return LOCATION_SOURCE_ALIASES.get(normalized, "manual")


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_for_search(value: Any) -> str:
    text = str(value or "").strip().translate(ARABIC_NORMALIZATION).casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = SEARCH_TOKEN_PATTERN.sub(" ", text)
    return " ".join(text.split())


def _candidate_values(locality: dict[str, Any]) -> tuple[str, ...]:
    values = [
        locality.get("name"),
        locality.get("name_en"),
        locality.get("name_ar"),
        locality.get("ascii_name"),
        locality.get("display_name"),
        locality.get("district"),
        locality.get("governorate"),
    ]
    values.extend(locality.get("alternate_names") or [])

    normalized_values = []
    seen = set()
    for value in values:
        normalized = _normalize_for_search(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)

    return tuple(normalized_values)


def _prepare_gazetteer_result(place: dict[str, Any]) -> dict[str, Any] | None:
    try:
        lat = float(place.get("lat"))
        lng = float(place.get("lng"))
    except (TypeError, ValueError):
        return None

    if not is_inside_lebanon(lat, lng):
        return None

    name = _clean_text(place.get("name_en")) or _clean_text(place.get("ascii_name")) or _clean_text(place.get("name"))
    if not name:
        return None

    result = {
        "geoname_id": place.get("geoname_id"),
        "name": name,
        "name_en": _clean_text(place.get("name_en")) or name,
        "name_ar": _clean_text(place.get("name_ar")),
        "ascii_name": _clean_text(place.get("ascii_name")) or name,
        "alternate_names": place.get("alternate_names") or [],
        "district": _clean_text(place.get("district")),
        "governorate": _clean_text(place.get("governorate")),
        "lat": lat,
        "lng": lng,
        "type": _clean_text(place.get("type")) or "populated place",
        "feature_code": _clean_text(place.get("feature_code")),
        "population": int(place.get("population") or 0),
        "bounding_box": None,
        "source": "geonames",
    }
    result["display_name"] = _compact_display_name(
        result.get("name"),
        result.get("district"),
        result.get("governorate"),
    )
    return result


def _fallback_localities() -> tuple[dict[str, Any], ...]:
    return tuple(_with_display_name(item) for item in LOCAL_LEBANESE_LOCALITIES)


@lru_cache(maxsize=1)
def _load_gazetteer_payload() -> tuple[bool, tuple[dict[str, Any], ...]]:
    if not LOCALITIES_DATA_PATH.exists():
        return False, _fallback_localities()

    try:
        payload = json.loads(LOCALITIES_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, _fallback_localities()

    places = []
    for place in payload.get("places", []):
        if not isinstance(place, dict):
            continue

        result = _prepare_gazetteer_result(place)
        if result:
            places.append(result)

    if not places:
        return False, _fallback_localities()

    return True, tuple(places)


def _gazetteer_available() -> bool:
    available, _places = _load_gazetteer_payload()
    return available


def _gazetteer_places() -> tuple[dict[str, Any], ...]:
    available, places = _load_gazetteer_payload()

    if not available or LOCALITIES_DATA_PATH != DEFAULT_LOCALITIES_DATA_PATH:
        return tuple(_dedupe_results(places))

    return tuple(_dedupe_results((*_fallback_localities(), *places)))


def _display_part(raw_place: dict[str, Any], keys: list[str]) -> str | None:
    address = raw_place.get("address") or {}

    for key in keys:
        value = _clean_text(address.get(key))
        if value:
            return value

    return None


def _name_from_namedetails(raw_place: dict[str, Any]) -> str | None:
    namedetails = raw_place.get("namedetails") or {}

    for key in ("name:en", "name", "name:ar", "official_name", "alt_name"):
        value = _clean_text(namedetails.get(key))
        if value:
            return value

    display_name = _clean_text(raw_place.get("display_name"))
    if display_name:
        return display_name.split(",")[0].strip() or None

    return None


def _normalize_bounding_box(raw_place: dict[str, Any]) -> dict[str, float] | None:
    raw_box = raw_place.get("boundingbox")

    if not isinstance(raw_box, (list, tuple)) or len(raw_box) != 4:
        return None

    try:
        south, north, west, east = (float(value) for value in raw_box)
    except (TypeError, ValueError):
        return None

    if south > north or west > east:
        return None

    if not all(is_valid_coordinate_pair(lat, lng) for lat, lng in ((south, west), (north, east))):
        return None

    return {
        "south": south,
        "north": north,
        "west": west,
        "east": east,
    }


def _compact_display_name(*parts: str | None) -> str:
    seen = set()
    compacted = []

    for part in parts:
        value = _clean_text(part)
        if not value:
            continue

        normalized = value.casefold()
        if normalized in seen:
            continue

        seen.add(normalized)
        compacted.append(value)

    return ", ".join(compacted)


def normalize_geocoder_result(raw_place: dict[str, Any]) -> dict[str, Any] | None:
    address = raw_place.get("address") or {}
    country_code = str(address.get("country_code") or "").lower()

    if country_code != "lb":
        return None

    place_class = str(raw_place.get("class") or "").lower()
    place_type = str(raw_place.get("type") or "").lower()

    if place_type in REJECTED_TYPES:
        return None

    if place_class not in SETTLEMENT_CLASSES:
        return None

    if place_type not in SETTLEMENT_TYPES:
        return None

    try:
        lat = float(raw_place["lat"])
        lng = float(raw_place["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    if not is_inside_lebanon(lat, lng):
        return None

    name = _display_part(
        raw_place,
        [
            "city",
            "town",
            "village",
            "municipality",
            "hamlet",
            "locality",
            "suburb",
            "neighbourhood",
            "quarter",
        ],
    ) or _name_from_namedetails(raw_place)

    if not name:
        return None

    namedetails = raw_place.get("namedetails") or {}
    name_en = _clean_text(namedetails.get("name:en"))
    name_ar = _clean_text(namedetails.get("name:ar"))
    district = _display_part(
        raw_place,
        ["state_district", "district", "county"],
    )
    governorate = _display_part(
        raw_place,
        ["state", "province", "region"],
    )

    return {
        "name": name,
        "name_en": name_en,
        "name_ar": name_ar,
        "district": district,
        "governorate": governorate,
        "lat": lat,
        "lng": lng,
        "type": place_type,
        "bounding_box": _normalize_bounding_box(raw_place),
        "source": "nominatim",
        "display_name": _compact_display_name(name, district, governorate),
    }


def _nominatim_request(query: str) -> list[dict[str, Any]]:
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "namedetails": 1,
            "accept-language": "en,ar",
            "countrycodes": "lb",
            "viewbox": (
                f"{LEBANON_BOUNDS['west']},{LEBANON_BOUNDS['north']},"
                f"{LEBANON_BOUNDS['east']},{LEBANON_BOUNDS['south']}"
            ),
            "bounded": 1,
            "dedupe": 1,
            "limit": NOMINATIM_RESULT_LIMIT,
        },
        headers={
            "User-Agent": "Tariq.lb road reporting platform",
            "Accept-Language": "en,ar;q=0.8",
        },
        timeout=8,
    )
    response.raise_for_status()
    return response.json()


def _with_display_name(locality: dict[str, Any]) -> dict[str, Any]:
    result = dict(locality)
    result.setdefault("district", None)
    result.setdefault("name_en", result.get("name"))
    result.setdefault("name_ar", None)
    result.setdefault("bounding_box", None)
    result.setdefault("source", "local")
    result["display_name"] = _compact_display_name(
        result.get("name"),
        result.get("district"),
        result.get("governorate"),
    )
    return result


def _local_search(query: str) -> list[dict[str, Any]]:
    normalized = _normalize_for_search(query)
    if not normalized:
        return []

    matches = []
    for index, locality in enumerate(_gazetteer_places()):
        values = _candidate_values(locality)

        if any(value == normalized for value in values):
            rank = 0
        elif any(value.startswith(normalized) for value in values):
            rank = 1
        elif any(
            token.startswith(normalized)
            for value in values
            for token in value.split()
        ):
            rank = 2
        elif any(normalized in value for value in values):
            rank = 3
        else:
            continue

        population = int(locality.get("population") or 0)
        curated_priority = 0 if locality.get("source") == "local" else 1
        matches.append((rank, curated_priority, -population, index, locality))

    matches.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return [item[4] for item in matches]


def _result_key(result: dict[str, Any]) -> tuple[str, str, str, float, float]:
    return (
        str(result.get("name") or "").casefold(),
        str(result.get("district") or "").casefold(),
        str(result.get("governorate") or "").casefold(),
        round(float(result.get("lat") or 0), 4),
        round(float(result.get("lng") or 0), 4),
    )


def _safe_coordinate(value: Any) -> float | None:
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(coordinate):
        return None

    return coordinate


def _result_names(result: dict[str, Any]) -> tuple[str, ...]:
    values = [
        result.get("name"),
        result.get("name_en"),
        result.get("ascii_name"),
    ]

    values.extend(result.get("alternate_names") or [])

    normalized_values = []
    seen = set()
    for value in values:
        normalized = _normalize_for_search(value)
        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        normalized_values.append(normalized)

    return tuple(normalized_values)


def _names_look_like_same_place(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_names = _result_names(left)
    right_names = _result_names(right)

    for left_name in left_names:
        for right_name in right_names:
            if left_name == right_name:
                return True

            shorter, longer = sorted(
                (left_name, right_name),
                key=len,
            )

            if len(shorter) >= 3 and longer.startswith(f"{shorter} "):
                return True

    return False


def _coordinates_are_near(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_lat = _safe_coordinate(left.get("lat"))
    left_lng = _safe_coordinate(left.get("lng"))
    right_lat = _safe_coordinate(right.get("lat"))
    right_lng = _safe_coordinate(right.get("lng"))

    if None in (left_lat, left_lng, right_lat, right_lng):
        return False

    return (
        abs(left_lat - right_lat) <= NEAR_DUPLICATE_DEGREES
        and abs(left_lng - right_lng) <= NEAR_DUPLICATE_DEGREES
    )


def _same_visible_result(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_display = _normalize_for_search(left.get("display_name"))
    right_display = _normalize_for_search(right.get("display_name"))

    if left_display and left_display == right_display:
        return True

    if _result_key(left) == _result_key(right):
        return True

    return _coordinates_are_near(left, right) and _names_look_like_same_place(left, right)


def _coordinate_bucket(result: dict[str, Any]) -> tuple[int, int] | None:
    lat = _safe_coordinate(result.get("lat"))
    lng = _safe_coordinate(result.get("lng"))

    if lat is None or lng is None:
        return None

    return (
        math.floor(lat / NEAR_DUPLICATE_DEGREES),
        math.floor(lng / NEAR_DUPLICATE_DEGREES),
    )


def _dedupe_results(
    results: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique_results = []
    seen_exact_keys = set()
    seen_display_names = set()
    coordinate_buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}

    for result in results:
        exact_key = _result_key(result)
        display_name = _normalize_for_search(result.get("display_name"))

        if exact_key in seen_exact_keys:
            continue

        if display_name and display_name in seen_display_names:
            continue

        bucket = _coordinate_bucket(result)
        nearby_results = []

        if bucket is not None:
            bucket_lat, bucket_lng = bucket
            for lat_offset in (-1, 0, 1):
                for lng_offset in (-1, 0, 1):
                    nearby_results.extend(
                        coordinate_buckets.get(
                            (bucket_lat + lat_offset, bucket_lng + lng_offset),
                            [],
                        )
                    )

        if any(_same_visible_result(result, existing) for existing in nearby_results):
            continue

        seen_exact_keys.add(exact_key)
        if display_name:
            seen_display_names.add(display_name)
        unique_results.append(result)

        if bucket is not None:
            coordinate_buckets.setdefault(bucket, []).append(result)

    return unique_results


@lru_cache(maxsize=512)
def search_lebanese_localities(query: str) -> tuple[dict[str, Any], ...]:
    normalized_query = " ".join((query or "").split())

    if len(normalized_query) < 1:
        return tuple()

    full_gazetteer_available = _gazetteer_available()
    local_results = _local_search(normalized_query)

    if full_gazetteer_available and local_results:
        return tuple(_dedupe_results(local_results)[:SEARCH_RESULT_LIMIT])

    if len(normalized_query) < SEARCH_MIN_REMOTE_LENGTH:
        return tuple(_dedupe_results(local_results)[:SEARCH_RESULT_LIMIT])

    try:
        raw_results = _nominatim_request(normalized_query)
    except requests.RequestException as exc:
        if local_results or full_gazetteer_available:
            return tuple(_dedupe_results(local_results)[:SEARCH_RESULT_LIMIT])
        raise GeocoderError("Failed geocoder request.") from exc

    results: list[dict[str, Any]] = []

    for raw_place in raw_results:
        result = normalize_geocoder_result(raw_place)
        if not result:
            continue

        if any(_same_visible_result(result, existing) for existing in results):
            continue

        results.append(result)

    for result in local_results:
        if any(_same_visible_result(result, existing) for existing in results):
            continue

        results.append(result)

    return tuple(results[:SEARCH_RESULT_LIMIT])


