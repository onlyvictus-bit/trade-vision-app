"""Transactional SQLite checkpoints and append-only event receipts.

One connection per operation; BEGIN IMMEDIATE serializes approval races across
threads AND local processes. SQLITE_BUSY is an error, never permission. Use a
local filesystem, not an unverified network share. Backup using SQLite backup.
"""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path
from typing import Callable
from .contracts import canonical, digest
from .runtime import SessionState


class StoreError(RuntimeError): pass
class Conflict(StoreError): pass


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as c:
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StoreError("UNSUPPORTED_STORE_SCHEMA_VERSION")
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                  account_id TEXT NOT NULL, session_date TEXT NOT NULL,
                  state_json TEXT NOT NULL, state_hash TEXT NOT NULL, tip TEXT NOT NULL,
                  PRIMARY KEY(account_id, session_date));
                CREATE TABLE IF NOT EXISTS events (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  account_id TEXT NOT NULL, session_date TEXT NOT NULL, event_id TEXT NOT NULL,
                  request_json TEXT NOT NULL, request_hash TEXT NOT NULL,
                  response_json TEXT NOT NULL, response_hash TEXT NOT NULL,
                  resulting_state_hash TEXT NOT NULL, parent TEXT NOT NULL, receipt_hash TEXT NOT NULL,
                  UNIQUE(account_id, session_date, event_id));
                CREATE TABLE IF NOT EXISTS sealed_holdout_dates (
                  session_date TEXT PRIMARY KEY, study_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS trials (
                  study_id TEXT PRIMARY KEY, registration_json TEXT NOT NULL,
                  registration_hash TEXT NOT NULL, final_report_json TEXT, final_report_hash TEXT);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        c = sqlite3.connect(str(self.path), timeout=5.0, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute("PRAGMA busy_timeout=5000")
            c.execute("PRAGMA synchronous=FULL")
            c.execute("PRAGMA foreign_keys=ON")
            yield c
        except sqlite3.Error as exc:
            raise StoreError("SQLITE_OPERATION_FAILED_CLOSED:" + type(exc).__name__) from exc
        finally:
            c.close()

    def _load(self, c, account: str, day: str) -> tuple[SessionState | None, str]:
        row = c.execute("SELECT * FROM sessions WHERE account_id=? AND session_date=?", (account,day)).fetchone()
        if row is None:
            return None, "GENESIS"
        payload = json.loads(row["state_json"])
        if digest(payload) != row["state_hash"]:
            raise StoreError("CHECKPOINT_INTEGRITY_FAILED")
        tip = c.execute("SELECT resulting_state_hash,receipt_hash FROM events WHERE account_id=? AND session_date=? ORDER BY sequence DESC LIMIT 1", (account,day)).fetchone()
        if tip is None or tip["resulting_state_hash"] != row["state_hash"] or tip["receipt_hash"] != row["tip"]:
            raise StoreError("CHECKPOINT_LOG_BINDING_FAILED")
        return SessionState.model_validate(payload), row["tip"]

    def load(self, account: str, day: str) -> SessionState | None:
        with self.connection() as c:
            c.execute("BEGIN")
            value = self._load(c, account, day)[0]
            c.execute("COMMIT")
            return value

    def transact(self, account: str, day: str, event_id: str, request: dict,
                 transition: Callable[[SessionState | None], tuple[SessionState, dict]]) -> dict:
        encoded, request_hash = canonical(request), digest(request)
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                previous = c.execute("SELECT * FROM events WHERE account_id=? AND session_date=? AND event_id=?", (account,day,event_id)).fetchone()
                if previous:
                    if previous["request_hash"] != request_hash:
                        raise Conflict("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_CONTENT")
                    response = json.loads(previous["response_json"])
                    if digest(response) != previous["response_hash"]:
                        raise StoreError("EVENT_RESPONSE_INTEGRITY_FAILED")
                    c.execute("COMMIT")
                    return response
                state, parent = self._load(c, account, day)
                updated, response = transition(state)
                state_json, state_hash = canonical(updated), digest(updated)
                response_json, response_hash = canonical(response), digest(response)
                receipt = digest([parent, account, day, event_id, request_hash, response_hash, state_hash])
                c.execute("INSERT INTO events(account_id,session_date,event_id,request_json,request_hash,response_json,response_hash,resulting_state_hash,parent,receipt_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (account,day,event_id,encoded,request_hash,response_json,response_hash,state_hash,parent,receipt))
                c.execute("INSERT INTO sessions VALUES(?,?,?,?,?) ON CONFLICT(account_id,session_date) DO UPDATE SET state_json=excluded.state_json,state_hash=excluded.state_hash,tip=excluded.tip",
                          (account,day,state_json,state_hash,receipt))
                c.execute("COMMIT")
                return response
            except BaseException:
                if c.in_transaction: c.execute("ROLLBACK")
                raise

    def audit(self, account: str, day: str) -> dict:
        with self.connection() as c:
            c.execute("BEGIN")
            integrity = c.execute("PRAGMA quick_check").fetchone()[0]
            rows = c.execute("SELECT * FROM events WHERE account_id=? AND session_date=? ORDER BY sequence", (account,day)).fetchall()
            parent = "GENESIS"
            for row in rows:
                request_hash = digest(json.loads(row["request_json"]))
                response_hash = digest(json.loads(row["response_json"]))
                wanted = digest([parent, account, day, row["event_id"], request_hash, response_hash, row["resulting_state_hash"]])
                if request_hash != row["request_hash"] or response_hash != row["response_hash"] or row["parent"] != parent or wanted != row["receipt_hash"]:
                    raise StoreError("APPEND_LOG_INTEGRITY_FAILED")
                parent = wanted
            self._load(c, account, day)
            c.execute("COMMIT")
            return {"integrity": integrity, "events": len(rows), "tip_hash": parent,
                    "tamper_evident_not_tamper_proof": True}

    def register_trial(self, study_id: str, registration: dict) -> None:
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                for day in registration.get("holdout_dates", []):
                    c.execute("INSERT INTO sealed_holdout_dates(session_date,study_id) VALUES(?,?)", (day,study_id))
                c.execute("INSERT INTO trials(study_id,registration_json,registration_hash) VALUES(?,?,?)",
                          (study_id, canonical(registration), digest(registration)))
                c.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                c.execute("ROLLBACK")
                raise Conflict("STUDY_ALREADY_REGISTERED_DO_NOT_REPEATEDLY_CONSULT_HOLDOUT") from exc

    def finish_trial(self, study_id: str, report: dict) -> None:
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            changed = c.execute("UPDATE trials SET final_report_json=?,final_report_hash=? WHERE study_id=? AND final_report_hash IS NULL",
                                (canonical(report), digest(report), study_id)).rowcount
            if changed != 1:
                c.execute("ROLLBACK")
                raise Conflict("TRIAL_NOT_REGISTERED_OR_FINAL_HOLDOUT_ALREADY_REPORTED")
            c.execute("COMMIT")

    def backup(self, destination: str | Path) -> None:
        target = Path(destination).resolve()
        if target == self.path or target.exists():
            raise ValueError("BACKUP_DESTINATION_MUST_BE_NEW")
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as src, closing(sqlite3.connect(str(target))) as dst:
            src.backup(dst)
