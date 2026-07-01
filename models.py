"""
models.py — SQLAlchemy models for Tariq.lb

Owner: Zahraa. If a schema change is needed after Week 1, open a PR
here (with a migration note) rather than editing the tables directly —
see Section 7 (Integration Strategy) of the project plan.
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Report(db.Model):
    """A single road-damage report submitted by a user."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)

    # "gps" if extracted from EXIF, "manual" if the user pinned it on the map
    location_source = db.Column(db.String(10), nullable=False, default="manual")

    # pending -> reviewed -> resolved (admin workflow)
    status = db.Column(db.String(20), nullable=False, default="pending")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Deleting a Report deletes its Detection too (Week 3 cascade task)
    detections = db.relationship(
        "Detection",
        backref="report",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "image_path": self.image_path,
            "lat": self.lat,
            "lng": self.lng,
            "location_source": self.location_source,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class Detection(db.Model):
    """The AI detection result linked to a single Report."""

    __tablename__ = "detections"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)

    damage_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    severity_score = db.Column(db.Integer, nullable=False)       # 0-100
    severity_label = db.Column(db.String(20), nullable=False)    # Low/Medium/High/Critical
    annotated_image_path = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "damage_type": self.damage_type,
            "confidence": self.confidence,
            "severity_score": self.severity_score,
            "severity_label": self.severity_label,
            "annotated_image_path": self.annotated_image_path,
        }
