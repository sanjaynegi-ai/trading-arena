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
