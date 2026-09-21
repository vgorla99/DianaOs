"""
Append-only audit/action log for the control plane.

SQLite-backed. Every entry is immutable once written - no update/delete
API is exposed here.

Notes:
- `CREATE TABLE IF NOT EXISTS` does not add columns to an
  already-existing table from an earlier schema version.
  `_migrate_schema()` runs an explicit, idempotent PRAGMA-diff + `ALTER
  TABLE ADD COLUMN` pass on every import, so an existing database gains
  new columns automatically instead of throwing "no column named X" on
  the first insert after an upgrade.
- `read_recent()`/`count_all()` keep an exact, stable 7-column
  projection, so any API response shape built on them never changes just
  because the table grows new columns. `read_recent_full()` returns all
  columns, for callers that need the extended data.
- Redaction: `_redact()` runs on detail/errors/commands/inputs_ref/
  outputs_ref before they're written, stripping common credential/token
  shapes. This is a floor, not a guarantee - callers are still responsible
  for not handing raw secrets to record_action() in the first place.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

from core.control_plane.approval import ApprovalLevel

_DB_PATH = Path(os.getenv("CONTROL_PLANE_DB_PATH", "data/control_plane.db"))
_LOCK = threading.Lock()

_LEGACY_COLUMNS = ("id", "ts", "action", "level", "approved", "path", "detail")

_NEW_COLUMNS: dict[str, str] = {
    "run_id": "TEXT",
    "agent_id": "TEXT",
    "agent_version": "TEXT",
    "skill_id": "TEXT",
    "skill_version": "TEXT",
    "project_id": "TEXT",
    "started_at": "REAL",
    "finished_at": "REAL",
    "status": "TEXT",
    "approval_level_required": "INTEGER",
    "approval_id": "TEXT",
    "approval_result": "TEXT",
    "inputs_ref": "TEXT",
    "outputs_ref": "TEXT",
    "files_read": "TEXT",
    "files_written": "TEXT",
    "commands": "TEXT",
    "errors": "TEXT",
    "evaluator_result": "TEXT",
}

_REDACT_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|bearer)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),  # common API-key-shaped tokens
]


def _redact(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    redacted = text
    for pattern in _REDACT_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                action TEXT NOT NULL,
                level INTEGER NOT NULL,
                approved INTEGER NOT NULL,
                path TEXT,
                detail TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts)")
    _migrate_schema()


def _migrate_schema() -> None:
    """Idempotent additive migration: add any of _NEW_COLUMNS not already
    present on the real, existing audit_log table."""
    with _conn() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
        for column, sql_type in _NEW_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE audit_log ADD COLUMN {column} {sql_type}")


_ensure_table()


def record_action(
    action: str,
    level: ApprovalLevel,
    approved: bool,
    path: Optional[str] = None,
    detail: Optional[str] = None,
    *,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_version: Optional[str] = None,
    skill_id: Optional[str] = None,
    skill_version: Optional[str] = None,
    project_id: Optional[str] = None,
    started_at: Optional[float] = None,
    finished_at: Optional[float] = None,
    status: Optional[str] = None,
    approval_level_required: Optional[int] = None,
    approval_id: Optional[str] = None,
    approval_result: Optional[str] = None,
    inputs_ref: Optional[str] = None,
    outputs_ref: Optional[str] = None,
    files_read: Optional[str] = None,
    files_written: Optional[str] = None,
    commands: Optional[str] = None,
    errors: Optional[str] = None,
    evaluator_result: Optional[str] = None,
) -> int:
    """
    Append one immutable audit record. Returns the new row id. The first 5
    positional params are this module's original signature - every field
    added since is keyword-only with a default, so existing callers keep
    working unmodified across schema upgrades.
    """
    with _LOCK, _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO audit_log (
                ts, action, level, approved, path, detail,
                run_id, agent_id, agent_version, skill_id, skill_version, project_id,
                started_at, finished_at, status,
                approval_level_required, approval_id, approval_result,
                inputs_ref, outputs_ref, files_read, files_written, commands, errors,
                evaluator_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(), action, int(level), int(approved), path, _redact(detail),
                run_id, agent_id, agent_version, skill_id, skill_version, project_id,
                started_at, finished_at, status,
                approval_level_required, approval_id, approval_result,
                _redact(inputs_ref), _redact(outputs_ref), files_read, files_written,
                _redact(commands), _redact(errors),
                evaluator_result,
            ),
        )
        assert cur.lastrowid is not None  # always set after a successful INSERT
        return int(cur.lastrowid)


def read_recent(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """
    Paginated read, newest first. Legacy 7-column projection ONLY - any
    route already relying on this exact response shape must not have it
    change just because the table grows new columns.
    """
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        cols = ", ".join(_LEGACY_COLUMNS)
        rows = conn.execute(
            f"SELECT {cols} FROM audit_log ORDER BY ts DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def read_recent_full(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Paginated read, newest first, ALL columns. Not wired into any API
    route in this release - for callers/tests that need the extended data."""
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY ts DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def count_all() -> int:
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
        return int(row[0])
