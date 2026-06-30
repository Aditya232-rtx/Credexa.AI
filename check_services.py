import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
os.environ.setdefault("DB_BACKEND", "sqlite")

from db.connection import get_db_connection

print('--- Checking Database ---')
try:
    db = os.environ.get("DB_BACKEND", "sqlite")
    with get_db_connection() as conn:
        if db == "postgres":
            with conn.cursor() as cur:
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
                tables = cur.fetchall()
                print('DB Connection: SUCCESS')
                print('Tables found:', [t[0] for t in tables])
        else:
            print('DB Connection: SUCCESS (SQLite)')
except Exception as e:
    print('DB Connection: FAILED ->', e)

print('\n--- Checking Redis ---')
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    print('Redis Ping:', r.ping())
except Exception as e:
    print('Redis Connection: FAILED ->', e)

print('\n--- Checking VLM Model ---')
try:
    from services.vlm import _model_is_cached
    if _model_is_cached():
        print('VLM Model: CACHED (Qwen2.5-VL-7B-4bit)')
    else:
        print('VLM Model: NOT CACHED (place model at models/qwen2.5-vl-7b-4bit/)')
except Exception as e:
    print('VLM Model: CHECK FAILED ->', e)
