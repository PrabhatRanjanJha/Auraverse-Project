"""
video_predictor.py

Universal single-word topic extraction for videos.

Pipeline:
1. Sample evenly spaced frames
2. Caption frames with BLIP (Salesforce/blip-image-captioning-base)
3. Combine captions into a document embedding (all-MiniLM-L6-v2)
4. Generate candidate words from captions (filtered)
5. Score candidate words by cosine similarity to the document embedding
6. Return the highest-scoring single-word topic (cleaned)

Works for ANY video:
- animals
- vehicles
- people
- buildings
- scenery
- fantasy creatures (dragon, griffin, etc.)
"""

from pathlib import Path
import re
from typing import List, Optional

# Lazy-loaded model placeholders
_BLIP_PROC = None
_BLIP_MODEL = None
_ST_MODEL = None
_util = None

# Lightweight stopwords
_STOPWORDS = {
    "the","and","for","with","that","this","from","have","were","which","their",
    "they","your","about","there","what","when","where","who","been","will",
    "could","should","also","these","those","each","many","some","more","such",
    "only","other","into","than","then","said","says","say","are","was","his","her","its",
    "you","their","them","she","he","a","an","in","on","at","by","of","is","it"
}

# ------------------------------------------------------------
# Lazy loaders
# ------------------------------------------------------------
def _ensure_blip():
    """Loads BLIP image captioning model only when needed."""
    global _BLIP_PROC, _BLIP_MODEL
    if _BLIP_PROC is not None and _BLIP_MODEL is not None:
        return True
    try:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        _BLIP_PROC = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _BLIP_MODEL = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        return True
    except Exception as e:
        print(f"[video_predictor] BLIP unavailable: {e}")
        return False


def _ensure_st():
    """Loads Sentence-Transformer model only when needed."""
    global _ST_MODEL, _util
    if _ST_MODEL is not None and _util is not None:
        return True
    try:
        from sentence_transformers import SentenceTransformer, util
        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        _util = util
        return True
    except Exception as e:
        print(f"[video_predictor] sentence-transformers unavailable: {e}")
        return False


# ------------------------------------------------------------
# Video frame extraction
# ------------------------------------------------------------
def _sample_frames(video_path: str, max_frames: int = 12):
    """Extract evenly spaced frames from a video."""
    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames = []

    if total <= 0:
        # fallback: first frames
        for _ in range(max_frames):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(Image.fromarray(frame[:, :, ::-1]))
        cap.release()
        return frames

    step = max(1, total // max_frames)
    idx = 0

    while len(frames) < max_frames and idx < total:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(Image.fromarray(frame[:, :, ::-1]))
        idx += step

    cap.release()
    return frames


# ------------------------------------------------------------
# Caption a frame using BLIP
# ------------------------------------------------------------
def _caption_image_pil(pil_img):
    if not _ensure_blip():
        return None
    try:
        proc, model = _BLIP_PROC, _BLIP_MODEL
        inputs = proc(images=pil_img, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=20)
        return proc.decode(out[0], skip_special_tokens=True)
    except Exception:
        return None


# ------------------------------------------------------------
# Extract candidate words
# ------------------------------------------------------------
def _extract_candidates_from_captions(captions: List[str], min_len: int = 4) -> List[str]:
    text = " ".join(captions).lower()
    words = re.findall(r"[a-zA-Z]{%d,}" % min_len, text)

    unique = []
    seen = set()

    for w in words:
        w = w.lower()
        if w in _STOPWORDS:
            continue
        if w in seen:
            continue
        seen.add(w)
        unique.append(w)

    return unique


# ------------------------------------------------------------
# Score candidates by semantic similarity
# ------------------------------------------------------------
def _choose_best_candidate_by_embedding(captions: List[str], candidates: List[str]):
    if not candidates:
        return None
    if not _ensure_st():
        return None

    try:
        doc_text = " ".join(captions)
        doc_emb = _ST_MODEL.encode([doc_text], convert_to_tensor=True)[0]
        cand_embs = _ST_MODEL.encode(candidates, convert_to_tensor=True)

        sims = _util.cos_sim(doc_emb, cand_embs)[0]
        import torch
        best_idx = int(torch.argmax(sims).item())
        return candidates[best_idx]
    except Exception:
        return None


# ------------------------------------------------------------
# Fallback: simple frequency
# ------------------------------------------------------------
def _choose_by_frequency(captions: List[str]):
    from collections import Counter
    words = re.findall(r"[a-zA-Z]{4,}", " ".join(captions).lower())
    words = [w for w in words if w not in _STOPWORDS]
    if not words:
        return None
    return Counter(words).most_common(1)[0][0]


# ------------------------------------------------------------
# Final topic cleaning
# ------------------------------------------------------------
def _clean_token(tok: str):
    tok = tok.lower().strip()
    tok = re.sub(r"[^a-z0-9]+", "_", tok).strip("_")
    return tok if tok else "unknown"


# ------------------------------------------------------------
# PUBLIC ENTRY POINT
# ------------------------------------------------------------
def label_from_video(path: str, max_frames: int = 12) -> str:
    """Main function. Returns single clean topic word."""

    frames = _sample_frames(path, max_frames)
    if not frames:
        return _clean_token(Path(path).stem)

    captions = []
    for img in frames:
        cap = _caption_image_pil(img)
        if cap:
            captions.append(cap.strip())

    if not captions:
        return _clean_token(Path(path).stem)

    candidates = _extract_candidates_from_captions(captions)

    best = None
    if candidates:
        best = _choose_best_candidate_by_embedding(captions, candidates)

    if not best:
        best = _choose_by_frequency(captions)

    return _clean_token(best or Path(path).stem)
