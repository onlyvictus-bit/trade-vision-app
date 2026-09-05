from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    SimulatedExecutionCostBreakdown,
    SimulatedPaperLifecycleObservationRequest,
    SimulatedPaperLifecycleOutcome,
)
from .atomic_json_store import load_record_map, update_record_map
from .orb_guidance import load_guidance_ticket
from .paper_guidance_config import (
    PaperGuidanceStorageConfig,
    load_paper_guidance_storage_config,
)
from .point_in_time_guard import timeframe_duration_ns
from .simulated_paper_ledger import load_simulated_paper_trade


ORB_PAPER_OUTCOME_VERSION = "orb-paper-lifecycle.v1.94"
ORB_PAPER_OUTCOME_STORE_PATH = (
    load_paper_guidance_storage_config().outcome_store_path
)


def evaluate_simulated_paper_lifecycle(
    request: SimulatedPaperLifecycleObservationRequest,
    *,
    config: PaperGuidanceStorageConfig | None = None,
) -> SimulatedPaperLifecycleOutcome:
    settings = config or load_paper_guidance_storage_config()
    paper = load_simulated_paper_trade(request.paper_record_id)
    if paper is None:
        raise KeyError(f"Simulated paper record {request.paper_record_id} was not found")
    ticket = load_guidance_ticket(paper.guidance_id)
    if ticket is None:
        raise ValueError("Paper record is orphaned because its guidance ticket is missing")
    _validate_identity(request, paper, ticket)
    bars = _validated_observation_bars(request, ticket.decision_time_ns, settings)
    observation_hash = _hash(
        {
            "series": request.series.model_dump(mode="json"),
            "observation_time_ns": request.observation_time_ns,
            "max_holding_bars": request.max_holding_bars,
        }
    )

    completed = _completed_outcome_for_paper(paper.paper_record_id)
    if completed is not None:
        return completed

    outcome = _build_outcome(
        request=request,
        paper=paper,
        ticket=ticket,
        bars=bars,
        observation_hash=observation_hash,
        settings=settings,
    )

    def _upsert(records: dict[str, dict]):
        existing = records.get(outcome.outcome_id)
        if existing is not None:
            return records, SimulatedPaperLifecycleOutcome.model_validate(existing)
        records[outcome.outcome_id] = outcome.model_dump(mode="json")
        return records, outcome

    return update_record_map(ORB_PAPER_OUTCOME_STORE_PATH, _upsert)


def list_simulated_paper_outcomes(
    *,
    paper_record_id: str | None = None,
    playbook_id: str | None = None,
    completed_only: bool = False,
) -> list[SimulatedPaperLifecycleOutcome]:
    rows = [
        SimulatedPaperLifecycleOutcome.model_validate(payload)
        for payload in load_record_map(ORB_PAPER_OUTCOME_STORE_PATH).values()
    ]
    filtered = [
        item
        for item in rows
        if (paper_record_id is None or item.paper_record_id == paper_record_id)
        and (playbook_id is None or item.playbook_id == playbook_id)
        and (not completed_only or item.completed)
    ]
    return sorted(
        filtered,
        key=lambda item: (
            item.observation_time_ns,
            item.outcome_id,
        ),
        reverse=True,
    )


def paper_outcome_store_rows() -> dict[str, dict]:
    return load_record_map(ORB_PAPER_OUTCOME_STORE_PATH)


def _completed_outcome_for_paper(
    paper_record_id: str,
) -> SimulatedPaperLifecycleOutcome | None:
    rows = list_simulated_paper_outcomes(
        paper_record_id=paper_record_id,
        completed_only=True,
    )
    return rows[0] if rows else None


def _validate_identity(request, paper, ticket) -> None:
    mismatches: list[str] = []
    if request.source_snapshot_hash != paper.source_snapshot_hash:
        mismatches.append("paper source snapshot")
    if ticket.source_snapshot_hash != paper.source_snapshot_hash:
        mismatches.append("guidance source snapshot")
    if ticket.guidance_id != paper.guidance_id:
        mismatches.append("guidance id")
    if ticket.playbook_id != paper.playbook_id:
        mismatches.append("playbook id")
    if ticket.proof_id != paper.proof_id or ticket.proof_hash != paper.proof_hash:
        mismatches.append("proof identity")
    if request.series.symbol.upper() != paper.symbol:
        mismatches.append("symbol")
    if request.series.timeframe != paper.timeframe:
        mismatches.append("timeframe")
    if mismatches:
        raise ValueError(
            "Lifecycle observation identity mismatch: " + ", ".join(mismatches)
        )


def _validated_observation_bars(
    request: SimulatedPaperLifecycleObservationRequest,
    decision_time_ns: int,
    settings: PaperGuidanceStorageConfig,
) -> list[CandleBar]:
    bars = list(request.series.bars)
    if not bars:
        raise ValueError("Lifecycle observation requires at least one closed candle")
    limit = min(request.max_holding_bars, settings.maximum_observation_bars)
    if len(bars) > limit:
        raise ValueError(
            f"Lifecycle observation has {len(bars)} candles; maximum is {limit}"
        )
    timestamps = [bar.timestamp_ns for bar in bars]
    if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
        raise ValueError("Lifecycle candles must be unique and strictly chronological")
    sequences = [bar.sequence_number for bar in bars]
    if any(current != previous + 1 for previous, current in zip(sequences, sequences[1:])):
        raise ValueError("Lifecycle candle sequence has a missing or duplicate bar")
    duration_ns = timeframe_duration_ns(request.series.timeframe)
    for bar in bars:
        if bar.timestamp_ns < decision_time_ns:
            raise ValueError(
                "Lifecycle observation contains a candle from before the guidance decision"
            )
        if bar.timestamp_ns + duration_ns > request.observation_time_ns:
            raise ValueError(
                "Lifecycle observation contains an incomplete or future candle"
            )
        if not (
            bar.high >= max(bar.open, bar.close)
            and bar.low <= min(bar.open, bar.close)
            and bar.high >= bar.low
        ):
            raise ValueError("Lifecycle observation contains invalid OHLC geometry")
    return bars


def _build_outcome(
    *,
    request,
    paper,
    ticket,
    bars: list[CandleBar],
    observation_hash: str,
    settings: PaperGuidanceStorageConfig,
) -> SimulatedPaperLifecycleOutcome:
    fill_index, base_fill = _first_fill(paper.side, paper.entry, bars)
    if fill_index is None or base_fill is None:
        completed = len(bars) >= request.max_holding_bars
        return _outcome(
            request=request,
            paper=paper,
            ticket=ticket,
            observation_hash=observation_hash,
            fill_index=None,
            fill_price=None,
            exit_price=None,
            label="NO_FILL" if completed else "PENDING",
            completed=completed,
            bars=bars,
            same_bar=False,
            conservative=False,
            target_offset=None,
            stop_offset=None,
            settings=settings,
            reason=(
                "Entry trigger was not reached within the completed observation window."
                if completed
                else "Entry trigger has not been reached; lifecycle remains pending."
            ),
        )

    fill_price = _adverse_fill_price(paper.side, base_fill, settings)
    post_fill = bars[fill_index:]
    (
        label,
        completed,
        exit_price,
        target_offset,
        stop_offset,
        same_bar,
        conservative,
        reason,
    ) = _resolve_exit(
        paper.side,
        paper.stop,
        paper.target,
        post_fill,
        request.max_holding_bars,
    )
    return _outcome(
        request=request,
        paper=paper,
        ticket=ticket,
        observation_hash=observation_hash,
        fill_index=fill_index,
        fill_price=fill_price,
        exit_price=exit_price,
        label=label,
        completed=completed,
        bars=bars,
        same_bar=same_bar,
        conservative=conservative,
        target_offset=target_offset,
        stop_offset=stop_offset,
        settings=settings,
        reason=reason,
    )


def _outcome(
    *,
    request,
    paper,
    ticket,
    observation_hash: str,
    fill_index: int | None,
    fill_price: float | None,
    exit_price: float | None,
    label: str,
    completed: bool,
    bars: list[CandleBar],
    same_bar: bool,
    conservative: bool,
    target_offset: int | None,
    stop_offset: int | None,
    settings: PaperGuidanceStorageConfig,
    reason: str,
) -> SimulatedPaperLifecycleOutcome:
    mark = exit_price
    if mark is None and fill_index is not None:
        mark = bars[-1].close
    risk_per_unit = (
        max(abs(paper.entry - paper.stop), 1e-9)
        if fill_price is None
        else max(abs(fill_price - paper.stop), 1e-9)
    )
    after_fill = [] if fill_index is None else bars[fill_index:]
    mfe, mae = _mfe_mae(paper.side, fill_price, after_fill)
    gross_r = (
        0.0
        if fill_price is None or mark is None
        else _directional_move(paper.side, paper.entry, mark) / risk_per_unit
    )
    costs = _costs(
        paper.entry,
        mark,
        risk_per_unit,
        filled=fill_price is not None,
        settings=settings,
    )
    net_r = gross_r - costs.total_cost_r
    outcome_id = str(
        uuid5(
            NAMESPACE_URL,
            "tradevision:orb-paper-outcome:v1.94:"
            + paper.paper_record_id
            + ":"
            + observation_hash
            + ":"
            + str(request.max_holding_bars),
        )
    )
    payload = {
        "outcome_version": ORB_PAPER_OUTCOME_VERSION,
        "outcome_id": outcome_id,
        "paper_record_id": paper.paper_record_id,
        "guidance_id": paper.guidance_id,
        "playbook_id": paper.playbook_id,
        "proof_id": paper.proof_id,
        "proof_hash": paper.proof_hash,
        "symbol": paper.symbol,
        "timeframe": paper.timeframe,
        "source_snapshot_hash": paper.source_snapshot_hash,
        "observation_snapshot_hash": observation_hash,
        "decision_time_ns": ticket.decision_time_ns,
        "observation_time_ns": request.observation_time_ns,
        "side": paper.side,
        "entry_trigger": paper.entry,
        "simulated_fill_price": (
            None if fill_price is None else round(fill_price, 8)
        ),
        "exit_price": None if mark is None else round(mark, 8),
        "stop": paper.stop,
        "target": paper.target,
        "fill_status": "NOT_FILLED" if fill_price is None else "FILLED",
        "lifecycle_status": (
            "COMPLETED"
            if completed
            else "PENDING_TRIGGER"
            if fill_price is None
            else "OPEN"
        ),
        "outcome_label": label,
        "completed": completed,
        "bars_observed": len(bars),
        "bars_to_fill": None if fill_index is None else fill_index + 1,
        "bars_to_target": (
            None
            if fill_index is None or target_offset is None
            else fill_index + target_offset + 1
        ),
        "bars_to_stop": (
            None
            if fill_index is None or stop_offset is None
            else fill_index + stop_offset + 1
        ),
        "same_bar_ambiguous": same_bar,
        "conservative_stop_first_used": conservative,
        "mfe": round(mfe, 8),
        "mae": round(mae, 8),
        "gross_r": round(gross_r, 8),
        "net_r": round(net_r, 8),
        "costs": costs.model_dump(mode="json"),
        "reason": reason,
        "point_in_time_safe": True,
        "no_future_leakage": True,
        "deterministic": True,
        "simulation_only": True,
        "human_approved_source": True,
        "automatic_fill_attempted": False,
        "external_execution_attempted": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    return SimulatedPaperLifecycleOutcome(
        **payload,
        integrity_hash=_hash(payload),
    )


def _first_fill(
    side: str,
    entry: float,
    bars: Iterable[CandleBar],
) -> tuple[int | None, float | None]:
    for index, bar in enumerate(bars):
        if side == "LONG":
            if bar.open >= entry:
                return index, bar.open
            if bar.high >= entry:
                return index, entry
        else:
            if bar.open <= entry:
                return index, bar.open
            if bar.low <= entry:
                return index, entry
    return None, None


def _adverse_fill_price(
    side: str,
    base_fill: float,
    settings: PaperGuidanceStorageConfig,
) -> float:
    friction_bps = (
        settings.spread_bps / 2.0
        + settings.slippage_bps
        + settings.impact_bps
    )
    multiplier = 1.0 + friction_bps / 10_000.0
    if side == "SHORT":
        multiplier = 1.0 - friction_bps / 10_000.0
    return max(base_fill * multiplier, 1e-9)


def _resolve_exit(
    side: str,
    stop: float,
    target: float,
    bars: list[CandleBar],
    max_holding_bars: int,
):
    for offset, bar in enumerate(bars[:max_holding_bars]):
        stop_hit = bar.low <= stop if side == "LONG" else bar.high >= stop
        target_hit = bar.high >= target if side == "LONG" else bar.low <= target
        if stop_hit and target_hit:
            return (
                "STOP_HIT",
                True,
                stop,
                offset,
                offset,
                True,
                True,
                "Stop and target touched in one OHLCV bar; conservative stop-first rule applied.",
            )
        if stop_hit:
            return (
                "STOP_HIT",
                True,
                stop,
                None,
                offset,
                False,
                False,
                "Stop was reached before target in the closed-candle replay.",
            )
        if target_hit:
            return (
                "TARGET_HIT",
                True,
                target,
                offset,
                None,
                False,
                False,
                "Target was reached before stop in the closed-candle replay.",
            )
    if len(bars) >= max_holding_bars:
        return (
            "TIME_EXIT",
            True,
            bars[max_holding_bars - 1].close,
            None,
            None,
            False,
            False,
            "Maximum holding window completed without target or stop.",
        )
    return (
        "PENDING",
        False,
        None,
        None,
        None,
        False,
        False,
        "Paper lifecycle is open; more closed replay candles are required.",
    )


def _mfe_mae(
    side: str,
    fill_price: float | None,
    bars: list[CandleBar],
) -> tuple[float, float]:
    if fill_price is None or not bars:
        return 0.0, 0.0
    if side == "LONG":
        return (
            max(0.0, max(bar.high - fill_price for bar in bars)),
            max(0.0, max(fill_price - bar.low for bar in bars)),
        )
    return (
        max(0.0, max(fill_price - bar.low for bar in bars)),
        max(0.0, max(bar.high - fill_price for bar in bars)),
    )


def _directional_move(side: str, entry: float, exit_price: float) -> float:
    return exit_price - entry if side == "LONG" else entry - exit_price


def _costs(
    entry: float,
    exit_price: float | None,
    risk_per_unit: float,
    *,
    filled: bool,
    settings: PaperGuidanceStorageConfig,
) -> SimulatedExecutionCostBreakdown:
    if not filled:
        total_cost = 0.0
    else:
        friction_bps = (
            settings.spread_bps / 2.0
            + settings.slippage_bps
            + settings.impact_bps
        )
        entry_cost = entry * friction_bps / 10_000.0
        exit_cost = (
            0.0
            if exit_price is None
            else exit_price
            * (settings.spread_bps / 2.0 + settings.slippage_bps)
            / 10_000.0
        )
        brokerage_cost = (
            entry + (exit_price if exit_price is not None else entry)
        ) * settings.brokerage_bps / 10_000.0
        total_cost = entry_cost + exit_cost + brokerage_cost
    return SimulatedExecutionCostBreakdown(
        spread_bps=settings.spread_bps,
        slippage_bps=settings.slippage_bps,
        impact_bps=settings.impact_bps,
        brokerage_bps=settings.brokerage_bps,
        total_cost_per_unit=round(total_cost, 8),
        total_cost_r=round(total_cost / max(risk_per_unit, 1e-9), 8),
    )


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
