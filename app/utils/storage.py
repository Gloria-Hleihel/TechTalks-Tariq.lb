import os
import uuid
from werkzeug.utils import secure_filename
import config

# Read allowed extensions and upload folder from config.py (Zahraa base)
ALLOWED_EXT = set(getattr(config, "ALLOWED_EXTENSIONS", {"jpg", "jpeg", "png"}))
UPLOAD_FOLDER = getattr(config, "UPLOAD_FOLDER", "static/uploads")

def _is_allowed(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXT

def save_image(file) -> str:
    """
    Save uploaded Werkzeug FileStorage to UPLOAD_FOLDER using a UUID filename.
    Returns relative path (e.g., "static/uploads/<uuid>.jpg") on success, or empty string on failure.
    """
    filename = secure_filename(getattr(file, "filename", "") or "")
    if not _is_allowed(filename):
        return ""

    # Resolve upload directory to an absolute path
    if os.path.isabs(UPLOAD_FOLDER):
        upload_dir = UPLOAD_FOLDER
    else:
        upload_dir = os.path.join(os.getcwd(), UPLOAD_FOLDER)

    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)

    ext = filename.rsplit(".", 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(upload_dir, new_name)

    # Save file
    file.save(save_path)

    # Return path relative to project root usable by templates (forward slashes)
    rel_path = os.path.join(UPLOAD_FOLDER, new_name).replace("\\", "/")
    return rel_path
