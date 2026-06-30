from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any, Dict, List, Sequence

from loguru import logger

ALLOWED_DOC_TYPES = frozenset({
    "bank_statement", "form_26as", "itr", "salary_slip",
    "balance_sheet", "profit_loss", "gst_return", "unknown",
})


FINANCIAL_DOC_TYPES = [
    "bank_statement", "form_26as", "itr", "salary_slip",
    "balance_sheet", "profit_loss", "gst_return", "unknown",
]


def _sanitize_text(text: str, max_len: int = 2000) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
    return cleaned[:max_len]


def _sanitize_doc_type(doc_type: str) -> str:
    return doc_type if doc_type in ALLOWED_DOC_TYPES else "unknown"


def _save_image_to_temp(image) -> str:
    try:
        from PIL import Image
        if not isinstance(image, Image.Image):
            try:
                image = Image.open(image)
            except Exception:
                return ""
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        image.convert("RGB").save(tmp, format="JPEG")
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"Failed to save image to temp: {e}")
        return ""


def _vlm_predict(
    image,
    text_prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.0,
) -> str:
    try:
        from services.sarvam_service import sarvam_chat, sarvam_vision_analyze

        if image is not None:
            img_path = _save_image_to_temp(image)
            if img_path:
                combined = f"{text_prompt}\n\n(Image saved as document for OCR analysis)"
                result = sarvam_vision_analyze(img_path, combined)
                try:
                    os.unlink(img_path)
                except Exception:
                    pass
                if result:
                    return result
        return sarvam_chat(text_prompt, max_tokens=max_new_tokens, temperature=temperature)
    except Exception as e:
        logger.warning(f"Sarvam VLM predict error: {e}")
        return ""


def classify_financial_doc(image, text: str = "") -> str:
    try:
        from services.sarvam_service import sarvam_classify_doc, sarvam_vision_analyze

        if image is not None and text:
            img_path = _save_image_to_temp(image)
            if img_path:
                result = sarvam_vision_analyze(img_path, f"Classify this document. Text: {text[:500]}")
                try:
                    os.unlink(img_path)
                except Exception:
                    pass
                for dt in FINANCIAL_DOC_TYPES:
                    if dt in result.lower():
                        return dt
        return sarvam_classify_doc(text) if text else "unknown"
    except Exception as e:
        logger.warning(f"Sarvam classify error: {e}")
        return "unknown"


def kv_extract(image, text: str = "", doc_type: str = "") -> Dict[str, Any]:
    try:
        from services.sarvam_service import sarvam_extract_kv

        if text:
            return sarvam_extract_kv(text, doc_type)
        if image is not None:
            img_path = _save_image_to_temp(image)
            if img_path:
                from services.sarvam_service import sarvam_extract_text
                extracted = sarvam_extract_text(img_path)
                try:
                    os.unlink(img_path)
                except Exception:
                    pass
                if extracted:
                    return sarvam_extract_kv(extracted, doc_type)
        return {}
    except Exception as e:
        logger.warning(f"Sarvam KV extract error: {e}")
        return {}


def generate_explanation_vlm(
    flags: Sequence[Dict[str, Any]],
    risk_score: int,
    status: str,
    case_id: str = "",
    docs: Sequence[Dict[str, Any]] | None = None,
) -> str:
    try:
        from services.sarvam_service import sarvam_explain
        return sarvam_explain(flags, risk_score, status, case_id, docs=docs)
    except Exception as e:
        logger.warning(f"Sarvam explain error: {e}")
        return ""


def extract_financials_vlm(text: str) -> dict:
    try:
        from services.sarvam_service import sarvam_extract_financials
        return sarvam_extract_financials(text)
    except Exception as e:
        logger.warning(f"Sarvam financials error: {e}")
        return {}
