from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover - optional dependency fallback
    np = None
    IsolationForest = None


@dataclass
class AnomalyResult:
    score: float
    flags: List[Dict[str, Any]]
    features: Dict[str, float]


def _count_round_numbers(text: str) -> tuple:
    """Count monetary amounts and what % end in 000."""
    amounts = re.findall(r"(?:₹|rs\.?\s*|inr\s*)?(\d[\d,]*(?:\.\d{1,2})?)", text, re.I)
    parsed = []
    for raw in amounts:
        try:
            val = float(raw.replace(",", ""))
            if 100.0 <= val <= 100_000_000.0:
                parsed.append(val)
        except ValueError:
            continue
    if not parsed:
        return 0, 0.0
    round_count = sum(1 for a in parsed if a % 1000 == 0)
    return len(parsed), (round_count / len(parsed)) * 100.0


def _build_feature_vector(documents: Sequence[Dict[str, Any]]) -> List[List[float]]:
    """Build an enhanced feature vector with fraud-relevant domain features."""
    vectors: List[List[float]] = []
    for document in documents:
        text = document.get("text", "") or ""
        flags = document.get("flags", []) or []
        metadata = document.get("metadata", {}) or {}
        tables = document.get("tables", []) or []
        pages = document.get("pages", []) or []

        # Original structural features
        text_length = float(len(text))
        flag_count = float(len(flags))
        table_count = float(len(tables))
        page_count = float(len(pages))
        file_size = float(document.get("file_size", 0) or 0)
        metadata_count = float(len(metadata.keys()))

        # NEW domain features for fraud detection
        # 1. Round number percentage
        amount_count, pct_round = _count_round_numbers(text)

        # 2. Flag score sum (severity-weighted)
        flag_score_sum = sum(float(f.get("score", 0)) for f in flags)

        # 3. OCR confidence average (if available from pages)
        ocr_confidences = []
        for page in pages:
            conf = page.get("ocr_confidence")
            if conf is not None:
                ocr_confidences.append(float(conf))
        ocr_confidence_avg = float(np.mean(ocr_confidences)) if ocr_confidences and np else 0.0

        # 4. Text density (chars per page)
        text_density = text_length / max(1.0, page_count)

        # 5. Amount count (number of monetary values found)
        amount_feature = float(amount_count)

        vectors.append([
            text_length,
            flag_count,
            table_count,
            page_count,
            file_size,
            metadata_count,
            pct_round,           # % of amounts ending in 000
            flag_score_sum,      # total severity score
            ocr_confidence_avg,  # OCR quality signal
            text_density,        # chars per page
            amount_feature,      # how many monetary values found
        ])
    return vectors


def detect_anomalies(documents: Sequence[Dict[str, Any]]) -> AnomalyResult:
    if not documents:
        return AnomalyResult(score=0.0, flags=[], features={"documents": 0.0})

    vectors = _build_feature_vector(documents)
    feature_names = [
        "text_length", "flag_count", "table_count", "page_count",
        "file_size", "metadata_count", "pct_round_numbers",
        "flag_score_sum", "ocr_confidence_avg", "text_density", "amount_count",
    ]
    aggregates = {name: 0.0 for name in feature_names}

    for vector in vectors:
        for index, value in enumerate(vector):
            if index < len(feature_names):
                aggregates[feature_names[index]] += float(value)

    if IsolationForest is None or np is None or len(vectors) < 3:
        total_flag_count = sum(len(document.get("flags", []) or []) for document in documents)
        total_text = sum(len(document.get("text", "") or "") for document in documents)
        heuristic_score = min(100.0, total_flag_count * 12.5 + (0 if total_text > 500 else 15.0))
        return AnomalyResult(score=heuristic_score, flags=[], features=aggregates)

    matrix = np.asarray(vectors, dtype=float)

    # Try to load a pre-trained model from feedback retraining
    model = None
    try:
        from anomaly.retrain import load_trained_model
        model = load_trained_model()
    except Exception:
        pass

    if model is None:
        model = IsolationForest(contamination=min(0.4, max(0.05, 1.0 / len(vectors))), random_state=42)
        model.fit(matrix)

    predictions = model.fit_predict(matrix) if not hasattr(model, 'predict') else model.predict(matrix)
    anomaly_mask = predictions == -1
    anomaly_score = float(anomaly_mask.mean() * 100.0)

    anomaly_flags: List[Dict[str, Any]] = []
    for index, is_anomaly in enumerate(anomaly_mask):
        if is_anomaly:
            doc_id = documents[index].get('document_id') or index + 1
            # Build a more descriptive finding
            vec = vectors[index]
            details = []
            if vec[6] > 40:  # pct_round
                details.append(f"{vec[6]:.0f}% round numbers")
            if vec[7] > 100:  # flag_score_sum
                details.append(f"high flag severity ({vec[7]:.0f})")
            detail_str = f" ({', '.join(details)})" if details else ""

            anomaly_flags.append(
                {
                    "layer": "ML Anomaly",
                    "finding": f"Document {doc_id} is a statistical outlier across {len(feature_names)} fraud features{detail_str}.",
                    "severity": "medium",
                    "score": 35,
                }
            )

    return AnomalyResult(score=anomaly_score, flags=anomaly_flags, features=aggregates)

