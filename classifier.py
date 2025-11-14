import os
import shutil
import mimetypes
import re
from content_labeler_impl import label_from_content

__all__ = ["classify_and_organize"]

IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "heic"}
VIDEO_EXTS = {"mp4", "mkv", "avi", "mov", "webm", "flv"}
AUDIO_EXTS = {"mp3", "wav", "m4a", "flac", "aac", "ogg"}
DOC_EXTS = {"pdf", "doc", "docx", "txt", "rtf", "odt", "md", "html", "htm"}
ARCHIVE_EXTS = {"zip", "tar", "gz", "tgz", "bz2", "rar", "7z"}
SHEET_EXTS = {"xls", "xlsx", "csv"}
PRESENTATION_EXTS = {"ppt", "pptx"}
CODE_EXTS = {"py", "js", "java", "c", "cpp", "cs", "rb", "go", "rs", "ts"}

def _read_start_bytes(path, n=16):
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except Exception:
        return b""

def _detect_by_magic(path):
    b = _read_start_bytes(path, 16)
    if not b:
        return None
    if b.startswith(b"%PDF"):
        return "pdf"
    if b.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if b.startswith(b"\x89PNG"):
        return "png"
    if b.startswith(b"GIF8"):
        return "gif"
    if b[4:8] == b"ftyp":
        return "mp4"
    if b.startswith(b"PK\x03\x04"):
        return "zip"
    return None

def _safe_move(src, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.basename(src)
    dest = os.path.join(dest_dir, base)
    name, ext = os.path.splitext(base)
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(dest_dir, f"{name}_{counter}{ext}")
        counter += 1
    shutil.move(src, dest)
    return dest

def classify_and_organize(src_path: str, base_dir: str = "categorized_data"):
    """
    Classify a file by content topic first, then by file type, and move it into:
    <base_dir>/<topic>/<FileType>/filename
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    _, fname = os.path.split(src_path)
    ext = os.path.splitext(fname)[1].lower().lstrip(".")

    magic = _detect_by_magic(src_path)
    if magic and (not ext or magic != ext):
        ext = magic

    # Determine category for FileType folder
    category = "Others"
    if ext in IMAGE_EXTS:
        category = "Images"
    elif ext in VIDEO_EXTS:
        category = "Videos"
    elif ext in AUDIO_EXTS:
        category = "Audio"
    elif ext in DOC_EXTS:
        category = "Documents"
    elif ext in SHEET_EXTS:
        category = "Spreadsheets"
    elif ext in PRESENTATION_EXTS:
        category = "Presentations"
    elif ext in CODE_EXTS:
        category = "Code"
    elif ext in ARCHIVE_EXTS:
        category = "Archives"
    else:
        mime, _ = mimetypes.guess_type(src_path)
        if mime:
            if mime.startswith("image"): category = "Images"
            elif mime.startswith("video"): category = "Videos"
            elif mime.startswith("audio"): category = "Audio"
            elif mime == "application/pdf": category = "Documents"

    file_type = ext or "unknown"

    # Attempt semantic content labeling
    try:
        content_label = label_from_content(src_path, file_type)
    except Exception as e:
        print(f"[classifier] content labeler failed: {e}")
        content_label = None

    # fallback: filename-based token
    if not content_label:
        name_no_ext = os.path.splitext(fname)[0]
        toks = [t for t in re.split(r"[^A-Za-z0-9]+", name_no_ext.lower()) if t]
        generic = {"image","img","photo","picture","file","document","test"}
        for t in toks:
            if t not in generic:
                content_label = t
                break
        if not content_label:
            content_label = category.lower()

    # final structure: categorized_data/topic/category/filename
    dest_dir = os.path.join(base_dir, content_label, category)
    new_path = _safe_move(src_path, dest_dir)
    return content_label, file_type, new_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(classify_and_organize(sys.argv[1]))
    else:
        print("Usage: python classifier.py <path>")
