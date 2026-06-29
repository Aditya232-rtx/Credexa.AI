from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Sequence, Union, Iterator


DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite").lower()
DB_DSN = os.environ.get("DB_DSN", "dbname=credexa user=postgres host=localhost port=5432 password=postgres")
SQLITE_PATH = os.environ.get("SQLITE_PATH", str(Path(__file__).resolve().parent.parent / "credexa.db"))

_sqlite_lock = threading.Lock()


class CursorWrapper:
    def __init__(self, cursor, backend: str):
        self._cursor = cursor
        self._backend = backend

    def execute(self, query: str, params: Optional[Union[tuple, dict]] = None):
        if self._backend == "sqlite" and params is not None:
            query = query.replace("%s", "?")
        return self._cursor.execute(query, params or ())

    def executemany(self, query: str, params: Sequence):
        if self._backend == "sqlite":
            query = query.replace("%s", "?")
        return self._cursor.executemany(query, params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row) if hasattr(row, 'keys') else row

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class DatabaseConnection:
    def __init__(self, conn, backend: str):
        self._conn = conn
        self._backend = backend

    @property
    def autocommit(self):
        return getattr(self._conn, 'autocommit', False)

    @autocommit.setter
    def autocommit(self, value: bool):
        if self._backend == "postgres":
            self._conn.autocommit = value
        else:
            self._conn.isolation_level = None if value else ""

    def cursor(self, cursor_factory=None):
        if self._backend == "postgres":
            cur = self._conn.cursor(cursor_factory=cursor_factory)
        else:
            self._conn.row_factory = sqlite3.Row
            cur = self._conn.cursor()
        return CursorWrapper(cur, self._backend)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Global pool for PostgreSQL
_db_pool = None

if DB_BACKEND == "postgres":
    try:
        from psycopg2 import pool
        _db_pool = pool.SimpleConnectionPool(1, 20, DB_DSN)
    except Exception as e:
        print(f"Error creating DB pool: {e}")
        _db_pool = None


@contextmanager
def get_db_connection():
    if DB_BACKEND == "postgres":
        conn = _get_postgres_conn()
    else:
        conn = _get_sqlite_conn()
    try:
        yield conn
    finally:
        conn.close()


def _get_postgres_conn() -> DatabaseConnection:
    global _db_pool
    import psycopg2
    if _db_pool:
        raw = _db_pool.getconn()
    else:
        raw = psycopg2.connect(DB_DSN)
    return DatabaseConnection(raw, "postgres")


def _get_sqlite_conn() -> DatabaseConnection:
    db_path = Path(SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30)
    with _sqlite_lock:
        raw.execute("PRAGMA journal_mode=WAL")
        raw.execute("PRAGMA foreign_keys=ON")
        raw.execute("PRAGMA busy_timeout=5000")
    return DatabaseConnection(raw, "sqlite")


def init_db(schema_path: Optional[Path] = None) -> None:
    if schema_path is None:
        base = Path(__file__).resolve().parent
        schema_path = base / "schema_sqlite.sql" if DB_BACKEND == "sqlite" else base / "schema.sql"
    if not schema_path.exists():
        return
    with get_db_connection() as conn:
        raw = conn._conn
        if DB_BACKEND == "postgres":
            with raw.cursor() as cur:
                cur.execute(schema_path.read_text(encoding="utf-8"))
        else:
            raw.executescript(schema_path.read_text(encoding="utf-8"))


def get_db_backend() -> str:
    return DB_BACKEND
