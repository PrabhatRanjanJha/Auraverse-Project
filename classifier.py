# classifier.py
import os
import shutil
from pathlib import Path

from content_labeler_impl import label_from_content
from video_predictor import label_from_video   # <-- CORRECT FUNCTION

# -----------------------------------------------------------
# CLASSIFY & ORGANIZE
# -----------------------------------------------------------

def classify_and_organize(path: str, base_dir: str = "categorized_data"):
    """
    Classifies any file (text, doc, pdf, video, image)
    Returns: (topic, file_type, new_path)
    """

    # extension without dot
    ext = Path(path).suffix.lower().replace(".", "")

    # --------------------------
    # Determine FILE TYPE GROUP
    # --------------------------
    if ext in {"txt", "pdf", "docx", "pptx", "csv", "md", "rtf", "html", "htm"}:
        file_type = "Documents"

        topic = label_from_content(path, ext)

    elif ext in {"jpg", "jpeg", "png", "bmp", "gif", "webp"}:
        file_type = "Images"

        # image predictor returns Imagenet class → OK for folder name
        from image_predictor import load_model, classify_image
        from PIL import Image

        model = load_model()
        img = Image.open(path).convert("RGB")
        preds = classify_image(model, img)

        if preds:
            topic = preds[0][1].lower().replace(" ", "_")
        else:
            topic = "unknown"

    elif ext in {"mp4", "avi", "mkv", "mov", "webm"}:
        file_type = "Videos"

        topic = label_from_video(path)    # <-- FIXED

    else:
        file_type = "Others"
        topic = "unknown"

    # Clean topic name
    topic = topic.strip().replace(" ", "_")
    topic = topic.replace("__", "_")
    topic = topic.lower()
    if not topic or topic == "":
        topic = "unknown"

    # ------------------------------------
    # FINAL SAVE PATH
    # categorized_data/topic/fileType/file
    # ------------------------------------
    topic_dir = os.path.join(base_dir, topic)
    type_dir = os.path.join(topic_dir, file_type)

    os.makedirs(type_dir, exist_ok=True)

    filename = Path(path).name
    new_path = os.path.join(type_dir, filename)

    # Prevent overwriting files with same name
    if os.path.exists(new_path):
        name, ext2 = os.path.splitext(filename)
        counter = 1
        while os.path.exists(new_path):
            new_path = os.path.join(type_dir, f"{name}_{counter}{ext2}")
            counter += 1

    shutil.move(path, new_path)

    return topic, file_type, new_path
