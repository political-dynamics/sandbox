"""SQLite file cache keyed by stable hash."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any


class SQLiteCache:
    """Simple SQLite-backed JSON cache."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_items (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def build_key(namespace: str, payload: Any) -> str:
        raw = json.dumps({"namespace": namespace, "payload": payload}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM cache_items WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        payload = json.dumps(value, default=str)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO cache_items (cache_key, payload)
                VALUES (?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    created_at = CURRENT_TIMESTAMP
                """,
                (key, payload),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

