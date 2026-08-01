"""SQLAlchemy models for Tariq.lb."""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utc_now() -> datetime:
    """Return naive UTC timestamps for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Report(db.Model):
    """A single road-damage report submitted by a user."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    lat = db.Column(db.Float, nullable=False, index=True)
    lng = db.Column(db.Float, nullable=False, index=True)
    location_source = db.Column(
        db.String(10),
        nullable=False,
        default="manual",
        index=True,
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    detection_status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    detection_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        index=True,
    )

    detections = db.relationship(
        "Detection",
        backref="report",
        cascade="all, delete-orphan",
        lazy="selectin",
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
    """The AI detection result linked to a single Report."""

    __tablename__ = "detections"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("reports.id"),
        nullable=False,
        index=True,
    )
    damage_type = db.Column(db.String(50), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    severity_score = db.Column(db.Integer, nullable=False)
    severity_label = db.Column(db.String(20), nullable=False, index=True)
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


class FeedbackMessage(db.Model):
    """A contact or feedback message submitted from the public website."""

    __tablename__ = "feedback_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("reports.id"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        index=True,
    )

    report = db.relationship(
        "Report",
        backref=db.backref("feedback_messages", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "message": self.message,
            "report_id": self.report_id,
            "created_at": self.created_at.isoformat(),
        }
