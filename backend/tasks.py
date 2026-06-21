import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from celery_app import app
from services.case_pipeline import CasePipeline

ROOT_DIR = BASE_DIR.parent
DOCUMENT_TYPES_PATH = ROOT_DIR / "documenttypes.md"

import os
DB_DSN = os.environ.get("DB_DSN", "dbname=credexa user=adityajadhav host=localhost port=5432")

pipeline = CasePipeline(BASE_DIR, DB_DSN, DOCUMENT_TYPES_PATH)

@app.task(bind=True)
def process_case_task(self, case_id: str):
    """
    Celery task to run the case pipeline in the background.
    """
    try:
        result = pipeline.process_case(case_id)
        return result
    except Exception as e:
        # We can update the case status to 'failed' here if needed
        # Or log it
        print(f"Error processing case {case_id}: {str(e)}")
        raise
