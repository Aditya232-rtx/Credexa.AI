"""
Feedback Retraining — retrain the Isolation Forest from reviewer-approved cases.

Instead of fitting the model from scratch each time with no learned baseline,
this module loads approved case feature vectors from the feedback table and
trains a persistent model to distinguish normal from anomalous documents.
"""
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

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "isolation_forest.pkl"


def _get_db_connection():
    """Get a psycopg2 connection using the standard DSN."""
    import psycopg2
    dsn = os.environ.get("DB_DSN", "dbname=credexa user=adityajadhav host=localhost port=5432")
    return psycopg2.connect(dsn)


def collect_training_data() -> List[List[float]]:
    """
    Collect feature vectors from approved (non-fraudulent) cases.
    These form the 'normal' baseline for the Isolation Forest.
    """
    try:
        from psycopg2.extras import RealDictCursor
        conn = _get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all cases that were approved through the feedback loop
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
                    flag_count = cur.fetchone()["cnt"]

                    vectors.append([
                        float(doc.get("file_size", 0) or 0),
                        float(flag_count),
                        0.0,  # table_count — not stored, default 0
                        0.0,  # page_count — not stored, default 0
                        float(doc.get("file_size", 0) or 0),
                        0.0,  # metadata_count
                    ])

        conn.close()
        return vectors

    except Exception as e:
        logger.error(f"Failed to collect training data: {e}")
        return []


def retrain_model() -> Optional[str]:
    """
    Retrain the Isolation Forest on approved (normal) cases and save to disk.
    Returns the path to the saved model, or None on failure.
    """
    if IsolationForest is None or np is None:
        logger.error("scikit-learn not available. Cannot retrain.")
        return None

    vectors = collect_training_data()
    if len(vectors) < 5:
        logger.warning(f"Insufficient training data ({len(vectors)} vectors). Need at least 5.")
        return None

    matrix = np.asarray(vectors, dtype=float)
    model = IsolationForest(
        contamination=0.05,  # 5% contamination — approved cases are mostly clean
        n_estimators=200,
        random_state=42,
    )
    model.fit(matrix)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    logger.info(f"Isolation Forest retrained on {len(vectors)} samples, saved to {MODEL_PATH}")
    return str(MODEL_PATH)


def load_trained_model() -> Optional[Any]:
    """Load a previously trained model from disk."""
    if not MODEL_PATH.exists():
        return None
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.warning(f"Could not load trained model: {e}")
        return None
