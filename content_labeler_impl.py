"""
content_labeler_impl.py
--------------------------------------------------
Stable, dependency-free topic inference system.
No ML models required. No sentence-transformers.
Works 100% offline.

This classifier:
- Reads txt, pdf, docx, pptx, csv, md, html, rtf
- Extracts text
- Applies semantic keyword analysis
- Maps meaning → topic
--------------------------------------------------
"""

from pathlib import Path
import re

# ------------------------------------------------------------
# EXTRACT TEXT FROM FILES
# ------------------------------------------------------------
def extract_text(path, ext):
    try:
        if ext == "txt":
            return Path(path).read_text(encoding="utf-8", errors="ignore")

        elif ext == "pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in reader.pages)

        elif ext == "docx":
            import docx
            doc = docx.Document(path)
            return "\n".join(p.text for p in doc.paragraphs)

        elif ext == "pptx":
            from pptx import Presentation
            prs = Presentation(path)
            return "\n".join(
                shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")
            )

        elif ext in {"csv", "md", "html", "htm", "rtf"}:
            return Path(path).read_text(encoding="utf-8", errors="ignore")

    except Exception as e:
        print("[WARN] Extraction failed:", e)

    return ""


# ------------------------------------------------------------
# SEMANTIC TOPIC MAPS (RULE-BASED)
# ------------------------------------------------------------
SEMANTIC_MAP = {
    "dragon": [
        "scale", "scaly", "horn", "fire", "fire-breath", "wing", "wings",
        "myth", "mythical", "creature", "beast",
        "cave", "mountain lair", "lair",
        "giant", "tail",
    ],
    "animal": [
        "fur", "claw", "tail", "wild", "forest",
        "mammal", "predator", "hunt",
    ],
    "technology": [
        "software", "algorithm", "computer", "system",
        "data", "hardware", "ai", "machine", "network"
    ],
    "finance": [
        "money", "bank", "investment", "loan", "market", "trade", "stock"
    ],
    "medicine": [
        "health", "disease", "treatment", "patient", "clinical"
    ],
    "history": [
        "ancient", "king", "empire", "historic", "civilization"
    ]
}

STOPWORDS = {
    "the","and","for","with","that","this","from","have","were","which","their",
    "they","your","about","there","what","when","where","who","been","will",
    "could","should","also","these","those","each","many","some","more","such",
    "only","other","into","than","said","says","say","are","was","his","her","its",
    "you","their","them","she","he"
}


# ------------------------------------------------------------
# SEMANTIC TOPIC DETECTION (NO ML)
# ------------------------------------------------------------
def semantic_infer(text: str) -> str:
    text = text.lower()
    words = re.findall(r"[a-z]{3,}", text)

    if not words:
        return "unknown"

    words = [w for w in words if w not in STOPWORDS]

    # Count topic scores
    scores = {topic: 0 for topic in SEMANTIC_MAP}

    for word in words:
        for topic, keys in SEMANTIC_MAP.items():
            for key in keys:
                if key in word:
                    scores[topic] += 1

    # Pick the highest scoring topic
    best_topic = max(scores, key=lambda t: scores[t])

    if scores[best_topic] > 0:
        return best_topic

    # If no semantic match → fallback to strongest keyword
    from collections import Counter
    return Counter(words).most_common(1)[0][0]


# ------------------------------------------------------------
# FINAL ENTRY POINT
# ------------------------------------------------------------
def label_from_content(path: str, file_type=None) -> str:
    ext = (file_type or Path(path).suffix[1:]).lower()

    text = extract_text(path, ext)

    if text:
        topic = semantic_infer(text)
        return topic

    # fallback → filename
    name = Path(path).stem.lower()
    name = re.sub(r"[^a-z0-9]+", " ", name).strip()
    if not name:
        return "unknown"
    return name
