"""
image_predictor.py
--------------------------------------------------------
Used for two things:
1. As a backend module imported by classifier.py for
   automated topic detection from images.

2. As a standalone Streamlit app when run directly:
       python image_predictor.py

IMPORTANT:
The Streamlit UI runs ONLY when __name__ == "__main__".
So importing this file in classifier.py will NOT launch UI.
--------------------------------------------------------
"""

import cv2
import numpy as np
from tensorflow.keras.applications.mobilenet_v2 import (
    MobileNetV2,
    preprocess_input,
    decode_predictions,
)
from PIL import Image
import os

# ------------------------------------------------------------
# GLOBAL MODEL CACHE
# ------------------------------------------------------------
_model_cache = None


def load_model():
    """Load MobileNetV2 (cached)."""
    global _model_cache
    if _model_cache is None:
        _model_cache = MobileNetV2(weights="imagenet")
    return _model_cache


def preprocess_image(image):
    """Resize → preprocess → prepare for MobileNet."""
    img = np.array(image)
    img = cv2.resize(img, (224, 224))
    img = preprocess_input(img)
    img = np.expand_dims(img, axis=0)
    return img


def classify_image(model, image):
    """
    Returns ImageNet top-3 predictions:
    [(id, label, score), ...]
    """
    try:
        processed = preprocess_image(image)
        preds = model.predict(processed)
        decoded = decode_predictions(preds, top=3)[0]
        return decoded
    except Exception as e:
        print(f"[image_predictor] ERROR: {e}")
        return None


# ====================================================================
# STREAMLIT UI (RUNS ONLY WHEN FILE IS EXECUTED DIRECTLY)
# ====================================================================

def run_streamlit_app():
    import streamlit as st
    import requests, io
    from dotenv import load_dotenv

    load_dotenv()

    st.set_page_config(page_title="AI Image Classifier")
    st.title("AI Image Classifier")
    st.write("Upload an image and let AI tell you what is in it!")

    PEXELS_API_KEY = os.getenv("Pexels_API_Key")
    PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}

    @st.cache_resource
    def load_cached_model():
        return load_model()

    model = load_cached_model()

    uploaded = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded:
        st.image(uploaded, caption="Uploaded image", use_container_width=True)

        if st.button("Classify Image"):
            with st.spinner("Processing..."):
                img = Image.open(uploaded)
                preds = classify_image(model, img)

                if preds:
                    st.subheader("Predictions")
                    for _, label, score in preds:
                        st.write(f"**{label}** — {score:.2%}")

                    # Optional Pexels search
                    def pexels_search(query):
                        if not PEXELS_API_KEY:
                            return None
                        try:
                            url = "https://api.pexels.com/v1/search"
                            r = requests.get(
                                url,
                                headers=PEXELS_HEADERS,
                                params={"query": query, "per_page": 1},
                            )
                            data = r.json()
                            if "photos" in data and data["photos"]:
                                img_url = data["photos"][0]["src"]["medium"]
                                r2 = requests.get(img_url)
                                return Ima
                        except:
                            pass