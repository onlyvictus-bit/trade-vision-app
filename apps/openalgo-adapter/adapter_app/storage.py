from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any


_lock = Lock()


def db_path() -> Path:
    configured = os.environ.get("TRADEVISION_ADAPTER_DB")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "data" / "openalgo_adapter_receipts.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _lock, connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS intent_receipts (
                idempotency_key TEXT PRIMARY KEY,
                delivery_id TEXT NOT NULL,
                package_hash TEXT NOT NULL,
                received_at TEXT NOT NULL,
                receipt_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_intent_receipts_delivery ON intent_receipts(delivery_id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS service_nonces (
                nonce TEXT PRIMARY KEY,
                service_id TEXT NOT NULL,
                received_at INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_service_nonces_time ON service_nonces(received_at)"
        )


def load_receipt(idempotency_key: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT receipt_json FROM intent_receipts WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    return json.loads(row["receipt_json"]) if row else None


def save_receipt(idempotency_key: str, receipt: dict[str, Any]) -> bool:
    with _lock, connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO intent_receipts
            (idempotency_key, delivery_id, package_hash, received_at, receipt_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO NOTHING
            """,
            (
                idempotency_key,
                receipt["delivery_id"],
                receipt["package_hash"],
                receipt["received_at"],
                json.dumps(receipt, sort_keys=True, separators=(",", ":")),
            ),
        )
        return cursor.rowcount == 1


def receipt_count() -> int:
    with connect() as connection:
        return int(connection.execute("SELECT COUNT(*) AS n FROM intent_receipts").fetchone()["n"])


def claim_nonce(nonce: str, service_id: str, received_at: int) -> bool:
    with _lock, connect() as connection:
        connection.execute("DELETE FROM service_nonces WHERE received_at < ?", (received_at - 300,))
        cursor = connection.execute(
            """
            INSERT INTO service_nonces (nonce, service_id, received_at)
            VALUES (?, ?, ?)
            ON CONFLICT(nonce) DO NOTHING
            """,
            (nonce, service_id, received_at),
        )
        return cursor.rowcount == 1
