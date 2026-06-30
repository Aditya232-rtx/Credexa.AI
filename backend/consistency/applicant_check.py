from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from loguru import logger


def _normalize(text: str) -> str:
    return " ".join(text.lower().split()).strip()


def _extract_pincode(text: str) -> str | None:
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else None


def _extract_city(text: str) -> str | None:
    known_cities = [
        "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai",
        "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "surat",
        "chandigarh", "bhopal", "indore", "nagpur", "patna", "thane",
        "agra", "varanasi", "noida", "gurgaon", "ghaziabad", "faridabad",
        "navi mumbai", "vasai-virar", "srinagar", "coimbatore", "kochi",
        "visakhapatnam", "vijayawada", "mysore", "guwahati", "ranchi",
        "raipur", "dehradun", "shimla", "gangtok", "itanagar", "dispur",
    ]
    lower = text.lower()
    for city in known_cities:
        if city in lower:
            return city
    return None


def _address_component_score(applicant_addr: str, doc_addr: str) -> Dict[str, Any]:
    app_norm = _normalize(applicant_addr)
    doc_norm = _normalize(doc_addr)

    app_pin = _extract_pincode(app_norm)
    doc_pin = _extract_pincode(doc_norm)

    app_city = _extract_city(app_norm)
    doc_city = _extract_city(doc_norm)

    pincode_match = app_pin and doc_pin and app_pin == doc_pin
    city_match = app_city and doc_city and app_city == doc_city

    # Token overlap for the rest (street, building, landmark)
    app_tokens = set(t for t in app_norm.replace(",", "").split() if t not in (app_pin or ""))
    doc_tokens = set(t for t in doc_norm.replace(",", "").split() if t not in (doc_pin or ""))
    # Remove city tokens from overlap check so landmarks don't matter as much
    if app_city:
        app_tokens.discard(app_city)
    if doc_city:
        doc_tokens.discard(doc_city)

    overlap = app_tokens & doc_tokens
    token_sim = len(overlap) / max(len(app_tokens | doc_tokens), 1)

    if pincode_match and city_match and token_sim > 0.3:
        return {"match": True, "severity": None, "details": "Address matches (pincode, city, and street details align)."}
    if pincode_match and city_match:
        return {"match": True, "severity": "low", "details": "Pincode and city match; minor wording differences in address details."}
    if pincode_match:
        return {"match": False, "severity": "medium", "details": "Pincode matches but city or locality differs — possible wrong address entry or relocated."}
    if city_match:
        return {"match": False, "severity": "medium", "details": "City matches but pincode differs — double-check the exact address."}

    # No pincode or city match in both
    if app_pin and doc_pin and app_pin != doc_pin:
        return {"match": False, "severity": "high", "details": f"Pincode mismatch: entered {app_pin}, document shows {doc_pin}."}
    if token_sim > 0.5:
        return {"match": True, "severity": "low", "details": "Partial address match; verify specific details manually."}
    return {"match": False, "severity": "medium", "details": "Address could not be reliably cross-checked — OCR may have missed details."}


def _name_match_score(applicant_name: str, doc_names: Sequence[str]) -> Dict[str, Any]:
    app_parts = _normalize(applicant_name).split()
    if not app_parts or not doc_names:
        return {"match": None, "severity": None, "details": "No name data available for comparison."}

    best = 0
    best_name = ""
    for doc_name in doc_names:
        doc_parts = _normalize(doc_name).split()
        if not doc_parts:
            continue
        # Check if all applicant name parts appear in doc name (middle name added case)
        app_in_doc = all(ap in doc_parts for ap in app_parts)
        doc_in_app = all(dp in app_parts for dp in doc_parts)
        if app_in_doc or doc_in_app:
            overlap = len(set(app_parts) & set(doc_parts))
            total = max(len(app_parts), len(doc_parts))
            score = overlap / total
            if score > best:
                best = score
                best_name = doc_name

    if best >= 0.8:
        return {"match": True, "severity": None, "details": f"Name matches: applicant '{applicant_name}' aligns with document name '{best_name}'."}
    if best >= 0.5:
        return {"match": True, "severity": "low", "details": f"Name partially matches: '{applicant_name}' vs '{best_name}' (e.g., middle name present in one). This is common and not a risk."}
    if best > 0:
        return {"match": False, "severity": "medium", "details": f"Name differs significantly: '{applicant_name}' vs '{best_name}'."}
    return {"match": False, "severity": "medium", "details": f"Name could not be matched: '{applicant_name}' does not match any name found in documents (e.g., '{doc_names[0]}')."}


def check_applicant_consistency(
    case_data: Dict[str, Any],
    doc_entities_list: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    applicant_name = case_data.get("applicant_name", "").strip()
    applicant_addr = case_data.get("address", "").strip()
    applicant_mobile = case_data.get("mobile_no", "").strip()

    if not applicant_name and not applicant_addr:
        return flags

    # Collect all extracted names, addresses from documents
    extracted_names: List[str] = []
    extracted_addresses: List[str] = []

    for item in doc_entities_list:
        entities = item.get("entities", {}) or {}
        names = entities.get("names", []) or []
        extracted_names.extend(names)
        indian_pii = entities.get("indian_pii", {}) or {}
        for pn in indian_pii.get("person_name", []):
            if pn and isinstance(pn, str):
                extracted_names.append(pn)
        addr = entities.get("address")
        if addr and len(addr) > 10:
            extracted_addresses.append(addr)

    if applicant_name and extracted_names:
        name_result = _name_match_score(applicant_name, extracted_names)
        if name_result.get("severity"):
            flags.append({
                "layer": "Applicant Data Check",
                "finding": name_result["details"],
                "severity": name_result["severity"],
                "score": 15 if name_result["severity"] == "medium" else 8,
            })

    if applicant_addr and extracted_addresses:
        for doc_addr in extracted_addresses:
            addr_result = _address_component_score(applicant_addr, doc_addr)
            if addr_result.get("severity"):
                flags.append({
                    "layer": "Applicant Data Check",
                    "finding": addr_result["details"],
                    "severity": addr_result["severity"],
                    "score": 20 if addr_result["severity"] == "high" else (15 if addr_result["severity"] == "medium" else 5),
                })

    return flags
