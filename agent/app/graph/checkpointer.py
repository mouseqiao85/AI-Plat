"""SQLite-based checkpointer for LangGraph state persistence."""
import json
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SQLiteCheckpointer:
    """SQLite-based state persistence for agent sessions."""

    def __init__(self, db_path: str = "data/checkpoints.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        import os
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    state TEXT NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id)
            """)
            conn.commit()
        finally:
            conn.close()

    def get(self, config: dict) -> Optional[dict]:
        thread_id = config.get("configurable", {}).get("thread_id", "")
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT state, metadata FROM checkpoints WHERE thread_id = ? ORDER BY created_at DESC LIMIT 1",
                (thread_id,)
            ).fetchone()
            if row:
                return {
                    "config": config,
                    "values": json.loads(row["state"]),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
            return None
        finally:
            conn.close()

    def put(self, config: dict, checkpoint: dict, metadata: dict = None) -> None:
        thread_id = config.get("configurable", {}).get("thread_id", "")
        checkpoint_id = checkpoint.get("id", "default")
        parent_id = checkpoint.get("parent_id")

        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_id, parent_checkpoint_id, state, metadata) VALUES (?, ?, ?, ?, ?)",
                (thread_id, checkpoint_id, parent_id,
                 json.dumps(checkpoint, ensure_ascii=False, default=str),
                 json.dumps(metadata, ensure_ascii=False, default=str) if metadata else None),
            )
            conn.commit()
        finally:
            conn.close()

    def list(self, config: dict):
        thread_id = config.get("configurable", {}).get("thread_id", "")
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT checkpoint_id, state, metadata, created_at FROM checkpoints WHERE thread_id = ? ORDER BY created_at DESC",
                (thread_id,)
            ).fetchall()
            for row in rows:
                yield {
                    "checkpoint_id": row["checkpoint_id"],
                    "values": json.loads(row["state"]),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
        finally:
            conn.close()
