import os
from flask import (
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from app.reports import bp
from app.utils.storage import save_image
from app.utils.exif import extract_gps

@bp.route("/")
def index():
    """Redirect root of blueprint to /upload route."""
    return redirect(url_for("reports.upload"))

@bp.route("/upload", methods=["GET"])
def upload():
    """
    Render the upload page.
    gps and saved_filename context values are optional and used to show results after POST.
    """
    return render_template("upload.html", gps=None, saved_filename=None)

@bp.route("/upload", methods=["POST"])
def upload_post():
    """
    POC POST handler:
    - Accept an uploaded image file
    - Save it using save_image(file) which uses UUID filenames
    - Run extract_gps(saved_abs_path) to try to get EXIF GPS
    - Render upload.html showing GPS result (if any) or prompting manual map pin
    NOTE: This is intentionally a Week 1 POC. It does NOT save Report/Detection records,
    does NOT invoke YOLO/detection API, and does NOT implement full report flow.
    """
    if "image" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(request.url)

    file = request.files.get("image")
    if not file or file.filename == "":
        flash("No selected file.", "error")
        return redirect(request.url)

    # Save image (returns relative path like "static/uploads/uuid.jpg" or empty string on failure)
    saved_rel_path = save_image(file)
    if not saved_rel_path:
        flash("Failed to save file. Allowed extensions: jpg, jpeg, png.", "error")
        return redirect(request.url)

    # Build absolute path to saved file
    saved_abs_path = os.path.join(current_app.root_path, saved_rel_path)

    # Try to extract GPS from EXIF
    gps = extract_gps(saved_abs_path)  # returns (lat, lng) or None

    if gps:
        lat, lng = gps
        flash(f"GPS found: {lat:.6f}, {lng:.6f}", "success")
        # Render upload page showing detected GPS and preview
        return render_template("upload.html", gps={"lat": lat, "lng": lng}, saved_filename=saved_rel_path)
    else:
        flash("No GPS found in image EXIF. Please select a location on the map.", "info")
        # Render upload page with saved file preview and prompt to manually select location
        return render_template("upload.html", gps=None, saved_filename=saved_rel_path)

# Week 2 placeholders (do NOT implement in Week 1):
# - POST /api/reports : persist Report to DB
# - Call detection service (e.g., POST /api/detect) and save Detection records
# - Redirect to report detail page
