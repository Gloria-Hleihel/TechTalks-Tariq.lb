"""
scripts/seed.py — Seed data for Tariq.lb

Inserts 10 sample reports (with linked detections) so Majd, Malek,
and Gloria can all develop and test against real-looking data without
waiting on a live upload flow.

Usage (from the project root):
    python scripts/seed.py
"""

import os
import sys
import random
from datetime import datetime, timedelta

# Allow running this script directly from scripts/ while still importing
# config.py and models.py from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask

import config
from models import db, Report, Detection

app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

# A spread of real coordinates across Lebanon so the map looks populated
# during development (Beirut, Tripoli, Sidon, Tyre, Zahle, Byblos, etc.)
SAMPLE_LOCATIONS = [
    (33.8938, 35.5018),  # Beirut
    (33.8959, 35.4784),  # Hamra
    (33.8203, 35.4878),  # Baabda
    (34.4346, 35.8362),  # Tripoli
    (33.5571, 35.3729),  # Sidon
    (33.2704, 35.2038),  # Tyre
    (33.8333, 35.9667),  # Zahle
    (34.1208, 35.6517),  # Byblos
    (33.9000, 35.5000),  # Beirut (manual pin)
    (33.8869, 35.5131),  # Achrafieh
]

SEVERITY_TABLE = [
    ("Low", 20),
    ("Medium", 45),
    ("High", 70),
    ("Critical", 92),
]


def build_seed_data():
    reports = []

    for i in range(10):
        lat, lng = SAMPLE_LOCATIONS[i]
        location_source = "gps" if i % 3 != 0 else "manual"
        status = config.REPORT_STATUSES[i % len(config.REPORT_STATUSES)]
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 14))

        report = Report(
            image_path=f"static/uploads/seed_{i + 1}.jpg",
            lat=lat,
            lng=lng,
            location_source=location_source,
            status=status,
            created_at=created_at,
        )
        db.session.add(report)
        db.session.flush()  # assign report.id before we create the Detection

        damage_type = config.DAMAGE_TYPES[i % len(config.DAMAGE_TYPES)]
        severity_label, severity_score = SEVERITY_TABLE[i % len(SEVERITY_TABLE)]
        confidence = round(random.uniform(0.55, 0.97), 2)

        detection = Detection(
            report_id=report.id,
            damage_type=damage_type,
            confidence=confidence,
            severity_score=severity_score,
            severity_label=severity_label,
            annotated_image_path=f"static/uploads/annotated/seed_{i + 1}_annotated.jpg",
        )
        db.session.add(detection)
        reports.append(report)

    db.session.commit()
    return reports


def main():
    with app.app_context():
        db.create_all()

        existing = Report.query.count()
        if existing > 0:
            print(f"Database already has {existing} reports — skipping seed to avoid duplicates.")
            print("Delete tariq.db and re-run if you want a fresh seed.")
            return

        reports = build_seed_data()
        print(f"Seeded {len(reports)} reports with linked detections.\n")
        for r in reports:
            d = r.detections[0]
            print(
                f"  Report #{r.id}: {d.damage_type} ({d.severity_label}) "
                f"at ({r.lat}, {r.lng}) — status={r.status}, source={r.location_source}"
            )


if __name__ == "__main__":
    main()
