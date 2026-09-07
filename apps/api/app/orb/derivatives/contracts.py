from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NS = 1_000_000_000
DERIVATIVES_ENGINE_VERSION = "orb-derivatives.v2.02"

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Pct = Annotated[float, Field(ge=-100000.0, le=100000.0, allow_inf_nan=False)]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False, validate_default=True)


def canonical(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class DerivativesIdentityError(ValueError):
    """Raised when scenario/context identity or PIT ordering is violated.

    Codes: DERIVATIVES_SYMBOL_IDENTITY_MISMATCH, DERIVATIVES_CONTEXT_FROM_FUTURE,
    DERIVATIVES_EXPIRY_MISMATCH. Never repaired by advancing the decision
    timestamp (max(...) is forbidden); the caller must supply causal inputs.
    """


class OptionType(StrEnum):
    CE = "CE"
    PE = "PE"


class EvidenceRelation(StrEnum):
    SUPPORT = "SUPPORT"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"
    BLOCK = "BLOCK"


class ScenarioKind(StrEnum):
    CONTINUATION = "CONTINUATION"
    RETEST = "RETEST"
    FAILURE = "FAILURE"
    RECLAIM = "RECLAIM"
    GAP_FADE = "GAP_FADE"
    CHOP = "CHOP"
    EXTENSION = "EXTENSION"
    UNKNOWN = "UNKNOWN"


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self == Side.LONG else -1


class OptionQuote(Frozen):
    symbol: str = Field(min_length=1, max_length=96)
    option_type: OptionType
    strike: Positive
    label: str = Field(default="", max_length=24)
    ltp: NonNegative = 0.0
    bid: NonNegative = 0.0
    ask: NonNegative = 0.0
    open: NonNegative = 0.0
    high: NonNegative = 0.0
    low: NonNegative = 0.0
    prev_close: NonNegative = 0.0
    volume: NonNegative = 0.0
    oi: NonNegative = 0.0
    lot_size: Annotated[int, Field(strict=True, gt=0)]
    tick_size: Positive

    @model_validator(mode="after")
    def validate_market_geometry(self) -> "OptionQuote":
        if self.ask and self.bid and self.ask + 1e-12 < self.bid:
            raise ValueError("ask cannot be below bid")
        if self.high and self.low and self.high + 1e-12 < self.low:
            raise ValueError("high cannot be below low")
        return self


class OptionStrike(Frozen):
    strike: Positive
    ce: OptionQuote | None = None
    pe: OptionQuote | None = None

    @model_validator(mode="after")
    def same_strike(self) -> "OptionStrike":
        for leg in (self.ce, self.pe):
            if leg is not None and not math.isclose(leg.strike, self.strike, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("leg strike differs from row strike")
        return self


class OptionChainSnapshot(Frozen):
    engine_version: Literal["orb-derivatives.v2.02"] = DERIVATIVES_ENGINE_VERSION
    source: str = Field(default="openalgo", min_length=1, max_length=64)
    source_instance: str = Field(default="default", min_length=1, max_length=96)
    underlying: str = Field(min_length=1, max_length=64)
    underlying_exchange: str = Field(min_length=1, max_length=24)
    options_exchange: str = Field(default="NFO", min_length=1, max_length=24)
    expiry_date: date
    underlying_ltp: Positive
    atm_strike: Positive
    as_of_ns: Annotated[int, Field(strict=True, ge=0)]
    received_ns: Annotated[int, Field(strict=True, ge=0)]
    rows: tuple[OptionStrike, ...]
    provider_payload_hash: str = Field(min_length=16, max_length=128)
    quote_timestamp_status: Literal["PROVIDER_TIMESTAMP", "OBSERVED_AT_RECEIPT"] = "OBSERVED_AT_RECEIPT"

    @model_validator(mode="after")
    def validate_chain(self) -> "OptionChainSnapshot":
        if self.received_ns < self.as_of_ns:
            # Provider quote time is sometimes unavailable; in that case caller must set as_of=received.
            raise ValueError("received_ns cannot precede as_of_ns")
        if not self.rows:
            raise ValueError("option chain cannot be empty")
        strikes = [r.strike for r in self.rows]
        if len(set(strikes)) != len(strikes):
            raise ValueError("duplicate strike rows")
        if tuple(strikes) != tuple(sorted(strikes)):
            raise ValueError("strikes must be sorted ascending")
        return self

    @property
    def snapshot_hash(self) -> str:
        return digest(self)


class FuturesSnapshot(Frozen):
    engine_version: Literal["orb-derivatives.v2.02"] = DERIVATIVES_ENGINE_VERSION
    source: str = "openalgo"
    symbol: str = Field(min_length=1, max_length=96)
    exchange: str = Field(default="NFO", min_length=1, max_length=24)
    expiry_date: date | None = None
    ltp: Positive
    bid: NonNegative = 0.0
    ask: NonNegative = 0.0
    open: NonNegative = 0.0
    high: NonNegative = 0.0
    low: NonNegative = 0.0
    prev_close: NonNegative = 0.0
    volume: NonNegative = 0.0
    oi: NonNegative = 0.0
    as_of_ns: Annotated[int, Field(strict=True, ge=0)]
    received_ns: Annotated[int, Field(strict=True, ge=0)]
    provider_payload_hash: str = Field(min_length=16, max_length=128)
    quote_timestamp_status: Literal["PROVIDER_TIMESTAMP", "OBSERVED_AT_RECEIPT"] = "OBSERVED_AT_RECEIPT"

    @property
    def snapshot_hash(self) -> str:
        return digest(self)


class Greeks(Frozen):
    symbol: str = Field(min_length=1, max_length=96)
    strike: Positive
    option_type: OptionType
    days_to_expiry: NonNegative
    forward_price: Positive
    option_price: NonNegative
    implied_volatility_pct: NonNegative
    delta: float = Field(allow_inf_nan=False)
    gamma: float = Field(ge=0.0, allow_inf_nan=False)
    theta_per_day: float = Field(allow_inf_nan=False)
    vega_per_vol_point: float = Field(allow_inf_nan=False)
    rho: float = Field(allow_inf_nan=False)
    vanna_per_vol_point: float | None = Field(default=None, allow_inf_nan=False)
    charm_delta_per_day: float | None = Field(default=None, allow_inf_nan=False)
    model: str = Field(default="OPENALGO_BLACK76", max_length=64)
    status: Literal["VALID", "PARTIAL", "INVALID"] = "VALID"
    reason: str = Field(default="", max_length=300)


class Wall(Frozen):
    strike: Positive
    strength: NonNegative
    distance_pct: Pct
    oi: NonNegative
    oi_change: float = Field(default=0.0, allow_inf_nan=False)
    persistence: Annotated[int, Field(strict=True, ge=0)] = 0
    state: Literal["FORMING", "STABLE", "STRENGTHENING", "WEAKENING", "UNWINDING", "UNKNOWN"] = "UNKNOWN"


class DerivativesEvidence(Frozen):
    evidence_id: str = Field(min_length=16, max_length=128)
    family: str = Field(min_length=1, max_length=80)
    relation: EvidenceRelation
    fact: str = Field(min_length=1, max_length=320)
    known_at_ns: Annotated[int, Field(strict=True, ge=0)]
    expires_ns: Annotated[int, Field(strict=True, gt=0)]
    blocks_new_entry: bool = False
    source_hash: str = Field(min_length=16, max_length=128)

    @model_validator(mode="after")
    def validate_time(self) -> "DerivativesEvidence":
        if self.expires_ns <= self.known_at_ns:
            raise ValueError("evidence expiry must follow availability")
        return self


class DerivativesContext(Frozen):
    engine_version: Literal["orb-derivatives.v2.02"] = DERIVATIVES_ENGINE_VERSION
    symbol: str
    expiry_date: date
    as_of_ns: Annotated[int, Field(strict=True, ge=0)]
    source_hash: str = Field(min_length=16, max_length=128)
    chain_snapshot_hash: str = Field(min_length=16, max_length=128)
    futures_snapshot_hash: str | None = Field(default=None, min_length=16, max_length=128)
    # G11: per-input provenance. Each names the exact raw input behind the context
    # result so proof-grade replay can re-derive and compare every contributor.
    greeks_snapshot_hash: str | None = Field(default=None, min_length=16, max_length=128)
    previous_chain_hash: str | None = Field(default=None, min_length=16, max_length=128)
    previous_futures_hash: str | None = Field(default=None, min_length=16, max_length=128)
    iv_history_hash: str | None = Field(default=None, min_length=16, max_length=128)
    next_expiry_snapshot_hash: str | None = Field(default=None, min_length=16, max_length=128)
    status: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE", "STALE"]
    stale_seconds: NonNegative = 0.0
    reason_codes: tuple[str, ...] = ()

    underlying_ltp: Positive
    futures_ltp: Positive | None = None
    futures_basis_pct: float | None = Field(default=None, allow_inf_nan=False)
    futures_oi_change_pct: float | None = Field(default=None, allow_inf_nan=False)
    futures_state: Literal[
        "LONG_BUILDUP", "SHORT_BUILDUP", "SHORT_COVERING", "LONG_UNWINDING", "NEUTRAL", "UNKNOWN"
    ] = "UNKNOWN"

    pcr_oi: NonNegative | None = None
    pcr_volume: NonNegative | None = None
    call_oi_total: NonNegative = 0.0
    put_oi_total: NonNegative = 0.0
    call_volume_total: NonNegative = 0.0
    put_volume_total: NonNegative = 0.0
    call_oi_change: float = 0.0
    put_oi_change: float = 0.0
    call_oi_wall: Wall | None = None
    put_oi_wall: Wall | None = None
    call_gamma_wall: Wall | None = None
    put_gamma_wall: Wall | None = None
    oi_concentration_pct: NonNegative | None = None

    max_pain: Positive | None = None
    max_pain_distance_pct: NonNegative | None = None
    atm_straddle_expected_move_pct: NonNegative | None = None
    iv_horizon_expected_move_pct: NonNegative | None = None
    expected_move_horizon_minutes: Annotated[int, Field(strict=True, ge=1, le=1440)] = 30

    atm_iv_pct: NonNegative | None = None
    iv_rank: NonNegative | None = None
    iv_percentile: NonNegative | None = None
    skew_25d_pct: float | None = Field(default=None, allow_inf_nan=False)
    term_structure_spread_pct: float | None = Field(default=None, allow_inf_nan=False)

    call_gamma_exposure_proxy: NonNegative | None = None
    put_gamma_exposure_proxy: NonNegative | None = None
    gamma_balance_proxy: float | None = Field(default=None, allow_inf_nan=False)
    gamma_balance_level: Positive | None = None

    evidence: tuple[DerivativesEvidence, ...] = ()
    no_future_leakage: Literal[True] = True
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True

    @property
    def context_hash(self) -> str:
        return digest(self)


class PriceScenario(Frozen):
    symbol: str
    session_date: date
    as_of_ns: Annotated[int, Field(strict=True, ge=0)]
    kind: ScenarioKind
    # G5: optional challenged-expiry identity. When present, the admission gate
    # rejects contexts built for a different expiry (PIT-004). None = not asserted.
    expiry_date: date | None = None
    side: Side | None = None
    entry: Positive | None = None
    target: Positive | None = None
    stop: Positive | None = None
    or_high: Positive | None = None
    or_low: Positive | None = None
    session_vwap: Positive | None = None
    gap_pct: float | None = Field(default=None, allow_inf_nan=False)
    extension_or: NonNegative | None = None
    accepted_closes: Annotated[int, Field(strict=True, ge=0)] = 0
    failure_count: Annotated[int, Field(strict=True, ge=0)] = 0
    chop_risk: bool = False
    expiry_day: bool = False


class ScenarioBranch(Frozen):
    branch_id: str
    state: Literal["POSSIBLE", "WATCHING", "SUPPORTED", "CONFLICTED", "BLOCKED", "UNKNOWN"]
    relation: EvidenceRelation
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()
    predicted_failure_mode: str | None = None
    next_required: str
    refute_on: str


class ScenarioAssessment(Frozen):
    engine_version: Literal["orb-derivatives.v2.02"] = DERIVATIVES_ENGINE_VERSION
    symbol: str
    as_of_ns: Annotated[int, Field(strict=True, ge=0)]
    scenario_kind: ScenarioKind
    relation: EvidenceRelation
    public_ticket_cap: Literal["WAIT", "WATCH", "UNCHANGED"]
    reason_codes: tuple[str, ...]
    branches: tuple[ScenarioBranch, ...]
    support_families: tuple[str, ...] = ()
    conflict_families: tuple[str, ...] = ()
    unknown_families: tuple[str, ...] = ()
    predicted_failure_modes: tuple[str, ...] = ()
    no_future_leakage: Literal[True] = True
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class DerivativesPolicy(Frozen):
    policy_id: str = "orb-derivatives-default-v202"
    max_chain_age_seconds: Annotated[int, Field(strict=True, ge=1, le=300)] = 20
    evidence_ttl_seconds: Annotated[int, Field(strict=True, ge=1, le=600)] = 30
    expected_move_target_buffer: Annotated[float, Field(ge=1.0, le=2.0)] = 1.10
    near_wall_pct: Annotated[float, Field(gt=0.0, le=5.0)] = 1.25
    pin_active_pct: Annotated[float, Field(gt=0.0, le=5.0)] = 0.40
    pin_nearby_pct: Annotated[float, Field(gt=0.0, le=5.0)] = 1.25
    high_oi_concentration_pct: Annotated[float, Field(ge=0.0, le=100.0)] = 65.0
    high_iv_percentile: Annotated[float, Field(ge=0.0, le=100.0)] = 80.0
    extreme_pcr_high: Annotated[float, Field(gt=0.0, le=10.0)] = 1.30
    extreme_pcr_low: Annotated[float, Field(gt=0.0, le=10.0)] = 0.70
    skew_tail_warning_pct: Annotated[float, Field(gt=0.0, le=50.0)] = 5.0
    term_inversion_warning_pct: Annotated[float, Field(gt=0.0, le=50.0)] = 5.0
    futures_basis_warning_pct: Annotated[float, Field(gt=0.0, le=10.0)] = 0.35
    wall_top_k: Annotated[int, Field(strict=True, ge=1, le=10)] = 3
    wall_distance_decay_pct: Annotated[float, Field(gt=0.01, le=10.0)] = 2.0
    minimum_chain_rows: Annotated[int, Field(strict=True, ge=3, le=1000)] = 11
    minimum_greeks_coverage: Annotated[float, Field(ge=0.0, le=1.0)] = 0.65
    require_fresh_chain_for_entry: bool = True
    derivatives_can_create_trade: Literal[False] = False
    hard_block_on_stale: bool = True

    @property
    def policy_hash(self) -> str:
        return digest(self)


def utc_now_ns() -> int:
    return int(datetime.now(timezone.utc).timestamp() * NS)
