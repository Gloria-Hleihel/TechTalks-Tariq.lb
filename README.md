# 🛣️ Tariq.lb — Smart Road Condition Detection & Mapping Platform

> Roads. Solutions. Progress.

Tariq.lb is a smart web application that allows users to report road damage in Lebanon by uploading photos. The system automatically detects road damage using YOLOv8, scores its severity, and displays reports on an interactive map — turning scattered complaints into one centralized, visual, and shareable road damage map.

---

## 🚀 Features

- 📸 Upload road photos to report damage
- 🤖 Automatic damage detection using YOLOv8
- 📊 Severity scoring (Low / Medium / High / Critical)
- 📍 GPS extraction from photo EXIF metadata
- 🗺️ Manual location selection via interactive map
- 🗺️ Interactive Leaflet map with color-coded severity pins
- 🔧 Admin panel to manage and review reports
- 📈 Analytics dashboard with damage breakdowns

---

## 👥 Team

| Member | Module | Role |
|--------|--------|------|
| Zahraa | M4 — Database & Admin | Database schema, SQLAlchemy models, admin panel |
| Malek | M1 — Report Submission | Upload form, GPS extraction, file storage |
| Gloria | M3 — Map & Visualization | Leaflet map, pins, filters, report detail page |
| Majd | M2 — AI Detection Engine | YOLOv8 inference, severity scoring, detection API |

---

## 🛠️ Tech Stack

| Area | Tools |
|------|-------|
| Frontend | HTML, CSS, JavaScript, Leaflet.js, Jinja2 |
| Backend | Python 3.12, Flask, Flask-SQLAlchemy |
| AI/ML | YOLOv8 (ultralytics), oracl4/RoadDamageDetection weights |
| Database | SQLite |
| Utilities | Pillow (EXIF GPS), Werkzeug (file uploads) |

---

## ⚙️ Setup Instructions

### 1. Clone the repository

git clone https://github.com/Gloria-Hleihel/TechTalks-Tariq.lb.git
cd TechTalks-Tariq.lb

### 2. Create a virtual environment

python -m venv venv

Activate it:
- **Windows:** venv\Scripts\activate
- **Mac/Linux:** source venv/bin/activate

### 3. Install dependencies

pip install -r requirements.txt

### 4. Download YOLOv8 model weights

Download roaddamage.pt from oracl4/RoadDamageDetection (trained on RDD2022) and place it in models/road_damage.pt

### 5. Seed the database

python scripts/seed.py

This inserts 10 sample reports across Lebanon for development and testing.

### 6. Run the application

python run.py

The app will be available at http://127.0.0.1:5000

---

## 🔐 Admin Panel

Access the admin panel at http://127.0.0.1:5000/admin/login

Default credentials:
- **Username:** admin
- **Password:** changeme

---

## 🗄️ Database

SQLite database with two tables:
- **reports** — user-submitted road damage reports
- **detections** — AI detection results linked to reports

Full schema documentation: docs/schema.md

---

## 🗺️ Map

The interactive map is centered on Lebanon (lat: 33.85, lng: 35.86) and displays color-coded pins:
- 🟢 Green — Low severity
- 🟡 Yellow — Medium severity
- 🟠 Orange — High severity
- 🔴 Red — Critical severity

---

## 📖 Documentation

- Database Schema: docs/schema.md
- API Documentation: docs/api.md
- DB Integrity Check: docs/db_integrity_check.md

---

## 🔧 Troubleshooting

### Problem: Port 5000 Already in Use
- Run `flask run --port 3001`

### Problem: No module named ultralytics
- Make sure your virtual environment is activated before pip install
- Re-run `pip install -r requirements.txt`

### Problem: Model fails to load / roaddamage.pt not found
- Confirm the weights file exists at models/road_damage.pt
- Re-download from the oracl4 repo if corrupted

### Problem: Pins don't appear on the map
- Check the photo actually had GPS data; if not, use the manual pin fallback
- Open the browser console (F12) and confirm GET /api/reports returns data

### Problem: Map tiles don't load
- Confirm you have an internet connection (Leaflet fetches tiles from OpenStreetMap)

### Problem: Detection is slow
- The first inference loads the model into memory and is always slowest

---

## ⚠️ Notes

- This app runs locally only — no cloud deployment required
- GPS data is not always present in uploaded photos — manual pin selection is always available
- Default admin credentials should be changed via environment variables in production
- SQLite is used for development scope — no PostgreSQL migration needed

---

Tariq.lb — Zahraa · Malek · Gloria · Majd · 2026