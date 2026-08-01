import io
import json
import os
import requests

import pytest
from PIL import Image

from app import create_app
from app.utils.detection_client import trigger_detection
from models import Detection, Report, db


def image_bytes(fmt="PNG"):
    """Create a small valid image in memory for upload tests."""
    stream = io.BytesIO()

    Image.new(
        "RGB",
        (4, 4),
        "white",
    ).save(
        stream,
        format=fmt,
    )

    stream.seek(0)

    return stream


@pytest.fixture()
def app(tmp_path):
    """Create an isolated Flask application for every test."""
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(static_folder),
            "UPLOAD_FOLDER": str(upload_folder),
            "ANNOTATED_FOLDER": str(annotated_folder),
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Create a Flask test client."""
    return app.test_client()


def pending_detection(_report, _path):
    return {
        "status": "pending",
        "error": "Detector unavailable in test.",
    }


def completed_detection(_report, _path):
    return {
        "status": "completed",
        "damage_type": "None",
        "confidence": 0.99,
        "severity_score": 0,
        "severity_label": "Low",
        "annotated_image_path": None,
    }


def test_upload_page_has_shared_nav_modals(client):
    """The shared navbar modals should work on the report upload page."""
    response = client.get("/upload")

    assert response.status_code == 200
    assert b'id="faq-modal"' in response.data
    assert b'id="support-modal"' in response.data
    assert b"Report Problem" in response.data
    assert b"Contact and feedback form" in response.data
    assert b"https://www.instagram.com/tariq.leb" in response.data
    assert b"tariqlb.contact@gmail.com" in response.data
    assert b"LinkedIn" not in response.data
    assert b"Facebook" not in response.data
    assert b'name="next" value="/upload"' in response.data
    assert b'aria-haspopup="dialog"' in response.data
    assert b'aria-controls="support-modal"' in response.data
    assert b'id="localitySearchStatus"' in response.data
    assert b'aria-describedby="searchHelp searchError selectedSearchPlace localitySearchStatus"' in response.data
    assert b'id="mapInstructions"' in response.data
    assert b'id="map"' in response.data
    assert b'role="region"' in response.data
    assert b'aria-current="step"' in response.data


def test_valid_exif_upload_creates_report_and_redirects(
    app,
    client,
    monkeypatch,
):
    """A valid Lebanon GPS image should create a report and detection."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (33.8938, 35.5018),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        completed_detection,
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    assert response.headers["Location"].endswith(
        "/reports/1"
    )

    with app.app_context():
        report = db.session.get(Report, 1)

        assert report is not None
        assert report.location_source == "gps"
        assert report.lat == pytest.approx(33.8938)
        assert report.lng == pytest.approx(35.5018)
        assert report.image_path.startswith("uploads/")

        saved_file = os.path.join(
            app.config["UPLOAD_FOLDER"],
            os.path.basename(report.image_path),
        )

        assert os.path.exists(saved_file)

        assert Detection.query.filter_by(
            report_id=report.id
        ).count() == 1


def test_invalid_file_is_rejected_without_report(
    app,
    client,
):
    """A fake image file should not create a report."""
    response = client.post(
        "/upload",
        data={
            "image": (
                io.BytesIO(b"not an image"),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    assert response.headers["Location"].endswith(
        "/upload"
    )

    with app.app_context():
        assert Report.query.count() == 0


def test_manual_location_is_used_when_exif_is_missing(
    app,
    client,
    monkeypatch,
):
    """Manual coordinates inside Lebanon should be accepted."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        pending_detection,
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
            "lat": "33.9001",
            "lng": "35.5002",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    assert response.headers["Location"].endswith(
        "/reports/1"
    )

    with app.app_context():
        report = db.session.get(Report, 1)

        assert report is not None
        assert report.location_source == "manual"
        assert report.lat == pytest.approx(33.9001)
        assert report.lng == pytest.approx(35.5002)
        assert report.detections == []


def test_missing_manual_location_keeps_image_and_does_not_create_report(
    app,
    client,
    monkeypatch,
):
    """
    When GPS and manual coordinates are missing, keep the uploaded
    image and show the form again without creating a report.
    """
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 200

    assert b"Your uploaded image has been kept" in response.data
    assert b"Select the road location on the map" in response.data
    assert b'name="saved_image_path"' in response.data

    with app.app_context():
        assert Report.query.count() == 0

    uploaded_items = os.listdir(app.config["UPLOAD_FOLDER"])

    saved_images = [
        filename
        for filename in uploaded_items
        if filename != "annotated"
    ]

    assert len(saved_images) == 1
    assert saved_images[0].endswith(".png")


def test_report_detail_page_renders_after_redirect(
    app,
    client,
    monkeypatch,
):
    """A successful upload should render the redesigned report page."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (33.8938, 35.5018),
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        pending_detection,
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            )
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert b"Report submitted successfully." in response.data
    assert b"Detection Pending" in response.data
    assert b"Report Information" in response.data
    assert b"Original Road Image" in response.data


def test_browser_location_source_is_saved_when_exif_is_missing(
    app,
    client,
    monkeypatch,
):
    """Browser coordinates inside Lebanon should keep their source."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        pending_detection,
    )

    response = client.post(
        "/upload",
        data={
            "image": (
                image_bytes(),
                "road.png",
            ),
            "lat": "33.8938",
            "lng": "35.5018",
            "location_source": "browser",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        report = db.session.get(Report, 1)

        assert report is not None
        assert report.location_source == "browser"
        assert report.lat == pytest.approx(33.8938)
        assert report.lng == pytest.approx(35.5018)


def test_search_location_source_is_saved_when_exif_is_missing(
    app,
    client,
    monkeypatch,
):
    """Search-selected coordinates should be accepted inside Lebanon."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )
    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        pending_detection,
    )

    response = client.post(
        "/upload",
        data={
            "image": (image_bytes(), "road.png"),
            "lat": "33.8938",
            "lng": "35.5018",
            "location_source": "search",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        report = db.session.get(Report, 1)
        assert report is not None
        assert report.location_source == "search"
        assert report.lat == pytest.approx(33.8938)
        assert report.lng == pytest.approx(35.5018)


def test_marker_outside_lebanon_is_rejected(
    app,
    client,
    monkeypatch,
):
    """Manual coordinates outside Lebanon must never create a report."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    response = client.post(
        "/upload",
        data={
            "image": (image_bytes(), "road.png"),
            "lat": "40.7128",
            "lng": "-74.0060",
            "location_source": "manual",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Please select a location inside Lebanon." in response.data

    with app.app_context():
        assert Report.query.count() == 0


def test_browser_coordinates_outside_lebanon_are_rejected(
    app,
    client,
    monkeypatch,
):
    """Browser GPS outside Lebanon should be rejected by the server."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: None,
    )

    response = client.post(
        "/upload",
        data={
            "image": (image_bytes(), "road.png"),
            "lat": "48.8566",
            "lng": "2.3522",
            "location_source": "browser",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Please select a location inside Lebanon." in response.data

    with app.app_context():
        assert Report.query.count() == 0


def test_exif_gps_outside_lebanon_without_manual_location_is_rejected(
    app,
    client,
    monkeypatch,
):
    """EXIF GPS outside Lebanon should not create a report."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (48.8566, 2.3522),
    )

    response = client.post(
        "/upload",
        data={"image": (image_bytes(), "road.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Image GPS appears outside Lebanon" in response.data

    with app.app_context():
        assert Report.query.count() == 0


def test_exif_outside_lebanon_can_fall_back_to_manual_lebanon_location(
    app,
    client,
    monkeypatch,
):
    """A user may override unusable EXIF with a valid Lebanon marker."""
    monkeypatch.setattr(
        "app.reports.routes.extract_gps",
        lambda _path: (48.8566, 2.3522),
    )
    monkeypatch.setattr(
        "app.reports.routes.trigger_detection",
        pending_detection,
    )

    response = client.post(
        "/upload",
        data={
            "image": (image_bytes(), "road.png"),
            "lat": "33.8938",
            "lng": "35.5018",
            "location_source": "manual",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        report = db.session.get(Report, 1)
        assert report is not None
        assert report.location_source == "manual"
        assert report.lat == pytest.approx(33.8938)
        assert report.lng == pytest.approx(35.5018)


def test_valid_lebanese_city_search_returns_coordinates(
    client,
    monkeypatch,
    tmp_path,
):
    """The search API should keep Lebanese settlement results."""
    from app.reports import location as location_module

    disable_default_gazetteer(location_module, monkeypatch, tmp_path)
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: [
            {
                "lat": "33.8938",
                "lon": "35.5018",
                "class": "place",
                "type": "city",
                "display_name": "Beirut, Beirut Governorate, Lebanon",
                "address": {
                    "city": "Beirut",
                    "state": "Beirut Governorate",
                    "country_code": "lb",
                },
            }
        ],
    )

    response = client.get("/api/lebanon-localities/search?q=Beirut")

    assert response.status_code == 200
    data = response.get_json()

    assert data["results"][0]["name"] == "Beirut"
    assert data["results"][0]["governorate"] == "Beirut Governorate"
    assert data["results"][0]["lat"] == pytest.approx(33.8938)
    assert data["results"][0]["lng"] == pytest.approx(35.5018)


def test_non_lebanese_search_result_is_rejected(
    client,
    monkeypatch,
):
    """The search API should reject places outside Lebanon."""
    from app.reports import location as location_module

    location_module.search_lebanese_localities.cache_clear()
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: [
            {
                "lat": "48.8566",
                "lon": "2.3522",
                "class": "place",
                "type": "city",
                "display_name": "Paris, France",
                "address": {
                    "city": "Paris",
                    "country_code": "fr",
                },
            }
        ],
    )

    response = client.get("/api/lebanon-localities/search?q=Paris")

    assert response.status_code == 200
    data = response.get_json()

    assert data["results"] == []
    assert data["message"] == "No Lebanese city or village found."


def test_search_rejects_road_level_results(
    client,
    monkeypatch,
):
    """Roads and POIs should not appear as user suggestions."""
    from app.reports import location as location_module

    location_module.search_lebanese_localities.cache_clear()
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: [
            {
                "lat": "33.8938",
                "lon": "35.5018",
                "class": "highway",
                "type": "road",
                "display_name": "Some Road, Beirut, Lebanon",
                "address": {
                    "road": "Some Road",
                    "city": "Beirut",
                    "country_code": "lb",
                },
            }
        ],
    )

    response = client.get("/api/lebanon-localities/search?q=Some%20Road")

    assert response.status_code == 200
    assert response.get_json()["results"] == []

def test_single_letter_b_search_shows_common_lebanese_places(client):
    """Typing B should immediately show useful built-in Lebanese places."""
    response = client.get("/api/lebanon-localities/search?q=B")

    assert response.status_code == 200
    names = [item["name"] for item in response.get_json()["results"]]

    assert "Beirut" in names
    assert "Byblos" in names
    assert "Batroun" in names
    assert "Bater" in names


def test_search_collapses_near_duplicate_visible_places(client):
    """The same visible locality should not appear twice under alternate names."""
    from app.reports import location as location_module

    reset_location_caches(location_module)

    response = client.get("/api/lebanon-localities/search?q=Bater")

    assert response.status_code == 200
    display_names = [
        item["display_name"]
        for item in response.get_json()["results"]
    ]

    assert "Bater, Mount Lebanon" in display_names
    assert "Bater ech Chouf, Mount Lebanon" not in display_names
    assert len(display_names) == len(set(display_names))


def geocoder_place(
    name,
    lat=33.60207,
    lng=35.61731,
    place_type="village",
    district="Chouf District",
    governorate="Mount Lebanon Governorate",
    name_ar=None,
):
    """Build a Nominatim-like Lebanese locality response for search tests."""
    namedetails = {"name:en": name, "name": name}
    if name_ar:
        namedetails["name:ar"] = name_ar

    return {
        "lat": str(lat),
        "lon": str(lng),
        "class": "place",
        "type": place_type,
        "display_name": f"{name}, {district}, {governorate}, Lebanon",
        "boundingbox": [
            str(lat - 0.01),
            str(lat + 0.01),
            str(lng - 0.01),
            str(lng + 0.01),
        ],
        "namedetails": namedetails,
        "address": {
            "village": name,
            "county": district,
            "state": governorate,
            "country_code": "lb",
        },
    }


def test_small_village_search_returns_district_governorate_and_bbox(
    client,
    monkeypatch,
    tmp_path,
):
    """Small localities should include context and geometry for precise map fitting."""
    from app.reports import location as location_module

    disable_default_gazetteer(location_module, monkeypatch, tmp_path)
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: [geocoder_place("Bater")],
    )

    response = client.get("/api/lebanon-localities/search?q=Bater")

    assert response.status_code == 200
    result = response.get_json()["results"][0]

    assert result["name"] == "Bater"
    assert result["district"] == "Chouf District"
    assert result["governorate"] == "Mount Lebanon Governorate"
    assert result["display_name"] == "Bater, Chouf District, Mount Lebanon Governorate"
    assert result["source"] == "nominatim"
    assert result["bounding_box"] == {
        "south": pytest.approx(33.59207),
        "north": pytest.approx(33.61207),
        "west": pytest.approx(35.60731),
        "east": pytest.approx(35.62731),
    }


def test_arabic_locality_search_keeps_arabic_and_english_names(
    client,
    monkeypatch,
):
    """Arabic and multilingual names should be preserved for UI display."""
    from app.reports import location as location_module

    location_module.search_lebanese_localities.cache_clear()
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: [
            geocoder_place(
                "Beirut",
                lat=33.8938,
                lng=35.5018,
                place_type="city",
                district="Beirut District",
                governorate="Beirut Governorate",
                name_ar="\u0628\u064a\u0631\u0648\u062a",
            )
        ],
    )

    response = client.get(
        "/api/lebanon-localities/search",
        query_string={"q": "\u0628\u064a\u0631\u0648\u062a"},
    )

    assert response.status_code == 200
    result = response.get_json()["results"][0]

    assert result["name"] == "Beirut"
    assert result["name_en"] == "Beirut"
    assert result["name_ar"] == "\u0628\u064a\u0631\u0648\u062a"


def test_duplicate_place_names_keep_district_context(
    client,
    monkeypatch,
    tmp_path,
):
    """Places with the same name in different districts should stay distinguishable."""
    from app.reports import location as location_module

    disable_default_gazetteer(location_module, monkeypatch, tmp_path)
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: [
            geocoder_place(
                "Ain",
                lat=33.7600,
                lng=35.5600,
                district="Aley District",
                governorate="Mount Lebanon Governorate",
            ),
            geocoder_place(
                "Ain",
                lat=34.0800,
                lng=36.0500,
                district="Bsharri District",
                governorate="North Lebanon Governorate",
            ),
        ],
    )

    response = client.get("/api/lebanon-localities/search?q=Ain")

    assert response.status_code == 200
    display_names = [item["display_name"] for item in response.get_json()["results"]]

    assert "Ain, Aley District, Mount Lebanon Governorate" in display_names
    assert "Ain, Bsharri District, North Lebanon Governorate" in display_names


def test_search_returns_more_than_eight_geocoder_results(
    client,
    monkeypatch,
    tmp_path,
):
    """The API should expose broad locality suggestions, not stop at a tiny list."""
    from app.reports import location as location_module

    disable_default_gazetteer(location_module, monkeypatch, tmp_path)
    raw_results = [
        geocoder_place(
            f"B Locality {index}",
            lat=33.7500 + (index * 0.004),
            lng=35.5500 + (index * 0.004),
            district="Baabda District",
            governorate="Mount Lebanon Governorate",
        )
        for index in range(12)
    ]
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: raw_results,
    )

    response = client.get("/api/lebanon-localities/search?q=Ba")

    assert response.status_code == 200
    nominatim_results = [
        item for item in response.get_json()["results"] if item["source"] == "nominatim"
    ]

    assert len(nominatim_results) == 12


def write_gazetteer(tmp_path, places):
    """Write a temporary GeoNames-style localities JSON file for tests."""
    path = tmp_path / "lebanon_localities.json"
    path.write_text(
        json.dumps(
            {
                "source": "GeoNames",
                "country_code": "LB",
                "count": len(places),
                "places": places,
            }
        ),
        encoding="utf-8",
    )
    return path


def reset_location_caches(location_module):
    """Clear cached locality data after monkeypatching the source path."""
    location_module.clear_location_caches()


def disable_default_gazetteer(location_module, monkeypatch, tmp_path):
    """Force tests through the remote-geocoder branch deterministically."""
    monkeypatch.setattr(
        location_module,
        "LOCALITIES_DATA_PATH",
        tmp_path / "missing_lebanon_localities.json",
    )
    reset_location_caches(location_module)


def gazetteer_place(
    geoname_id,
    name,
    lat=33.82,
    lng=35.62,
    aliases=None,
    name_ar=None,
    district="Chouf District",
    governorate="Mount Lebanon Governorate",
):
    return {
        "geoname_id": geoname_id,
        "name": name,
        "name_en": name,
        "name_ar": name_ar,
        "ascii_name": name,
        "alternate_names": aliases or [name],
        "district": district,
        "governorate": governorate,
        "lat": lat,
        "lng": lng,
        "type": "populated place",
        "feature_code": "PPL",
        "population": 1000 - geoname_id,
    }


def test_full_local_gazetteer_returns_many_villages_without_remote_geocoder(
    client,
    monkeypatch,
    tmp_path,
):
    """A generated GeoNames file should replace the old tiny hardcoded list."""
    from app.reports import location as location_module

    places = [
        gazetteer_place(
            index,
            f"B Village {index}",
            lat=33.70 + (index * 0.001),
            lng=35.55 + (index * 0.001),
        )
        for index in range(60)
    ]
    monkeypatch.setattr(location_module, "LOCALITIES_DATA_PATH", write_gazetteer(tmp_path, places))
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: pytest.fail("local gazetteer search should not call Nominatim"),
    )
    reset_location_caches(location_module)

    response = client.get("/api/lebanon-localities/search?q=B")

    assert response.status_code == 200
    results = response.get_json()["results"]

    assert len(results) == 50
    assert all(item["source"] == "geonames" for item in results)
    assert results[0]["display_name"].endswith("Chouf District, Mount Lebanon Governorate")


def test_locality_search_preload_builds_reusable_index(
    monkeypatch,
    tmp_path,
):
    """The local gazetteer should be indexed once for faster repeated searches."""
    from app.reports import location as location_module

    places = [
        gazetteer_place(1, "Bater"),
        gazetteer_place(2, "Batroun", governorate="North Lebanon Governorate"),
    ]
    monkeypatch.setattr(
        location_module,
        "LOCALITIES_DATA_PATH",
        write_gazetteer(tmp_path, places),
    )
    reset_location_caches(location_module)

    assert location_module.preload_locality_search() == 2
    assert location_module._gazetteer_search_index.cache_info().currsize == 1

    results = location_module.search_lebanese_localities("Bat")
    assert [result["name"] for result in results] == ["Bater", "Batroun"]


def test_full_local_gazetteer_supports_arabic_place_names(
    client,
    monkeypatch,
    tmp_path,
):
    """Arabic names from the generated dataset should be searchable."""
    from app.reports import location as location_module

    arabic_bater = "\u0628\u0627\u062a\u0631"
    places = [
        gazetteer_place(
            1,
            "Bater",
            lat=33.60207,
            lng=35.61731,
            aliases=["Bater", arabic_bater],
            name_ar=arabic_bater,
        )
    ]
    monkeypatch.setattr(location_module, "LOCALITIES_DATA_PATH", write_gazetteer(tmp_path, places))
    reset_location_caches(location_module)

    response = client.get(
        "/api/lebanon-localities/search",
        query_string={"q": arabic_bater},
    )

    assert response.status_code == 200
    result = response.get_json()["results"][0]

    assert result["name"] == "Bater"
    assert result["name_ar"] == arabic_bater
    assert result["lat"] == pytest.approx(33.60207)
    assert result["lng"] == pytest.approx(35.61731)


def test_curated_duplicate_keeps_arabic_aliases(
    client,
    monkeypatch,
    tmp_path,
):
    """Curated cities should still match Arabic names after dedupe."""
    from app.reports import location as location_module

    arabic_beirut = "\u0628\u064a\u0631\u0648\u062a"
    places = [
        gazetteer_place(
            1,
            "Beirut",
            lat=33.89332,
            lng=35.50157,
            governorate="Beirut Governorate",
            aliases=["Beirut", arabic_beirut],
            name_ar=arabic_beirut,
        )
    ]
    monkeypatch.setattr(
        location_module,
        "LOCALITIES_DATA_PATH",
        write_gazetteer(tmp_path, places),
    )
    monkeypatch.setattr(
        location_module,
        "_nominatim_request",
        lambda _query: pytest.fail("Arabic city search should be local"),
    )
    reset_location_caches(location_module)

    response = client.get(
        "/api/lebanon-localities/search",
        query_string={"q": arabic_beirut},
    )

    assert response.status_code == 200
    result = response.get_json()["results"][0]

    assert result["name"] == "Beirut"
    assert result["name_ar"] == arabic_beirut


def test_full_local_gazetteer_supports_alternate_english_spellings(
    client,
    monkeypatch,
    tmp_path,
):
    """Alternate transliterations should match without silently choosing another place."""
    from app.reports import location as location_module

    places = [
        gazetteer_place(
            1,
            "Deir el Qamar",
            aliases=["Deir el Qamar", "Dayr al Qamar", "Deir El Kamar"],
        )
    ]
    monkeypatch.setattr(location_module, "LOCALITIES_DATA_PATH", write_gazetteer(tmp_path, places))
    reset_location_caches(location_module)

    response = client.get("/api/lebanon-localities/search?q=Dayr%20al%20Qamar")

    assert response.status_code == 200
    result = response.get_json()["results"][0]

    assert result["name"] == "Deir el Qamar"
    assert result["source"] == "geonames"


def test_oversized_pixel_image_is_rejected_without_report(app, client):
    """Images above the configured pixel limit should be rejected after save."""
    app.config["MAX_IMAGE_PIXELS"] = 8

    with pytest.warns(Image.DecompressionBombWarning):
        response = client.post(
            "/upload",
            data={"image": (image_bytes(), "road.png")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/upload")

    with app.app_context():
        assert Report.query.count() == 0


def test_detection_client_does_not_request_api_database_save(
    app,
    tmp_path,
    monkeypatch,
):
    image_path = tmp_path / "road.png"
    image_path.write_bytes(image_bytes().getvalue())
    captured = {}

    class ExampleReport:
        id = 42

    class FakeResponse:
        ok = True

        @staticmethod
        def json():
            return {
                "success": True,
                "damage_type": "Potholes",
                "confidence": 0.84,
                "severity_score": 82,
                "severity_label": "Critical",
                "annotated_image_path": "static/uploads/annotated/road.jpg",
            }

    def fake_post(_url, **kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(
        "app.utils.detection_client.requests.post",
        fake_post,
    )

    with app.app_context():
        result = trigger_detection(ExampleReport(), str(image_path))

    assert result["status"] == "completed"
    assert captured["json"] == {"image_path": str(image_path)}


def test_detection_client_timeout_returns_pending(
    app,
    tmp_path,
    monkeypatch,
):
    image_path = tmp_path / "road.png"
    image_path.write_bytes(image_bytes().getvalue())

    class ExampleReport:
        id = 42

    def raise_timeout(*_args, **_kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(
        "app.utils.detection_client.requests.post",
        raise_timeout,
    )

    with app.app_context():
        result = trigger_detection(ExampleReport(), str(image_path))

    assert result["status"] == "pending"
    assert "timed out" in result["error"]


def test_detection_client_http_error_returns_pending(
    app,
    tmp_path,
    monkeypatch,
):
    image_path = tmp_path / "road.png"
    image_path.write_bytes(image_bytes().getvalue())

    class ExampleReport:
        id = 42

    class FakeResponse:
        ok = False
        status_code = 503
        text = "service unavailable"

        @staticmethod
        def json():
            return {"error": "model unavailable"}

    monkeypatch.setattr(
        "app.utils.detection_client.requests.post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    with app.app_context():
        result = trigger_detection(ExampleReport(), str(image_path))

    assert result["status"] == "pending"
    assert "HTTP 503" in result["error"]
