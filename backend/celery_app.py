import os
from celery import Celery
from loguru import logger

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("RESULT_BACKEND", f"{REDIS_URL}/1")

app = Celery(
    "credexa_worker",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=["tasks"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
)

if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    app.start()
