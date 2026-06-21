import os
from celery import Celery

# Default PostgreSQL database URL and Redis URL
# We use synchronous psycopg2 connection string format here or sqlalchemy if preferred,
# but for celery we just need the broker string.

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "credexa_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
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
    app.start()
