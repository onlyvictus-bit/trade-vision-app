"""Local transactional audit of decisions. This is NOT an order/reservation ledger."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3

from .codec import canonical_json, fingerprint
from .models import Decision, Request


class AuditConflict(RuntimeError):
    """Same decision identity produced a different decision; fail closed."""


class AuditJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("use an on-disk audit path, not transient :memory:")
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL CHECK(schema_version = 1),
                    input_digest TEXT NOT NULL,
                    output_digest TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def record(self, request: Request, decision: Decision) -> bool:
        """Returns True when inserted, False for an identical replay; conflicts raise."""
        input_json, output_json = canonical_json(request), canonical_json(decision)
        expected = fingerprint({"engine": "tradevision-d6-v1", "request": request})
        if decision.decision_id != expected:
            raise AuditConflict("decision does not belong to the supplied request")
        input_digest, output_digest = fingerprint(request), fingerprint(decision)
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "INSERT OR IGNORE INTO decisions VALUES (?, 1, ?, ?, ?, ?)",
                (decision.decision_id, input_digest, output_digest, input_json, output_json),
            )
            inserted = cursor.rowcount == 1
            stored = conn.execute(
                "SELECT input_digest, output_digest FROM decisions WHERE decision_id = ?",
                (decision.decision_id,),
            ).fetchone()
            if stored != (input_digest, output_digest):
                raise AuditConflict("idempotency conflict; earlier decision was not overwritten")
            return inserted

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

    def read(self, decision_id: str) -> tuple[str, str] | None:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT input_json, output_json FROM decisions WHERE decision_id = ?",
                                (decision_id,)).fetchone()
