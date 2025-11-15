"""
classifier.py - MIME + extension-based fixes
"""

import os
import shutil
import magic
from pathlib import Path


# Extensions that should ALWAYS be treated as audio
AUDIO_EXT_OVERRIDES = {
    "m4a", "mp3", "wav", "aac", "flac", "ogg", "wma", "aiff", "alac"
}


def detect_filetype(path: str) -> str:
    """
    Detect category using MIME type via python-magic,
    with overrides for extensions that libmagic misidentifies.
    """
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")

    # ----------------------------------
    # 1. EXTENSION OVERRIDE FOR AUDIO
    # ----------------------------------
    if ext in AUDIO_EXT_OVERRIDES:
        return "Audio"

    # ----------------------------------
    # 2. MIME-BASED DETECTION
    # ----------------------------------
    mime = magic.from_file(path, mime=True)  # e.g. video/mp4, audio/mpeg, image/png
    mime_main = mime.split("/")[0]

    if mime_main == "image":
        return "Images"
    if mime_main == "video":
        return "Videos"
    if mime_main == "audio":
        return "Audio"
    if mime_main == "text":
        return "Documents"
    if mime_main == "application":
        return "Documents"

    return "Others"


def classify_and_organize(src_path: str, base_dir: str = "categorized_data"):
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    p = Path(src_path)
    file_type_folder = detect_filetype(src_path)

    dest_dir = Path(base_dir) / file_type_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / p.name
    if dest_path.exists():
        name, extension = os.path.splitext(p.name)
        i = 1
        while (dest_dir / f"{name}_{i}{extension}").exists():
            i += 1
        dest_path = dest_dir / f"{name}_{i}{extension}"

    shutil.move(src_path, str(dest_path))

    return None, None, file_type_folder, str(dest_path)
