"""
classifier.py

Routes uploaded files to right predictor and organizes into:
categorized_data/<coarse_topic>/<fine_topic_or_filename>/<FileType>/filename

Returns:
    (coarse_topic, fine_topic, file_type, new_path)
"""
import os
import shutil
from pathlib import Path

from content_labeler_impl import label_from_content
from video_predictor import label_from_video
from image_predictor import load_model, classify_image, get_general_category
from PIL import Image

IMAGE_EXTS = {"jpg","jpeg","png","webp","bmp","gif","tiff"}
VIDEO_EXTS = {"mp4","mkv","avi","mov","webm","flv"}
DOC_EXTS = {"txt","pdf","doc","docx","rtf","md","html","htm","pptx","csv","xls","xlsx"}

def _safe_filename(name: str) -> str:
    name = name.lower().strip()
    name = "".join(c if c.isalnum() or c in (" ","_","-") else "_" for c in name)
    name = name.replace(" ", "_")
    return name or "unknown"

def classify_and_organize(src_path: str, base_dir: str = "categorized_data"):
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    p = Path(src_path)
    ext = p.suffix.lstrip(".").lower()
    file_type_folder = "Others"
    coarse = None
    fine = None

    try:
        if ext in IMAGE_EXTS:
            file_type_folder = "Images"
            model = load_model()
            img = Image.open(src_path).convert("RGB")
            fine_label, decoded = classify_image(model, img)  # fine label
            fine = _safe_filename(fine_label)
            coarse = _safe_filename(get_general_category(fine_label))

        elif ext in VIDEO_EXTS:
            file_type_folder = "Videos"
            topic = label_from_video(src_path)
            coarse = _safe_filename(topic)
            fine = coarse

        elif ext in DOC_EXTS:
            file_type_folder = "Documents"
            topic = label_from_content(src_path, ext)
            coarse = _safe_filename(topic)
            fine = coarse

        else:
            file_type_folder = "Others"
            coarse = _safe_filename(p.stem)
            fine = coarse

    except Exception as e:
        print(f"[classifier] error during classification: {e}")
        coarse = _safe_filename(p.stem)
        fine = coarse

    # Build destination: base_dir / coarse / fine / FileType / filename
    dest_dir = Path(base_dir) / coarse / fine / file_type_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    # avoid overwrite
    dest_path = dest_dir / p.name
    if dest_path.exists():
        name, extension = os.path.splitext(p.name)
        i = 1
        while (dest_dir / f"{name}_{i}{extension}").exists():
            i += 1
        dest_path = dest_dir / f"{name}_{i}{extension}"

    shutil.move(src_path, str(dest_path))

    return coarse, fine, file_type_folder, str(dest_path)
