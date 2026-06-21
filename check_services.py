import psycopg2
import redis
import urllib.request
import json

print('--- Checking PostgreSQL ---')
try:
    conn = psycopg2.connect('dbname=credexa user=adityajadhav host=localhost port=5432')
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    tables = cur.fetchall()
    print('DB Connection: SUCCESS')
    print('Tables found:', [t[0] for t in tables])
except Exception as e:
    print('DB Connection: FAILED ->', e)

print('\n--- Checking Redis ---')
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    print('Redis Ping:', r.ping())
except Exception as e:
    print('Redis Connection: FAILED ->', e)

print('\n--- Checking Ollama ---')
try:
    req = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)
    data = json.loads(req.read())
    models = [m['name'] for m in data.get('models', [])]
    print('Ollama Connection: SUCCESS')
    print('Models available:', models)
except Exception as e:
    print('Ollama Connection: FAILED ->', e)
