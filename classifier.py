"""
classifier.py
MIME + extension-based classifier
"""

import os
import shutil
import magic
from pathlib import Path

AUDIO_EXT_OVERRIDES = {
    "m4a", "mp3", "wav", "aac", "flac", "ogg", "wma", "aiff", "alac"
}

def detect_filetype(path: str) -> str:
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    if ext in AUDIO_EXT_OVERRIDES:
        return "Audio"

    try:
        mime = magic.from_file(path, mime=True)
    except:
        return "Others"

    if not mime or "/" not in mime:
        return "Others"

    mime_main = mime.split("/")[0]

    if mime_main == "image":
        return "Images"
    if mime_main == "video":
        return "Videos"
    if mime_main == "audio":
        return "Audio"
    if mime_main in ("text", "application"):
        return "Documents"

    return "Others"


def classify_and_organize(src_path: str, base_dir: str = "categorized_data", uid: str = None):
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    p = Path(src_path)
    category = detect_filetype(src_path)

    dest_dir = Path(base_dir) / category
    dest_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{uid}_" if uid else ""
    dest_name = prefix + p.name
    dest_path = dest_dir / dest_name

    shutil.move(src_path, str(dest_path))

    return category, str(dest_path)
