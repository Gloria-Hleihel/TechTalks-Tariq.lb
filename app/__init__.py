from flask import Flask
from models import db  # use Zahraa's models.py as source of truth
import config

def create_app():
    """
    App factory for Tariq.lb (Malek Week 1 POC).
    Initializes Flask, loads config.py, initializes SQLAlchemy (db from models.py),
    and registers the reports blueprint.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    # Load configuration from Zahraa's config.py
    app.config.from_object(config)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp)

    # Placeholders for future blueprint registration (Week 2)
    # from app.detect import bp as detect_bp
    # app.register_blueprint(detect_bp, url_prefix="/detect")
    # from app.map import bp as map_bp
    # app.register_blueprint(map_bp, url_prefix="/map")
    # from app.admin import bp as admin_bp
    # app.register_blueprint(admin_bp, url_prefix="/admin")

    return app
