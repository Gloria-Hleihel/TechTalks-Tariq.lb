import logging
import os

from flask import Flask, flash, jsonify, redirect, request, url_for
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

    return app
