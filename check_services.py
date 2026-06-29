import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
os.environ.setdefault("DB_BACKEND", "postgres")

from db.connection import get_db_connection

print('--- Checking PostgreSQL ---')
try:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
            tables = cur.fetchall()
            print('DB Connection: SUCCESS')
            print('Tables found:', [t[0] for t in tables])
except Exception as e:
    print('DB Connection: FAILED ->', e)

print('\n--- Checking Redis ---')
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    print('Redis Ping:', r.ping())
except Exception as e:
    print('Redis Connection: FAILED ->', e)

print('\n--- Checking Ollama ---')
try:
    import urllib.request
    import json
    req = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)
    data = json.loads(req.read())
    models = [m['name'] for m in data.get('models', [])]
    print('Ollama Connection: SUCCESS')
    print('Models available:', models)
except Exception as e:
    print('Ollama Connection: FAILED ->', e)
