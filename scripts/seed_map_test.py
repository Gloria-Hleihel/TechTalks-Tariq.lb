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
    # --- 15 new for the 30+ test ---
    ("Nabatieh",      33.3789, 35.4839),
    ("Batroun",       34.2553, 35.6581),
    ("Zgharta",       34.3983, 35.8947),
    ("Bcharre",       34.2508, 36.0108),
    ("Jbeil North",   34.1300, 35.6510),
    ("Chtaura",       33.8206, 35.8556),
    ("Hermel",        34.3939, 36.3892),
    ("Marjeyoun",     33.3608, 35.5919),
    ("Bint Jbeil",    33.1219, 35.4308),
    ("Dbayeh",        33.9503, 35.5811),
    ("Baabda",        33.8339, 35.5442),
    ("Nabatieh East", 33.3900, 35.5000),
    ("Sidon East",    33.5600, 35.4000),
    ("Jounieh Port",  33.9750, 35.6200),
    ("Tripoli South", 34.4200, 35.8500),
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