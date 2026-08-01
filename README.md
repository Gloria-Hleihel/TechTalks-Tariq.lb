# Tariq.lb — Smart Road Damage Detection & Mapping Platform

**Roads. Solutions. Progress.**

Tariq.lb is a smart web application that allows citizens to report road damage in Lebanon by uploading photos. The system analyzes uploaded images using YOLOv8, estimates damage severity, stores the report location, and displays active reports on an interactive map.

The platform helps turn scattered road complaints into one centralized, visual, and manageable road damage system.

## Features

- Upload road photos to report damage
- Automatic road damage detection using YOLOv8
- Severity scoring: Low, Medium, High, Critical
- GPS extraction from image EXIF metadata
- Manual location selection using an interactive map
- Lebanese city and village search
- Interactive Leaflet live map with severity-based markers
- Admin dashboard for reviewing and managing reports
- Admin map view for managing reports geographically
- Live, Under Review, and Done report sections
- Completed reports are hidden from the public map but kept in admin records
- Contact and feedback form for user messages
- FAQ and support modals


## Tech Stack

| Area | Tools |
|---|---|
| Frontend | HTML, CSS, JavaScript, Leaflet.js, Jinja2 |
| Backend | Python 3.12, Flask, Flask-SQLAlchemy |
| AI/ML | YOLOv8, Ultralytics |
| Database | SQLite |
| Utilities | Pillow, Werkzeug |

## Setup Instructions

### 1. Clone the repository

    git clone https://github.com/Gloria-Hleihel/TechTalks-Tariq.lb.git
    cd TechTalks-Tariq.lb

### 2. Create a virtual environment

    python -m venv venv

Activate it on Windows:

    venv\Scripts\activate

Activate it on Mac/Linux:

    source venv/bin/activate

### 3. Install dependencies

    pip install -r requirements.txt

### 4. Add the YOLO model

Place the model file here:

    models/road_damage.pt

### 5. Seed the database

    python scripts/seed.py

### 6. Run the application

    python run.py

Open the app in your browser:

    http://127.0.0.1:5000

## Admin Panel

Admin login page:

    http://127.0.0.1:5000/admin/login

Default credentials:

    Username: admin
    Password: changeme

## Testing

Run all tests:

    python -m pytest tests

## Database

The SQLite database includes:

- `reports` — submitted road damage reports
- `detections` — AI detection results linked to reports
- `feedback_messages` — contact and support messages from users

Full schema documentation is available in:

    docs/schema.md

## Map Severity Colors

- Green — Low
- Yellow — Medium
- Orange — High
- Red — Critical

## Documentation

- Database Schema: `docs/schema.md`
- API Documentation: `docs/api.md`
- DB Integrity Check: `docs/db_integrity_check.md`


## Troubleshooting


### Port 5000 already in use

Run the app on another port:

    flask run --port 3001

### No module named ultralytics

Make sure your virtual environment is activated, then run:

    pip install -r requirements.txt

### Model file not found

Make sure this file exists:

    models/road_damage.pt

### Map pins do not appear

Check that reports have valid latitude and longitude values. Completed reports are intentionally hidden from the public live map.

### Map tiles do not load

Check your internet connection because map tiles are loaded from online map providers.

### Detection is slow

The first detection may be slower because the model needs to load into memory.

## Notes

This project is designed for local development and university submission. For production deployment, change the default admin credentials, use environment variables, and consider a production database instead of SQLite.

## Project Structure
```text
TechTalks-Tariq.lb/
├── app/
│   ├── admin/
│   ├── detection/
│   ├── reports/
│   └── utils/
├── models/
│   └── road_damage.pt
├── scripts/
├── static/
├── templates/
├── tests/
├── docs/
├── config.py
├── models.py
├── requirements.txt
└── run.py
