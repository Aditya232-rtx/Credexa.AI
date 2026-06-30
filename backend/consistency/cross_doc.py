"""Cross-document consistency checks (ITR vs 26AS, income vs credits, entity extraction).

Note: Entity extraction and textual analysis are optimized for Latin-script content.
Documents primarily in Devanagari or other non-Latin scripts may have reduced
accuracy and should be reviewed manually.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Sequence

from utils.model_registry import registry

try:
    import spacy
except Exception:
    spacy = None

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

try:
    from text_unidecode import unidecode as _unidecode
except Exception:
    try:
        from unidecode import unidecode as _unidecode
    except Exception:
        _unidecode = None


_semantic_model = None
_nlp = None
_ner_module = None


def _load_semantic_model_once():
    global _semantic_model
    if _semantic_model is not None:
        return _semantic_model
    model_name = 'all-MiniLM-L6-v2'
    model_cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2"
    if not model_cache.exists():
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _semantic_model = SentenceTransformer(model_name)
        return _semantic_model
    except Exception:
        return None


def _get_semantic_model():
    return registry.get(
        key="sentence_transformer",
        loader=_load_semantic_model_once,
        size_gb=0.09,
        group="pinned",
    )


def _get_indic_semantic_model():
    model_cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--l3cube-pune--indic-sentence-similarity-sbert"
    if not model_cache.exists():
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer('l3cube-pune/indic-sentence-similarity-sbert')
    except Exception:
        return None


def _load_nlp_once():
    global _nlp
    if _nlp is not None and _nlp is not False:
        return _nlp if _nlp is not False else None
    if spacy:
        try:
            nlp_model = spacy.load("en_core_web_sm")
            try:
                from ner.indian_ner_spacy import add_entity_ruler
                add_entity_ruler(nlp_model)
            except Exception:
                pass
            _nlp = nlp_model
            return nlp_model
        except Exception:
            _nlp = False
    else:
        _nlp = False
    return None


def _get_nlp():
    return registry.get(
        key="spacy_nlp",
        loader=_load_nlp_once,
        size_gb=0.05,
        group="pinned",
    )


def _get_indian_ner():
    global _ner_module
    if _ner_module is not None and _ner_module is not False:
        return _ner_module
    # Only load GLiNER if already cached locally (avoid 834MB download)
    gliner_cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--VK1402--AADHAAR_Extractor"
    if not gliner_cache.exists():
        _ner_module = False
        return None
    try:
        from ner.indian_pii import extract_indian_pii
        _ner_module = extract_indian_pii
    except Exception:
        _ner_module = False
    return _ner_module if _ner_module is not False else None


def _phonetic_normalize(text: str) -> str:
    if _unidecode is not None:
        return _unidecode(text).lower().strip()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower().strip()


def _phonetic_score(left: str, right: str) -> int:
    left_norm = _phonetic_normalize(left)
    right_norm = _phonetic_normalize(right)
    if not left_norm or not right_norm:
        return 0
    if fuzz is not None:
        return int(fuzz.token_sort_ratio(left_norm, right_norm))
    return 100 if left_norm == right_norm else 0


def extract_entities(text: str) -> Dict[str, Any]:
    if not text:
        return {"names": [], "dates": [], "orgs": [], "amounts": []}

    nlp = _get_nlp()

    names: set = set()
    dates: set = set()
    orgs: set = set()

    truncate_at = 100000
    if len(text) > truncate_at:
        text = text[:truncate_at].rsplit(' ', 1)[0]

    if nlp is not None:
        document = nlp(text)
        for entity in document.ents:
            if entity.label_ == "PERSON":
                names.add(entity.text.strip())
            elif entity.label_ == "DATE":
                dates.add(entity.text.strip())
            elif entity.label_ == "ORG":
                orgs.add(entity.text.strip())

    # Regex fallback for English names in Indian ID documents
    # (catches patterns like "Aditya Sandeep Jadhay" that spaCy may miss in mixed-script text)
    name_matches = re.findall(r"[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", text)
    for match in name_matches:
        parts = match.split()
        if len(parts) >= 2 and not any(w in match.lower() for w in ["mobile", "number", "no"]):
            names.add(match.strip())

    amount_matches = re.findall(r"(?:₹|rs\.?|inr)?\s?[0-9][0-9,]*(?:\.[0-9]+)?", text, flags=re.I)

    dob_match = re.search(r"DOB:?\s*([\dA-Za-z-]+)", text, re.IGNORECASE)
    pan_match = re.search(r"PAN:?\s*([A-Z0-9]{10})", text, re.IGNORECASE)

    address_lines = []
    pincode_matches = list(re.finditer(r"\b(\d{6})\b", text))
    for pincode_match in pincode_matches[:3]:
        start = max(0, pincode_match.start() - 150)
        end = min(len(text), pincode_match.end() + 50)
        context = text[start:end].replace("\n", " ").strip()
        if len(context) > 10:
            address_lines.append(context)

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

    indian_pii = {}
    try:
        indian_ner_fn = _get_indian_ner()
        if indian_ner_fn:
            indian_pii = indian_ner_fn(text)
    except Exception:
        pass

    raw_address = address_lines[0] if address_lines else None
    if raw_address:
        try:
            from ner.indian_ner_spacy import normalize_address_cities
            raw_address = normalize_address_cities(raw_address)
        except Exception:
            pass

    return {
        "names": sorted(names),
        "dates": sorted(dates),
        "orgs": sorted(orgs),
        "amounts": amount_matches[:25],
        "dob": dob_match.group(1).strip() if dob_match else None,
        "pan": pan_match.group(1).strip() if pan_match else None,
        "address": raw_address,
        "declared_income": declared_income,
        "total_credits": total_credits,
        "indian_pii": indian_pii,
    }


def _semantic_score(left: str, right: str) -> int:
    semantic_model = _get_semantic_model()
    if semantic_model:
        emb1 = semantic_model.encode(left.lower(), convert_to_tensor=True)
        emb2 = semantic_model.encode(right.lower(), convert_to_tensor=True)
        from sentence_transformers import util
        cosine_scores = util.cos_sim(emb1, emb2)
        return int(cosine_scores[0][0].item() * 100)
    elif fuzz is not None:
        return int(fuzz.token_sort_ratio(left.lower(), right.lower()))
    return 100 if left.lower() == right.lower() else 0


def _best_match_score(name: str, candidates: List[str]) -> int:
    best = 0
    for candidate in candidates:
        semantic = _semantic_score(name, candidate)
        phonetic = _phonetic_score(name, candidate)
        best = max(best, semantic, phonetic)
        if _has_devanagari(name) or _has_devanagari(candidate):
            indic_model = _get_indic_semantic_model()
            if indic_model is not None:
                try:
                    emb1 = indic_model.encode(name.lower(), convert_to_tensor=True)
                    emb2 = indic_model.encode(candidate.lower(), convert_to_tensor=True)
                    from sentence_transformers import util
                    indic_sim = int(util.cos_sim(emb1, emb2).item() * 100)
                    best = max(best, indic_sim)
                except Exception:
                    pass
    return best


def _has_devanagari(text: str) -> bool:
    devanagari_range = range(0x0900, 0x0980)
    return any(ord(c) in devanagari_range for c in text)


def cross_check_documents(doc_entities_list: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    # 1. Fuzzy Name Matching (with phonetic transliteration for Indic names)
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
                    semantic_sim = _semantic_score(left_name, right_name)
                    phonetic_sim = _phonetic_score(left_name, right_name)
                    combined_sim = max(semantic_sim, phonetic_sim)
                    if 75 < combined_sim < 85:
                        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Name mismatch across documents: '{left_name}' vs '{right_name}' (Similarity: {combined_sim:.1f}%, phonetic: {phonetic_sim}%)", "severity": "medium", "score": int((100 - combined_sim) * 0.8)})

    # 2. Hard Identity Verification (DOB & PAN)
    dobs = set()
    pans = set()
    aadhaars = set()
    for item in doc_entities_list:
        dob = item.get("entities", {}).get("dob")
        if dob: dobs.add(dob.upper())
        pan = item.get("entities", {}).get("pan")
        if pan: pans.add(pan.upper())
        indian_pii = item.get("entities", {}).get("indian_pii", {}) or {}
        for aadhaar in indian_pii.get("aadhaar", []):
            aadhaars.add(aadhaar)
        for p in indian_pii.get("pan", []):
            pans.add(p.upper())

    if len(dobs) > 1:
        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Identity Forgery: Mismatching Date of Birth detected: {', '.join(dobs)}", "severity": "high", "score": 95})

    if len(pans) > 1:
        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Identity Forgery: Mismatching PAN detected: {', '.join(pans)}", "severity": "high", "score": 95})

    if len(aadhaars) > 1:
        flags.append({"layer": "Cross-Doc Consistency", "finding": f"Identity Forgery: Mismatching Aadhaar detected: {', '.join(aadhaars)}", "severity": "high", "score": 95})

    # 3. Address Fuzzy Matching (with IndicSBERT for Devanagari addresses)
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
            if _has_devanagari(addr_a) or _has_devanagari(addr_b):
                indic_model = _get_indic_semantic_model()
                if indic_model is not None:
                    try:
                        emb1 = indic_model.encode(addr_a.lower(), convert_to_tensor=True)
                        emb2 = indic_model.encode(addr_b.lower(), convert_to_tensor=True)
                        from sentence_transformers import util
                        indic_sim = int(util.cos_sim(emb1, emb2).item() * 100)
                        sim = max(sim, indic_sim)
                    except Exception:
                        pass
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

    # 5. Indian PII cross-checks (GLiNER extracted)
    gliner_names: Dict[str, List[str]] = {}
    for item in doc_entities_list:
        indian_pii = item.get("entities", {}).get("indian_pii", {}) or {}
        pn = indian_pii.get("person_name", [])
        if pn:
            gliner_names[item["doc_id"]] = pn

    gliner_ids = list(gliner_names.keys())
    for i in range(len(gliner_ids)):
        for j in range(i + 1, len(gliner_ids)):
            for name_a in gliner_names[gliner_ids[i]]:
                for name_b in gliner_names[gliner_ids[j]]:
                    sim = _best_match_score(name_a, [name_b])
                    if 70 < sim < 85:
                        flags.append({
                            "layer": "Cross-Doc Consistency",
                            "finding": f"Person name discrepancy via NER: '{name_a}' vs '{name_b}' (match: {sim}%)",
                            "severity": "medium",
                            "score": int((100 - sim) * 0.8),
                        })

    unique_flags: List[Dict[str, Any]] = []
    seen = set()
    for flag in flags:
        if flag["finding"] in seen:
            continue
        seen.add(flag["finding"])
        unique_flags.append(flag)
    return unique_flags