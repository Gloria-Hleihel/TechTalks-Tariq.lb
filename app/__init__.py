import os

from flask import Flask

import config
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

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True,
    )

    os.makedirs(
        app.config["ANNOTATED_FOLDER"],
        exist_ok=True,
    )

    db.init_app(app)

    # Register blueprints
    from app.reports import bp as reports_bp
    from app.detection.routes import detection_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(reports_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

    return app