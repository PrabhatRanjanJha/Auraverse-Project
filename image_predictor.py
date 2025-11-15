"""
image_predictor.py

- Loads MobileNetV2 (ImageNet) and returns fine-grained predictions.
- Uses NLTK WordNet to automatically compute a coarse parent category (hypernym).
- Exposes:
    load_model() -> model
    classify_image(model, PIL.Image) -> (fine_label, decoded_predictions)
    get_general_category(fine_label) -> coarse_label
Notes:
- One-time NLTK data install required: wordnet + omw-1.4
  Run (PowerShell):
    python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
"""
from PIL import Image
import numpy as np
import cv2
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
import nltk
from nltk.corpus import wordnet as wn
import os

# Ensure WordNet available (attempt auto-download if missing)
try:
    wn.synsets("dog")
except Exception:
    try:
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)
    except Exception:
        pass

_model_cache = None

def load_model():
    """Load MobileNetV2 (cached)."""
    global _model_cache
    if _model_cache is None:
        _model_cache = MobileNetV2(weights="imagenet")
    return _model_cache

def _preprocess_image_pil(image: Image.Image):
    # convert to rgb np array and resize
    arr = np.array(image.convert("RGB"))
    arr = cv2.resize(arr, (224, 224))
    arr = preprocess_input(arr)
    arr = np.expand_dims(arr, axis=0)
    return arr

def classify_image(model, image: Image.Image):
    """
    Returns:
        fine_label (str) e.g. "labrador_retriever"
        decoded (list) raw ImageNet decoded predictions (id, label, score)
    """
    try:
        x = _preprocess_image_pil(image)
        preds = model.predict(x)
        decoded = decode_predictions(preds, top=3)[0]
        # decoded entries look like: (id, label, score)
        fine_label = decoded[0][1]  # e.g. 'Labrador_retriever' or 'pug'
        fine_label = fine_label.replace(" ", "_").lower()
        return fine_label, decoded
    except Exception as e:
        print(f"[image_predictor] ERROR: {e}")
        return "unknown", None

def get_general_category(fine_label: str) -> str:
    """
    Derive a coarse category automatically via WordNet hypernyms.
    If WordNet lookup fails, fall back to simple heuristics (substring checks).
    """
    label = (fine_label or "").lower().replace(" ", "_")
    if not label:
        return "unknown"

    try:
        synsets = wn.synsets(label)
        if synsets:
            syn = synsets[0]
            hyper = syn.hypernyms()
            if hyper:
                parent = hyper[0].lemma_names()[0]
                return parent.replace("_", " ").lower()
    except Exception:
        pass

    # Fallback heuristics (safe, not manual mapping)
    if any(k in label for k in ["dog", "terrier", "retriever", "hound", "pug", "chihuahua", "shepherd"]):
        return "dog"
    if "cat" in label:
        return "cat"
    if any(k in label for k in ["bird", "eagle", "parrot", "owl", "macaw"]):
        return "bird"
    if any(k in label for k in ["car", "sports_car", "convertible", "cab"]):
        return "car"
    if any(k in label for k in ["plane", "airliner", "warplane"]):
        return "airplane"
    # default return original fine label as coarse fallback
    return label
