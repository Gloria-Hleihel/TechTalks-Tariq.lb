"""
EXIF GPS utilities for Tariq.lb.
"""

from PIL import ExifTags, Image, UnidentifiedImageError


GPS_INFO_TAG = ExifTags.IFD.GPSInfo


class GPSExtractionError(Exception):
    """Raised when GPS EXIF metadata cannot be read or parsed."""


def _decode_ref(value):
    """Normalize EXIF GPS direction references."""
    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="ignore",
        )

    return str(value)


def _number_to_float(value):
    """Convert EXIF rational-like values into floats."""
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        if value.denominator == 0:
            raise GPSExtractionError(
                "GPS metadata is incomplete or corrupted."
            )

        return float(value.numerator) / float(value.denominator)

    if isinstance(value, tuple) and len(value) == 2:
        numerator, denominator = value

        if denominator == 0:
            raise GPSExtractionError(
                "GPS metadata is incomplete or corrupted."
            )

        return float(numerator) / float(denominator)

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        ) from exc


def _dms_to_decimal(values, ref):
    """
    Convert GPS degrees/minutes/seconds to decimal degrees.
    """
    if values is None or len(values) != 3:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    degrees = _number_to_float(values[0])
    minutes = _number_to_float(values[1])
    seconds = _number_to_float(values[2])

    if not 0 <= minutes < 60:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    if not 0 <= seconds < 60:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    decimal = (
        degrees
        + minutes / 60
        + seconds / 3600
    )

    ref = _decode_ref(ref).strip().upper()

    if ref in {"S", "W"}:
        decimal = -decimal

    elif ref not in {"N", "E"}:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    return decimal


def _get_gps_ifd(exif):
    """
    Read the GPS IFD from a Pillow EXIF object.
    """
    if not exif:
        return None

    try:
        gps_ifd = exif.get_ifd(
            GPS_INFO_TAG
        )
    except Exception as exc:
        raise GPSExtractionError(
            "GPS metadata could not be read."
        ) from exc

    if gps_ifd:
        return gps_ifd

    possible_gps = exif.get(
        GPS_INFO_TAG
    )

    if isinstance(possible_gps, dict):
        return possible_gps

    return None


def _normalize_gps_dict(gps_ifd):
    """
    Convert GPS numeric tags to readable names.
    """
    gps = {}

    for tag_id, value in gps_ifd.items():
        tag_name = ExifTags.GPSTAGS.get(
            tag_id,
            tag_id,
        )

        gps[tag_name] = value

    return gps


def extract_gps(image_path):
    """
    Extract decimal GPS coordinates from an image.

    Returns:
        (lat, lng) if GPS exists.
        None if image is valid but has no GPS.

    Raises:
        GPSExtractionError if metadata exists but cannot be parsed,
        or if the file is not a valid image.
    """
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()

    except (UnidentifiedImageError, OSError) as exc:
        raise GPSExtractionError(
            "GPS metadata could not be read."
        ) from exc

    gps_ifd = _get_gps_ifd(
        exif
    )

    if not gps_ifd:
        return None

    gps = _normalize_gps_dict(
        gps_ifd
    )

    required_keys = {
        "GPSLatitudeRef",
        "GPSLatitude",
        "GPSLongitudeRef",
        "GPSLongitude",
    }

    if not required_keys.issubset(gps):
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    lat = _dms_to_decimal(
        gps["GPSLatitude"],
        gps["GPSLatitudeRef"],
    )

    lng = _dms_to_decimal(
        gps["GPSLongitude"],
        gps["GPSLongitudeRef"],
    )

    if not -90 <= lat <= 90:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    if not -180 <= lng <= 180:
        raise GPSExtractionError(
            "GPS metadata is incomplete or corrupted."
        )

    return lat, lng