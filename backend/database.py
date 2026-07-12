"""Storage helpers for persisted account snapshots and activity logs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "accounts.db"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _normalize_name(name: str) -> str:
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("name must not be empty")
    return normalized


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                name TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                datetime TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_logs_name_id
            ON logs (name, id)
            """
        )


def write_account(name: str, account_dict: dict[str, Any]) -> None:
    """Create or replace the stored JSON snapshot for one account.

    The account name is normalized to lowercase before writing, so callers can
    use user-facing names without worrying about case-sensitive duplicates. The
    dictionary should already be JSON-compatible, such as the output of a
    Pydantic model's `model_dump(mode="json")`.
    """

    normalized_name = _normalize_name(name)
    account_json = json.dumps(account_dict, sort_keys=True)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO accounts (name, data)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET data = excluded.data
            """,
            (normalized_name, account_json),
        )


def read_account(name: str) -> dict[str, Any] | None:
    """Read one account snapshot from SQLite by lowercase-normalized name.

    Returns the decoded JSON dictionary when an account exists, or `None` when
    no account has been stored for that name. This function does not validate
    the account shape; model validation is handled by `backend.accounts.Account`.
    """

    normalized_name = _normalize_name(name)

    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM accounts WHERE name = ?",
            (normalized_name,),
        ).fetchone()

    if row is None:
        return None
    return json.loads(row[0])


def write_log(name: str, type: str, message: str) -> None:
    """Append a timestamped activity log entry for an account.

    Logs are stored separately from account snapshots so reads, buys, sells, and
    other events can be inspected without changing the account JSON structure.
    Names are normalized to lowercase, timestamps are recorded in UTC ISO 8601
    format, and the `type` value is a short category such as `buy`, `sell`, or
    `report`.
    """

    normalized_name = _normalize_name(name)
    timestamp = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, ?, ?, ?)
            """,
            (normalized_name, timestamp, type, message),
        )


def read_log(name: str, last_n: int = 10) -> list[dict[str, Any]]:
    """Return the most recent log entries for an account.

    The account name is normalized to lowercase and up to `last_n` rows are
    returned. Results are ordered oldest-to-newest within the requested recent
    window so callers can display them chronologically. Passing a value below
    one returns an empty list.
    """

    normalized_name = _normalize_name(name)
    if last_n < 1:
        return []

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, datetime, type, message
            FROM logs
            WHERE name = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (normalized_name, last_n),
        ).fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "datetime": row[2],
            "type": row[3],
            "message": row[4],
        }
        for row in reversed(rows)
    ]


_init_db()
