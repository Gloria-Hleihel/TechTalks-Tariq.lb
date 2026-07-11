import os
import uuid

from werkzeug.utils import secure_filename

import config


def allowed_file(filename: str) -> bool:
    """Return True if the file has an allowed image extension."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in getattr(config, "ALLOWED_EXTENSIONS", {"jpg", "jpeg", "png"})


def get_file_size(file) -> int:
    """Return uploaded file size in bytes without consuming the file."""
    try:
        current_position = file.stream.tell()
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(current_position)
        return size
    except Exception:
        return 0


def save_image(file) -> str:
    """
    Save uploaded image using a UUID filename.

    Returns a path relative to the Flask static folder, for example:
        uploads/abc123.jpg

    This path is stored in Report.image_path and used with:
        url_for("static", filename=image_path)
    """
    original_filename = secure_filename(getattr(file, "filename", "") or "")

    if not allowed_file(original_filename):
        return ""

    upload_folder = getattr(config, "UPLOAD_FOLDER", os.path.join("static", "uploads"))
    os.makedirs(upload_folder, exist_ok=True)

    extension = original_filename.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{extension}"

    absolute_path = os.path.join(upload_folder, new_filename)
    file.save(absolute_path)

    return f"uploads/{new_filename}"