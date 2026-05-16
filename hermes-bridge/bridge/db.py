"""SQLite-backed persistence for the multi-agent orchestrator.

A separate database file from the Go gateway's ``agent.db`` to avoid
cross-process write contention. The path is configurable via
``ORCHESTRATOR_DB`` so tests can point at a temp file.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

DB_PATH = Path(
    os.getenv("ORCHESTRATOR_DB", "/root/.agent-platform/orchestrator.db")
)

_MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS dialog_flows (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id     INTEGER DEFAULT 0,
        name         TEXT NOT NULL,
        description  TEXT DEFAULT '',
        flow_type    TEXT NOT NULL CHECK (flow_type IN ('sequential','parallel')),
        role_ids     TEXT NOT NULL,            -- JSON array of role slugs, ordered
        scenario_id  TEXT DEFAULT '',
        prompt_template TEXT DEFAULT '',
        model        TEXT DEFAULT 'deepseek-v4-flash',
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS flow_runs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        flow_id      INTEGER NOT NULL,
        input_text   TEXT DEFAULT '',
        status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','running','succeeded','failed','cancelled')),
        error        TEXT DEFAULT '',
        outputs      TEXT NOT NULL DEFAULT '[]', -- JSON: [{role_id, content, latency_ms, error}]
        started_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        finished_at  DATETIME,
        FOREIGN KEY (flow_id) REFERENCES dialog_flows(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_runs_flow ON flow_runs(flow_id)",
    # Migration: add model column to existing tables
    "ALTER TABLE dialog_flows ADD COLUMN model TEXT DEFAULT 'deepseek-v4-flash'",
]


# ── Connection management ────────────────────────────────────────────────────

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            # Ignore "duplicate column" errors from ALTER TABLE
            if "duplicate column" not in str(e).lower():
                raise
    conn.commit()


def init() -> None:
    """Open the connection and apply migrations. Idempotent."""
    global _conn
    with _lock:
        if _conn is None:
            _conn = _connect()
            _migrate(_conn)
            logger.info("orchestrator db ready: %s", DB_PATH)


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    """Yield a cursor with the lock held — use for any write or read.

    SQLite handles its own locking, but a single in-process lock keeps our
    write-then-read patterns linearizable without surprises.
    """
    if _conn is None:
        init()
    assert _conn is not None
    with _lock:
        cur = _conn.cursor()
        try:
            yield cur
            _conn.commit()
        except Exception:
            _conn.rollback()
            raise
        finally:
            cur.close()
