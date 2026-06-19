# Tariq.lb 🛣️

A smart road-condition app that detects damage in road photos, scores its severity, and maps it automatically — turning scattered complaints about Lebanon's roads into a single, visual, shareable record.


## 📖 Project Description

Tariq.lb is a full-stack web application built to solve a visibility problem: there's no central, up-to-date picture of *where* Lebanon's roads are damaged or *how bad* it is. Reports are scattered, anecdotal, and impossible to act on.

Instead of relying on word-of-mouth and manual surveys, Tariq.lb provides:

- **One-Photo Reporting** — Upload a road photo and let the model do the rest
- **Automatic Damage Detection** — A computer vision model finds and classifies potholes, cracks, and surface wear
- **Severity Scoring** — Every detection gets a severity score so the worst spots stand out
- **Automatic Geolocation** — GPS pulled straight from the photo's EXIF data, with a manual map-pin fallback
- **Interactive Damage Map** — Every report becomes a color-coded pin on a live map
- **Persistent Record** — All uploads and detections are stored, so the map builds up over time

### Why Tariq.lb?

✅ **Effortless to Use** — If you can take a photo, you can file a report
✅ **No Manual Classification** — The model identifies and scores damage for you
✅ **Map-First** — See the whole picture at a glance instead of reading a list
✅ **Runs Locally** — Detection happens on your own machine; no paid AI API required
✅ **Built for Lebanon** — Designed around the real gap in local road-condition data

---

## 🛠 Tech Stack

### Frontend
- **HTML / CSS / JavaScript** — Core interface
- **Leaflet.js** — Interactive map and pins
- **Jinja2** — Server-side templating from Flask

### Backend
- **Python 3.10+** — Language
- **Flask** — Lightweight web framework, pairs naturally with the ML code
- **Flask-SQLAlchemy** — Database ORM
- **Flask-CORS** — Cross-origin handling (if frontend runs separately)

### ML / Detection
- **YOLOv8** (`ultralytics`) — Object detection model
- **OpenCV** — Image handling
- **Pretrained weights** from [`oracl4/RoadDamageDetection`](https://github.com/oracl4/RoadDamageDetection), trained on the **RDD2022** dataset — no custom training needed

### Database & Utilities
- **SQLite** — Zero-setup file-based database
- **Pillow** — Reads GPS coordinates from photo EXIF metadata
- **pandas** — Light data wrangling

---

## 📋 Requirements

### System Requirements
- **Python** v3.10 or higher ([Download](https://www.python.org/downloads/))
- **pip** (comes with Python)
- **Git** — for cloning the repo and the pretrained model

### Recommended
- **VS Code** — Code editor
- **A virtual environment** — to keep dependencies isolated
- **Postman** — API testing (optional)

> 💡 No paid services are required. The detection model, the dataset, and the entire stack are free and open source, and the model runs locally.

---

## 🚀 Installation & Setup

### Step 1: Clone the Project
```bash
git clone <repository-url>
cd Tariq.lb
```

### Step 2: Set Up the Backend

**2.1 Navigate to the backend folder**
```bash
cd backend
```

**2.2 Create and activate a virtual environment**
```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**2.3 Install dependencies**
```bash
pip install -r requirements.txt
```

**2.4 Add the pretrained model weights**

Download the YOLOv8 weights from the [`oracl4/RoadDamageDetection`](https://github.com/oracl4/RoadDamageDetection) repository and place the file here:
```
backend/ml/weights/best.pt
```

**2.5 Run the backend**
```bash
flask run
```
You should see:
```
 * Running on http://127.0.0.1:5000
```
> If port 5000 is busy, run `flask run --port 3001` instead.

### Step 3: Open in Browser
- Go to `http://localhost:5000`
- Upload a road photo and watch it appear on the map!

---

## 📁 Project Structure

```
Tariq.lb/
│
├── backend/                          # Flask server + ML
│   ├── app.py                        # Main app & route definitions
│   ├── models.py                     # SQLAlchemy models (PhotoUpload, Detection)
│   ├── ml/
│   │   ├── detect.py                 # YOLOv8 inference
│   │   ├── severity.py               # Severity scoring logic
│   │   └── weights/
│   │       └── best.pt               # Pretrained model weights
│   ├── utils/
│   │   └── exif_gps.py               # Reads GPS from photo EXIF
│   ├── instance/
│   │   └── tariq.db                  # SQLite database (auto-created)
│   ├── uploads/                      # Stored uploaded photos
│   └── requirements.txt
│
└── frontend/                         # Client interface
    ├── templates/
    │   ├── index.html                # Upload page
    │   └── map.html                  # Map view (Leaflet.js)
    └── static/
        ├── css/
        │   └── style.css
        └── js/
            └── map.js                # Fetches detections, renders pins
```

---

## 🎯 How to Use Tariq.lb

### 1. Upload a Photo
- Open the upload page
- Choose a road photo (ideally one with GPS data in it)
- Submit — the model runs automatically

### 2. Let It Detect
- The photo is passed through YOLOv8
- Each piece of damage is classified and given a confidence score
- A severity score is calculated per detection

### 3. Set the Location
- GPS is read automatically from the photo's EXIF metadata
- If the photo has no GPS data, drop a pin on the map to set it manually

### 4. View the Map
- Switch to the map view
- Each detection appears as a color-coded pin
- Click a pin to see the damage type, severity, and the original photo

### 5. Watch It Grow
- Every upload is saved, so the map fills in over time as more photos come in

---

## 🗄 Database Schema

Two tables, linked one-to-many:

### PHOTO_UPLOAD
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer (PK) | Unique photo ID |
| `filename` | String | Stored file name |
| `latitude` | Float | From EXIF or manual pin |
| `longitude` | Float | From EXIF or manual pin |
| `uploaded_at` | DateTime | Upload timestamp |

### DETECTION
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer (PK) | Unique detection ID |
| `photo_id` | Integer (FK) | Links to PHOTO_UPLOAD |
| `damage_type` | String | e.g. pothole, longitudinal crack |
| `confidence` | Float | Model confidence (0–1) |
| `severity` | Float | Computed severity score |

> GPS is stored on the photo record. One photo can produce many detections.

---

## 📚 API Endpoints Reference

### Photos & Detection
```
POST   /api/upload                 # Upload a photo, run detection, store results
GET    /api/photos                 # List all uploaded photos
GET    /api/photos/:id             # Get one photo and its detections
DELETE /api/photos/:id             # Delete a photo and its detections
```

### Map Data
```
GET    /api/detections             # All detections (used to render map pins)
GET    /api/detections/:id         # Single detection detail
```

### Stats (optional)
```
GET    /api/stats                  # Totals by damage type / severity
```

---

## 🖥 How a Request Flows

1. The browser loads the upload page from Flask; the user submits a photo.
2. Flask saves the file, reads its EXIF GPS via `exif_gps.py`, and calls `detect.py` to run YOLOv8 inference.
3. Detections are scored by `severity.py` and written to the database through `models.py`.
4. On the map page, `map.js` calls `GET /api/detections`, receives JSON, and drops a colored pin for each detection.

---

## 🔧 Troubleshooting

### Problem: Port 5000 Already in Use
- Run `flask run --port 3001`
- Update the frontend's API base URL if your JS points at port 5000

### Problem: "No module named ultralytics" (or similar)
- Make sure your virtual environment is **activated** before `pip install`
- Re-run `pip install -r requirements.txt`

### Problem: Model fails to load / `best.pt` not found
- Confirm the weights file is at `backend/ml/weights/best.pt`
- Re-download from the oracl4 repo if the file is corrupted or incomplete

### Problem: Pins don't appear on the map
- Check the photo actually had GPS data; if not, use the manual pin fallback
- Open the browser console (F12) and confirm `GET /api/detections` returns data
- Check the backend terminal for errors during detection

### Problem: Map tiles don't load
- Confirm you have an internet connection (Leaflet fetches map tiles from OpenStreetMap)
- Check the tile URL in `map.js` is correct

### Problem: Detection is slow
- The first inference loads the model into memory and is always slowest
- Large images take longer; consider resizing very large photos before upload

---

## 🔐 Notes & Good Practice

- The detection model runs **locally** — no images are sent to any external API
- `instance/tariq.db` and the `uploads/` folder hold user data; don't commit them to Git
- Add `venv/`, `instance/`, `uploads/`, and `__pycache__/` to your `.gitignore`
- Use HTTPS if you ever deploy this publicly

---

## 💰 Cost

**Zero, as scoped.** Every dependency — YOLOv8/ultralytics, OpenCV, Flask, SQLite, Pillow, Leaflet — is free and open source, the pretrained model and RDD2022 dataset are free downloads, and detection runs on your own machine with no paid AI API. The only optional cost is public hosting if you want it live 24/7 (free tiers like Render or PythonAnywhere comfortably cover a student demo).

---

## 📦 Deploying for a Demo

For the project demo, running locally is perfectly fine — no hosting needed. If you want it online:

- **Backend + Frontend** — Host on a free-tier platform (Render, Railway, PythonAnywhere)
- Note that free tiers sleep when idle and have CPU limits, which can slow inference
- Keep the database and uploaded photos out of version control
- Set any secrets via the host's environment variables, not in code

---

## 📄 License

This project is provided for educational purposes.

---

## 📝 Scope & Roadmap

**v1.0.0 (Current MVP)**
- Photo upload with automatic damage detection
- Severity scoring per detection
- EXIF GPS with manual map-pin fallback
- Interactive Leaflet map with color-coded pins
- Persistent SQLite storage

**Deliberately out of scope for this phase:**
- Video ingestion and frame extraction
- Automatic deduplication of repeated damage across photos
- A custom-trained detection model

**Possible future work:**
- User accounts and report attribution
- Filtering the map by damage type or severity
- Exporting reports for municipalities

---

Built for safer roads. 🛣️✨
