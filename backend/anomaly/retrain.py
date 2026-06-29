from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
except ImportError:
    np = None
    IsolationForest = None

from db.connection import get_db_connection

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "anomaly"
MODEL_PATH = MODEL_DIR / "isolation_forest.pkl"

FEATURE_NAMES = [
    "text_length", "flag_count", "table_count", "page_count",
    "file_size", "metadata_count", "pct_round_numbers",
    "flag_score_sum", "ocr_confidence_avg", "text_density", "amount_count",
]


def collect_training_data() -> List[List[float]]:
    try:
        conn = get_db_connection().__enter__()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id as case_id
                FROM cases c
                INNER JOIN feedback f ON f.case_id = c.id
                WHERE LOWER(f.decision) = 'approved'
                GROUP BY c.id
            """)
            approved_case_ids = [row["case_id"] for row in cur.fetchall()]
            if not approved_case_ids:
                logger.warning("No approved cases found for retraining")
                return []
            vectors: List[List[float]] = []
            for case_id in approved_case_ids:
                cur.execute("SELECT * FROM documents WHERE case_id = %s", (case_id,))
                docs = cur.fetchall()
                for doc in docs:
                    cur.execute("SELECT COUNT(*) as cnt FROM flags WHERE document_id = %s", (doc["id"],))
                    flag_count = float(cur.fetchone()["cnt"])
                    vectors.append([
                        float(len(doc.get("text", "") or "")),
                        flag_count,
                        0.0,
                        0.0,
                        float(doc.get("file_size", 0) or 0),
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    ])
        conn.close()
        return vectors
    except Exception as e:
        logger.error(f"Failed to collect training data: {e}")
        return []


def retrain_model() -> Optional[str]:
    if IsolationForest is None or np is None:
        logger.error("scikit-learn not available. Cannot retrain.")
        return None
    vectors = collect_training_data()
    if len(vectors) < 5:
        logger.warning(f"Insufficient training data ({len(vectors)} vectors). Need at least 5.")
        return None
    matrix = np.asarray(vectors, dtype=float)
    model = IsolationForest(contamination=0.05, n_estimators=200, random_state=42)
    model.fit(matrix)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Isolation Forest retrained on {len(vectors)} samples, saved to {MODEL_PATH}")
    return str(MODEL_PATH)


def load_trained_model() -> Optional[Any]:
    if not MODEL_PATH.exists():
        return None
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        if hasattr(model, "n_features_in_") and model.n_features_in_ != len(FEATURE_NAMES):
            logger.warning(f"Model expects {model.n_features_in_} features, but {len(FEATURE_NAMES)} required. Ignoring.")
            return None
        return model
    except Exception as e:
        logger.warning(f"Could not load trained model: {e}")
        return None
