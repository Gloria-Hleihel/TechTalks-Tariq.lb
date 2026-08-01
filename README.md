# 🛣️ Tariq.lb — Smart Road Damage Detection & Mapping Platform

**Roads. Solutions. Progress.**

Tariq.lb is a smart web application that allows citizens to report road damage in Lebanon by uploading photos. The system analyzes uploaded images using YOLOv8, estimates damage severity, stores the report location, and displays active reports on an interactive map.

The platform helps turn scattered road complaints into one centralized, visual, and manageable road damage system.

## 🚀 Features

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

## 👥 Team

| Member | Module | Role |
|---|---|---|
| Zahraa | M4 — Database & Admin | Database schema, SQLAlchemy models, admin panel |
| Malek | M1 — Report Submission | Upload form, GPS extraction, file storage |
| Gloria | M3 — Map & Visualization | Leaflet map, pins, filters, report detail page |
| Majd | M2 — AI Detection Engine | YOLOv8 inference, severity scoring, detection API |

## 🛠️ Tech Stack

| Area | Tools |
|---|---|
| Frontend | HTML, CSS, JavaScript, Leaflet.js, Jinja2 |
| Backend | Python 3.12, Flask, Flask-SQLAlchemy |
| AI/ML | YOLOv8, Ultralytics |
| Database | SQLite |
| Utilities | Pillow, Werkzeug |

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Gloria-Hleihel/TechTalks-Tariq.lb.git
cd TechTalks-Tariq.lb
