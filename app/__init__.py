import logging
import os

from flask import Flask, flash, jsonify, redirect, request, url_for
from sqlalchemy import inspect, text
from werkzeug.exceptions import RequestEntityTooLarge

import config
from app.security import init_security
from models import db


def create_app(test_config=None):
    """Create and configure the Tariq.lb Flask application."""
    test_config = test_config or {}

    static_folder = test_config.get(
        "STATIC_FOLDER",
        os.path.join(config.BASE_DIR, "static"),
    )

    template_folder = test_config.get(
        "TEMPLATE_FOLDER",
        os.path.join(config.BASE_DIR, "templates"),
    )

    app = Flask(
        __name__,
        static_folder=static_folder,
        template_folder=template_folder,
    )

    app.config.from_object(config)
    app.config.update(test_config)
    _validate_production_config(app)

    if not app.debug and not app.testing:
        logging.basicConfig(level=logging.INFO)

    init_security(app)

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True,
    )

    os.makedirs(
        app.config["ANNOTATED_FOLDER"],
        exist_ok=True,
    )

    db.init_app(app)

    from app.admin.routes import admin_bp
    from app.detection.routes import detection_bp
    from app.reports import bp as reports_bp

    app.register_blueprint(reports_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(admin_bp)

    if not app.testing:
        _preload_runtime_assets(app)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(_error):
        message = (
            "The upload is larger than 5MB. "
            "Compress the image or choose a smaller file."
        )

        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": message,
                        "field": "image",
                    }
                ),
                413,
            )

        flash(message, "error")
        return redirect(url_for("reports.upload"), code=303)

    if app.config.get("AUTO_CREATE_DATABASE", True):
        with app.app_context():
            db.create_all()
            _upgrade_sqlite_schema()

    return app


def _preload_runtime_assets(app: Flask) -> None:
    """Warm low-risk runtime caches so first user actions feel faster."""
    if app.config.get("PRELOAD_LOCALITY_SEARCH", True):
        try:
            from app.reports.location import preload_locality_search

            indexed_count = preload_locality_search()
            app.logger.info(
                "Preloaded %s Lebanese locality search entries.",
                indexed_count,
            )
        except Exception:
            app.logger.exception(
                "Could not preload locality search data."
            )

    if app.config.get("DETECTION_PRELOAD_MODEL", False):
        try:
            from app.detection.detector import preload_model

            preload_model()
            app.logger.info("Preloaded YOLO detection model.")
        except Exception:
            app.logger.exception(
                "Could not preload YOLO detection model."
            )


def _validate_production_config(app: Flask) -> None:
    """Fail fast when production mode still uses local demo secrets."""
    if app.testing:
        return

    if not app.config.get("REQUIRE_PRODUCTION_SECRETS", False):
        return

    problems = []

    if app.config.get("SECRET_KEY") == "dev-secret-change-me":
        problems.append("set SECRET_KEY to a strong random value")

    password_hash = app.config.get("ADMIN_PASSWORD_HASH")
    admin_password = app.config.get("ADMIN_PASSWORD")
    if not password_hash and admin_password == "changeme":
        problems.append(
            "set ADMIN_PASSWORD_HASH or change ADMIN_PASSWORD"
        )

    if problems:
        raise RuntimeError(
            "Unsafe production configuration: "
            + "; ".join(problems)
            + "."
        )


def _upgrade_sqlite_schema() -> None:
    """Apply safe SQLite-only schema upgrades for existing local databases."""
    engine = db.engine

    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "reports" not in inspector.get_table_names():
        return

    report_columns = {
        column["name"]
        for column in inspector.get_columns("reports")
    }

    with engine.begin() as connection:
        if "detection_status" not in report_columns:
            connection.execute(
                text(
                    "ALTER TABLE reports "
                    "ADD COLUMN detection_status VARCHAR(20) "
                    "NOT NULL DEFAULT 'pending'"
                )
            )
            connection.execute(
                text(
                    "UPDATE reports "
                    "SET detection_status = 'completed' "
                    "WHERE EXISTS ("
                    "SELECT 1 FROM detections "
                    "WHERE detections.report_id = reports.id"
                    ")"
                )
            )

        if "detection_error" not in report_columns:
            connection.execute(
                text(
                    "ALTER TABLE reports "
                    "ADD COLUMN detection_error VARCHAR(500)"
                )
            )
