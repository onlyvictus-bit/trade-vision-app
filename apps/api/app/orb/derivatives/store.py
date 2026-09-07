from __future__ import annotations

import json
import sqlite3
import threading
import zlib
from pathlib import Path
from typing import Iterable, Sequence

from .contracts import DerivativesContext, FuturesSnapshot, OptionChainSnapshot

SCHEMA_VERSION = 1


class DerivativesStore:
    """Append-only PIT snapshot store using SQLite WAL.

    Full snapshots are zlib-compressed canonical JSON. Indexed metadata enables
    previous-snapshot lookup without decompressing unrelated rows.
    """

    def __init__(self, path: str | Path) -> None:
        raw = str(path)
        # G8: ":memory:" previously lost its schema because every operation opened
        # a brand-new private in-memory DB. Use a named shared-cache DB and hold one
        # (never used, only kept open) connection so the schema survives across ops.
        self._memory = raw == ":memory:"
        self.path = f"file:orb_deriv_mem_{id(self):x}?mode=memory&cache=shared" if self._memory else raw
        self._lock = threading.RLock()
        if not self._memory:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._keepalive = self._connect() if self._memory else None
        self._init()

    def close(self) -> None:
        if self._keepalive is not None:
            self._keepalive.close()
            self._keepalive = None

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5.0, uri=self._memory)
        if not self._memory:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA foreign_keys=ON")
        con.row_factory = sqlite3.Row
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS derivative_meta(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS option_chain_snapshot(
                    snapshot_hash TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    expiry_date TEXT NOT NULL,
                    as_of_ns INTEGER NOT NULL,
                    received_ns INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    payload BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chain_symbol_expiry_time
                  ON option_chain_snapshot(symbol, expiry_date, as_of_ns DESC);
                CREATE TABLE IF NOT EXISTS futures_snapshot(
                    snapshot_hash TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    as_of_ns INTEGER NOT NULL,
                    received_ns INTEGER NOT NULL,
                    payload BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_fut_symbol_time
                  ON futures_snapshot(symbol, as_of_ns DESC);
                CREATE TABLE IF NOT EXISTS derivatives_context(
                    context_hash TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    expiry_date TEXT NOT NULL,
                    as_of_ns INTEGER NOT NULL,
                    atm_iv_pct REAL,
                    payload BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ctx_symbol_time
                  ON derivatives_context(symbol, as_of_ns DESC);
                """
            )
            con.execute("INSERT OR REPLACE INTO derivative_meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))

    @staticmethod
    def _pack(model) -> bytes:
        raw = model.model_dump_json().encode("utf-8")
        return zlib.compress(raw, level=6)

    @staticmethod
    def _unpack(blob: bytes, cls):
        return cls.model_validate_json(zlib.decompress(blob))

    def put_chain(self, snapshot: OptionChainSnapshot) -> None:
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO option_chain_snapshot VALUES(?,?,?,?,?,?,?)",
                (snapshot.snapshot_hash, snapshot.underlying, snapshot.expiry_date.isoformat(), snapshot.as_of_ns,
                 snapshot.received_ns, snapshot.source, self._pack(snapshot)),
            )

    def previous_chain(self, symbol: str, expiry_date: str, before_ns: int) -> OptionChainSnapshot | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT payload FROM option_chain_snapshot WHERE symbol=? AND expiry_date=? AND as_of_ns<? ORDER BY as_of_ns DESC LIMIT 1",
                (symbol.upper(), expiry_date, before_ns),
            ).fetchone()
        return None if row is None else self._unpack(row["payload"], OptionChainSnapshot)

    def put_futures(self, snapshot: FuturesSnapshot) -> None:
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO futures_snapshot VALUES(?,?,?,?,?)",
                (snapshot.snapshot_hash, snapshot.symbol, snapshot.as_of_ns, snapshot.received_ns, self._pack(snapshot)),
            )

    def previous_futures(self, symbol: str, before_ns: int) -> FuturesSnapshot | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT payload FROM futures_snapshot WHERE symbol=? AND as_of_ns<? ORDER BY as_of_ns DESC LIMIT 1",
                (symbol.upper(), before_ns),
            ).fetchone()
        return None if row is None else self._unpack(row["payload"], FuturesSnapshot)

    def put_context(self, context: DerivativesContext) -> None:
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO derivatives_context VALUES(?,?,?,?,?,?)",
                (context.context_hash, context.symbol, context.expiry_date.isoformat(), context.as_of_ns,
                 context.atm_iv_pct, self._pack(context)),
            )

    def iv_history(self, symbol: str, *, before_ns: int, limit: int = 252) -> tuple[float, ...]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT atm_iv_pct FROM derivatives_context WHERE symbol=? AND as_of_ns<? AND atm_iv_pct IS NOT NULL ORDER BY as_of_ns DESC LIMIT ?",
                (symbol.upper(), before_ns, limit),
            ).fetchall()
        return tuple(float(r["atm_iv_pct"]) for r in reversed(rows))
