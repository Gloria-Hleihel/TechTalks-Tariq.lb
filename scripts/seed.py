"""
scripts/seed.py — Seed data for Tariq.lb

Inserts 10 sample reports with linked detections so Majd, Malek,
and Gloria can develop and test using realistic sample data without
waiting for live uploads.

Usage from the project root:
    python scripts/seed.py
"""

import os
import random
import sys
from datetime import datetime, timedelta

# Allow this script to run directly while still importing config.py
# and models.py from the project root.
PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

sys.path.insert(0, PROJECT_ROOT)

from flask import Flask

import config
from models import Detection, Report, db


app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)


# Sample coordinates across Lebanon.
SAMPLE_LOCATIONS = [
    (33.8938, 35.5018),  # Beirut
    (33.8959, 35.4784),  # Hamra
    (33.8203, 35.4878),  # Baabda
    (34.4346, 35.8362),  # Tripoli
    (33.5571, 35.3729),  # Sidon
    (33.2704, 35.2038),  # Tyre
    (33.8333, 35.9667),  # Zahle
    (34.1208, 35.6517),  # Byblos
    (33.9000, 35.5000),  # Beirut, manual pin
    (33.8869, 35.5131),  # Achrafieh
]


SEVERITY_TABLE = [
    ("Low", 20),
    ("Medium", 45),
    ("High", 70),
    ("Critical", 92),
]


def build_seed_data():
    """Create and save 10 sample reports with linked detections."""
    reports = []

    for index in range(10):
        lat, lng = SAMPLE_LOCATIONS[index]

        location_source = (
            "gps"
            if index % 3 != 0
            else "manual"
        )

        status = config.REPORT_STATUSES[
            index % len(config.REPORT_STATUSES)
        ]

        created_at = datetime.utcnow() - timedelta(
            days=random.randint(0, 14)
        )

        report = Report(
            image_path=f"uploads/seed_{index + 1}.jpg",
            lat=lat,
            lng=lng,
            location_source=location_source,
            status=status,
            created_at=created_at,
        )

        db.session.add(report)
        db.session.flush()

        damage_type = config.DAMAGE_TYPES[
            index % len(config.DAMAGE_TYPES)
        ]

        severity_label, severity_score = SEVERITY_TABLE[
            index % len(SEVERITY_TABLE)
        ]

        confidence = round(
            random.uniform(0.55, 0.97),
            2,
        )

        detection = Detection(
            report_id=report.id,
            damage_type=damage_type,
            confidence=confidence,
            severity_score=severity_score,
            severity_label=severity_label,
            annotated_image_path=(
                f"uploads/annotated/"
                f"seed_{index + 1}_annotated.jpg"
            ),
        )

        db.session.add(detection)
        reports.append(report)

    db.session.commit()

    return reports


def main():
    """Create database tables and insert seed data."""
    with app.app_context():
        db.create_all()

        existing_reports = Report.query.count()

        if existing_reports > 0:
            print(
                f"Database already has {existing_reports} reports "
                "— skipping seed to avoid duplicates."
            )

            print(
                "Delete tariq.db and run the script again "
                "if you want fresh seed data."
            )

            return

        reports = build_seed_data()

        print(
            f"Seeded {len(reports)} reports "
            "with linked detections.\n"
        )

        for report in reports:
            detection = report.detections[0]

            print(
                f"  Report #{report.id}: "
                f"{detection.damage_type} "
                f"({detection.severity_label}) "
                f"at ({report.lat}, {report.lng}) — "
                f"status={report.status}, "
                f"source={report.location_source}"
            )


if __name__ == "__main__":
    main()