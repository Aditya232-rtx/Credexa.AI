from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from anomaly.pattern_detector import analyze_patterns

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
except Exception:
    np = None
    IsolationForest = None

MODEL_DIR = Path(__file__).resolve().parent / "models"
TRAINED_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "anomaly"

try:
    from pyod.models.ecod import ECOD
except ImportError:
    ECOD = None

try:
    import torch
    import torch.nn as nn
    from utils.device import get_device

    _device = get_device()
    TORCH_AVAILABLE = True

    class AnomalyAutoencoder(nn.Module):  # type: ignore
        def __init__(self, input_dim: int = 11, encoding_dim: int = 4):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, 8), nn.ReLU(),
                nn.Linear(8, encoding_dim), nn.ReLU(),
            )
            self.decoder = nn.Sequential(
                nn.Linear(encoding_dim, 8), nn.ReLU(),
                nn.Linear(8, input_dim),
            )

        def forward(self, x):
            return self.decoder(self.encoder(x))

except ImportError:
    _device = "cpu"
    TORCH_AVAILABLE = False

    class AnomalyAutoencoder:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is not available")

FEATURE_NAMES = [
    "text_length", "flag_count", "table_count", "page_count",
    "file_size", "metadata_count", "pct_round_numbers",
    "flag_score_sum", "ocr_confidence_avg", "text_density", "amount_count",
]


@dataclass
class AnomalyResult:
    score: float
    flags: List[Dict[str, Any]]
    features: Dict[str, float]


def _count_round_numbers(text: str) -> tuple:
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
    vectors: List[List[float]] = []
    for document in documents:
        try:
            text = document.get("text", "") or ""
            flags = document.get("flags", []) or []
            metadata = document.get("metadata", {}) or {}
            tables = document.get("tables", []) or []
            pages = document.get("pages", []) or []
            text_length = float(len(text))
            flag_count = float(len(flags))
            table_count = float(len(tables))
            page_count = float(len(pages))
            file_size = float(document.get("file_size", 0) or 0)
            metadata_count = float(len(metadata.keys()))
            amount_count, pct_round = _count_round_numbers(text)
            flag_score_sum = sum(float(f.get("score", 0)) for f in flags)
            ocr_confidences = []
            for page in pages:
                conf = page.get("ocr_confidence")
                if conf is not None:
                    ocr_confidences.append(float(conf))
            ocr_confidence_avg = float(np.mean(ocr_confidences)) if ocr_confidences and np else 0.0
            text_density = text_length / max(1.0, page_count)
            amount_feature = float(amount_count)
            vectors.append([
                text_length, flag_count, table_count, page_count,
                file_size, metadata_count, pct_round, flag_score_sum,
                ocr_confidence_avg, text_density, amount_feature,
            ])
        except Exception:
            logger.warning(f"Skipping malformed document in feature vector: {document.get('document_id', 'unknown')}")
            continue
    return vectors


def _load_scaler():
    path = TRAINED_MODEL_DIR / "scaler.pkl"
    if path.exists():
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    return None


def _load_trained_iforest() -> IsolationForest | None:
    for path in [TRAINED_MODEL_DIR / "isolation_forest.pkl", MODEL_DIR / "isolation_forest.pkl"]:
        if path.exists():
            try:
                with open(path, "rb") as f:
                    model = pickle.load(f)
                if hasattr(model, "n_features_in_") and model.n_features_in_ == len(FEATURE_NAMES):
                    return model
            except Exception:
                continue
    return None


def _load_trained_ecod():
    path = TRAINED_MODEL_DIR / "ecod.pkl"
    if path.exists() and ECOD is not None:
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    return None


def _load_trained_autoencoder():
    path = TRAINED_MODEL_DIR / "autoencoder.pth"
    if path.exists() and TORCH_AVAILABLE:
        try:
            model = AnomalyAutoencoder(input_dim=len(FEATURE_NAMES))
            state = torch.load(path, map_location=_device, weights_only=True)
            model.load_state_dict(state)
            model.to(_device)
            model.eval()
            return model
        except Exception:
            return None
    return None


def detect_anomalies(documents: Sequence[Dict[str, Any]]) -> AnomalyResult:
    if not documents:
        return AnomalyResult(score=0.0, flags=[], features={"documents": 0.0})

    vectors = _build_feature_vector(documents)
    aggregates = {name: 0.0 for name in FEATURE_NAMES}
    for vector in vectors:
        for index, value in enumerate(vector):
            aggregates[FEATURE_NAMES[index]] += float(value)

    all_flags: List[Dict[str, Any]] = []

    # Run Pattern Detector on each document's text
    for doc in documents:
        text = doc.get("text", "") or ""
        pattern_flags = analyze_patterns(text)
        all_flags.extend(pattern_flags)

    if IsolationForest is None or np is None or len(vectors) < 3:
        total_flag_count = sum(len(document.get("flags", []) or []) for document in documents)
        total_text = sum(len(document.get("text", "") or "") for document in documents)
        heuristic_score = min(100.0, total_flag_count * 12.5 + (0 if total_text > 500 else 15.0))
        return AnomalyResult(score=heuristic_score, flags=all_flags, features=aggregates)

    matrix = np.asarray(vectors, dtype=float)

    scaler = _load_scaler()
    if scaler is not None:
        matrix_scaled = scaler.transform(matrix)
    else:
        matrix_scaled = matrix

    anomaly_scores: List[float] = []

    # 1. Isolation Forest (pre-trained only)
    if_model = _load_trained_iforest()
    if if_model is not None:
        if_predictions = if_model.predict(matrix_scaled)
        if_scores = (if_predictions == -1).astype(float)
    else:
        if_scores = np.zeros(len(matrix))

    # 2. ECOD (pre-trained only)
    ecod_model = _load_trained_ecod()
    if ecod_model is not None:
        ecod_scores = ecod_model.predict(matrix_scaled)
    else:
        ecod_scores = np.zeros(len(matrix))

    # 3. Autoencoder reconstruction error
    ae_model = _load_trained_autoencoder()
    if ae_model is not None:
        with torch.no_grad():
            tensor = torch.FloatTensor(matrix_scaled).to(_device)
            reconst = ae_model(tensor)
            ae_errors = torch.mean((tensor.cpu() - reconst.cpu()) ** 2, dim=1).numpy()
        ae_threshold = float(np.percentile(ae_errors, 95))
        ae_anomalies = (ae_errors > ae_threshold).astype(float)
    else:
        ae_anomalies = np.zeros(len(matrix))

    # Ensemble: consensus-based anomaly scoring
    ensemble = (if_scores + ecod_scores + ae_anomalies) / 3.0
    anomaly_mask = ensemble > 0.5
    anomaly_score = float(anomaly_mask.mean() * 100.0)

    for index, is_anomaly in enumerate(anomaly_mask):
        if is_anomaly:
            doc_id = documents[index].get("document_id") or index + 1
            vec = vectors[index]
            details = []
            if vec[6] > 40:
                details.append(f"{vec[6]:.0f}% round numbers")
            if vec[7] > 100:
                details.append(f"high flag severity ({vec[7]:.0f})")
            sources = []
            if if_scores[index] > 0.5:
                sources.append("IF")
            if ecod_scores[index] > 0.5:
                sources.append("ECOD")
            if ae_anomalies[index] > 0.5:
                sources.append("AE")
            detail_str = f" ({', '.join(details)})" if details else ""
            all_flags.append({
                "layer": "ML Anomaly",
                "finding": f"Document {doc_id} is a statistical outlier across {len(FEATURE_NAMES)} fraud features{detail_str}. Detected by: {', '.join(sources)}.",
                "severity": "medium",
                "score": 35,
            })

    return AnomalyResult(score=anomaly_score, flags=all_flags, features=aggregates)
