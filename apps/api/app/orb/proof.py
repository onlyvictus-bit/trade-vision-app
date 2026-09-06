from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleSeries,
    OrbComboMetrics,
    OrbComboProof,
    OrbDiscoveryRequest,
    OrbPlaybook,
    OrbPlaybookPromotionRequest,
    OrbProofReport,
    OrbProofRequest,
    OrbStrategyConfig,
    OrbWalkForwardFold,
    now_iso,
)
from .discovery import run_orb_discovery


ORB_PROOF_VERSION = "orb-proof.v1.91"
ORB_PLAYBOOK_VERSION = "orb-playbook.v1.91"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
ORB_PROOF_STORE_PATH = PROJECT_ROOT / "data" / "orb_proofs.json"
ORB_PLAYBOOK_STORE_PATH = PROJECT_ROOT / "data" / "orb_playbooks.json"
_STORE_LOCK = RLock()


def run_orb_proof(request: OrbProofRequest) -> OrbProofReport:
    dates = _dates(request.discovery_request.series)
    full = run_orb_discovery(request.discovery_request)
    if len(dates) < 2:
        train_dates = dates
        holdout_dates: list[str] = []
    else:
        split = max(1, min(len(dates) - 1, int(len(dates) * (1.0 - request.holdout_fraction))))
        train_dates = dates[:split]
        holdout_dates = dates[split:]
    holdout = _run_subset(request.discovery_request, holdout_dates)
    folds = _fold_dates(dates, request.walk_forward_folds)
    fold_results = [
        (fold_id, fold_dates, _run_subset(request.discovery_request, fold_dates))
        for fold_id, fold_dates in folds
    ]
    combo_proofs = [
        _prove_combo(
            metrics,
            holdout,
            fold_results,
            request,
        )
        for metrics in full.ranked_combinations[: request.top_k]
    ]
    request_hash = _hash(request.model_dump(mode="json"))
    proof_id = str(uuid5(NAMESPACE_URL, f"tradevision:orb-proof:{request_hash}"))
    payload = {
        "proof_version": ORB_PROOF_VERSION,
        "proof_id": proof_id,
        "request_hash": request_hash,
        "symbol": request.discovery_request.series.symbol.upper(),
        "timeframe": request.discovery_request.series.timeframe,
        "train_dates": train_dates,
        "holdout_dates": holdout_dates,
        "combo_proofs": [item.model_dump(mode="json") for item in combo_proofs],
        "eligible_combo_ids": [
            item.combo_id for item in combo_proofs if item.promotion_eligible
        ],
        "deterministic": True,
        "no_future_leakage": full.no_future_leakage
        and all(
            item.overall_metrics.no_future_leakage
            for item in combo_proofs
        ),
    }
    report = OrbProofReport(
        **payload,
        proof_hash=_hash(payload),
    )
    _save_record(ORB_PROOF_STORE_PATH, proof_id, report.model_dump(mode="json"))
    return report


def load_orb_proof(proof_id: str) -> OrbProofReport | None:
    payload = _load_records(ORB_PROOF_STORE_PATH).get(proof_id)
    return None if payload is None else OrbProofReport.model_validate(payload)


def promote_orb_playbook(request: OrbPlaybookPromotionRequest) -> OrbPlaybook:
    proof = load_orb_proof(request.proof_id)
    if proof is None:
        raise KeyError(f"ORB proof {request.proof_id} was not found")
    combo = next(
        (item for item in proof.combo_proofs if item.combo_id == request.combo_id),
        None,
    )
    if combo is None:
        raise KeyError(f"ORB combo {request.combo_id} was not found in proof")
    if not combo.promotion_eligible:
        raise ValueError("ORB combo did not pass OOS/walk-forward promotion gates")
    config = _config_from_metrics(combo.overall_metrics)
    playbook_id = str(
        uuid5(
            NAMESPACE_URL,
            f"tradevision:orb-playbook:{proof.symbol}:{proof.timeframe}:{combo.combo_id}:{proof.proof_hash}",
        )
    )
    playbook = OrbPlaybook(
        playbook_version=ORB_PLAYBOOK_VERSION,
        playbook_id=playbook_id,
        symbol=proof.symbol,
        timeframe=proof.timeframe,
        combo_id=combo.combo_id,
        config=config,
        proof_id=proof.proof_id,
        proof_hash=proof.proof_hash,
        metrics=combo.overall_metrics,
        promoted_by=request.promoted_by,
        promoted_at=now_iso(),
    )
    records = _load_records(ORB_PLAYBOOK_STORE_PATH)
    for key, value in list(records.items()):
        if (
            value.get("symbol") == playbook.symbol
            and value.get("timeframe") == playbook.timeframe
            and value.get("status") == "active"
        ):
            value["status"] = "retired"
            records[key] = value
    records[playbook_id] = playbook.model_dump(mode="json")
    _write_records(ORB_PLAYBOOK_STORE_PATH, records)
    return playbook


def list_orb_playbooks(
    *,
    symbol: str | None = None,
    timeframe: str | None = None,
    active_only: bool = True,
) -> list[OrbPlaybook]:
    records = [
        OrbPlaybook.model_validate(payload)
        for payload in _load_records(ORB_PLAYBOOK_STORE_PATH).values()
    ]
    filtered = [
        item
        for item in records
        if (symbol is None or item.symbol == symbol.upper())
        and (timeframe is None or item.timeframe == timeframe)
        and (not active_only or item.status == "active")
    ]
    return sorted(filtered, key=lambda item: (item.symbol, item.timeframe, item.playbook_id))


def _prove_combo(
    overall: OrbComboMetrics,
    holdout_result,
    fold_results,
    request: OrbProofRequest,
) -> OrbComboProof:
    holdout = _find_metrics(holdout_result, overall.combo_id)
    oos_reasons = _pass_reasons(
        holdout,
        minimum_trades=request.thresholds.minimum_oos_trades,
        minimum_pf=request.thresholds.minimum_oos_profit_factor,
        minimum_net=request.thresholds.minimum_oos_net_r,
    )
    oos_pass = not oos_reasons
    fold_reports: list[OrbWalkForwardFold] = []
    for fold_id, dates, result in fold_results:
        metrics = _find_metrics(result, overall.combo_id)
        reasons = _pass_reasons(
            metrics,
            minimum_trades=max(1, request.thresholds.minimum_oos_trades // 2),
            minimum_pf=request.thresholds.minimum_oos_profit_factor,
            minimum_net=request.thresholds.minimum_oos_net_r,
        )
        fold_reports.append(
            OrbWalkForwardFold(
                fold_id=fold_id,
                start_date=dates[0] if dates else "",
                end_date=dates[-1] if dates else "",
                metrics=metrics,
                passed=not reasons,
                reasons=reasons,
            )
        )
    pass_rate = (
        sum(1 for fold in fold_reports if fold.passed) / len(fold_reports)
        if fold_reports
        else 0.0
    )
    repeated = pass_rate >= request.thresholds.minimum_walk_forward_pass_rate
    overall_pass = overall.trade_count >= request.thresholds.minimum_overall_trades
    reasons: list[str] = []
    if not overall_pass:
        reasons.append(
            f"Overall trades {overall.trade_count} are below "
            f"{request.thresholds.minimum_overall_trades}."
        )
    reasons.extend(f"OOS: {reason}" for reason in oos_reasons)
    if not repeated:
        reasons.append(
            f"Walk-forward pass rate {pass_rate:.2f} is below "
            f"{request.thresholds.minimum_walk_forward_pass_rate:.2f}."
        )
    return OrbComboProof(
        combo_id=overall.combo_id,
        overall_metrics=overall,
        holdout_metrics=holdout,
        walk_forward_folds=fold_reports,
        oos_passed=oos_pass,
        walk_forward_pass_rate=round(pass_rate, 8),
        repeated_success_passed=repeated,
        promotion_eligible=overall_pass and oos_pass and repeated,
        reasons=reasons,
    )


def _pass_reasons(
    metrics: OrbComboMetrics | None,
    *,
    minimum_trades: int,
    minimum_pf: float,
    minimum_net: float,
) -> list[str]:
    if metrics is None:
        return ["No matching combo metrics were produced."]
    reasons = []
    if metrics.trade_count < minimum_trades:
        reasons.append(f"Trades {metrics.trade_count} < {minimum_trades}.")
    if metrics.profit_factor < minimum_pf:
        reasons.append(f"Profit factor {metrics.profit_factor:.3f} < {minimum_pf:.3f}.")
    if metrics.net_r <= minimum_net:
        reasons.append(f"Net R {metrics.net_r:.3f} <= {minimum_net:.3f}.")
    return reasons


def _run_subset(request: OrbDiscoveryRequest, dates: list[str]):
    series = _series_for_dates(request.series, dates)
    return run_orb_discovery(
        request.model_copy(
            update={
                "series": series,
                "minimum_trades": 1,
            }
        )
    )


def _series_for_dates(series: CandleSeries, dates: list[str]) -> CandleSeries:
    allowed = set(dates)
    bars = [
        bar
        for bar in series.bars
        if _date_for_bar(bar.timestamp_ns) in allowed
    ]
    return CandleSeries(
        symbol=series.symbol,
        timeframe=series.timeframe,
        bars=bars,
        snapshot_id=f"{series.snapshot_id or 'orb'}:{_hash(sorted(allowed))[:12]}",
        schema_version=series.schema_version,
    )


def _dates(series: CandleSeries) -> list[str]:
    return sorted({_date_for_bar(bar.timestamp_ns) for bar in series.bars})


def _date_for_bar(timestamp_ns: int) -> str:
    local = datetime.fromtimestamp(
        timestamp_ns / 1_000_000_000,
        tz=timezone.utc,
    ) + timedelta(minutes=330)
    return str(local.date())


def _fold_dates(dates: list[str], requested: int):
    if not dates:
        return []
    fold_count = min(requested, len(dates))
    size = max(1, len(dates) // fold_count)
    folds = []
    for index in range(fold_count):
        start = index * size
        end = len(dates) if index == fold_count - 1 else min(len(dates), (index + 1) * size)
        chunk = dates[start:end]
        if chunk:
            folds.append((f"WF-{index + 1:02d}", chunk))
    return folds


def _find_metrics(result, combo_id: str) -> OrbComboMetrics | None:
    return next(
        (item for item in result.ranked_combinations if item.combo_id == combo_id),
        None,
    )


def _config_from_metrics(metrics: OrbComboMetrics) -> OrbStrategyConfig:
    values = {
        "strategy_family": metrics.strategy_family,
        "range_mode": metrics.range_mode,
        "reward_risk_ratio": metrics.reward_risk_ratio,
        "require_volume_confirmation": metrics.require_volume_confirmation,
    }
    if metrics.range_mode == "bar_count":
        values["orb_bar_count"] = metrics.orb_bar_count or 3
    elif metrics.clock_window:
        values["range_start"], values["range_end"] = metrics.clock_window
    return OrbStrategyConfig(**values)


def _save_record(path: Path, key: str, payload: dict) -> None:
    records = _load_records(path)
    records[key] = payload
    _write_records(path, records)


def _load_records(path: Path) -> dict[str, dict]:
    with _STORE_LOCK:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}


def _write_records(path: Path, records: dict[str, dict]) -> None:
    with _STORE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(records, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()

# BEGIN AFRE_V3_OPT_IN_ADDITION
def run_adaptive_orb_proof(days, controllers, *, holdout_start, thresholds=None):
    """Training-only selection; does not reuse or relabel legacy BEL proof."""
    from .adaptive.research import prove_policies
    from .adaptive.governance import code_fingerprint
    return prove_policies(days, controllers, holdout_start=holdout_start,
                          code_hash=code_fingerprint(), thresholds=thresholds)
# END AFRE_V3_OPT_IN_ADDITION
