# Setup Guide — Tariq.lb

Owner: Zahraa · Week 5

This guide walks you through everything needed to run Tariq.lb
locally from scratch — from cloning the repository to seeing the
app in your browser.

---

## Prerequisites

Make sure you have these installed before starting:

- Python 3.12+
- Git
- A terminal (Command Prompt, PowerShell, or Terminal on Mac/Linux)

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/Gloria-Hleihel/TechTalks-Tariq.lb.git
cd TechTalks-Tariq.lb
```

---

## Step 2 — Create a virtual environment

A virtual environment keeps the project's dependencies isolated
from your system Python.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal line.

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, SQLAlchemy, Pillow, ultralytics, and all
other required packages.

---

## Step 4 — Download the YOLOv8 model weights

Download `roaddamage.pt` from:
oracl4/RoadDamageDetection (trained on RDD2022)
Place the file at:
models/road_damage.pt
This file is not included in the repository due to its size.
The app will not run detection without it.

---

## Step 5 — Seed the database

This creates the SQLite database and inserts 10 sample reports
across Lebanon so you can test the app immediately.

```bash
python scripts/seed.py
```

Expected output:
Seeded 10 reports with linked detections.
Report #1: Longitudinal Crack (Low) at (33.8938, 35.5018) — status=reviewed, source=gps
Report #2: Transverse Crack (Medium) at (33.8959, 35.4784) — status=resolved, source=gps

If you see "Database already has X reports — skipping seed",
delete `tariq.db` and run again:
```bash
del tariq.db
python scripts/seed.py
```

---

## Step 6 — Run the application

```bash
python run.py
```

You should see:
Serving Flask app 'app'
Debug mode: on
Running on http://127.0.0.1:5000
---

## Step 7 — Open the app in your browser

| Page | URL |
|------|-----|
| Map (main page) | http://127.0.0.1:5000/map |
| Upload a report | http://127.0.0.1:5000/upload |
| Admin login | http://127.0.0.1:5000/admin/login |

---

## Step 8 — Log in to the admin panel

Go to `http://127.0.0.1:5000/admin/login` and enter:

- **Username:** `admin`
- **Password:** `changeme`

You will see the dashboard with all seeded reports and analytics.

---

## Running the tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Troubleshooting

**"No module named flask"**
Make sure your virtual environment is activated before running
any commands.

**"No module named PIL"**
Run `pip install Pillow`

**"Model not found" or detection errors**
Confirm `models/road_damage.pt` exists in the correct location.

**"Database already has reports"**
Delete `tariq.db` and re-run `python scripts/seed.py`

**Port 5000 already in use**
Run `flask run --port 3001` instead.

---

*Tariq.lb — Setup Guide · Zahraa · Week 5*
