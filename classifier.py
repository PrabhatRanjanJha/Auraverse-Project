"""
classifier.py

Simple MIME-based detector with audio-extension overrides.
We only use it to determine the file_type metadata; actual saved
files go to uploads/<username>/<uuid>.<ext> as you requested.
"""

import os
from pathlib import Path
import magic

AUDIO_EXT_OVERRIDES = {
    "m4a", "mp3", "wav", "aac", "flac", "ogg", "wma", "aiff", "alac"
}

def detect_filetype(path: str) -> str:
    """
    Return one of: Images, Videos, Audio, Documents, Others
    """
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    if ext in AUDIO_EXT_OVERRIDES:
        return "Audio"
    try:
        mime = magic.from_file(path, mime=True)  # e.g. "image/png"
    except Exception:
        mime = ""
    if not mime or "/" not in mime:
        return "Others"
    main = mime.split("/")[0]
    if main == "image":
        return "Images"
    if main == "video":
        return "Videos"
    if main == "audio":
        return "Audio"
    if main in ("text", "application"):
        return "Documents"
    return "Others"
