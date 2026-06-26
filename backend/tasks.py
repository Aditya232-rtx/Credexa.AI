import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from celery_app import app
from services.case_pipeline import CasePipeline

ROOT_DIR = BASE_DIR.parent
DOCUMENT_TYPES_PATH = ROOT_DIR / "docs" / "documenttypes.md"

import os
DB_DSN = os.environ.get("DB_DSN", "dbname=credexa user=adityajadhav host=localhost port=5432")

pipeline = CasePipeline(BASE_DIR, DB_DSN, DOCUMENT_TYPES_PATH)

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_case_task(self, case_id: str):
    """
    Celery task to run the case pipeline in the background.
    """
    try:
        logger.info(f"Starting pipeline for case {case_id}")
        result = pipeline.process_case(case_id)
        logger.info(f"Pipeline completed for case {case_id}: score={result.get('risk_score')}, status={result.get('status')}")
        return result
    except Exception as e:
        logger.error(f"Error processing case {case_id}: {str(e)}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            from db.connection import get_db_connection
            with get_db_connection() as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("UPDATE cases SET status = %s WHERE id = %s", ("failed", case_id))
            logger.critical(f"Case {case_id} failed after max retries")
            raise

