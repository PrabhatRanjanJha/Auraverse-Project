# classifier.py
"""
classify_and_save(file, base_dir, file_id) -> saved_path (string)

Saves non-JSON files into: categorized_data/<FileType>/<file_id><ext>
FileType examples: Images, Videos, Audio, Documents, Others, JSON
Uses python-magic when available, otherwise falls back to mimetypes/extension heuristics.
"""
import os
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime

try:
    import magic
    _HAS_MAGIC = True
except Exception:
    _HAS_MAGIC = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg"}
DOC_EXTS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".md", ".csv", ".json"}

CATEGORIZED_ROOT = Path("categorized_data")


def _mime_to_folder(mime_type: str) -> str:
    if not mime_type:
        return "Others"
    main = mime_type.split("/")[0]
    if main == "image":
        return "Images"
    if main == "video":
        return "Videos"
    if main == "audio":
        return "Audio"
    # treat JSON specially (though JSON handled by backend separately)
    if mime_type in ("application/json", "text/json"):
        return "JSON"
    # documents
    return "Documents"


def detect_folder_from_bytes(b: bytes, filename: str = "") -> str:
    # try magic
    if _HAS_MAGIC and b:
        try:
            mime = magic.from_buffer(b, mime=True)
            return _mime_to_folder(mime)
        except Exception:
            pass

    # fallback to filename/mimetypes
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTS:
            return "Images"
        if ext in VIDEO_EXTS:
            return "Videos"
        if ext in AUDIO_EXTS:
            return "Audio"
        if ext in DOC_EXTS:
            return "Documents"
    # last fallback: check first bytes for textual content
    text_sample = b[:512].decode("utf-8", errors="ignore")
    # heuristics: contains %PDF or JFIF etc
    if b.startswith(b"%PDF"):
        return "Documents"
    if "JFIF" in text_sample or text_sample.startswith("\xff\xd8"):
        return "Images"
    # assume documents if text-like else others
    if any(c.isalpha() for c in text_sample):
        return "Documents"
    return "Others"


def classify_and_save(file, base_dir: str, file_id: str) -> str:
    """
    file: werkzeug FileStorage (Flask request.files['file'])
    base_dir is unused for final storage (kept for compatibility), files go to categorized_data/
    file_id: unique id for file (string)
    returns: absolute or relative path to saved file as str
    """
    CATEGORIZED_ROOT.mkdir(parents=True, exist_ok=True)

    orig_name = getattr(file, "filename", "") or "uploaded"
    safe_name = secure_filename(orig_name)
    ext = Path(safe_name).suffix.lower()

    # read a sample from the stream for detection, then reset stream if possible
    sample = b""
    stream = getattr(file, "stream", None)
    try:
        if stream is not None:
            try:
                pos = stream.tell()
            except Exception:
                pos = None
            sample = stream.read(8192) or b""
            try:
                if pos is not None:
                    stream.seek(pos)
                else:
                    stream.seek(0)
            except Exception:
                pass
        else:
            try:
                sample = file.read(8192) or b""
            except Exception:
                sample = b""
    except Exception:
        sample = b""

    # If extension indicates JSON, return JSON folder (but backend should route JSON earlier)
    if ext == ".json":
        folder = "JSON"
    else:
        folder = detect_folder_from_bytes(sample, safe_name)

    # Prepare directory and file name
    target_dir = CATEGORIZED_ROOT / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    final_ext = ext if ext else ""
    # if no extension but magic can guess mime -> try to guess extension
    if not final_ext and _HAS_MAGIC and sample:
        try:
            mime = magic.from_buffer(sample, mime=True)
            guess = mimetypes.guess_extension(mime) or ""
            final_ext = guess
        except Exception:
            final_ext = ""

    final_name = f"{file_id}{final_ext}"
    final_path = target_dir / final_name

    # Save file
    try:
        save_func = getattr(file, "save", None)
        if callable(save_func):
            file.save(str(final_path))
        else:
            # fallback: read bytes and write
            try:
                data = file.read()
            except Exception:
                data = sample
            if isinstance(data, str):
                data = data.encode("utf-8")
            with open(final_path, "wb") as fw:
                fw.write(data or b"")
    except Exception:
        # last resort: stream copy
        with open(final_path, "wb") as fw:
            if stream:
                try:
                    stream.seek(0)
                except Exception:
                    pass
                fw.write(stream.read())
            else:
                fw.write(sample or b"")

    return str(final_path)
