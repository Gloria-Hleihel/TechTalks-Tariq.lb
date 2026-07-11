from PIL import Image, ExifTags
from typing import Optional, Tuple

def _dms_to_decimal(dms):
    """
    Convert EXIF DMS tuple to decimal degrees.
    dms example: ((deg_num, deg_den), (min_num, min_den), (sec_num, sec_den))
    Returns float or None on failure.
    """
    try:
        deg = dms[0][0] / dms[0][1]
        minute = dms[1][0] / dms[1][1]
        sec = dms[2][0] / dms[2][1]
        return deg + (minute / 60.0) + (sec / 3600.0)
    except Exception:
        return None

def extract_gps(image_path: str) -> Optional[Tuple[float, float]]:
    """
    Extract GPS coordinates from image EXIF.
    Returns (lat, lng) in decimal degrees, or None if not found or on error.
    Defensive: never raises to caller.
    """
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        if not exif:
            return None

        # Map numeric tags to names
        exif_by_name = {}
        for tag_id, value in exif.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            exif_by_name[tag] = value

        gps_info = exif_by_name.get("GPSInfo")
        if not gps_info:
            return None

        # Convert GPSInfo keys to human-readable names
        gps = {}
        for key in gps_info.keys():
            name = ExifTags.GPSTAGS.get(key, key)
            gps[name] = gps_info[key]

        lat_data = gps.get("GPSLatitude")
        lat_ref = gps.get("GPSLatitudeRef")
        lon_data = gps.get("GPSLongitude")
        lon_ref = gps.get("GPSLongitudeRef")

        if not (lat_data and lat_ref and lon_data and lon_ref):
            return None

        lat = _dms_to_decimal(lat_data)
        lon = _dms_to_decimal(lon_data)
        if lat is None or lon is None:
            return None

        # Apply reference for hemisphere
        if isinstance(lat_ref, bytes):
            lat_ref = lat_ref.decode(errors="ignore")
        if isinstance(lon_ref, bytes):
            lon_ref = lon_ref.decode(errors="ignore")

        if lat_ref.upper() == "S":
            lat = -abs(lat)
        if lon_ref.upper() == "W":
            lon = -abs(lon)

        return (lat, lon)
    except Exception:
        # Any error (corrupt image, not an image, unexpected EXIF) -> None
        return None
