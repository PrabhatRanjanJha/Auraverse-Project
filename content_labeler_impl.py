"""
content_labeler_impl.py
-----------------------------------------------------------
TRUE semantic topic extraction using YAKE (offline).
No predefined labels. No rule-based keywords.

Process:
1. Extract text
2. Clean text
3. Use YAKE to extract top meaningful keywords
4. First keyword = topic
-----------------------------------------------------------
"""

from pathlib import Path
import re
import yake
from typing import Optional

# ------------------------------------------------------------
# EXTRACT TEXT FROM ANY DOCUMENT TYPE
# ------------------------------------------------------------
def extract_text(path: str, ext: str) -> str:
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

        elif ext in {"csv", "html", "htm", "md", "rtf"}:
            return Path(path).read_text(encoding="utf-8", errors="ignore")

    except Exception as e:
        print("[WARN] Failed to extract text:", e)

    return ""


# ------------------------------------------------------------
# CLEAN TEXT BEFORE KEYWORD EXTRACTION
# ------------------------------------------------------------
def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)  # normalize spaces
    return text.strip()


# ------------------------------------------------------------
# SEMANTIC TOPIC USING YAKE (OFFLINE)
# ------------------------------------------------------------
def infer_topic(text: str) -> str:
    text = clean_text(text)

    if len(text) < 20:
        return "unknown"

    # YAKE keyword extractor
    kw_extractor = yake.KeywordExtractor(
        lan="en",
        n=1,             # 1-word keywords (best for folder names)
        top=5,           # take 5 best keywords
        dedupLim=0.9
    )

    keywords = kw_extractor.extract_keywords(text)

    if not keywords:
        return "unknown"

    # keywords → list of (phrase, score)
    best_keyword = keywords[0][0]

    # cleanup
    best_keyword = best_keyword.lower().strip()
    best_keyword = re.sub(r"[^a-z0-9]+", "_", best_keyword).strip("_")

    return best_keyword or "unknown"


# ------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------
def label_from_content(path: str, file_type: Optional[str] = None) -> str:
    ext = (file_type or Path(path).suffix[1:]).lower()

    text = extract_text(path, ext)

    if text.strip():
        topic = infer_topic(text)
        return topic

    # fallback → filename
    name = Path(path).stem.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return name or "unknown"
