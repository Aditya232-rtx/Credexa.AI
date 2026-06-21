from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

try:  # pragma: no cover - optional dependency fallback
    import spacy
except Exception:  # pragma: no cover
    spacy = None

try:  # pragma: no cover - optional dependency fallback
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover
    fuzz = None


try:
    nlp = spacy.load("en_core_web_sm") if spacy else None
except Exception:
    nlp = None


def extract_entities(text: str) -> Dict[str, List[str]]:
    if not text:
        return {"names": [], "dates": [], "orgs": [], "amounts": []}

    if nlp is None:
        amount_matches = re.findall(r"(?:₹|rs\.?|inr)?\s?[0-9][0-9,]*(?:\.[0-9]+)?", text, flags=re.I)
        return {"names": [], "dates": [], "orgs": [], "amounts": amount_matches[:10]}

    document = nlp(text[:100000])
    names, dates, orgs = set(), set(), set()
    for entity in document.ents:
        if entity.label_ == "PERSON":
            names.add(entity.text.strip())
        elif entity.label_ == "DATE":
            dates.add(entity.text.strip())
        elif entity.label_ == "ORG":
            orgs.add(entity.text.strip())

    amount_matches = re.findall(r"(?:₹|rs\.?|inr)?\s?[0-9][0-9,]*(?:\.[0-9]+)?", text, flags=re.I)
    
    dob_match = re.search(r"DOB:?\s*([\dA-Za-z-]+)", text, re.IGNORECASE)
    pan_match = re.search(r"PAN:?\s*([A-Z0-9]{10})", text, re.IGNORECASE)

    return {
        "names": sorted(names), 
        "dates": sorted(dates), 
        "orgs": sorted(orgs), 
        "amounts": amount_matches[:25],
        "dob": dob_match.group(1).strip() if dob_match else None,
        "pan": pan_match.group(1).strip() if pan_match else None
    }


def _fuzzy_score(left: str, right: str) -> int:
    if fuzz is not None:
        return int(fuzz.token_sort_ratio(left.lower(), right.lower()))
    return 100 if left.lower() == right.lower() else 0


def cross_check_documents(doc_entities_list: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    
    # 1. Fuzzy Name Matching
    docs_with_names = {}
    for item in doc_entities_list:
        names = item.get("entities", {}).get("names", []) or []
        if names:
            docs_with_names[item["doc_id"]] = names

    doc_ids = list(docs_with_names.keys())
    for left_index in range(len(doc_ids)):
        for right_index in range(left_index + 1, len(doc_ids)):
            left_doc = doc_ids[left_index]
            right_doc = doc_ids[right_index]
            for left_name in docs_with_names[left_doc]:
                for right_name in docs_with_names[right_doc]:
                    if len(left_name) < 5 or len(right_name) < 5:
                        continue
                    similarity = _fuzzy_score(left_name, right_name)
                    if 75 < similarity < 85: # Increased lower bound to reduce noise
                        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Name mismatch across documents: '{left_name}' vs '{right_name}' (Similarity: {similarity:.1f}%)", "severity": "medium", "score": int((100 - similarity) * 0.8)})

    # 2. Hard Identity Verification (DOB & PAN)
    dobs = set()
    pans = set()
    for item in doc_entities_list:
        dob = item.get("entities", {}).get("dob")
        if dob: dobs.add(dob.upper())
        pan = item.get("entities", {}).get("pan")
        if pan: pans.add(pan.upper())

    if len(dobs) > 1:
        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Identity Forgery: Mismatching Date of Birth detected: {', '.join(dobs)}", "severity": "high", "score": 95})

    if len(pans) > 1:
        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Identity Forgery: Mismatching PAN detected: {', '.join(pans)}", "severity": "high", "score": 95})

    unique_flags: List[Dict[str, Any]] = []
    seen = set()
    for flag in flags:
        if flag["finding"] in seen:
            continue
        seen.add(flag["finding"])
        unique_flags.append(flag)
    return unique_flags
