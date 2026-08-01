import pytest
from PIL import ExifTags, Image

from app.utils.exif import (
    GPSExtractionError,
    extract_gps,
)


def _save_jpeg(
    path,
    exif=None,
):
    image = Image.new(
        "RGB",
        (12, 12),
        "white",
    )

    if exif is None:
        image.save(
            path,
            format="JPEG",
        )
    else:
        image.save(
            path,
            format="JPEG",
            exif=exif,
        )


def _gps_exif(
    latitude=(33.0, 53.0, 37.68),
    longitude=(35.0, 30.0, 6.48),
    latitude_ref="N",
    longitude_ref="E",
):
    exif = Image.Exif()

    gps_ifd = {
        1: latitude_ref,
        2: latitude,
        3: longitude_ref,
        4: longitude,
    }

    exif[ExifTags.IFD.GPSInfo] = gps_ifd

    return exif


def test_extract_gps_returns_decimal_coordinates_for_valid_gps(
    tmp_path,
):
    image_path = (
        tmp_path
        / "with-gps.jpg"
    )

    _save_jpeg(
        image_path,
        _gps_exif(),
    )

    lat, lng = extract_gps(
        str(image_path)
    )

    assert lat == pytest.approx(
        33.8938,
        abs=0.0001,
    )

    assert lng == pytest.approx(
        35.5018,
        abs=0.0001,
    )


def test_extract_gps_returns_none_for_image_without_gps(
    tmp_path,
):
    image_path = (
        tmp_path
        / "without-gps.jpg"
    )

    _save_jpeg(
        image_path
    )

    assert extract_gps(
        str(image_path)
    ) is None


def test_extract_gps_raises_for_corrupted_gps_coordinates(
    tmp_path,
):
    image_path = (
        tmp_path
        / "corrupted-gps.jpg"
    )

    exif = _gps_exif(
        latitude=(
            33.0,
            53.0,
        )
    )

    _save_jpeg(
        image_path,
        exif,
    )

    with pytest.raises(
        GPSExtractionError
    ) as error:
        extract_gps(
            str(image_path)
        )

    assert (
        "incomplete or corrupted"
        in str(error.value)
    )


def test_extract_gps_raises_for_non_image_file(
    tmp_path,
):
    file_path = (
        tmp_path
        / "not-an-image.jpg"
    )

    file_path.write_bytes(
        b"this is not an image"
    )

    with pytest.raises(
        GPSExtractionError
    ) as error:
        extract_gps(
            str(file_path)
        )

    assert (
        "metadata could not be read"
        in str(error.value)
    )


def test_extract_gps_handles_south_and_west_references(
    tmp_path,
):
    image_path = (
        tmp_path
        / "south-west.jpg"
    )

    _save_jpeg(
        image_path,
        _gps_exif(
            latitude=(
                10.0,
                30.0,
                0.0,
            ),
            longitude=(
                20.0,
                15.0,
                0.0,
            ),
            latitude_ref="S",
            longitude_ref="W",
        ),
    )

    lat, lng = extract_gps(
        str(image_path)
    )

    assert lat == pytest.approx(
        -10.5
    )

    assert lng == pytest.approx(
        -20.25
    )