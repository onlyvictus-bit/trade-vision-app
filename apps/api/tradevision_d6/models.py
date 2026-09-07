"""Immutable, strictly validated public contracts. Decimal values are intentional."""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from enum import Enum
import re

ZERO = Decimal("0")
ONE = Decimal("1")
RISK_NAMES = ("event", "trap", "data_uncertainty", "liquidity", "execution")
REQUIRED_CHECKS = (
    "out_of_sample", "purged_splits", "costs_included",
    "multiple_testing_controlled", "calibration_passed",
    "point_in_time_checked", "dependence_handled", "paper_validation_passed",
)


class ContractError(ValueError):
    """Invalid/untrusted input: the caller must never turn this into approval."""


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Horizon(str, Enum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"


class Status(str, Enum):
    WAIT = "WAIT"
    WATCH = "WATCH"
    PAPER_CANDIDATE = "PAPER-CANDIDATE"


def number(value: Decimal, name: str, *, low: Decimal = ZERO,
           high: Decimal = Decimal("1e18")) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ContractError(f"{name}: a finite Decimal is required")
    if not low <= value <= high:
        raise ContractError(f"{name}: outside [{low}, {high}]")
    # Bound pathological inputs and make the internal 50-digit context sufficient.
    if len(value.as_tuple().digits) > 30 or not -18 <= value.as_tuple().exponent <= 18:
        raise ContractError(f"{name}: excessive numeric precision/exponent")


def score(value: Decimal, name: str) -> None:
    number(value, name, high=ONE)


def positive(value: Decimal, name: str) -> None:
    number(value, name)
    if value <= ZERO:
        raise ContractError(f"{name}: must be positive")


def integer(value: int, name: str, *, low: int = 0, high: int = 10**9) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ContractError(f"{name}: integer outside [{low}, {high}]")


def text(value: str, name: str, *, maximum: int = 128) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ContractError(f"{name}: nonempty bounded string required")
    if any(ord(c) < 32 for c in value):
        raise ContractError(f"{name}: control characters are forbidden")


def digest(value: str, name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError(f"{name}: lowercase SHA-256 hexadecimal required")


def timestamp(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError(f"{name}: timezone-aware datetime required")


def boolean(value: bool, name: str) -> None:
    if type(value) is not bool:
        raise ContractError(f"{name}: true/false required, not truthy values")


def enum_value(value: Enum, cls: type[Enum], name: str) -> None:
    if not isinstance(value, cls):
        raise ContractError(f"{name}: {cls.__name__} required")


def typed_tuple(value: tuple, cls: type, name: str, maximum: int) -> None:
    if not isinstance(value, tuple) or len(value) > maximum:
        raise ContractError(f"{name}: bounded immutable tuple required")
    if not all(isinstance(x, cls) for x in value):
        raise ContractError(f"{name}: invalid member type")


@dataclass(frozen=True, slots=True)
class RiskVector:
    event: Decimal
    trap: Decimal
    data_uncertainty: Decimal
    liquidity: Decimal
    execution: Decimal

    def __post_init__(self) -> None:
        for name in RISK_NAMES:
            score(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class SourceSpec:
    name: str
    group: str
    weight: Decimal
    required: bool = True

    def __post_init__(self) -> None:
        boolean(self.required, "source.required")
        text(self.name, "source.name")
        text(self.group, "source.group")
        positive(self.weight, "source.weight")


@dataclass(frozen=True, slots=True)
class GroupSpec:
    name: str
    weight: Decimal

    def __post_init__(self) -> None:
        text(self.name, "group.name")
        positive(self.weight, "group.weight")


@dataclass(frozen=True, slots=True)
class DirectionalEvidence:
    source: str
    long: Decimal
    short: Decimal

    def __post_init__(self) -> None:
        text(self.source, "evidence.source")
        score(self.long, "evidence.long")
        score(self.short, "evidence.short")


@dataclass(frozen=True, slots=True)
class StressScenario:
    name: str
    cost_multiplier: Decimal
    gap_multiplier: Decimal

    def __post_init__(self) -> None:
        text(self.name, "scenario.name")
        number(self.cost_multiplier, "cost_multiplier", low=ONE, high=Decimal("20"))
        number(self.gap_multiplier, "gap_multiplier", low=ONE, high=Decimal("20"))


@dataclass(frozen=True, slots=True)
class Policy:
    revision: str
    horizon: Horizon
    sources: tuple[SourceSpec, ...]
    groups: tuple[GroupSpec, ...]
    scenarios: tuple[StressScenario, ...]
    risk_caps: RiskVector
    minimum_evidence: Decimal
    minimum_direction_margin: Decimal
    minimum_quality: Decimal
    minimum_net_reward_risk: Decimal
    minimum_modeled_expectancy: Decimal
    risk_per_trade_fraction: Decimal
    portfolio_risk_fraction: Decimal
    daily_loss_fraction: Decimal
    weekly_loss_fraction: Decimal
    max_bar_age_seconds: int
    max_quote_age_seconds: int
    max_portfolio_age_seconds: int
    max_cost_age_seconds: int
    max_entry_drift_bps: Decimal
    minimum_validation_samples: int
    minimum_validation_confidence: Decimal
    validation_embargo_seconds: int
    max_validation_age_seconds: int
    max_proof_lifetime_seconds: int
    validation_method: str

    def __post_init__(self) -> None:
        text(self.revision, "policy.revision")
        enum_value(self.horizon, Horizon, "policy.horizon")
        typed_tuple(self.sources, SourceSpec, "sources", 128)
        typed_tuple(self.groups, GroupSpec, "groups", 32)
        typed_tuple(self.scenarios, StressScenario, "scenarios", 16)
        if not self.sources or not self.groups or not self.scenarios:
            raise ContractError("nonempty registry and scenarios required")
        for values, label in ((self.sources, "sources"), (self.groups, "groups"),
                              (self.scenarios, "scenarios")):
            if len({x.name for x in values}) != len(values):
                raise ContractError(f"duplicate {label}")
        group_names = {g.name for g in self.groups}
        if {s.group for s in self.sources} != group_names:
            raise ContractError("each registered group must have sources; no unknown groups")
        if not isinstance(self.risk_caps, RiskVector):
            raise ContractError("risk_caps must be RiskVector")
        if not any(s.cost_multiplier == ONE and s.gap_multiplier == ONE for s in self.scenarios):
            raise ContractError("base scenario required")
        if not any(s.cost_multiplier > ONE for s in self.scenarios):
            raise ContractError("adverse cost scenario required")
        if not any(s.gap_multiplier > ONE for s in self.scenarios):
            raise ContractError("adverse gap scenario required")
        for name in ("minimum_evidence", "minimum_direction_margin", "minimum_quality",
                     "risk_per_trade_fraction", "portfolio_risk_fraction",
                     "daily_loss_fraction", "weekly_loss_fraction"):
            score(getattr(self, name), name)
            if getattr(self, name) == ZERO:
                raise ContractError(f"{name} must be positive")
        positive(self.minimum_net_reward_risk, "minimum_net_reward_risk")
        positive(self.minimum_modeled_expectancy, "minimum_modeled_expectancy")
        number(self.max_entry_drift_bps, "max_entry_drift_bps", high=Decimal("1000"))
        for name in ("max_bar_age_seconds", "max_quote_age_seconds",
                     "max_portfolio_age_seconds", "max_cost_age_seconds",
                     "max_validation_age_seconds", "max_proof_lifetime_seconds"):
            integer(getattr(self, name), name, low=1, high=365 * 86400)
        integer(self.validation_embargo_seconds, "validation_embargo_seconds", high=365 * 86400)
        integer(self.minimum_validation_samples, "minimum_validation_samples", low=30)
        score(self.minimum_validation_confidence, "minimum_validation_confidence")
        if not ZERO < self.minimum_validation_confidence < ONE:
            raise ContractError("validation confidence must be strictly between zero and one")
        text(self.validation_method, "validation_method")


@dataclass(frozen=True, slots=True)
class Snapshot:
    snapshot_id: str
    symbol: str
    session_id: str
    horizon: Horizon
    bar_opened_at: datetime
    bar_closed_at: datetime
    data_received_at: datetime
    feature_available_at: datetime
    feature_cutoff_at: datetime
    quote_at: datetime
    feature_digest: str
    data_revision: str
    bid: Decimal
    ask: Decimal
    tick_size: Decimal
    lot_size: int
    capacity_units: int
    bar_is_closed: bool
    data_complete: bool
    corporate_actions_checked: bool
    event_feed_ok: bool
    session_entry_allowed: bool
    instrument_eligible: bool
    short_eligible: bool

    def __post_init__(self) -> None:
        for name in ("snapshot_id", "session_id", "data_revision"):
            text(getattr(self, name), name)
        if not isinstance(self.symbol, str) or re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{0,63}", self.symbol) is None:
            raise ContractError("invalid canonical symbol")
        enum_value(self.horizon, Horizon, "snapshot.horizon")
        for name in ("bar_opened_at", "bar_closed_at", "data_received_at", "feature_available_at",
                     "feature_cutoff_at", "quote_at"):
            timestamp(getattr(self, name), name)
        digest(self.feature_digest, "feature_digest")
        for name in ("bid", "ask", "tick_size"):
            positive(getattr(self, name), name)
        if self.ask < self.bid:
            raise ContractError("crossed quote")
        integer(self.lot_size, "lot_size", low=1)
        integer(self.capacity_units, "capacity_units")
        for name in ("bar_is_closed", "data_complete", "corporate_actions_checked", "event_feed_ok",
                     "session_entry_allowed", "instrument_eligible", "short_eligible"):
            boolean(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class Portfolio:
    account_id: str
    revision: str
    observed_at: datetime
    equity: Decimal
    available_notional: Decimal
    open_modeled_risk: Decimal
    daily_loss: Decimal
    weekly_loss: Decimal
    kill_switch: bool
    conflicting_position: bool
    account_entry_allowed: bool

    def __post_init__(self) -> None:
        text(self.account_id, "account_id")
        text(self.revision, "portfolio.revision")
        timestamp(self.observed_at, "portfolio.observed_at")
        positive(self.equity, "equity")
        for name in ("available_notional", "open_modeled_risk", "daily_loss", "weekly_loss"):
            number(getattr(self, name), name)
        for name in ("kill_switch", "conflicting_position", "account_entry_allowed"):
            boolean(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class Costs:
    round_trip_per_unit: Decimal
    gap_allowance_per_unit: Decimal
    model_revision: str
    estimated_at: datetime
    valid_for_min_units: int
    valid_for_max_units: int

    def __post_init__(self) -> None:
        positive(self.round_trip_per_unit, "round_trip_per_unit")
        positive(self.gap_allowance_per_unit, "gap_allowance_per_unit")
        text(self.model_revision, "cost.model_revision")
        timestamp(self.estimated_at, "cost.estimated_at")
        integer(self.valid_for_min_units, "valid_for_min_units", low=1)
        integer(self.valid_for_max_units, "valid_for_max_units", low=self.valid_for_min_units)


@dataclass(frozen=True, slots=True)
class TradePlan:
    side: Side
    setup_id: str
    setup_spec_digest: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    quality: Decimal
    costs: Costs

    def __post_init__(self) -> None:
        enum_value(self.side, Side, "plan.side")
        text(self.setup_id, "setup_id")
        digest(self.setup_spec_digest, "setup_spec_digest")
        for name in ("entry", "stop", "target"):
            positive(getattr(self, name), name)
        score(self.quality, "plan.quality")
        if not isinstance(self.costs, Costs):
            raise ContractError("plan.costs must be Costs")
        if self.side is Side.LONG and not self.stop < self.entry < self.target:
            raise ContractError("LONG requires stop < entry < target")
        if self.side is Side.SHORT and not self.target < self.entry < self.stop:
            raise ContractError("SHORT requires target < entry < stop")


@dataclass(frozen=True, slots=True)
class ValidationProof:
    side: Side
    binding_digest: str
    report_digest: str
    key_id: str
    issued_at: datetime
    expires_at: datetime
    validation_data_end_at: datetime
    independent_samples: int
    target_probability_lower_bound: Decimal
    confidence_level: Decimal
    valid_risk_envelope: RiskVector
    method: str
    passed_checks: tuple[str, ...]
    signature: str

    def __post_init__(self) -> None:
        enum_value(self.side, Side, "proof.side")
        digest(self.binding_digest, "proof.binding_digest")
        digest(self.report_digest, "proof.report_digest")
        text(self.key_id, "proof.key_id")
        for name in ("issued_at", "expires_at", "validation_data_end_at"):
            timestamp(getattr(self, name), name)
        integer(self.independent_samples, "independent_samples", low=1)
        score(self.target_probability_lower_bound, "target_probability_lower_bound")
        if self.target_probability_lower_bound == ONE:
            raise ContractError("finite-sample lower probability bound cannot be certainty")
        score(self.confidence_level, "confidence_level")
        if not ZERO < self.confidence_level < ONE:
            raise ContractError("confidence level must be strictly between zero and one")
        if not isinstance(self.valid_risk_envelope, RiskVector):
            raise ContractError("proof.valid_risk_envelope must be RiskVector")
        text(self.method, "proof.method")
        typed_tuple(self.passed_checks, str, "passed_checks", 32)
        if len(set(self.passed_checks)) != len(self.passed_checks):
            raise ContractError("duplicate validation checks")
        if set(self.passed_checks) - set(REQUIRED_CHECKS):
            raise ContractError("unknown validation check")
        if self.signature != "":
            digest(self.signature, "proof.signature")


@dataclass(frozen=True, slots=True)
class Request:
    evaluation_at: datetime
    snapshot: Snapshot
    portfolio: Portfolio
    policy: Policy
    evidence: tuple[DirectionalEvidence, ...]
    plans: tuple[TradePlan, ...]
    risks: RiskVector
    proofs: tuple[ValidationProof, ...] = ()

    def __post_init__(self) -> None:
        timestamp(self.evaluation_at, "evaluation_at")
        for value, cls in ((self.snapshot, Snapshot), (self.portfolio, Portfolio),
                           (self.policy, Policy), (self.risks, RiskVector)):
            if not isinstance(value, cls):
                raise ContractError(f"{cls.__name__} required")
        typed_tuple(self.evidence, DirectionalEvidence, "evidence", 128)
        typed_tuple(self.plans, TradePlan, "plans", 2)
        typed_tuple(self.proofs, ValidationProof, "proofs", 2)
        if len({e.source for e in self.evidence}) != len(self.evidence):
            raise ContractError("duplicate evidence source")
        if {e.source for e in self.evidence} - {s.name for s in self.policy.sources}:
            raise ContractError("unregistered evidence source")
        if len({p.side for p in self.plans}) != len(self.plans):
            raise ContractError("multiple plans for the same side")
        if len({p.side for p in self.proofs}) != len(self.proofs):
            raise ContractError("multiple proofs for the same side")
        if {p.side for p in self.proofs} - {p.side for p in self.plans}:
            raise ContractError("proof supplied without a plan")
        if self.snapshot.horizon is not self.policy.horizon:
            raise ContractError("snapshot/policy horizon mismatch")


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: str
    net_win_per_unit: Decimal
    modeled_loss_per_unit: Decimal
    net_reward_risk: Decimal
    modeled_expectancy_per_unit: Decimal | None


@dataclass(frozen=True, slots=True)
class SideAssessment:
    side: Side
    evidence: Decimal
    setup_exists: bool
    quality: Decimal
    permission: Decimal
    eligible: bool
    quantity: int
    proof_valid: bool
    scenarios: tuple[ScenarioResult, ...]
    hard_reasons: tuple[str, ...]
    watch_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Decision:
    decision_id: str
    symbol: str
    horizon: Horizon
    status: Status
    long_evidence: Decimal
    short_evidence: Decimal
    preferred_side: Side | None
    selected_side: Side | None
    trade_permission: Decimal
    valid_until: datetime | None
    long: SideAssessment
    short: SideAssessment
    reasons: tuple[str, ...]
    trace: tuple[str, ...]
