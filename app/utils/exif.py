from typing import Optional, Tuple

from PIL import ExifTags, Image


def _as_float(value) -> float:
    """Convert Pillow rationals or numerator/denominator pairs to float."""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return float(value[0]) / float(value[1])

    return float(value)


def _dms_to_decimal(dms) -> Optional[float]:
    """Convert EXIF degrees/minutes/seconds to decimal degrees."""
    try:
        degrees = _as_float(dms[0])
        minutes = _as_float(dms[1])
        seconds = _as_float(dms[2])

        return (
            degrees
            + (minutes / 60.0)
            + (seconds / 3600.0)
        )
    except (
        TypeError,
        ValueError,
        ZeroDivisionError,
        IndexError,
    ):
        return None


def extract_gps(
    image_path: str,
) -> Optional[Tuple[float, float]]:
    """Return (latitude, longitude) from EXIF data, or None."""
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()

            if not exif:
                return None

            gps_info = None

            gps_tag_id = next(
                (
                    tag_id
                    for tag_id, name in ExifTags.TAGS.items()
                    if name == "GPSInfo"
                ),
                34853,
            )

            if hasattr(exif, "get_ifd"):
                try:
                    gps_ifd = getattr(
                        getattr(ExifTags, "IFD", None),
                        "GPSInfo",
                        gps_tag_id,
                    )

                    gps_info = exif.get_ifd(gps_ifd)
                except (KeyError, TypeError):
                    gps_info = None

            if not gps_info:
                gps_info = exif.get(gps_tag_id)

            if not gps_info:
                return None

            gps = {
                ExifTags.GPSTAGS.get(key, key): value
                for key, value in gps_info.items()
            }

            lat_data = gps.get("GPSLatitude")
            lat_ref = gps.get("GPSLatitudeRef")

            lng_data = gps.get("GPSLongitude")
            lng_ref = gps.get("GPSLongitudeRef")

            if not all(
                (
                    lat_data,
                    lat_ref,
                    lng_data,
                    lng_ref,
                )
            ):
                return None

            lat = _dms_to_decimal(lat_data)
            lng = _dms_to_decimal(lng_data)

            if lat is None or lng is None:
                return None

            if isinstance(lat_ref, bytes):
                lat_ref = lat_ref.decode(errors="ignore")

            if isinstance(lng_ref, bytes):
                lng_ref = lng_ref.decode(errors="ignore")

            if str(lat_ref).upper() == "S":
                lat = -abs(lat)

            if str(lng_ref).upper() == "W":
                lng = -abs(lng)

            return lat, lng

    except (
        AttributeError,
        OSError,
        SyntaxError,
        TypeError,
        ValueError,
    ):
        return None