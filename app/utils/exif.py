from typing import Optional, Tuple

from PIL import ExifTags, Image, UnidentifiedImageError


class GPSExtractionError(Exception):
    """Raised when EXIF GPS data cannot be read safely."""


def _as_float(value) -> float:
    """Convert Pillow rational values to float."""
    if (
        isinstance(value, (tuple, list))
        and len(value) == 2
    ):
        return (
            float(value[0])
            / float(value[1])
        )

    return float(value)


def _dms_to_decimal(dms) -> Optional[float]:
    """Convert degrees, minutes and seconds to decimal degrees."""
    try:
        degrees = _as_float(
            dms[0]
        )

        minutes = _as_float(
            dms[1]
        )

        seconds = _as_float(
            dms[2]
        )

        return (
            degrees
            + minutes / 60.0
            + seconds / 3600.0
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
    """
    Return latitude and longitude from EXIF.

    None means the image has no usable GPS information.
    GPSExtractionError means the metadata could not be read.
    """
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()

            if not exif:
                return None

            gps_info = None

            gps_tag_id = next(
                (
                    tag_id
                    for tag_id, name
                    in ExifTags.TAGS.items()
                    if name == "GPSInfo"
                ),
                34853,
            )

            if hasattr(exif, "get_ifd"):
                try:
                    gps_ifd = getattr(
                        getattr(
                            ExifTags,
                            "IFD",
                            None,
                        ),
                        "GPSInfo",
                        gps_tag_id,
                    )

                    gps_info = exif.get_ifd(
                        gps_ifd
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    gps_info = None

            if not gps_info:
                gps_info = exif.get(
                    gps_tag_id
                )

            if not gps_info:
                return None

            try:
                gps = {
                    ExifTags.GPSTAGS.get(
                        key,
                        key,
                    ): value
                    for key, value
                    in gps_info.items()
                }

            except (
                AttributeError,
                TypeError,
            ) as exc:
                raise GPSExtractionError(
                    "The photo contains damaged GPS metadata."
                ) from exc

            lat_data = gps.get(
                "GPSLatitude"
            )

            lat_ref = gps.get(
                "GPSLatitudeRef"
            )

            lng_data = gps.get(
                "GPSLongitude"
            )

            lng_ref = gps.get(
                "GPSLongitudeRef"
            )

            if not all(
                (
                    lat_data,
                    lat_ref,
                    lng_data,
                    lng_ref,
                )
            ):
                return None

            lat = _dms_to_decimal(
                lat_data
            )

            lng = _dms_to_decimal(
                lng_data
            )

            if lat is None or lng is None:
                raise GPSExtractionError(
                    "The photo GPS coordinates are "
                    "incomplete or corrupted."
                )

            if isinstance(lat_ref, bytes):
                lat_ref = lat_ref.decode(
                    errors="ignore"
                )

            if isinstance(lng_ref, bytes):
                lng_ref = lng_ref.decode(
                    errors="ignore"
                )

            if str(lat_ref).upper() == "S":
                lat = -abs(lat)

            if str(lng_ref).upper() == "W":
                lng = -abs(lng)

            if not (
                -90 <= lat <= 90
                and -180 <= lng <= 180
            ):
                raise GPSExtractionError(
                    "The photo contains GPS coordinates "
                    "outside the valid range."
                )

            return lat, lng

    except GPSExtractionError:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise GPSExtractionError(
            "The photo metadata could not be read. "
            "Select the location manually."
        ) from exc