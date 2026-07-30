"""
models.py — SQLAlchemy models for Tariq.lb
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Report(db.Model):
    """A road-damage report submitted by a user."""

    __tablename__ = "reports"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    image_path = db.Column(
        db.String(255),
        nullable=False,
    )

    lat = db.Column(
        db.Float,
        nullable=False,
    )

    lng = db.Column(
        db.Float,
        nullable=False,
    )

    # "gps" from EXIF, "browser" from device location, "manual" from map click
    location_source = db.Column(
        db.String(10),
        nullable=False,
        default="manual",
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )

    # Detection remains pending if the API fails or times out.
    detection_status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )

    # Stores the most recent detection failure reason.
    detection_error = db.Column(
        db.String(500),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

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
            "detection_status": self.detection_status,
            "detection_error": self.detection_error,
            "created_at": self.created_at.isoformat(),
        }


class Detection(db.Model):
    """AI detection result linked to a Report."""

    __tablename__ = "detections"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    report_id = db.Column(
        db.Integer,
        db.ForeignKey("reports.id"),
        nullable=False,
    )

    damage_type = db.Column(
        db.String(50),
        nullable=False,
    )

    confidence = db.Column(
        db.Float,
        nullable=False,
    )

    severity_score = db.Column(
        db.Integer,
        nullable=False,
    )

    severity_label = db.Column(
        db.String(20),
        nullable=False,
    )

    annotated_image_path = db.Column(
        db.String(255),
        nullable=True,
    )

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