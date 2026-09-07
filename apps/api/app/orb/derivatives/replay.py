from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from .contracts import DerivativesContext, PriceScenario, ScenarioAssessment, digest
from .reasoning import DerivativesScenarioController


@dataclass(frozen=True, slots=True)
class ReplayPoint:
    session_date: date
    decision_ns: int
    scenario: PriceScenario
    context: DerivativesContext


@dataclass(frozen=True, slots=True)
class ReplayAssessment:
    replay_id: str
    session_date: date
    decision_ns: int
    assessment: ScenarioAssessment
    pit_safe: bool
    blockers: tuple[str, ...]


def evaluate_replay(points: Sequence[ReplayPoint], controller: DerivativesScenarioController | None = None) -> tuple[ReplayAssessment, ...]:
    """Strict PIT replay of pre-built canonical contexts.

    A point is rejected if context/scenario availability is after decision time,
    if dates mismatch, or if context is from another symbol. No interpolation
    from later snapshots is permitted.
    """
    controller = controller or DerivativesScenarioController()
    out: list[ReplayAssessment] = []
    for p in sorted(points, key=lambda x: (x.session_date, x.decision_ns, x.scenario.symbol)):
        blockers: list[str] = []
        if p.context.as_of_ns > p.decision_ns:
            blockers.append("FUTURE_DERIVATIVES_CONTEXT")
        if p.scenario.as_of_ns > p.decision_ns:
            blockers.append("FUTURE_PRICE_SCENARIO")
        if p.scenario.session_date != p.session_date:
            blockers.append("SESSION_DATE_MISMATCH")
        if p.context.symbol.upper() != p.scenario.symbol.upper():
            blockers.append("SYMBOL_MISMATCH")
        if p.scenario.expiry_date is not None and p.context.expiry_date != p.scenario.expiry_date:
            blockers.append("EXPIRY_MISMATCH")
        if blockers:
            # We intentionally do not call the controller with invalid PIT data.
            continue
        assessment = controller.evaluate(p.scenario, p.context)
        out.append(ReplayAssessment(
            replay_id=digest({"date": p.session_date.isoformat(), "decision_ns": p.decision_ns,
                              "scenario": p.scenario.model_dump(mode="json"), "context": p.context.context_hash}),
            session_date=p.session_date, decision_ns=p.decision_ns,
            assessment=assessment, pit_safe=True, blockers=(),
        ))
    return tuple(out)


def train_only_dates(all_dates: Sequence[date], holdout_fraction: float) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """Small utility matching the repo's repaired selection discipline."""
    dates = tuple(sorted(set(all_dates)))
    if len(dates) < 2:
        return dates, ()
    split = max(1, min(len(dates) - 1, int(len(dates) * (1.0 - holdout_fraction))))
    return dates[:split], dates[split:]


def expanding_folds(train_dates: Sequence[date], folds: int) -> tuple[tuple[tuple[date, ...], tuple[date, ...]], ...]:
    dates = tuple(sorted(set(train_dates)))
    if not dates or folds <= 0:
        return ()
    # Contiguous validation chunks; each fold trains strictly on earlier chunks.
    chunk = max(1, (len(dates) + folds - 1) // folds)
    chunks = tuple(dates[i:i+chunk] for i in range(0, len(dates), chunk))
    return tuple((tuple(d for c in chunks[:i] for d in c), chunks[i]) for i in range(len(chunks)))
