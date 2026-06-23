"""
GPS EXIF extraction utility -- uses Pillow, per PRD Section 12 (Tech Stack)
and Section 11 (POC: "Read GPS coordinates from EXIF metadata using Pillow").
"""
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def _convert_to_degrees(value):
    """Convert EXIF GPS rational (degrees, minutes, seconds) to decimal degrees."""
    d, m, s = value
    return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)


def extract_gps(image_path):
    """
    Attempt to read GPS latitude/longitude from an image's EXIF metadata.

    Returns:
        (lat, lon) tuple of floats if GPS data is present and valid,
        otherwise None.
    """
    try:
        image = Image.open(image_path)
        exif_data = image.getexif()
        if not exif_data:
            return None

        # GPS info lives in a nested IFD (tag 0x8825 / 34853)
        gps_ifd = exif_data.get_ifd(0x8825)
        if not gps_ifd:
            return None

        gps_info = {GPSTAGS.get(key, key): value for key, value in gps_ifd.items()}

        lat_data = gps_info.get("GPSLatitude")
        lat_ref = gps_info.get("GPSLatitudeRef")
        lon_data = gps_info.get("GPSLongitude")
        lon_ref = gps_info.get("GPSLongitudeRef")

        if not (lat_data and lat_ref and lon_data and lon_ref):
            return None

        lat = _convert_to_degrees(lat_data)
        if lat_ref != "N":
            lat = -lat

        lon = _convert_to_degrees(lon_data)
        if lon_ref != "E":
            lon = -lon

        return (lat, lon)

    except Exception:
        # Any parsing failure just means "no usable GPS data" --
        # the app falls back to manual pin placement.
        return None
