"""Seed 10 extra test reports so the map has 15+ real database entries.

Run from the repo root:  python scripts/seed_map_test.py
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Allow importing app/models from the repo root when running from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db          # adjust if db lives in models.py
from models import Report, Detection

# (name, lat, lng) — spread across Lebanon
LOCATIONS = [
    ("Tripoli",  34.4346, 35.8362),
    ("Jounieh",  33.9808, 35.6178),
    ("Beirut - Hamra", 33.8959, 35.4784),
    ("Beirut - Achrafieh", 33.8886, 35.5211),
    ("Zahle",    33.8463, 35.9020),
    ("Saida",    33.5571, 35.3729),
    ("Tyre",     33.2704, 35.2038),
    ("Baalbek",  34.0058, 36.2181),
    ("Byblos",   34.1208, 35.6517),
    ("Aley",     33.8106, 35.5972),
]

DAMAGE_TYPES = ["Pothole", "Road Crack", "Surface Wear", "Other", "None"]

SEVERITIES = [
    # (label, score range)
    ("Low",      (0.10, 0.30)),
    ("Medium",   (0.30, 0.55)),
    ("High",     (0.55, 0.80)),
    ("Critical", (0.80, 0.98)),
]


def seed():
    created = 0
    for i, (name, lat, lng) in enumerate(LOCATIONS):
        damage_type = DAMAGE_TYPES[i % len(DAMAGE_TYPES)]
        sev_label, (lo, hi) = SEVERITIES[i % len(SEVERITIES)]
        sev_score = round(random.uniform(lo, hi), 2)

        # small jitter so pins don't overlap exactly on repeated runs
        jitter = lambda: random.uniform(-0.004, 0.004)

        report = Report(
            lat=lat + jitter(),
            lng=lng + jitter(),
            image_path="uploads/seed_placeholder.jpg",
            location_source="manual",
            status="pending",
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 20)),
        )
        db.session.add(report)
        db.session.flush()  # get report.id before commit

        detection = Detection(
            report_id=report.id,
            damage_type=damage_type,
            confidence=round(random.uniform(0.60, 0.95), 2),
            severity_score=sev_score,
            severity_label=sev_label,
            annotated_image_path="uploads/seed_placeholder.jpg",
        )
        db.session.add(detection)
        created += 1
        print(f"  + {name}: {damage_type} / {sev_label}")

    db.session.commit()
    print(f"\nDone — inserted {created} reports.")


if __name__ == "__main__":
    with app.app_context():
        seed()