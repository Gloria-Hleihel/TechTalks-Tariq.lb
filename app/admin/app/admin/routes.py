from flask import Blueprint, render_template, request, redirect, url_for, session
import config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        else:
            error = "Invalid credentials"
    
    return render_template("admin/login.html", error=error)

@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))
