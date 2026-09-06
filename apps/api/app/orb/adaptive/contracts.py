"""Immutable, strictly validated domain contracts. Prices are in currency/unit.

Integer nanoseconds are UTC. Candle timestamps explicitly describe intervals;
bar availability is NOT assumed equal to its interval end. All outputs retain
research-only safety literals. Model copies go through validation via evolve().
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

NS = 1_000_000_000
MINUTE = 60 * NS
IST = timezone(timedelta(minutes=330))
ENGINE_VERSION = "AFRE-3.0.0rc1"
FEATURE_VERSION = "afre-features-1"
LABEL_VERSION = "afre-structural-labels-1"
APPROVAL_PHRASE = "RECORD_SIMULATED_PAPER_TRADE"

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:@/-]+$")]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False,
                              validate_default=True)


class SafeOutput(Frozen):
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    live_trading_blocked: Literal[True] = True
    order_routing_enabled: Literal[False] = False


T = TypeVar("T", bound=Frozen)


def evolve(value: T, **updates: Any) -> T:
    return type(value).model_validate({**value.model_dump(mode="python"), **updates})


def canonical(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def clock_ns(day: str, minute: int) -> int:
    d = date.fromisoformat(day)
    dt = datetime(d.year, d.month, d.day, tzinfo=IST) + timedelta(minutes=minute)
    return int(dt.timestamp()) * NS


def day_of(timestamp_ns: int) -> str:
    return datetime.fromtimestamp(timestamp_ns // NS, IST).date().isoformat()


def next_grid_ns(timestamp_ns: int, day: str, minutes: int) -> int:
    anchor = clock_ns(day, 555)
    step = minutes * MINUTE
    return anchor + max(0, (timestamp_ns - anchor + step - 1) // step) * step


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self == Side.LONG else -1


class Template(StrEnum):
    FIRST_BREAK = "FIRST_BREAK"
    ACCEPTANCE = "ACCEPTANCE"
    RETEST_HOLD = "RETEST_HOLD"
    GAP_FADE = "GAP_FADE"
    RECLAIM = "RECLAIM"
    PD_LEVEL_BREAK = "PD_LEVEL_BREAK"


class Bar(Frozen):
    symbol: Identifier
    minutes: Literal[1, 3, 5, 15, 30, 60]
    open_ns: Annotated[int, Field(strict=True, ge=0)]
    close_ns: Annotated[int, Field(strict=True, ge=0)]
    available_ns: Annotated[int, Field(strict=True, ge=0)]
    open: Positive
    high: Positive
    low: Positive
    close: Positive
    volume: NonNegative
    source_id: Identifier
    price_basis: Identifier
    revision: Annotated[int, Field(strict=True, ge=0)] = 0

    @model_validator(mode="after")
    def valid(self) -> Bar:
        if self.symbol != self.symbol.upper():
            raise ValueError("symbol must be canonical uppercase")
        if self.close_ns != self.open_ns + self.minutes * MINUTE:
            raise ValueError("bar interval must match declared resolution")
        if self.available_ns < self.close_ns:
            raise ValueError("closed bar cannot be available before its close")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("invalid OHLC geometry")
        return self

    @property
    def event_id(self) -> str:
        return digest(self)


class PriorContext(Frozen):
    symbol: Identifier
    session_date: str
    available_ns: Annotated[int, Field(strict=True, ge=0)]
    high: Positive
    low: Positive
    close: Positive
    atr14: Positive
    tick_size: Positive
    price_basis: Identifier
    source_id: Identifier
    verified_prior_session: Literal[True]
    basis_verified: Literal[True]
    context_revision: Annotated[int, Field(strict=True, ge=0)] = 0

    @model_validator(mode="after")
    def valid(self) -> PriorContext:
        date.fromisoformat(self.session_date)
        if self.high <= self.low or not self.low <= self.close <= self.high:
            raise ValueError("prior context must have valid, nondegenerate geometry")
        if self.symbol != self.symbol.upper():
            raise ValueError("canonical uppercase symbol required")
        return self


class Costs(Frozen):
    # Declared simulator assumptions; not exchange/broker tax schedules.
    spread_bps: Annotated[float, Field(ge=0, le=1000)] = 1.0
    slippage_bps: Annotated[float, Field(ge=0, le=1000)] = 1.0
    impact_bps: Annotated[float, Field(ge=0, le=1000)] = 0.5
    fee_bps_per_side: Annotated[float, Field(ge=0, le=1000)] = 1.0
    version: Identifier = "costs-assumed-1"


class Policy(Frozen):
    """The complete deterministic selector, not just one leaf strategy.

    Bounds/thresholds below are registered research choices, NOT proved market
    constants. Changing any value changes policy_hash and invalidates proof.
    """
    policy_id: Identifier = "gap-adaptive-v3"
    engine_version: Literal["AFRE-3.0.0rc1"] = ENGINE_VERSION
    feature_minutes: Literal[3, 5] = 5
    execution_minutes: Literal[1, 3, 5] = 5
    range_minutes: Annotated[int, Field(strict=True, ge=3, le=30)] = 15
    open_minute: Literal[555] = 555
    last_entry_minute: Literal[615] = 615
    flat_minute: Literal[909, 910] = 910
    gap_flat_pct: Literal[0.1] = 0.1
    reward_risk: Literal[1, 2] = 2
    templates: tuple[Template, ...] = (
        Template.RECLAIM, Template.RETEST_HOLD, Template.ACCEPTANCE, Template.GAP_FADE,
    )
    accepted_closes: Annotated[int, Field(strict=True, ge=2, le=5)] = 2
    chop_extra_closes: Annotated[int, Field(strict=True, ge=0, le=2)] = 1
    buffer_ticks: Annotated[int, Field(strict=True, ge=0, le=20)] = 1
    stop_buffer_ticks: Annotated[int, Field(strict=True, ge=1, le=20)] = 1
    retest_tolerance_or: Annotated[float, Field(ge=0, le=0.5)] = 0.10
    max_extension_or: Annotated[float, Field(gt=0, le=5)] = 1.0
    entry_envelope_ticks: Annotated[int, Field(strict=True, ge=1, le=100)] = 4
    minimum_stop_ticks: Annotated[int, Field(strict=True, ge=1, le=100)] = 2
    maximum_cost_r: Annotated[float, Field(gt=0, le=1)] = 0.20
    require_session_vwap: bool = True
    require_volume_confirmation: bool = False
    minimum_volume_ratio: Annotated[float, Field(gt=0, le=10)] = 1.0
    allow_continuation_after_gap_fill: bool = False
    proposal_ttl_seconds: Annotated[int, Field(strict=True, ge=1, le=900)] = 300
    replay_approval_delay_seconds: Annotated[int, Field(strict=True, ge=1, le=120)] = 1
    strict_one_approval_attempt: Literal[True] = True
    max_branches: Literal[8] = 8
    max_candidates: Literal[6] = 6
    challenge_passes: Literal[1] = 1
    minimum_risk_budget: Positive = 1.0
    max_feature_lag_seconds: Annotated[int, Field(strict=True, ge=0, le=300)] = 30
    required_capabilities: tuple[Identifier, ...] = ()
    host_d1_source_hash: str | None = None
    forecast_model_hash: str | None = None
    value_model_hash: str | None = None
    costs: Costs = Field(default_factory=Costs)

    @model_validator(mode="after")
    def valid(self) -> Policy:
        if not self.templates or len(set(self.templates)) != len(self.templates) or len(self.templates) > 6:
            raise ValueError("one to six distinct templates required")
        if self.range_minutes % self.feature_minutes:
            raise ValueError("range boundary cannot split a feature candle")
        if self.execution_minutes > self.feature_minutes:
            raise ValueError("execution bars must be no coarser than feature bars")
        if self.feature_minutes % self.execution_minutes:
            raise ValueError("feature and execution intervals must nest exactly")
        if (self.flat_minute - self.open_minute) % self.execution_minutes:
            raise ValueError("flat time unobservable: use finer execution bars or explicit 15:09 policy")
        if self.flat_minute == 909 and self.execution_minutes != 3:
            raise ValueError("15:09 policy is the explicit native-3m earlier-flat variant")
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise ValueError("duplicate required capability")
        return self

    @property
    def rules_hash(self) -> str:
        return digest(self.model_dump(mode="json", exclude={"forecast_model_hash", "value_model_hash"}))

    @property
    def policy_hash(self) -> str:
        return digest(self)


class AccountLimits(Frozen):
    account_id: Identifier
    risk_budget: Positive
    maximum_notional: Positive
    maximum_quantity: Annotated[int, Field(strict=True, gt=0)]


class Capability(Frozen):
    name: Identifier
    available_ns: Annotated[int, Field(strict=True, ge=0)]
    expires_ns: Annotated[int, Field(strict=True, gt=0)]
    status: Literal["VALID", "BLOCKED"]
    evidence_hash: Annotated[str, Field(min_length=16)]
    # Upstream independently verified factual data only. No narrative-to-score.
    blocks_new_entry: bool = False
    reason: Annotated[str, Field(max_length=300)] = ""

    @model_validator(mode="after")
    def valid(self) -> Capability:
        if self.expires_ns <= self.available_ns:
            raise ValueError("capability expiry must follow availability")
        return self


class MarketSnapshot(Frozen):
    session_date: str
    as_of_ns: Annotated[int, Field(strict=True, ge=0)]
    prior: PriorContext
    bars: tuple[Bar, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    data_blockers: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid(self) -> MarketSnapshot:
        date.fromisoformat(self.session_date)
        if self.prior.session_date >= self.session_date:
            raise ValueError("context must be from a strictly earlier session")
        if self.prior.available_ns > clock_ns(self.session_date, 555):
            raise ValueError("prior reference unavailable at session open")
        if self.as_of_ns < clock_ns(self.session_date, 555):
            raise ValueError("snapshot cannot precede session open")
        if len(self.bars) > 400:
            raise ValueError("bounded one-session snapshot exceeded")
        if len({c.name for c in self.capabilities}) != len(self.capabilities):
            raise ValueError("duplicate capability state")
        for bar in self.bars:
            if bar.symbol != self.prior.symbol or bar.price_basis != self.prior.price_basis:
                raise ValueError("bar identity/price basis mismatch")
            if bar.available_ns > self.as_of_ns:
                raise ValueError("future availability in decision snapshot")
            if day_of(bar.open_ns) != self.session_date:
                raise ValueError("cross-session feature input")
        return self

    @property
    def snapshot_hash(self) -> str:
        return digest(self)


class Evidence(Frozen):
    event_id: str
    known_at_ns: int
    family: str
    facts: tuple[str, ...]


class Branch(Frozen):
    branch_id: str
    state: Literal["POSSIBLE", "WATCHING", "ARMED", "CONFIRMED", "REFUTED", "EXPIRED", "UNOBSERVABLE", "UNSUPPORTED"]
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    next_required: str
    refute_on: str
    expires_ns: int


class Forecast(SafeOutput):
    forecast_id: str
    snapshot_hash: str
    policy_hash: str
    symbol: str
    session_date: str
    event: str
    label_version: str = LABEL_VERSION
    prediction_kind: Literal["PREDICTION"] = "PREDICTION"
    horizon_kind: Literal["FEATURE_BARS", "WALL_CLOCK"] = "FEATURE_BARS"
    requested_end_ns: int | None = None
    action_policy_id: str | None = None
    plan_proposal_id: str | None = None
    issued_ns: int
    horizon_bars: int
    horizon_minutes: int
    effective_end_ns: int
    episode_id: str
    forecast_status: Literal["UNESTIMATED", "ESTIMATED", "UNOBSERVABLE"] = "UNESTIMATED"
    probability: Annotated[float, Field(ge=0, le=1)] | None = None
    interval: tuple[float, float] | None = None
    model_hash: str | None = None
    support_unique_dates: int = 0
    reason: str = "NO_VALIDATED_MODEL_FOR_THIS_EVENT_POLICY_HORIZON"
    evidence_event_ids: tuple[str, ...] = ()


class TradePlan(SafeOutput):
    proposal_id: str
    policy_hash: str
    snapshot_hash: str
    symbol: str
    session_date: str
    template: Template
    side: Side
    created_ns: int
    expires_ns: int
    last_entry_ns: int
    flat_ns: int
    execution_minutes: Literal[1, 3, 5]
    tick_size: Positive
    price_basis: str
    reference_entry: Positive
    minimum_entry: Positive
    maximum_entry: Positive
    stop: Positive
    reward_risk: Literal[1, 2]
    reference_target: Positive
    maximum_quantity: Annotated[int, Field(strict=True, gt=0)]
    risk_budget: Positive
    maximum_notional: Positive
    cost_model: Costs
    pdc: Positive
    requires_gap_unfilled: bool
    invalidation_level: Positive
    invalidate_on: Literal["CLOSE_BACK_INSIDE", "GAP_DIRECTION_RECLAIM"]
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def valid(self) -> TradePlan:
        if not self.created_ns < self.expires_ns <= self.last_entry_ns < self.flat_ns:
            raise ValueError("invalid proposal deadlines")
        if not self.minimum_entry <= self.reference_entry <= self.maximum_entry:
            raise ValueError("entry outside approved envelope")
        if self.side == Side.LONG and self.stop >= self.minimum_entry:
            raise ValueError("long stop must be below EVERY approved entry")
        if self.side == Side.SHORT and self.stop <= self.maximum_entry:
            raise ValueError("short stop must be above EVERY approved entry")
        return self


class Candidate(Frozen):
    template: Template
    status: Literal["FEASIBLE", "REJECTED", "WAITING"]
    reasons: tuple[str, ...]
    plan: TradePlan | None = None
    next_trigger: str
    refutation: str
    expiry_ns: int
    action_value_status: str = "UNESTIMATED"
    expected_net_budget_units: float | None = None
    lower_bound: float | None = None
    challenge: tuple[str, ...] = ()


class Decision(SafeOutput):
    decision_id: str
    engine_version: str = ENGINE_VERSION
    policy_hash: str
    snapshot_hash: str
    session_date: str
    symbol: str
    as_of_ns: int
    public_ticket: Literal["WAIT", "WATCH", "PAPER-CANDIDATE"]
    internal_action: str
    reason_codes: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    branches: tuple[Branch, ...]
    forecasts: tuple[Forecast, ...]
    candidates: tuple[Candidate, ...]
    selected_plan: TradePlan | None
    gap_ever_touched_pdc: bool | None
    observed_failure_episodes: int
    features: dict[str, float | int | str | bool | None]
    scenario_status: dict[str, str]
    next_triggers: tuple[str, ...]
    proof_hash: str | None = None


class Position(SafeOutput):
    position_id: str
    account_id: str
    plan: TradePlan
    approved_ns: int
    approved_by: str
    quantity: Annotated[int, Field(strict=True, gt=0)]
    origin: Literal["HUMAN_APPROVED_PAPER", "RESEARCH_REPLAY"]
    status: Literal["PENDING", "OPEN", "CLOSED", "NO_FILL", "UNKNOWN"] = "PENDING"
    label: str = "PENDING_TRIGGER"
    expected_open_ns: int
    fill_ns: int | None = None
    fill_price: Positive | None = None
    target: Positive | None = None
    initial_risk_per_unit: Positive | None = None
    exit_ns: int | None = None
    exit_time_precision: Literal["OPEN", "OBSERVATION_ENDPOINT", "SCHEDULED_CLOSE"] | None = None
    exit_price: Positive | None = None
    gross_pnl: float | None = None
    fees: NonNegative | None = None
    net_pnl: float | None = None
    net_r: float | None = None
    net_budget_units: float | None = None
    mfe_lower: NonNegative = 0.0
    mfe_upper: NonNegative = 0.0
    mae_lower: NonNegative = 0.0
    mae_upper: NonNegative = 0.0
    same_bar_ambiguous: bool = False
    observations: int = 0
    last_execution_event: str | None = None
    unavailable_reason: str | None = None


class SafetyState(Frozen):
    mode: Literal["MOCK", "RESEARCH", "PAPER"]
    kill_switch_armed: bool
    data_gate_passed: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def allows_analysis(self) -> bool:
        return self.kill_switch_armed and self.data_gate_passed
