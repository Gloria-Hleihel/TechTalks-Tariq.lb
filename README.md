# Tariq.lb — MVP

Smart road-condition detection and mapping platform for Lebanon, built from the PRD's
MVP Features list (Section 5).

## Scope of this MVP

Everything in the PRD's MVP feature list is implemented **except the AI model itself**:

| Feature | Status |
|---|---|
| Upload road photo | ✅ Real |
| YOLOv8 detection | 🟡 **Mocked** — see `app/detection.py` |
| Damage classification | 🟡 **Mocked** (returned by the same mock) |
| Severity score | 🟡 **Mocked** |
| EXIF GPS extraction | ✅ Real (Pillow) |
| Manual map-pin fallback | ✅ Real |
| Save report to database | ✅ Real (SQLite) |
| Leaflet map display | ✅ Real |
| View report details | ✅ Real |

**Why mock detection?** Running real YOLOv8 inference requires `ultralytics` +
pretrained weights, which need installing in your environment. Mocking it means you can
stand up and test the entire upload → detect → score → map pipeline right now, then
swap in the real model later without touching any other part of the app.

### Swapping in real YOLOv8 later

Open `app/detection.py` — it has a docstring with the exact steps. In short:
install `ultralytics` and `opencv-python`, load the pretrained weights once at module
level, and replace the body of `run_detection()` with a real inference call. The
function signature stays the same, so nothing else in the app needs to change.

### A note on the tech stack

The PRD's suggested stack (Section 12) includes Flask-SQLAlchemy and Flask-CORS. This
build environment had no package-install access beyond what's preinstalled, so:

- **Flask-SQLAlchemy → plain `sqlite3`** (see `app/models.py`). Same schema, same data
  shape returned to callers — swap back to SQLAlchemy later with no changes needed
  outside that one file.
- **Flask-CORS → removed.** It's not actually needed: the frontend and API are served
  from the same Flask app (same origin), so there's no cross-origin request to allow.

If your local machine has internet access, `pip install Flask-SQLAlchemy Flask-CORS`
will work fine if you'd rather use those — just isn't required for this MVP to run.

## Setup

```bash
cd tariq-lb
pip install -r requirements.txt
cd app
python app.py
```

Visit `http://localhost:5000`.

## Project structure

```
tariq-lb/
├── requirements.txt
└── app/
    ├── app.py            # Flask routes (pages + JSON API)
    ├── models.py         # SQLite data layer
    ├── detection.py       # MOCKED AI detection — swap for real YOLOv8 here
    ├── gps_utils.py       # Real EXIF GPS extraction (Pillow)
    ├── templates/
    │   ├── index.html     # Map + upload dispatch console
    │   └── report.html    # Single report detail page
    └── static/
        ├── css/style.css
        ├── js/map.js       # Leaflet map + pin rendering
        ├── js/upload.js    # Upload flow + manual pin fallback
        └── uploads/        # Uploaded report photos land here
```

## How the manual-pin fallback works

1. User uploads a photo.
2. Server tries to read GPS from the photo's EXIF metadata.
3. If GPS is found → report saves immediately, pin drops on the map.
4. If GPS is missing → server responds with a "no_gps" status instead of saving.
   The frontend then puts the map into pin-placement mode; the user taps a location,
   and the same photo is submitted again with those manual coordinates attached.

## API

| Method | Route | Description |
|---|---|---|
| GET | `/api/reports` | List all reports, newest first |
| GET | `/api/reports/<id>` | Get one report |
| POST | `/api/reports` | Create a report (multipart form: `image`, optional `manual_lat`/`manual_lon`) |

## Not included (by design, per "static features only")

Per the PRD's Future Features (Section 14) and this MVP's scope: no user accounts,
no admin dashboard, no filtering, no notifications, no real-time updates. Single shared
view of all reports, no auth.
