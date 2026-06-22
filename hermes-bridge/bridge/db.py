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
        flow_type    TEXT NOT NULL CHECK (flow_type IN ('sequential','parallel','hierarchical','competitive','pipeline','peer_to_peer','dag')),
        role_ids     TEXT NOT NULL,            -- JSON array of role slugs, ordered
        scenario_id  TEXT DEFAULT '',
        prompt_template TEXT DEFAULT '',
        model        TEXT DEFAULT 'deepseek-v4-flash',
        sandbox_policy TEXT DEFAULT '{}',
        flow_spec    TEXT DEFAULT '{}',
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
    """
    CREATE TABLE IF NOT EXISTS flow_run_events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id      INTEGER NOT NULL,
        seq         INTEGER NOT NULL,
        event_type  TEXT NOT NULL,
        payload     TEXT NOT NULL,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES flow_runs(id) ON DELETE CASCADE,
        UNIQUE(run_id, seq)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_flow_run_events_run_seq ON flow_run_events(run_id, seq)",
    """
    CREATE TABLE IF NOT EXISTS collaboration_messages (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id       INTEGER NOT NULL,
        seq          INTEGER NOT NULL,
        from_agent   TEXT NOT NULL,
        to_agent     TEXT NOT NULL,
        type         TEXT NOT NULL,
        payload      TEXT NOT NULL DEFAULT '{}',
        priority     INTEGER NOT NULL DEFAULT 0,
        timeout_ms   INTEGER,
        status       TEXT NOT NULL DEFAULT 'queued'
                     CHECK (status IN ('queued','sent','received','failed','timed_out')),
        role_id      TEXT,
        output_index INTEGER,
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES flow_runs(id) ON DELETE CASCADE,
        UNIQUE(run_id, seq)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_collaboration_messages_run_seq ON collaboration_messages(run_id, seq)",
    "CREATE INDEX IF NOT EXISTS idx_collaboration_messages_run_role ON collaboration_messages(run_id, role_id)",
    # Migration: add model column to existing tables
    "ALTER TABLE dialog_flows ADD COLUMN model TEXT DEFAULT 'deepseek-v4-flash'",
    # Migration: persist per-flow sandbox policy.
    "ALTER TABLE dialog_flows ADD COLUMN sandbox_policy TEXT DEFAULT '{}'",
    # Migration: persist per-run artifact/work directories.
    "ALTER TABLE flow_runs ADD COLUMN project_dir TEXT DEFAULT ''",
    # Migration: reserve structured flow metadata for collaboration modes.
    "ALTER TABLE dialog_flows ADD COLUMN flow_spec TEXT DEFAULT '{}'",
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


def _dialog_flows_allows_current_flow_types(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'dialog_flows'"
    ).fetchone()
    sql = row[0] if row and row[0] else ""
    return all(flow_type in sql for flow_type in ("hierarchical", "competitive", "pipeline", "peer_to_peer", "dag"))


def _ensure_dialog_flows_current_flow_types(conn: sqlite3.Connection) -> None:
    if _dialog_flows_allows_current_flow_types(conn):
        return
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("ALTER TABLE dialog_flows RENAME TO dialog_flows_old")
    conn.execute(
        """
        CREATE TABLE dialog_flows (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id     INTEGER DEFAULT 0,
            name         TEXT NOT NULL,
            description  TEXT DEFAULT '',
            flow_type    TEXT NOT NULL CHECK (flow_type IN ('sequential','parallel','hierarchical','competitive','pipeline','peer_to_peer','dag')),
            role_ids     TEXT NOT NULL,
            scenario_id  TEXT DEFAULT '',
            prompt_template TEXT DEFAULT '',
            model        TEXT DEFAULT 'deepseek-v4-flash',
            sandbox_policy TEXT DEFAULT '{}',
            flow_spec    TEXT DEFAULT '{}',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    old_columns = {row[1] for row in conn.execute("PRAGMA table_info(dialog_flows_old)").fetchall()}
    sandbox_expr = "sandbox_policy" if "sandbox_policy" in old_columns else "'{}' AS sandbox_policy"
    flow_spec_expr = "flow_spec" if "flow_spec" in old_columns else "'{}' AS flow_spec"
    conn.execute(
        f"""INSERT INTO dialog_flows
           (id, owner_id, name, description, flow_type, role_ids, scenario_id,
            prompt_template, model, sandbox_policy, flow_spec, created_at, updated_at)
           SELECT id, owner_id, name, description, flow_type, role_ids,
                  scenario_id, prompt_template, model, {sandbox_expr}, {flow_spec_expr}, created_at, updated_at
           FROM dialog_flows_old"""
    )
    conn.execute("DROP TABLE dialog_flows_old")
    conn.execute("PRAGMA foreign_keys=ON")


def _table_sql(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row[0] if row and row[0] else ""


def _table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({name})").fetchall()}


def _column_expr(columns: set[str], name: str, default: str) -> str:
    return name if name in columns else f"{default} AS {name}"


def _ensure_flow_run_foreign_keys_current(conn: sqlite3.Connection) -> None:
    flow_runs_sql = _table_sql(conn, "flow_runs")
    if "dialog_flows_old" not in flow_runs_sql:
        return

    logger.info("repairing flow_runs foreign key target from dialog_flows_old to dialog_flows")
    conn.execute("PRAGMA foreign_keys=OFF")

    flow_run_columns = _table_columns(conn, "flow_runs")
    project_dir_expr = _column_expr(flow_run_columns, "project_dir", "''")
    finished_at_expr = _column_expr(flow_run_columns, "finished_at", "NULL")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flow_runs_new (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id      INTEGER NOT NULL,
            input_text   TEXT DEFAULT '',
            status       TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','running','succeeded','failed','cancelled')),
            error        TEXT DEFAULT '',
            outputs      TEXT NOT NULL DEFAULT '[]',
            started_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at  DATETIME,
            project_dir  TEXT DEFAULT '',
            FOREIGN KEY (flow_id) REFERENCES dialog_flows(id)
        )
        """
    )
    conn.execute(
        f"""INSERT INTO flow_runs_new
            (id, flow_id, input_text, status, error, outputs, started_at, finished_at, project_dir)
           SELECT id, flow_id, input_text, status, error, outputs, started_at, {finished_at_expr}, {project_dir_expr}
           FROM flow_runs"""
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flow_run_events_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL,
            seq         INTEGER NOT NULL,
            event_type  TEXT NOT NULL,
            payload     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES flow_runs(id) ON DELETE CASCADE,
            UNIQUE(run_id, seq)
        )
        """
    )
    if _table_sql(conn, "flow_run_events"):
        conn.execute(
            """INSERT INTO flow_run_events_new
               (id, run_id, seq, event_type, payload, created_at)
               SELECT id, run_id, seq, event_type, payload, created_at
               FROM flow_run_events"""
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS collaboration_messages_new (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id       INTEGER NOT NULL,
            seq          INTEGER NOT NULL,
            from_agent   TEXT NOT NULL,
            to_agent     TEXT NOT NULL,
            type         TEXT NOT NULL,
            payload      TEXT NOT NULL DEFAULT '{}',
            priority     INTEGER NOT NULL DEFAULT 0,
            timeout_ms   INTEGER,
            status       TEXT NOT NULL DEFAULT 'queued'
                         CHECK (status IN ('queued','sent','received','failed','timed_out')),
            role_id      TEXT,
            output_index INTEGER,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES flow_runs(id) ON DELETE CASCADE,
            UNIQUE(run_id, seq)
        )
        """
    )
    if _table_sql(conn, "collaboration_messages"):
        message_columns = _table_columns(conn, "collaboration_messages")
        timeout_expr = _column_expr(message_columns, "timeout_ms", "NULL")
        role_expr = _column_expr(message_columns, "role_id", "NULL")
        output_expr = _column_expr(message_columns, "output_index", "NULL")
        updated_expr = _column_expr(message_columns, "updated_at", "created_at")
        conn.execute(
            f"""INSERT INTO collaboration_messages_new
               (id, run_id, seq, from_agent, to_agent, type, payload, priority,
                timeout_ms, status, role_id, output_index, created_at, updated_at)
               SELECT id, run_id, seq, from_agent, to_agent, type, payload, priority,
                      {timeout_expr}, status, {role_expr}, {output_expr}, created_at, {updated_expr}
               FROM collaboration_messages"""
        )

    conn.execute("DROP TABLE IF EXISTS collaboration_messages")
    conn.execute("DROP TABLE IF EXISTS flow_run_events")
    conn.execute("DROP TABLE flow_runs")
    conn.execute("ALTER TABLE flow_runs_new RENAME TO flow_runs")
    conn.execute("ALTER TABLE flow_run_events_new RENAME TO flow_run_events")
    conn.execute("ALTER TABLE collaboration_messages_new RENAME TO collaboration_messages")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_flow ON flow_runs(flow_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flow_run_events_run_seq ON flow_run_events(run_id, seq)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_collaboration_messages_run_seq ON collaboration_messages(run_id, seq)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_collaboration_messages_run_role ON collaboration_messages(run_id, role_id)")
    conn.execute("PRAGMA foreign_keys=ON")


def _migrate(conn: sqlite3.Connection) -> None:
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            # Ignore "duplicate column" errors from ALTER TABLE
            if "duplicate column" not in str(e).lower():
                raise
    _ensure_dialog_flows_current_flow_types(conn)
    _ensure_flow_run_foreign_keys_current(conn)
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
