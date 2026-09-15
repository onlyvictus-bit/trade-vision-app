"""ORB clock-window timing research batch engine (v1.97).

Answers per stock: which opening-range end wins intraday - 09:20 / 09:30 /
09:35 / 09:40 (default windows). Pure research: reuses the proven v1.90
discovery engine unchanged, aggregates per-window results into a leaderboard,
checkpoints after every symbol so long runs are resumable.

No trading authority: research_only / live_trading_blocked on every output.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    OrbDiscoveryRequest,
    OrbTimingLeaderboardEntry,
    OrbTimingResearchJob,
    OrbTimingResearchRequest,
    OrbTimingResearchResult,
    OrbTimingWindowRow,
)
from .candidate_intake import (
    CandidateState,
    OrbCandidateIntakeV1,
    manual_candidate_intake,
    project_eligible_symbols,
    trendforge_candidate_intakes,
)
from .discovery import run_orb_discovery
from .hstry_csv import HstryCsvNotFound, load_hstry_series

ORB_TIMING_RESEARCH_VERSION = "orb-timing-research.v1.97"
ORB_SYMBOL_SHADOW_VERSION = "orb-symbol-shadow.v1"
NO_SIGNIFICANT_DIFFERENCE_THRESHOLD_R = 1.0
EXPLICIT_SYMBOL_LIMIT = 50
TRENDFORGE_INTAKE_SCAN_LIMIT = 5

_JOBS: dict[str, OrbTimingResearchJob] = {}
_LOCK = threading.RLock()

_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "orb_research"


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _explicit_symbols(symbols: list[str]) -> list[str]:
    """Legacy explicit-list projection: strip/upper/dedupe, first 50. Pure."""
    if not symbols:
        raise ValueError("explicit symbols_source requires a non-empty symbols list")
    seen: dict[str, None] = {}
    for raw in symbols:
        clean = str(raw).strip().upper()
        if clean:
            seen.setdefault(clean, None)
    return list(seen)[:EXPLICIT_SYMBOL_LIMIT]


def _scan_trendforge_intakes(intakes: list[dict]) -> tuple[list[str], dict | None]:
    """Legacy intake scan: first intake with READY/PRIORITY_RADAR symbols.

    Returns (symbols, chosen_intake). Empty symbols + None when no intake
    qualifies. Mirrors the historical resolve_symbols() scan exactly.
    """
    for intake in intakes:
        packet = intake.get("packet") if isinstance(intake, dict) else None
        evidence = packet.get("evidence") if isinstance(packet, dict) else None
        candidates = evidence.get("candidates") if isinstance(evidence, dict) else None
        if not isinstance(candidates, list):
            continue
        symbols: list[str] = []
        for row in candidates:
            if not isinstance(row, dict):
                continue
            if row.get("state") in {"READY", "PRIORITY_RADAR"}:
                symbol = str(row.get("symbol") or "").strip().upper()
                if symbol and symbol not in symbols:
                    symbols.append(symbol)
        if symbols:
            return symbols[:EXPLICIT_SYMBOL_LIMIT], intake if isinstance(intake, dict) else None
    return [], None


def _load_recent_intakes() -> list[dict]:
    from .. import storage

    return storage.list_trendforge_intakes(limit=TRENDFORGE_INTAKE_SCAN_LIMIT)


def resolve_symbols(request: OrbTimingResearchRequest) -> list[str]:
    if request.symbols_source == "explicit":
        return _explicit_symbols(request.symbols)

    # trendforge_latest: READY / PRIORITY_RADAR candidates from latest accepted intake
    symbols, _ = _scan_trendforge_intakes(_load_recent_intakes())
    if symbols:
        return symbols
    raise ValueError("trendforge_latest found no READY/PRIORITY_RADAR candidates in recent intakes")


# ---------------------------------------------------------------------------
# BUILD-1 shadow: canonical candidate intake on the active runtime path.
#
# Research-only. resolve_symbols_with_shadow() runs on every run_timing_research()
# call: legacy symbols still drive the run, but the canonical shadow observes the
# same resolution and emits a parity receipt. For trendforge_latest, a shadow
# divergence (stale/unvalidated evidence visible to legacy but refused by the
# canonical adapter) fails the run closed instead of silently activating research.
# For explicit user-supplied symbols there is no evidence trust involved, so the
# run proceeds on legacy output with the divergence recorded.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrbSymbolShadowReceiptV1:
    """Point-in-time receipt comparing legacy vs canonical symbol resolution."""

    shadow_version: str
    symbols_source: str
    selection_cutoff: str  # UTC ISO instant captured once per resolution
    legacy_symbols: tuple[str, ...]
    canonical_symbols: tuple[str, ...]
    parity: bool
    mismatches: tuple[str, ...]  # LEGACY_ONLY:<SYM> / CANONICAL_ONLY:<SYM>
    candidate_hashes: tuple[str, ...]
    provenance: str  # "manual" or the TrendForge intakeId
    shadow_error: str | None  # canonical-build failure; legacy output unaffected
    # BUILD-1 observability: aggregate counters over the canonical candidates.
    candidate_count: int = 0
    eligible_count: int = 0
    source_count: int = 0
    reason_count: int = 0
    instrument_type_counts: tuple[tuple[str, int], ...] = ()
    universe_scope_counts: tuple[tuple[str, int], ...] = ()
    availability_counts: tuple[tuple[str, int], ...] = ()
    # Wall-clock canonical-build latency. Excluded from receipt_hash so that
    # deterministic replay stays byte-identical across runs.
    latency_ms: float = 0.0
    receipt_hash: str = ""


def _receipt_hash(payload: dict) -> str:
    return _hash(payload)


def _observe_candidates(candidates: list[OrbCandidateIntakeV1]) -> dict[str, object]:
    """Aggregate BUILD-1 observability counters over canonical candidates."""
    instruments: Counter[str] = Counter()
    scopes: Counter[str] = Counter()
    availabilities: Counter[str] = Counter()
    sources: set[str] = set()
    reasons = 0
    eligible = 0
    for candidate in candidates:
        instruments[candidate.instrument_type.value] += 1
        scopes[candidate.universe_scope.value] += 1
        reasons += len(candidate.reasons)
        sources.add(candidate.source_record_id)
        for fact in candidate.source_facts:
            availabilities[fact.availability.value] += 1
        if candidate.state is CandidateState.ELIGIBLE_FOR_STUDY:
            eligible += 1
    return {
        "candidate_count": len(candidates),
        "eligible_count": eligible,
        "source_count": len(sources),
        "reason_count": reasons,
        "instrument_type_counts": tuple(sorted(instruments.items())),
        "universe_scope_counts": tuple(sorted(scopes.items())),
        "availability_counts": tuple(sorted(availabilities.items())),
    }


def _finalize_shadow_receipt(
    *,
    symbols_source: str,
    selection_cutoff: str,
    legacy_symbols: list[str],
    canonical_symbols: list[str],
    mismatches: list[str],
    candidate_hashes: list[str],
    provenance: str,
    shadow_error: str | None,
    parity: bool,
    candidate_count: int = 0,
    eligible_count: int = 0,
    source_count: int = 0,
    reason_count: int = 0,
    instrument_type_counts: tuple[tuple[str, int], ...] = (),
    universe_scope_counts: tuple[tuple[str, int], ...] = (),
    availability_counts: tuple[tuple[str, int], ...] = (),
    latency_ms: float = 0.0,
) -> OrbSymbolShadowReceiptV1:
    payload = {
        "shadow_version": ORB_SYMBOL_SHADOW_VERSION,
        "symbols_source": symbols_source,
        "selection_cutoff": selection_cutoff,
        "legacy_symbols": list(legacy_symbols),
        "canonical_symbols": list(canonical_symbols),
        "parity": parity,
        "mismatches": list(mismatches),
        "candidate_hashes": list(candidate_hashes),
        "provenance": provenance,
        "shadow_error": shadow_error,
        "candidate_count": candidate_count,
        "eligible_count": eligible_count,
        "source_count": source_count,
        "reason_count": reason_count,
        "instrument_type_counts": [list(item) for item in instrument_type_counts],
        "universe_scope_counts": [list(item) for item in universe_scope_counts],
        "availability_counts": [list(item) for item in availability_counts],
    }
    return OrbSymbolShadowReceiptV1(
        shadow_version=payload["shadow_version"],
        symbols_source=payload["symbols_source"],
        selection_cutoff=payload["selection_cutoff"],
        legacy_symbols=tuple(payload["legacy_symbols"]),
        canonical_symbols=tuple(payload["canonical_symbols"]),
        parity=payload["parity"],
        mismatches=tuple(payload["mismatches"]),
        candidate_hashes=tuple(payload["candidate_hashes"]),
        provenance=payload["provenance"],
        shadow_error=payload["shadow_error"],
        candidate_count=candidate_count,
        eligible_count=eligible_count,
        source_count=source_count,
        reason_count=reason_count,
        instrument_type_counts=instrument_type_counts,
        universe_scope_counts=universe_scope_counts,
        availability_counts=availability_counts,
        latency_ms=latency_ms,
        receipt_hash=_receipt_hash(payload),
    )


def manual_shadow_candidates(
    symbols: list[str], *, selection_cutoff: datetime
) -> list[OrbCandidateIntakeV1]:
    """Deterministic manual receipts for legacy explicit symbols.

    One captured cutoff serves every symbol, so replay with the identical
    cutoff reproduces identical candidate hashes.
    """
    if selection_cutoff.tzinfo is None or selection_cutoff.utcoffset() is None:
        raise ValueError("selection_cutoff must be timezone-aware")
    cutoff = selection_cutoff.astimezone(timezone.utc)
    return [manual_candidate_intake(symbol, selected_at=cutoff) for symbol in _explicit_symbols(symbols)]


def compare_symbol_shadow(
    legacy_symbols: list[str], canonical_symbols: list[str]
) -> tuple[bool, list[str]]:
    """Exact-order parity check. Differences become explicit mismatch codes."""
    mismatches: list[str] = []
    legacy_set = set(legacy_symbols)
    canonical_set = set(canonical_symbols)
    for symbol in legacy_symbols:
        if symbol not in canonical_set:
            mismatches.append(f"LEGACY_ONLY:{symbol}")
    for symbol in canonical_symbols:
        if symbol not in legacy_set:
            mismatches.append(f"CANONICAL_ONLY:{symbol}")
    if not mismatches and list(canonical_symbols) != list(legacy_symbols):
        mismatches.append("ORDER_DIVERGENCE")
    return (not mismatches, mismatches)


def resolve_symbols_with_shadow(
    request: OrbTimingResearchRequest,
    *,
    selection_cutoff: datetime | None = None,
    intakes: list[dict] | None = None,
) -> tuple[list[str], list[OrbCandidateIntakeV1], OrbSymbolShadowReceiptV1]:
    """Legacy symbols plus parallel canonical candidates plus parity receipt.

    Legacy errors propagate exactly as resolve_symbols() raises them today.
    A canonical-build failure is recorded on the receipt (parity False) and
    never alters the returned legacy symbols.
    """
    if request.symbols_source == "explicit":
        legacy_symbols = _explicit_symbols(request.symbols)
        cutoff = (selection_cutoff or datetime.now(timezone.utc)).astimezone(timezone.utc)
        started = time.perf_counter()
        try:
            candidates = manual_shadow_candidates(request.symbols, selection_cutoff=cutoff)
            canonical_symbols = project_eligible_symbols(candidates)
            shadow_error: str | None = None
        except Exception as exc:  # noqa: BLE001 - shadow must not break legacy resolution
            candidates = []
            canonical_symbols = []
            shadow_error = f"{type(exc).__name__}: {exc}"
        latency_ms = (time.perf_counter() - started) * 1000.0
        parity, mismatches = compare_symbol_shadow(legacy_symbols, canonical_symbols)
        if shadow_error is not None:
            parity = False
            mismatches = [*mismatches, f"SHADOW_ERROR:{shadow_error}"]
        receipt = _finalize_shadow_receipt(
            symbols_source="explicit",
            selection_cutoff=cutoff.isoformat(),
            legacy_symbols=legacy_symbols,
            canonical_symbols=canonical_symbols,
            mismatches=mismatches,
            candidate_hashes=[c.candidate_hash for c in candidates],
            provenance="manual",
            shadow_error=shadow_error,
            parity=parity,
            latency_ms=latency_ms,
            **_observe_candidates(candidates),
        )
        return legacy_symbols, candidates, receipt

    scanned = _load_recent_intakes() if intakes is None else intakes
    legacy_symbols, chosen = _scan_trendforge_intakes(scanned)
    if not legacy_symbols:
        raise ValueError("trendforge_latest found no READY/PRIORITY_RADAR candidates in recent intakes")
    provenance = str((chosen or {}).get("intakeId") or "trendforge-unknown")
    started = time.perf_counter()
    try:
        candidates = trendforge_candidate_intakes(chosen or {})
        canonical_symbols = project_eligible_symbols(candidates)
        shadow_error = None
    except Exception as exc:  # noqa: BLE001 - shadow must not break legacy resolution
        candidates = []
        canonical_symbols = []
        shadow_error = f"{type(exc).__name__}: {exc}"
    latency_ms = (time.perf_counter() - started) * 1000.0
    parity, mismatches = compare_symbol_shadow(legacy_symbols, canonical_symbols)
    if shadow_error is not None:
        parity = False
        mismatches = [*mismatches, f"SHADOW_ERROR:{shadow_error}"]
    # The PIT cutoff is the accepted receipt's receivedAt. It must survive even
    # when the canonical adapter correctly yields zero candidates (stale input):
    # an empty cutoff would make the divergence unreplayable.
    cutoff_iso = _received_at_iso(chosen)
    if candidates:
        cutoff_iso = candidates[0].selection_cutoff.astimezone(timezone.utc).isoformat()
    receipt = _finalize_shadow_receipt(
        symbols_source="trendforge_latest",
        selection_cutoff=cutoff_iso,
        legacy_symbols=legacy_symbols,
        canonical_symbols=canonical_symbols,
        mismatches=mismatches,
        candidate_hashes=[c.candidate_hash for c in candidates],
        provenance=provenance,
        shadow_error=shadow_error,
        parity=parity,
        latency_ms=latency_ms,
        **_observe_candidates(candidates),
    )
    return legacy_symbols, candidates, receipt


def _received_at_iso(chosen: dict | None) -> str:
    """Best-effort PIT cutoff from a TrendForge receipt; never raises."""
    try:
        raw = str((chosen or {}).get("receivedAt") or "")
        if not raw:
            return ""
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        return ""


def _checkpoint_path(request_hash: str) -> Path:
    directory = _DATA_DIR / "checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{request_hash[:16]}.json"


def _load_checkpoint(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_checkpoint(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _extract_window_rows(
    symbol: str,
    windows: list[tuple[str, str]],
    discovery_payload: dict,
) -> tuple[list[OrbTimingWindowRow], int]:
    ranked = discovery_payload.get("ranked_combinations") or []
    session_days = len({trade.get("local_session_date") for trade in discovery_payload.get("trades") or []})
    no_leak = bool(discovery_payload.get("no_future_leakage", True))
    rows: list[OrbTimingWindowRow] = []
    for window in windows:
        matches = [
            item
            for item in ranked
            if isinstance(item, dict) and item.get("clock_window") == list(window)
        ]
        best = max(matches, key=lambda m: m.get("composite_score", 0.0)) if matches else None
        rows.append(
            OrbTimingWindowRow(
                symbol=symbol,
                clock_window=window,
                best_combo_id=(best or {}).get("combo_id"),
                strategy_family=(best or {}).get("strategy_family"),
                reward_risk_ratio=(best or {}).get("reward_risk_ratio"),
                require_volume_confirmation=(best or {}).get("require_volume_confirmation"),
                trade_count=int((best or {}).get("trade_count") or 0),
                win_rate=float((best or {}).get("win_rate") or 0.0),
                profit_factor=float((best or {}).get("profit_factor") or 0.0),
                net_r=float((best or {}).get("net_r") or 0.0),
                consistency=float((best or {}).get("profitable_period_rate") or 0.0),
                max_drawdown_r=float((best or {}).get("max_drawdown_r") or 0.0),
                composite_score=float((best or {}).get("composite_score") or 0.0),
                minimum_trades_pass=bool((best or {}).get("minimum_trades_pass")),
                no_future_leakage=no_leak,
            )
        )
    return rows, session_days


def aggregate_leaderboard(
    rows_by_symbol: dict[str, list[OrbTimingWindowRow]],
    days_by_symbol: dict[str, int],
) -> tuple[list[OrbTimingLeaderboardEntry], dict[str, int]]:
    leaderboard: list[OrbTimingLeaderboardEntry] = []
    win_counts: Counter[str] = Counter()
    for symbol in sorted(rows_by_symbol):
        rows = sorted(rows_by_symbol[symbol], key=lambda r: r.composite_score, reverse=True)
        passing = [r for r in rows if r.minimum_trades_pass]
        entry = OrbTimingLeaderboardEntry(symbol=symbol, session_days=days_by_symbol.get(symbol, 0))
        if not passing:
            entry.verdict = "INSUFFICIENT_DATA"
            entry.top_composite_score = rows[0].composite_score if rows else 0.0
            leaderboard.append(entry)
            continue
        top = passing[0]
        entry.best_window_composite = top.clock_window
        entry.top_composite_score = top.composite_score
        entry.composite_spread = round(top.composite_score - passing[1].composite_score, 8) if len(passing) > 1 else 0.0
        entry.verdict = (
            "NO_SIGNIFICANT_DIFFERENCE"
            if len(passing) > 1 and entry.composite_spread < NO_SIGNIFICANT_DIFFERENCE_THRESHOLD_R
            else "OK"
        )
        entry.best_window_consistency = max(passing, key=lambda r: (r.consistency, r.net_r)).clock_window
        entry.best_window_net_r = max(passing, key=lambda r: (r.net_r, r.composite_score)).clock_window
        if entry.verdict == "OK":
            win_counts[f"{top.clock_window[0]}-{top.clock_window[1]}"] += 1
        leaderboard.append(entry)
    return leaderboard, dict(win_counts)


def run_timing_research(
    request: OrbTimingResearchRequest,
    *,
    base_dir: Path | None = None,
    progress=None,
) -> OrbTimingResearchResult:
    """Blocking batch run. `progress(done, total, current_symbol)` optional callback."""
    request_payload = request.model_dump(mode="json")
    request_hash = _hash(request_payload)
    run_id = str(uuid5(NAMESPACE_URL, f"tradevision:orb-timing:{request_hash}"))

    # BUILD-1 shadow on the active path: one captured cutoff per run, legacy
    # symbols drive the run, the canonical shadow observes. A trendforge_latest
    # divergence (stale/unvalidated evidence visible to legacy but refused by
    # the canonical adapter) fails the run closed before any research runs.
    run_cutoff = datetime.now(timezone.utc)
    symbols, _shadow_candidates, shadow_receipt = resolve_symbols_with_shadow(
        request, selection_cutoff=run_cutoff
    )
    if request.symbols_source == "trendforge_latest" and not shadow_receipt.parity:
        raise ValueError(
            "trendforge_latest intake failed closed on shadow divergence: "
            + ";".join(shadow_receipt.mismatches)
        )

    cp_path = _checkpoint_path(request_hash)
    checkpoint = _load_checkpoint(cp_path)
    completed_rows: dict[str, list[OrbTimingWindowRow]] = {
        symbol: [OrbTimingWindowRow.model_validate(r) for r in rows]
        for symbol, rows in (checkpoint.get("rows") or {}).items()
        if symbol in symbols
    }
    days_by_symbol: dict[str, int] = {
        str(symbol): int(days) for symbol, days in (checkpoint.get("days") or {}).items()
    }
    failed: dict[str, str] = dict(checkpoint.get("failed") or {})

    total = len(symbols)
    done = 0
    for symbol in symbols:
        if symbol in completed_rows:
            done += 1
            if progress:
                progress(done, total, symbol)
            continue
        try:
            series = load_hstry_series(
                symbol,
                request.timeframe,
                start_date=request.start_date,
                end_date=request.end_date,
                base_dir=base_dir,
                max_bars=400_000 if request.timeframe == "1m" else None,
            )
            discovery_request = OrbDiscoveryRequest(
                series=series,
                strategy_families=request.strategy_families,
                orb_bar_counts=[3],
                clock_windows=request.clock_windows,
                reward_risk_grid=request.reward_risk_grid,
                volume_confirmation_grid=request.volume_confirmation_grid,
                maximum_combinations=request.maximum_combinations,
                minimum_trades=request.minimum_trades,
            )
            discovery_result = run_orb_discovery(discovery_request)
            payload = discovery_result.model_dump(mode="json")
            rows, session_days = _extract_window_rows(symbol, request.clock_windows, payload)
            completed_rows[symbol] = rows
            days_by_symbol[symbol] = session_days
        except (HstryCsvNotFound, ValueError) as exc:
            failed[symbol] = f"{type(exc).__name__}: {exc}"
        done += 1
        if progress:
            progress(done, total, symbol)
        _save_checkpoint(
            cp_path,
            {
                "version": ORB_TIMING_RESEARCH_VERSION,
                "rows": {s: [x.model_dump(mode="json") for x in rows] for s, rows in completed_rows.items()},
                "days": days_by_symbol,
                "failed": failed,
            },
        )

    leaderboard, universe_counts = aggregate_leaderboard(completed_rows, days_by_symbol)

    result_payload = {
        "result_version": ORB_TIMING_RESEARCH_VERSION,
        "run_id": run_id,
        "request_hash": request_hash,
        "timeframe": request.timeframe,
        "clock_windows": [list(w) for w in request.clock_windows],
        "symbols_requested": symbols,
        "symbols_completed": sorted(completed_rows),
        "symbols_failed": failed,
        "rows": [row.model_dump(mode="json") for symbol in symbols for row in completed_rows.get(symbol, [])],
        "leaderboard": [entry.model_dump(mode="json") for entry in leaderboard],
        "universe_window_win_counts": universe_counts,
        "no_significant_difference_threshold_r": NO_SIGNIFICANT_DIFFERENCE_THRESHOLD_R,
        "research_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    # The shadow receipt carries a wall-clock cutoff/latency, so it rides
    # alongside the result and is deliberately excluded from the deterministic
    # hash: identical requests must replay to identical hashes.
    symbol_shadow = {
        "shadow_version": shadow_receipt.shadow_version,
        "symbols_source": shadow_receipt.symbols_source,
        "selection_cutoff": shadow_receipt.selection_cutoff,
        "parity": shadow_receipt.parity,
        "mismatches": list(shadow_receipt.mismatches),
        "provenance": shadow_receipt.provenance,
        "shadow_error": shadow_receipt.shadow_error,
        "receipt_hash": shadow_receipt.receipt_hash,
        "counts": {
            "candidate_count": shadow_receipt.candidate_count,
            "eligible_count": shadow_receipt.eligible_count,
            "source_count": shadow_receipt.source_count,
            "reason_count": shadow_receipt.reason_count,
            "instrument_type_counts": dict(shadow_receipt.instrument_type_counts),
            "universe_scope_counts": dict(shadow_receipt.universe_scope_counts),
            "availability_counts": dict(shadow_receipt.availability_counts),
        },
        "latency_ms": shadow_receipt.latency_ms,
    }
    return OrbTimingResearchResult(
        **result_payload, deterministic_hash=_hash(result_payload), symbol_shadow=symbol_shadow
    )


def persist_run(result: OrbTimingResearchResult) -> None:
    """Save the run to SQLite (orb_timing_runs / orb_timing_rows). Idempotent by run_id."""
    from .. import storage

    storage.save_orb_timing_run(result.model_dump(mode="json"))


_CSV_COLUMNS = [
    "symbol", "window", "family", "rr", "volume", "trades", "win_rate",
    "profit_factor", "net_r", "consistency", "max_drawdown_r", "composite",
    "min_trades_pass", "no_future_leakage",
]


def export_csv_bytes(result: OrbTimingResearchResult) -> bytes:
    """Byte-stable leaderboard CSV: fixed columns, sorted rows, fixed float precision."""
    lines = [",".join(_CSV_COLUMNS)]
    rows = sorted(
        result.rows,
        key=lambda r: (r.symbol, r.clock_window[0], r.clock_window[1]),
    )
    for r in rows:
        lines.append(
            ",".join(
                [
                    r.symbol,
                    f"{r.clock_window[0]}-{r.clock_window[1]}",
                    r.strategy_family or "",
                    "" if r.reward_risk_ratio is None else f"{r.reward_risk_ratio:.6f}",
                    "" if r.require_volume_confirmation is None else ("1" if r.require_volume_confirmation else "0"),
                    str(r.trade_count),
                    f"{r.win_rate:.6f}",
                    f"{r.profit_factor:.6f}",
                    f"{r.net_r:.6f}",
                    f"{r.consistency:.6f}",
                    f"{r.max_drawdown_r:.6f}",
                    f"{r.composite_score:.6f}",
                    "1" if r.minimum_trades_pass else "0",
                    "1" if r.no_future_leakage else "0",
                ]
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_summary_markdown(result: OrbTimingResearchResult) -> str:
    by_symbol: dict[str, list[OrbTimingWindowRow]] = {}
    for row in result.rows:
        by_symbol.setdefault(row.symbol, []).append(row)
    entry_by_symbol = {e.symbol: e for e in result.leaderboard}

    lines = [
        f"# ORB Timing Research — {result.run_id}",
        "",
        f"- Version: {result.result_version}",
        f"- Timeframe: {result.timeframe}",
        f"- Windows: {' | '.join(f'{w[0]}-{w[1]}' for w in result.clock_windows)}",
        f"- Symbols completed/failed: {len(result.symbols_completed)}/{len(result.symbols_failed)}",
        f"- Universe window wins: {json.dumps(result.universe_window_win_counts, sort_keys=True)}",
        f"- Safety: research_only=true, trade_allowed=false, live_trading_blocked=true",
        "",
    ]
    for symbol in result.symbols_requested:
        entry = entry_by_symbol.get(symbol)
        if entry is None:
            reason = result.symbols_failed.get(symbol, "no data")
            lines += [f"## {symbol}", f"- FAILED: {reason}", ""]
            continue
        lines += [
            f"## {symbol} — {entry.verdict} (days={entry.session_days})",
            f"- Best composite: {entry.best_window_composite} score={entry.top_composite_score:.3f} spread={entry.composite_spread:.3f}",
            f"- Best consistency: {entry.best_window_consistency}",
            f"- Best net R: {entry.best_window_net_r}",
        ]
        for row in sorted(by_symbol.get(symbol, []), key=lambda r: r.composite_score, reverse=True):
            lines.append(
                f"  - {row.clock_window[0]}-{row.clock_window[1]}: trades={row.trade_count} "
                f"wr={row.win_rate:.2f} pf={row.profit_factor:.2f} netR={row.net_r:.2f} "
                f"consistency={row.consistency:.2f} composite={row.composite_score:.2f} "
                f"family={row.strategy_family} rr={row.reward_risk_ratio}"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_run_exports(
    result: OrbTimingResearchResult,
    out_dir: Path | None = None,
) -> dict[str, Path]:
    """Write {run_id}.json + leaderboard.csv + summary.md under data/orb_research/."""
    directory = out_dir if out_dir is not None else _DATA_DIR
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{result.run_id}.json"
    csv_path = directory / f"{result.run_id}_leaderboard.csv"
    summary_path = directory / f"{result.run_id}_summary.md"
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    csv_path.write_bytes(export_csv_bytes(result))
    summary_path.write_text(build_summary_markdown(result), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "summary": summary_path}


def submit_timing_research(request: OrbTimingResearchRequest) -> OrbTimingResearchJob:
    request_payload = request.model_dump(mode="json")
    request_hash = _hash(request_payload)
    job_id = str(uuid5(NAMESPACE_URL, f"tradevision:orb-timing-job:{request_hash}"))
    job = OrbTimingResearchJob(
        job_version=ORB_TIMING_RESEARCH_VERSION,
        job_id=job_id,
        request_hash=request_hash,
        status="queued",
        progress_pct=0.0,
    )
    with _LOCK:
        _JOBS[job_id] = job
    return job


def run_timing_research_job(job_id: str, request: OrbTimingResearchRequest) -> None:
    def _progress(done: int, total: int, current: str) -> None:
        pct = round((done / total) * 100.0, 2) if total else 100.0
        with _LOCK:
            job = _JOBS.get(job_id)
            if job is not None:
                _JOBS[job_id] = job.model_copy(
                    update={"progress_pct": pct, "current_symbol": current, "status": "running"}, deep=True
                )

    _update_job(job_id, status="running", progress_pct=1.0)
    try:
        result = run_timing_research(request, progress=_progress)
        persist_error = None
        try:
            persist_run(result)
            write_run_exports(result)
        except Exception as exc:  # noqa: BLE001 - persistence failure must not lose the research result
            persist_error = f"{type(exc).__name__}: {exc}"
        _update_job(
            job_id,
            status="completed",
            progress_pct=100.0,
            current_symbol=None,
            result=result,
            error=persist_error,
        )
    except Exception as exc:  # noqa: BLE001 - job boundary mirrors discovery.py behaviour
        _update_job(job_id, status="failed", progress_pct=100.0, error=f"{type(exc).__name__}: {exc}")


def get_timing_research_job(job_id: str) -> OrbTimingResearchJob | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return None if job is None else job.model_copy(deep=True)


def clear_timing_research_jobs() -> None:
    with _LOCK:
        _JOBS.clear()


def _update_job(job_id: str, **updates) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        _JOBS[job_id] = job.model_copy(update=updates, deep=True)
