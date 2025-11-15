"""
video_predictor.py

Video -> single-word topic:
- sample frames
- caption frames with BLIP
- use sentence-transformers to get document embedding
- score candidate words and pick best single token

Dependencies:
    pip install transformers sentence-transformers pillow opencv-python
"""
from pathlib import Path
import re
from typing import List, Optional

# lazy placeholders
_BLIP_PROC = None
_BLIP_MODEL = None
_ST_MODEL = None
_util = None

_STOPWORDS = {
    "the","and","for","with","that","this","from","have","were","which","their",
    "they","your","about","there","what","when","where","who","been","will",
    "could","should","also","these","those","each","many","some","more","such",
    "only","other","into","than","then","said","says","say","are","was","his","her","its",
    "you","their","them","she","he","a","an","in","on","at","by","of","is","it"
}

def _ensure_blip():
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

def _sample_frames(video_path: str, max_frames: int = 12):
    import cv2
    from PIL import Image
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames = []
    if total <= 0:
        # read first frames
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

def _caption_frame(pil_img):
    if not _ensure_blip():
        return None
    try:
        proc, model = _BLIP_PROC, _BLIP_MODEL
        inputs = proc(images=pil_img, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=20)
        caption = proc.decode(out[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        print(f"[video_predictor] caption error: {e}")
        return None

def _extract_candidates(captions: List[str], min_len: int = 4) -> List[str]:
    text = " ".join(captions).lower()
    words = re.findall(r"[a-zA-Z]{%d,}" % min_len, text)
    unique = []
    seen = set()
    for w in words:
        if w in _STOPWORDS:
            continue
        if w in seen:
            continue
        seen.add(w)
        unique.append(w)
    return unique

def _choose_by_embedding(captions: List[str], candidates: List[str]) -> Optional[str]:
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
    except Exception as e:
        print(f"[video_predictor] embedding scoring failed: {e}")
        return None

def _choose_by_freq(captions: List[str]) -> Optional[str]:
    from collections import Counter
    words = re.findall(r"[a-zA-Z]{4,}", " ".join(captions).lower())
    words = [w for w in words if w not in _STOPWORDS]
    if not words:
        return None
    return Counter(words).most_common(1)[0][0]

def _clean_token(tok: str) -> str:
    if not tok:
        return "unknown"
    tok = tok.lower().strip()
    tok = re.sub(r"[^a-z0-9]+", "_", tok).strip("_")
    return tok or "unknown"

def label_from_video(path: str, max_frames: int = 12) -> str:
    frames = _sample_frames(path, max_frames)
    if not frames:
        return _clean_token(Path(path).stem)
    captions = []
    for pil in frames:
        c = _caption_frame(pil)
        if c:
            captions.append(c.strip())
    if not captions:
        return _clean_token(Path(path).stem)
    candidates = _extract_candidates(captions)
    best = None
    if candidates:
        best = _choose_by_embedding(captions, candidates)
    if not best:
        best = _choose_by_freq(captions)
    return _clean_token(best)
