"""Verify that core project modules can be imported."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def test_core_backend_imports():
    from db.connection import get_db_connection, DatabaseConnection  # noqa: F811
    from scoring.main import score_case  # noqa: F811
    from scoring.explainability import generate_explanation  # noqa: F811
    from router.classifier import DocumentRouter  # noqa: F811
    from anomaly.main import detect_anomalies  # noqa: F811
    from forensics.math_validator import clean_indian_currency  # noqa: F811
    from utils.encryption import reload_cipher_suite, encrypt_data  # noqa: F811
    from celery_app import app as celery_app  # noqa: F811
