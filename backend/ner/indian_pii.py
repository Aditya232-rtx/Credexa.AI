from __future__ import annotations

import re
from typing import Dict, List

from utils.model_registry import registry

_gliner_model = None


def _load_gliner_once():
    global _gliner_model
    if _gliner_model is not None and _gliner_model is not False:
        return _gliner_model
    try:
        from gliner import GLiNER
        _gliner_model = GLiNER.from_pretrained("VK1402/AADHAAR_Extractor")
        return _gliner_model
    except Exception:
        _gliner_model = False
    return None


def _get_gliner_model():
    return registry.get(
        key="gliner",
        loader=_load_gliner_once,
        size_gb=0.5,
        group="evictable",
    )


INDIAN_ENTITY_PATTERNS = {
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "aadhaar": r"\b[2-9][0-9]{11}\b",
    "aadhaar_masked": r"\b(?:\d{4}\s){2}\d{4}\b",
    "ifsc": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "gstin": r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z][0-9]{2}\b",
    "pin": r"\b[1-9][0-9]{5}\b",
    "voter_id": r"\b[A-Z]{3}[0-9]{7}\b",
    "dl": r"\b(?:[A-Z]{2}[0-9]{2}(?:19|20)[0-9]{7})\b",
    "passport": r"\b[A-Z][0-9]{7}\b",
    "udyam": r"\bUDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}\b",
}


def extract_with_gliner(text: str) -> Dict[str, List[str]]:
    model = _get_gliner_model()
    if model is None:
        return {}
    try:
        entities = model.predict_entities(text, labels=["Person Name", "PAN Number", "Aadhaar Number", "IFSC Code", "Bank Name"])
        result: Dict[str, List[str]] = {}
        for entity in entities:
            label = entity.get("label", "")
            text_val = entity.get("text", "").strip()
            if not text_val:
                continue
            key = label.lower().replace(" ", "_")
            if key not in result:
                result[key] = []
            result[key].append(text_val)
        return result
    except Exception:
        return {}


def extract_regex_entities(text: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for entity_type, pattern in INDIAN_ENTITY_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            result[entity_type] = list(set(matches))
    return result


def extract_indian_pii(text: str) -> Dict[str, List[str]]:
    if not text:
        return {}

    gliner_result = extract_with_gliner(text)
    regex_result = extract_regex_entities(text)

    combined: Dict[str, List[str]] = {}
    for key, values in gliner_result.items():
        combined[key] = list(set(values))

    for key, values in regex_result.items():
        if key in combined:
            seen = set(combined[key])
            for v in values:
                if v not in seen:
                    combined[key].append(v)
                    seen.add(v)
        else:
            combined[key] = values

    return combined
