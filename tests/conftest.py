import os
import sys
from pathlib import Path

# Add backend directory to sys.path so that absolute imports like `from anomaly.pattern_detector ...` work
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
