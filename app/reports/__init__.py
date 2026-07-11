from flask import Blueprint

bp = Blueprint("reports", __name__)

# Import routes to register them with the blueprint
from app.reports import routes  # noqa: E402,F401
