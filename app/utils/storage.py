import os
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

import config


def _setting(name, default):
    """Read from Flask config when available, otherwise from config.py."""
    try:
        return current_app.config.get(name, default)
    except RuntimeError:
        return getattr(config, name, default)


def allowed_file(filename: str) -> bool:
    """Return True if the file has an allowed image extension."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in _setting(
        "ALLOWED_EXTENSIONS",
        {"jpg", "jpeg", "png"},
    )


def get_file_size(file) -> int:
    """Return uploaded file size in bytes without consuming the file."""
    try:
        current_position = file.stream.tell()

        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()

        file.stream.seek(current_position)

        return size
    except (AttributeError, OSError):
        return 0


def delete_image(relative_path: str) -> None:
    """Delete a previously saved image, ignoring missing files."""
    if not relative_path:
        return

    upload_folder = _setting(
        "UPLOAD_FOLDER",
        os.path.join("static", "uploads"),
    )

    absolute_path = os.path.join(
        upload_folder,
        os.path.basename(relative_path),
    )

    try:
        os.remove(absolute_path)
    except FileNotFoundError:
        pass


def save_image(file) -> str:
    """
    Validate and save an uploaded image using a UUID filename.

    Returns a path relative to Flask's static folder:
        uploads/abc123.jpg
    """
    original_filename = secure_filename(
        getattr(file, "filename", "") or ""
    )

    if not allowed_file(original_filename):
        return ""

    upload_folder = _setting(
        "UPLOAD_FOLDER",
        os.path.join("static", "uploads"),
    )

    os.makedirs(upload_folder, exist_ok=True)

    extension = original_filename.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{extension}"

    absolute_path = os.path.join(
        upload_folder,
        new_filename,
    )

    file.save(absolute_path)

    # Check the real contents, not only the filename extension.
    try:
        with Image.open(absolute_path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        try:
            os.remove(absolute_path)
        except FileNotFoundError:
            pass

        return ""

    return f"uploads/{new_filename}"