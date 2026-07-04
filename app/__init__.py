from flask import Flask
from models import db
import config

def create_app():
    app = Flask(__name__, template_folder="../templates")
    
    # Load all settings from config.py
    app.config.from_object(config)
    
    # Connect the database to the app
    db.init_app(app)
    
    # Register the admin blueprint
    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp)
    
    return app