from __future__ import annotations

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


def _build_feature_vector(documents: Sequence[Dict[str, Any]]) -> List[List[float]]:
    vectors: List[List[float]] = []
    for document in documents:
        text = document.get("text", "") or ""
        flags = document.get("flags", []) or []
        metadata = document.get("metadata", {}) or {}
        tables = document.get("tables", []) or []
        pages = document.get("pages", []) or []
        vectors.append(
            [
                float(len(text)),
                float(len(flags)),
                float(len(tables)),
                float(len(pages)),
                float(document.get("file_size", 0) or 0),
                float(len(metadata.keys())),
            ]
        )
    return vectors


def detect_anomalies(documents: Sequence[Dict[str, Any]]) -> AnomalyResult:
    if not documents:
        return AnomalyResult(score=0.0, flags=[], features={"documents": 0.0})

    vectors = _build_feature_vector(documents)
    feature_names = ["text_length", "flag_count", "table_count", "page_count", "file_size", "metadata_count"]
    aggregates = {name: 0.0 for name in feature_names}

    for vector in vectors:
        for index, value in enumerate(vector):
            aggregates[feature_names[index]] += float(value)

    if IsolationForest is None or np is None or len(vectors) < 3:
        total_flag_count = sum(len(document.get("flags", []) or []) for document in documents)
        total_text = sum(len(document.get("text", "") or "") for document in documents)
        heuristic_score = min(100.0, total_flag_count * 12.5 + (0 if total_text > 500 else 15.0))
        return AnomalyResult(score=heuristic_score, flags=[], features=aggregates)

    matrix = np.asarray(vectors, dtype=float)
    model = IsolationForest(contamination=min(0.4, max(0.05, 1.0 / len(vectors))), random_state=42)
    predictions = model.fit_predict(matrix)
    anomaly_mask = predictions == -1
    anomaly_score = float(anomaly_mask.mean() * 100.0)

    anomaly_flags: List[Dict[str, Any]] = []
    for index, is_anomaly in enumerate(anomaly_mask):
        if is_anomaly:
            anomaly_flags.append(
                {
                    "layer": "ML Anomaly",
                    "finding": f"Document {documents[index].get('document_id') or index + 1} is an outlier across file size, text volume, and evidence density.",
                    "severity": "medium",
                    "score": 35,
                }
            )

    return AnomalyResult(score=anomaly_score, flags=anomaly_flags, features=aggregates)
