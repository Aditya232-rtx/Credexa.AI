from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from loguru import logger

try:
    import torch
    from transformers import (
        LayoutLMv3ForSequenceClassification,
        LayoutLMv3Processor,
    )
except Exception:
    torch = None
    LayoutLMv3ForSequenceClassification = None
    LayoutLMv3Processor = None

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


def _normalize_box(box: Sequence[float], width: float, height: float) -> List[int]:
    return [
        max(0, min(1000, int(1000 * (box[0] / width)))),
        max(0, min(1000, int(1000 * (box[1] / height)))),
        max(0, min(1000, int(1000 * (box[2] / width)))),
        max(0, min(1000, int(1000 * (box[3] / height)))),
    ]


FINETUNED_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "layoutlmv3_router"


class DocumentRouter:
    """Routes documents to the correct processing pipeline based on content.
    
    Note: Keyword matching is optimized for Latin-script content. 
    Documents primarily in Devanagari or other non-Latin scripts may have 
    reduced classification accuracy and should be validated manually.
    """
    def __init__(self, documenttypes_path: str | Path | None = None, model_path: str | Path | None = None):
        self.documenttypes_path = Path(documenttypes_path) if documenttypes_path else None
        self.model_path = Path(model_path) if model_path else None
        self.taxonomy = self._load_taxonomy()
        self.processor = None
        self.model = None
        self.categories = list(DEFAULT_TAXONOMY.keys())
        self._load_layoutlmv3()

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

    def _get_finetuned_router_path(self) -> str | None:
        candidates = [
            self.model_path,
            FINETUNED_MODEL_PATH,
            Path(os.getenv("CREDEXA_ROUTER_MODEL", "")),
        ]
        for c in candidates:
            if c and Path(c).exists() and (Path(c) / "config.json").exists():
                return str(c)
        return None

    def _load_layoutlmv3(self) -> None:
        if LayoutLMv3ForSequenceClassification is None or LayoutLMv3Processor is None:
            return
        finetuned = self._get_finetuned_router_path()
        model_checkpoint = finetuned or "gordonlim/layoutlmv3-base-finetuned-rvlcdip"
        proc_checkpoint = "microsoft/layoutlmv3-base"
        try:
            self.model = LayoutLMv3ForSequenceClassification.from_pretrained(model_checkpoint)
            self.processor = LayoutLMv3Processor.from_pretrained(proc_checkpoint, apply_ocr=False)
            self.model.eval()
        except Exception:
            try:
                self.processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base", apply_ocr=False)
                self.model = LayoutLMv3ForSequenceClassification.from_pretrained(
                    "microsoft/layoutlmv3-base",
                    num_labels=len(self.categories),
                    id2label={i: c for i, c in enumerate(self.categories)},
                    label2id={c: i for i, c in enumerate(self.categories)},
                )
                self.model.eval()
            except Exception:
                self.processor = None
                self.model = None

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
                # Use word-boundary matching to avoid false matches (e.g., "pan" matching "company")
                if re.search(r'\b' + re.escape(keyword) + r'\b', search_blob):
                    scores[category] += 1.0
                elif len(keyword) > 4:
                    token_hits = sum(1 for token in keyword.split() if re.search(r'\b' + re.escape(token) + r'\b', search_blob))
                    if token_hits >= max(1, len(keyword.split()) // 2):
                        scores[category] += 0.35 * token_hits
        filename = str((metadata or {}).get("file_name", "")).lower()
        if any(token in filename for token in ["bank", "statement", "form16", "26as", "itr", "pnl", "tax"]):
            scores["Financial Statements & Tax Registries"] += 1.25
        if any(token in filename for token in ["aadhaar", "pan", "passport", "voter", "license", "poa", "affidavit"]):
            scores["Legal & Identity Documents"] += 1.25
        if any(token in filename for token in ["7_12", "712", "satbara", "property", "jamabandi", "khata", "sale deed", "encumbrance"]):
            scores["Land & Property Records"] += 1.25
        return scores

    def _layout_signal(self, payload: Mapping[str, Any]) -> Dict[str, float]:
        if self.processor is None or self.model is None or torch is None:
            return {}
        pages = payload.get("pages", []) or []
        if not pages:
            return {}
        page = pages[0]
        image = page.get("image")
        words = page.get("words", []) or []
        boxes = page.get("boxes", []) or []
        if image is None or not words or not boxes:
            return {}
        try:
            width, height = image.size
            normalized_boxes = [_normalize_box(box, width, height) for box in boxes[:512]]
            encoding = self.processor(image, words[:512], boxes=normalized_boxes, return_tensors="pt", truncation=True)
            with torch.no_grad():
                logits = self.model(**encoding).logits
            probs = torch.softmax(logits, dim=-1).squeeze()
            return {self.categories[i]: float(probs[i]) for i in range(len(self.categories)) if len(probs.shape) > 0}
        except Exception as e:
            logger.debug(f"Layout signal failed: {e}")
            return {}

    def classify_document(self, payload: Mapping[str, Any]) -> str:
        text = self._collect_text(payload)
        metadata = payload.get("metadata", {}) or {}
        keyword_scores = self._keyword_scores(text, metadata)
        layout_scores = self._layout_signal(payload)
        combined = {
            category: keyword_scores.get(category, 0.0) + layout_scores.get(category, 0.0) * 5.0
            for category in self.taxonomy
        }
        best_category, best_score = max(combined.items(), key=lambda item: item[1])
        return best_category if best_score > 0.25 else "Unknown"
