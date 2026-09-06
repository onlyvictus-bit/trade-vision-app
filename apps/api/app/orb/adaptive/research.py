"""Exact controller replay and train-only policy selection.

Data dates, not rows/symbols, are split. All symbols compete under one fixed
account budget. The final holdout never selects a policy. A strategy passing
this software's DECLARED gates is not a guarantee of future profitability.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Literal, Callable
from statistics import mean
from pydantic import Field, model_validator
from .contracts import (Frozen, SafeOutput, PriorContext, Bar, Capability, Policy, AccountLimits,
                        SafetyState, NS, MINUTE, clock_ns, digest, evolve)
from .controller import Controller
from .runtime import SessionState, EventBatch, new_session, advance_session, accept_proposal
from .execution import mark_unknown
from .value import lower_mean_bound


class ResearchMarket(Frozen):
    prior: PriorContext
    feature_bars: Annotated[tuple[Bar, ...], Field(max_length=400)]
    execution_bars: Annotated[tuple[Bar, ...], Field(max_length=400)]
    capabilities: tuple[Capability, ...] = ()


class ResearchDay(Frozen):
    session_date: str
    markets: Annotated[tuple[ResearchMarket, ...], Field(min_length=1, max_length=100)]
    source_origin: Literal["REAL_ATTESTED", "SYNTHETIC"]
    source_manifest_hash: Annotated[str, Field(min_length=16)]
    completeness_attested: bool

    @model_validator(mode="after")
    def valid(self):
        clock_ns(self.session_date, 555)
        if len({m.prior.symbol for m in self.markets}) != len(self.markets):
            raise ValueError("DUPLICATE_RESEARCH_SYMBOL")
        for m in self.markets:
            for bars in (m.feature_bars, m.execution_bars):
                keys = [b.open_ns for b in bars]
                if keys != sorted(set(keys)):
                    raise ValueError("RESEARCH_INPUT_MUST_BE_UNIQUE_AND_ORDERED")
        return self


class DailyResult(SafeOutput):
    session_date: str
    policy_hash: str
    source_origin: str
    status: Literal["COMPLETE", "UNKNOWN"]
    net_budget_units: float | None
    net_pnl: float | None
    entry_filled: bool
    accepted_attempt: bool
    end_state: SessionState


def _complete_intervals(bars: tuple[Bar, ...], start: int, end: int, minutes: int) -> bool:
    wanted = list(range(start, end, minutes * MINUTE))
    selected = [b for b in bars if start <= b.open_ns < end]
    return [b.open_ns for b in selected] == wanted and all(b.minutes == minutes and b.revision == 0 for b in selected)


def replay_day(day: ResearchDay, controller: Controller, *, retain_decisions: Callable | None = None) -> DailyResult:
    p, limits = controller.policy, controller.limits
    state = new_session(day.session_date, tuple(m.prior for m in day.markets), p, limits)
    groups = defaultdict(lambda: {"features": [], "execution": [], "capabilities": {}})
    stop = clock_ns(day.session_date, p.flat_minute)
    for market in day.markets:
        for b in market.feature_bars:
            if b.available_ns <= stop + p.max_feature_lag_seconds * NS:
                groups[b.available_ns]["features"].append(b)
        for b in market.execution_bars:
            if b.available_ns <= stop + p.max_feature_lag_seconds * NS:
                groups[b.available_ns]["execution"].append(b)
        for c in market.capabilities:
            groups[max(c.available_ns, state.watermark_ns)]["capabilities"].setdefault(market.prior.symbol, []).append(c)
    safety = SafetyState(mode="RESEARCH", kill_switch_armed=True, data_gate_passed=True)
    for watermark, group in sorted(groups.items()):
        event = EventBatch(event_id=digest([day.source_manifest_hash, day.session_date, watermark]),
                           available_ns=watermark, feature_bars=tuple(group["features"]),
                           execution_bars=tuple(group["execution"]),
                           capabilities={k: tuple(v) for k,v in group["capabilities"].items()})
        state = advance_session(state, event, controller, safety)
        if retain_decisions:
            retain_decisions(state)
        if state.active_proposal and not state.approval_accepted:
            plan = state.active_proposal
            approved = watermark + p.replay_approval_delay_seconds * NS
            try:
                state = accept_proposal(state, controller, plan.proposal_id, digest(plan),
                                        plan.maximum_quantity, approved, "REGISTERED_REPLAY_DELAY", research=True)
            except ValueError:
                # Expiry can leave no accepted attempt. No favorable later fill
                # is substituted under an already accepted approval.
                pass
    opening = clock_ns(day.session_date, p.open_minute)
    entry_end = clock_ns(day.session_date, p.last_entry_minute)
    # Unknown data cannot be disguised as profitable abstention. Require a
    # complete eligible feature window for every declared watchlist symbol.
    complete = day.completeness_attested and not state.quarantine and all(
        _complete_intervals(m.feature_bars, opening, entry_end, p.feature_minutes)
        for m in day.markets)
    position = state.position
    if position and position.status in {"PENDING", "OPEN"}:
        position = mark_unknown(position, "REPLAY_ENDED_WITHOUT_VERIFIED_TERMINAL_OUTCOME")
        state = evolve(state, position=position)
    if position and position.status == "UNKNOWN":
        complete = False
    if position and position.status in {"CLOSED", "NO_FILL"} and complete:
        value, cash = position.net_budget_units, position.net_pnl
    elif position is None and complete:
        value, cash = 0.0, 0.0
    else:
        value, cash = None, None
    return DailyResult(session_date=day.session_date, policy_hash=p.policy_hash,
                       source_origin=day.source_origin, status="COMPLETE" if complete else "UNKNOWN",
                       net_budget_units=value, net_pnl=cash, entry_filled=state.filled_entry_used,
                       accepted_attempt=state.approval_accepted, end_state=state)


class ProofThresholds(Frozen):
    minimum_development_dates: Annotated[int, Field(strict=True, ge=10)] = 60
    minimum_holdout_dates: Annotated[int, Field(strict=True, ge=5)] = 20
    minimum_holdout_fills: Annotated[int, Field(strict=True, ge=3)] = 10
    walk_forward_folds: Annotated[int, Field(strict=True, ge=2, le=6)] = 3
    minimum_walk_forward_pass_rate: Annotated[float, Field(ge=0, le=1)] = 0.66
    minimum_lower_mean_budget_units: Annotated[float, Field(ge=0)] = 0.0


class ProofReport(SafeOutput):
    version: Literal["afre-chronological-proof-1"] = "afre-chronological-proof-1"
    code_hash: str
    limits_hash: str
    dataset_hash: str
    universe: tuple[str, ...]
    source_origin: Literal["REAL_ATTESTED", "SYNTHETIC"]
    development_dates: tuple[str, ...]
    holdout_dates: tuple[str, ...]
    selected_policy: Policy
    selected_policy_hash: str
    registered_policy_hashes: tuple[str, ...]
    thresholds: ProofThresholds
    development_scores: dict[str, float | None]
    walk_forward: tuple[dict, ...]
    holdout_metrics: dict
    promotion_eligible: bool
    blockers: tuple[str, ...]
    proof_hash: str


def metrics(results: tuple[DailyResult, ...]) -> dict:
    unknown = sum(r.net_budget_units is None for r in results)
    values = tuple(r.net_budget_units for r in results if r.net_budget_units is not None)
    equity, peak, dd = 0., 0., 0.
    for v in values:
        equity += v
        peak = max(peak, equity)
        dd = max(dd, peak-equity)
    gains = sum(max(0, v) for v in values)
    losses = -sum(min(0, v) for v in values)
    return {"interval_method":"circular-date-block-percentile-bootstrap-512-repetitions-block-up-to-5-dates",
            "dates": len(results), "known_dates": len(values), "unknown_dates": unknown,
            "filled_entries": sum(r.entry_filled for r in results),
            "net_budget_units": sum(values) if not unknown else None,
            "mean_budget_units": mean(values) if values and not unknown else None,
            "lower_mean_bound": lower_mean_bound(values) if values and not unknown else None,
            "max_drawdown_budget_units": dd if not unknown else None,
            "profit_factor": gains/losses if losses and not unknown else None,
            "no_loss_sample": bool(values) and losses == 0,
            "coverage": sum(r.entry_filled for r in results)/len(results) if results else 0.}


def prove_policies(days: tuple[ResearchDay, ...], controllers: tuple[Controller, ...], *, holdout_start: str,
                   code_hash: str, thresholds: ProofThresholds | None = None) -> ProofReport:
    """Bounded pre-registered search; no test-data access during selection.

    Fold winners are selected on EACH earlier development prefix, evaluated on
    the next disjoint block, and never fitted on final holdout dates. Then one
    policy is frozen using full development only and evaluated on the holdout.
    """
    t = thresholds or ProofThresholds()
    if not days or not controllers or len(controllers) > 32:
        raise ValueError("NONEMPTY_DATA_AND_1_TO_32_REGISTERED_POLICIES_REQUIRED")
    dates = tuple(d.session_date for d in days)
    if dates != tuple(sorted(set(dates))):
        raise ValueError("SPLIT_REQUIRES_SORTED_UNIQUE_SESSION_DATES")
    identities = tuple(c.policy.policy_hash for c in controllers)
    if len(set(identities)) != len(identities) or len({digest(c.limits) for c in controllers}) != 1:
        raise ValueError("DUPLICATE_POLICY_OR_DIFFERENT_ACCOUNT_BUDGET")
    for c in controllers:
        for provider in (c.forecaster, c.values):
            if provider and provider.model.validated_through_ns >= clock_ns(days[0].session_date,555):
                raise ValueError("FROZEN_MODEL_MUST_PRECEDE_ALL_CONTROLLER_EVALUATION_DATES")
    universes = {tuple(sorted(m.prior.symbol for m in d.markets)) for d in days}
    if len(universes) != 1:
        raise ValueError("FROZEN_UNIVERSE_REQUIRED_FOR_REGISTERED_SELECTOR")
    dev = tuple(d for d in days if d.session_date < holdout_start)
    hold = tuple(d for d in days if d.session_date >= holdout_start)
    if len(dev) < 4 or not hold:
        raise ValueError("CHRONOLOGICAL_DEVELOPMENT_AND_HOLDOUT_REQUIRED")
    # Purge unresolved/delayed prior labels across split/fold boundaries.
    for left, right in zip(days, days[1:]):
        if any(b.available_ns >= clock_ns(right.session_date, 555)
               for m in left.markets for b in m.feature_bars+m.execution_bars):
            raise ValueError("DATA_OR_LABEL_AVAILABILITY_CROSSES_SESSION_SPLIT")
    cache = {}
    def evaluate(c, subset):
        rows = []
        for day in subset:
            key = (c.policy.policy_hash, day.session_date)
            if key not in cache:
                cache[key] = replay_day(day, c)
            rows.append(cache[key])
        return tuple(rows)
    def score(c, subset):
        m = metrics(evaluate(c, subset))
        return m["lower_mean_bound"]
    def select(subset):
        scored = [(score(c, subset), c.policy.policy_hash, c) for c in controllers]
        valid = [x for x in scored if x[0] is not None]
        if not valid:
            # Deterministic diagnostic selection, NEVER authority with unknowns.
            return min(controllers, key=lambda c: c.policy.policy_hash)
        return sorted(valid, key=lambda x: (-x[0], x[1]))[0][2]
    folds = []
    fold_count = min(t.walk_forward_folds, len(dev)//2)
    edges = [int(len(dev)*i/(fold_count+1)) for i in range(1,fold_count+2)]
    for i in range(fold_count):
        train, test = dev[:edges[i]], dev[edges[i]:edges[i+1]]
        winner = select(train)
        result = metrics(evaluate(winner, test))
        folds.append({"train_dates": [d.session_date for d in train],
                      "test_dates": [d.session_date for d in test], "selected_policy_hash": winner.policy.policy_hash,
                      "metrics": result, "passed": result["lower_mean_bound"] is not None and
                      result["lower_mean_bound"] > t.minimum_lower_mean_budget_units and result["filled_entries"] > 0})
    # This is the only final selection. Nothing above has evaluated holdout.
    selected = select(dev)
    dev_scores = {c.policy.policy_hash: score(c, dev) for c in controllers}
    held_metrics = metrics(evaluate(selected, hold))
    blockers = []
    if len(dev) < t.minimum_development_dates: blockers.append("INSUFFICIENT_DEVELOPMENT_DATES")
    if len(hold) < t.minimum_holdout_dates: blockers.append("INSUFFICIENT_HOLDOUT_DATES")
    if held_metrics["filled_entries"] < t.minimum_holdout_fills: blockers.append("INSUFFICIENT_HOLDOUT_FILLS")
    if held_metrics["lower_mean_bound"] is None or held_metrics["lower_mean_bound"] <= t.minimum_lower_mean_budget_units:
        blockers.append("HOLDOUT_DOES_NOT_BEAT_ZERO_WITH_DECLARED_BOUND")
    if held_metrics["unknown_dates"]: blockers.append("UNRESOLVED_HOLDOUT_OUTCOMES")
    if any(v is None for v in dev_scores.values()): blockers.append("UNRESOLVED_DEVELOPMENT_OUTCOMES")
    if sum(f["passed"] for f in folds)/len(folds) < t.minimum_walk_forward_pass_rate:
        blockers.append("WALK_FORWARD_POLICY_SELECTION_NOT_STABLE")
    real = all(d.source_origin == "REAL_ATTESTED" for d in days)
    if not real: blockers.append("SYNTHETIC_DATA_CANNOT_AUTHORIZE_PAPER_POLICY")
    payload = dict(version="afre-chronological-proof-1", code_hash=code_hash, limits_hash=digest(selected.limits),
                   dataset_hash=digest([d.model_dump(mode="json") for d in days]), universe=next(iter(universes)),
                   source_origin="REAL_ATTESTED" if real else "SYNTHETIC",
                   development_dates=tuple(d.session_date for d in dev), holdout_dates=tuple(d.session_date for d in hold),
                   selected_policy=selected.policy.model_dump(mode="json"), selected_policy_hash=selected.policy.policy_hash,
                   registered_policy_hashes=identities, thresholds=t.model_dump(mode="json"), development_scores=dev_scores,
                   walk_forward=folds, holdout_metrics=held_metrics, promotion_eligible=not blockers, blockers=tuple(blockers))
    payload = {**SafeOutput().model_dump(mode="json"), **payload}
    return ProofReport(**payload, proof_hash=digest(payload))
