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
    from sentence_transformers import SentenceTransformer, util
    semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    semantic_model = None

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

    # Address extraction — look for pincode patterns and surrounding lines
    address_lines = []
    pincode_match = re.search(r"\b(\d{6})\b", text)
    if pincode_match:
        # Grab up to 100 chars around the pincode as the address context
        start = max(0, pincode_match.start() - 100)
        end = min(len(text), pincode_match.end() + 20)
        address_lines.append(text[start:end].replace("\n", " ").strip())

    # Income extraction — look for declared income / total income / gross salary
    income_match = re.search(
        r"(?:total\s+income|gross\s+total\s+income|gross\s+salary|annual\s+income|net\s+salary)[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        text, re.IGNORECASE
    )
    declared_income = None
    if income_match:
        try:
            declared_income = float(income_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Bank statement total credits
    credits_match = re.search(
        r"total\s+credits?[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        text, re.IGNORECASE
    )
    total_credits = None
    if credits_match:
        try:
            total_credits = float(credits_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "names": sorted(names), 
        "dates": sorted(dates), 
        "orgs": sorted(orgs), 
        "amounts": amount_matches[:25],
        "dob": dob_match.group(1).strip() if dob_match else None,
        "pan": pan_match.group(1).strip() if pan_match else None,
        "address": address_lines[0] if address_lines else None,
        "declared_income": declared_income,
        "total_credits": total_credits,
    }


def _semantic_score(left: str, right: str) -> int:
    if semantic_model:
        emb1 = semantic_model.encode(left.lower(), convert_to_tensor=True)
        emb2 = semantic_model.encode(right.lower(), convert_to_tensor=True)
        cosine_scores = util.cos_sim(emb1, emb2)
        return int(cosine_scores[0][0].item() * 100)
    elif fuzz is not None:
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
                    similarity = _semantic_score(left_name, right_name)
                    if 75 < similarity < 85: # Increased lower bound to reduce noise
                        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Name mismatch across documents: '{left_name}' vs '{right_name}' (Semantic Similarity: {similarity:.1f}%)", "severity": "medium", "score": int((100 - similarity) * 0.8)})

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

    # 3. Address Fuzzy Matching
    addresses = {}
    for item in doc_entities_list:
        addr = item.get("entities", {}).get("address")
        if addr and len(addr) > 10:
            addresses[item["doc_id"]] = addr

    addr_doc_ids = list(addresses.keys())
    for i in range(len(addr_doc_ids)):
        for j in range(i + 1, len(addr_doc_ids)):
            addr_a = addresses[addr_doc_ids[i]]
            addr_b = addresses[addr_doc_ids[j]]
            sim = _semantic_score(addr_a, addr_b)
            if sim < 70:
                flags.append({
                    "layer": "Cross-Doc Consistency",
                    "finding": f"Address mismatch across documents (similarity {sim}%): '{addr_a[:60]}...' vs '{addr_b[:60]}...'",
                    "severity": "medium" if sim > 50 else "high",
                    "score": int((100 - sim) * 0.7),
                })

    # 4. Income vs Bank Credits Cross-Check
    declared_incomes = []
    total_credits_list = []
    for item in doc_entities_list:
        inc = item.get("entities", {}).get("declared_income")
        if inc:
            declared_incomes.append(inc)
        crd = item.get("entities", {}).get("total_credits")
        if crd:
            total_credits_list.append(crd)

    if declared_incomes and total_credits_list:
        avg_income = sum(declared_incomes) / len(declared_incomes)
        avg_credits = sum(total_credits_list) / len(total_credits_list)
        if avg_income > 0:
            ratio = abs(avg_credits - avg_income) / avg_income
            if ratio > 0.25:
                flags.append({
                    "layer": "Cross-Doc Consistency",
                    "finding": f"Income vs Bank Credits discrepancy: Declared income ₹{avg_income:,.0f} but bank statement credits ₹{avg_credits:,.0f} (difference {ratio*100:.0f}%).",
                    "severity": "high",
                    "score": 75,
                })

    unique_flags: List[Dict[str, Any]] = []
    seen = set()
    for flag in flags:
        if flag["finding"] in seen:
            continue
        seen.add(flag["finding"])
        unique_flags.append(flag)
    return unique_flags
