from pathlib import Path
import os
from loguru import logger

from celery_app import app
from services.case_pipeline import CasePipeline

BASE_DIR = Path(__file__).resolve().parent
DOCUMENT_TYPES_PATH = BASE_DIR.parent / "docs" / "documenttypes.md"
DB_DSN = os.environ.get("DB_DSN", "dbname=credexa user=postgres host=localhost port=5432 password=postgres")


def get_pipeline():
    return CasePipeline(BASE_DIR, DB_DSN, DOCUMENT_TYPES_PATH)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_case_task(self, case_id: str):
    """
    Celery task to run the case pipeline in the background.
    """
    # Update status to processing
    from db.connection import get_db_connection
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("UPDATE cases SET status = %s WHERE id = %s", ("processing", case_id))
    
    pipeline = get_pipeline()
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

