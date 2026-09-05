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
from collections import Counter
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
from .discovery import run_orb_discovery
from .hstry_csv import HstryCsvNotFound, load_hstry_series

ORB_TIMING_RESEARCH_VERSION = "orb-timing-research.v1.97"
NO_SIGNIFICANT_DIFFERENCE_THRESHOLD_R = 1.0

_JOBS: dict[str, OrbTimingResearchJob] = {}
_LOCK = threading.RLock()

_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "orb_research"


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def resolve_symbols(request: OrbTimingResearchRequest) -> list[str]:
    if request.symbols_source == "explicit":
        if not request.symbols:
            raise ValueError("explicit symbols_source requires a non-empty symbols list")
        seen: dict[str, None] = {}
        for raw in request.symbols:
            clean = str(raw).strip().upper()
            if clean:
                seen.setdefault(clean, None)
        return list(seen)[:50]

    # trendforge_latest: READY / PRIORITY_RADAR candidates from latest accepted intake
    from .. import storage

    intakes = storage.list_trendforge_intakes(limit=5)
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
            return symbols[:50]
    raise ValueError("trendforge_latest found no READY/PRIORITY_RADAR candidates in recent intakes")


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

    symbols = resolve_symbols(request)

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
    return OrbTimingResearchResult(**result_payload, deterministic_hash=_hash(result_payload))


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
