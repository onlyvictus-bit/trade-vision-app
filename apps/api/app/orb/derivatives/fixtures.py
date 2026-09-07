from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Iterable

from .contracts import FuturesSnapshot, Greeks, OptionChainSnapshot, OptionQuote, OptionStrike, OptionType, digest
from .openalgo import OpenAlgoError


def load_chain_csv(
    path: str | Path,
    *,
    underlying: str,
    underlying_exchange: str,
    expiry_date: date,
    underlying_ltp: float,
    atm_strike: float,
    as_of_ns: int,
    options_exchange: str = "NFO",
) -> OptionChainSnapshot:
    """Replay/fixture loader.

    CSV columns: strike,ce_symbol,ce_ltp,ce_bid,ce_ask,ce_volume,ce_oi,
    ce_lotsize,ce_tick,pe_symbol,pe_ltp,pe_bid,pe_ask,pe_volume,pe_oi,
    pe_lotsize,pe_tick. Missing leg columns may be blank.
    """
    raw = Path(path).read_bytes()
    rows: list[OptionStrike] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for r in csv.DictReader(handle):
            strike = float(r["strike"])

            def leg(prefix: str, kind: OptionType) -> OptionQuote | None:
                symbol = (r.get(f"{prefix}_symbol") or "").strip()
                if not symbol:
                    return None
                # G4: missing exchange contract metadata fails closed at parse time.
                # Fabricated lot_size=1 / tick_size=0.05 corrupts GEX/wall math, so a
                # leg without metadata is rejected, never defaulted. (Real vendor
                # field-name mapping is confirmed at G1 capture.)
                lot_raw = (r.get(f"{prefix}_lotsize") or "").strip()
                tick_raw = (r.get(f"{prefix}_tick") or "").strip()
                if not lot_raw or not tick_raw:
                    raise _ReplayMissing(
                        f"CONTRACT_METADATA_MISSING: {prefix} leg of strike {strike} "
                        f"has no lotsize/tick in {Path(path).name}")
                return OptionQuote(
                    symbol=symbol, option_type=kind, strike=strike,
                    ltp=float(r.get(f"{prefix}_ltp") or 0), bid=float(r.get(f"{prefix}_bid") or 0), ask=float(r.get(f"{prefix}_ask") or 0),
                    volume=float(r.get(f"{prefix}_volume") or 0), oi=float(r.get(f"{prefix}_oi") or 0),
                    lot_size=int(float(lot_raw)), tick_size=float(tick_raw),
                )
            rows.append(OptionStrike(strike=strike, ce=leg("ce", OptionType.CE), pe=leg("pe", OptionType.PE)))
    rows.sort(key=lambda x: x.strike)
    return OptionChainSnapshot(
        source="fixture_csv", source_instance=Path(path).name, underlying=underlying.upper(),
        underlying_exchange=underlying_exchange.upper(), options_exchange=options_exchange.upper(), expiry_date=expiry_date,
        underlying_ltp=underlying_ltp, atm_strike=atm_strike, as_of_ns=as_of_ns, received_ns=as_of_ns,
        rows=tuple(rows), provider_payload_hash=digest({"bytes_sha": __import__('hashlib').sha256(raw).hexdigest()}),
    )


class _ReplayMissing(OpenAlgoError, LookupError):
    """Missing replay fixture or fixture metadata: fail closed, never synthesize.

    Subclasses OpenAlgoError so service/api paths surface it as provider-
    unavailable (503) rather than an unhandled 500.
    """


class FixtureDerivativesProvider:
    """G6: replay-profile provider. Serves recorded canonical snapshots only.

    No network, no credentials, no clock reads: every timestamp returned is the
    recorded one, so PIT ordering is preserved by construction. Exact
    (underlying, expiry) match only — never nearest, never synthesized.
    Fixture files are written by :func:`record_replay_fixture` (from real service
    output) or by tests from canonical factories; both are replay inputs, and the
    G0 vendor-capture rule still governs anything claiming vendor compatibility.
    """

    def __init__(self, replay_dir: str | Path) -> None:
        self.replay_dir = Path(replay_dir)
        self._cache: dict[tuple[str, str], dict] = {}

    def _key(self, underlying: str, expiry: date) -> tuple[str, str]:
        return (underlying.upper(), expiry.isoformat())

    def _load(self, underlying: str, expiry: date) -> dict:
        key = self._key(underlying, expiry)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        path = self.replay_dir / f"{key[0]}_{key[1]}.json"
        if not path.is_file():
            raise _ReplayMissing(f"REPLAY_FIXTURE_MISSING: {path.name}")
        doc = json.loads(path.read_text(encoding="utf-8"))
        self._cache[key] = doc
        return doc

    def expiries(self, symbol: str, exchange: str, instrumenttype: str = "options") -> tuple[date, ...]:
        if instrumenttype != "options":
            return ()
        out = []
        for child in sorted(self.replay_dir.glob(f"{symbol.upper()}_*.json")):
            try:
                out.append(date.fromisoformat(child.stem.rsplit("_", 1)[1]))
            except ValueError:
                continue
        return tuple(sorted(out))

    def resolve_nearest_future(self, underlying: str, derivatives_exchange: str, *, on_or_after: date) -> tuple[str, date] | None:
        for expiry in sorted(self.expiries(underlying, derivatives_exchange)):
            if expiry < on_or_after:
                continue
            doc = self._load(underlying, expiry)
            fut = doc.get("futures")
            if isinstance(fut, dict) and fut.get("symbol"):
                return (str(fut["symbol"]), expiry)
        return None

    def quote(self, symbol: str, exchange: str, *, now_ns: int | None = None, expiry_date: date | None = None) -> FuturesSnapshot:
        for child in sorted(self.replay_dir.glob("*.json")):
            doc = json.loads(child.read_text(encoding="utf-8"))
            fut = doc.get("futures")
            if isinstance(fut, dict) and str(fut.get("symbol", "")).upper() == symbol.upper():
                return FuturesSnapshot.model_validate(fut)
        raise _ReplayMissing(f"REPLAY_FIXTURE_MISSING: no futures {symbol}")

    def option_chain(self, *, underlying: str, exchange: str, expiry_date: date,
                     strike_count: int | None = None, now_ns: int | None = None) -> OptionChainSnapshot:
        doc = self._load(underlying, expiry_date)
        return OptionChainSnapshot.model_validate(doc["chain"])

    def greeks_for_chain(self, chain: OptionChainSnapshot, *, interest_rate_pct: float = 0.0,
                         forward_symbol: str | None = None, batch_size: int = 50) -> tuple[Greeks, ...]:
        doc = self._load(chain.underlying, chain.expiry_date)
        wanted: set[str] = set()
        for row in chain.rows:
            if row.ce is not None:
                wanted.add(row.ce.symbol)
            if row.pe is not None:
                wanted.add(row.pe.symbol)
        out = [Greeks.model_validate(g) for g in doc.get("greeks", [])
               if isinstance(g, dict) and str(g.get("symbol", "")) in wanted]
        return tuple(out)


def record_replay_fixture(replay_dir: str | Path, *, chain: OptionChainSnapshot,
                          futures: FuturesSnapshot | None,
                          greeks: Iterable[Greeks]) -> Path:
    """Persist one replay point from real service output (shadow run or test factory)."""
    replay_dir = Path(replay_dir)
    replay_dir.mkdir(parents=True, exist_ok=True)
    path = replay_dir / f"{chain.underlying.upper()}_{chain.expiry_date.isoformat()}.json"
    doc = {"chain": chain.model_dump(mode="json"),
           "futures": futures.model_dump(mode="json") if futures is not None else None,
           "greeks": [g.model_dump(mode="json") for g in greeks]}
    path.write_text(json.dumps(doc, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return path
