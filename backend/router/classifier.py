from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping

from loguru import logger


DEFAULT_TAXONOMY = {
    "Financial Statements & Tax Registries": [
        "bank statement",
        "current account",
        "savings account",
        "balance sheet",
        "profit and loss",
        "p&l",
        "income statement",
        "cash flow",
        "form 16",
        "form 26as",
        "tax transcript",
        "income tax return",
        "itr",
        "tds",
        "salary",
        "credit card",
        "loan account",
    ],
    "Legal & Identity Documents": [
        "aadhaar",
        "adhaar",
        "pan",
        "passport",
        "driving license",
        "voter id",
        "birth certificate",
        "marriage certificate",
        "certificate of incorporation",
        "memorandum of association",
        "articles of association",
        "board resolution",
        "power of attorney",
        "affidavit",
        "partnership deed",
        "indemnity bond",
        "shareholder agreement",
    ],
    "Land & Property Records": [
        "7/12",
        "satbara",
        "8a extract",
        "property card",
        "jamabandi",
        "patta",
        "chitta",
        "khata",
        "sale deed",
        "gift deed",
        "mortgage deed",
        "lease deed",
        "encumbrance certificate",
        "cadastral map",
        "fmb",
        "field measurement book",
        "survey number",
        "bhulekh",
        "ror",
    ],
}


class DocumentRouter:
    def __init__(self, documenttypes_path: str | Path | None = None, model_path: str | Path | None = None):
        self.documenttypes_path = Path(documenttypes_path) if documenttypes_path else None
        self.taxonomy = self._load_taxonomy()
        self.categories = list(DEFAULT_TAXONOMY.keys())

    def _load_taxonomy(self) -> Dict[str, List[str]]:
        taxonomy = {category: list(values) for category, values in DEFAULT_TAXONOMY.items()}
        if not self.documenttypes_path or not self.documenttypes_path.exists():
            return taxonomy
        current_category = None
        for raw_line in self.documenttypes_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            normalized = re.sub(r"[\*`|<>]", "", line).lower()
            if "land" in normalized and "property" in normalized and "records" in normalized:
                current_category = "Land & Property Records"
                continue
            if "legal" in normalized and "identity" in normalized:
                current_category = "Legal & Identity Documents"
                continue
            if "financial" in normalized and "tax" in normalized:
                current_category = "Financial Statements & Tax Registries"
                continue
            if current_category and line.startswith("-"):
                cleaned = re.sub(r"^[-•\s]+", "", line)
                cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()
                cleaned = cleaned.replace("**", "")
                if ":" in cleaned:
                    cleaned = cleaned.split(":", 1)[0].strip()
                if cleaned and len(cleaned) > 2:
                    taxonomy.setdefault(current_category, []).append(cleaned.lower())
        for category, keywords in list(taxonomy.items()):
            deduped: List[str] = []
            for keyword in keywords:
                keyword = keyword.strip().lower()
                if keyword and keyword not in deduped:
                    deduped.append(keyword)
            taxonomy[category] = deduped
        return taxonomy

    def _collect_text(self, payload: Mapping[str, Any]) -> str:
        text = payload.get("text", "") or ""
        pages = payload.get("pages", []) or []
        if pages:
            page_text = [" ".join(page.get("words", [])) for page in pages]
            text = "\n".join(part for part in [text, *page_text] if part)
        return text

    def _keyword_scores(self, text: str, metadata: Mapping[str, Any] | None = None) -> Dict[str, float]:
        normalized_text = text.lower()
        metadata_blob = " ".join(str(value) for value in (metadata or {}).values()).lower()
        search_blob = f"{normalized_text} {metadata_blob}"
        scores = {category: 0.0 for category in self.taxonomy}
        for category, keywords in self.taxonomy.items():
            for keyword in keywords:
                if not keyword:
                    continue
                if re.search(r'\b' + re.escape(keyword) + r'\b', search_blob):
                    scores[category] += 1.0
                elif len(keyword) > 4:
                    token_hits = sum(1 for token in keyword.split() if re.search(r'\b' + re.escape(token) + r'\b', search_blob))
                    if token_hits >= max(1, len(keyword.split()) // 2):
                        scores[category] += 0.35 * token_hits
        filename = str((metadata or {}).get("file_name", "")).lower()
        if any(token in filename for token in ["bank", "statement", "form16", "26as", "itr", "pnl", "tax"]):
            scores["Financial Statements & Tax Registries"] += 1.25
        if any(token in filename for token in ["aadhaar", "adhaar", "pan", "passport", "voter", "license", "poa", "affidavit"]):
            scores["Legal & Identity Documents"] += 1.25
        if any(token in filename for token in ["7_12", "712", "satbara", "property", "jamabandi", "khata", "sale deed", "encumbrance"]):
            scores["Land & Property Records"] += 1.25
        return scores

    def _vlm_classify(self, payload: Mapping[str, Any]) -> str | None:
        pages = payload.get("pages", []) or []
        if not pages:
            return None
        text = self._collect_text(payload)
        for page in pages:
            image = page.get("image")
            if image is None:
                image_path = page.get("image_path")
                if image_path and os.path.exists(image_path):
                    from PIL import Image as PILImage
                    image = PILImage.open(image_path).convert("RGB")
            if image is None:
                continue
            try:
                from services.vlm import classify_financial_doc
                category = classify_financial_doc(image, text)
                doc_label_map = {
                    "bank_statement": "Financial Statements & Tax Registries",
                    "form_26as": "Financial Statements & Tax Registries",
                    "itr": "Financial Statements & Tax Registries",
                    "salary_slip": "Financial Statements & Tax Registries",
                    "balance_sheet": "Financial Statements & Tax Registries",
                    "profit_loss": "Financial Statements & Tax Registries",
                    "gst_return": "Financial Statements & Tax Registries",
                }
                label = doc_label_map.get(category)
                if label:
                    return label
            except Exception:
                continue
        return None

    def classify_document(self, payload: Mapping[str, Any]) -> str:
        text = self._collect_text(payload)
        metadata = payload.get("metadata", {}) or {}

        scores = self._keyword_scores(text, metadata)
        best_category, best_score = max(scores.items(), key=lambda item: item[1])

        if best_score > 0.25:
            return best_category

        vlm_label = self._vlm_classify(payload)
        return vlm_label if vlm_label else "Unknown"
