"""Structured non-price risk inputs for AFRE failure-scenario detection.

This module accepts already-verified factual flags from official calendars,
exchange restrictions, feed monitors, broker-paper telemetry, and research
validation. It never parses narrative text and never invents a missing state.
Facts are converted into expiring Capability records so the existing
MarketSnapshot causal guard remains the single integration boundary.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import Field, model_validator

from .contracts import Capability, Frozen, Identifier, digest


class RiskContextSnapshot(Frozen):
    symbol: Identifier
    session_date: date
    available_ns: Annotated[int, Field(strict=True, gt=0)]
    expires_ns: Annotated[int, Field(strict=True, gt=0)]
    source_id: Identifier

    scheduled_result: bool = False
    rbi_mpc_window: bool = False
    budget_or_election_event: bool = False
    ex_dividend_today: bool = False
    corporate_action_adjustment_verified: bool = True
    unscheduled_news_shock_verified: bool = False

    circuit_locked: bool = False
    asm_gsm_t2t_restricted: bool = False
    illiquid_or_slippage_risk: bool = False
    fno_ban: bool = False

    feed_lag: bool = False
    bad_tick_detected: bool = False
    order_rejected: bool = False
    broker_squareoff_risk: bool = False
    point_in_time_violation: bool = False
    replay_live_mismatch: bool = False

    oi_wall_rejection: bool = False
    gamma_squeeze_verified: bool = False
    rollover_distortion: bool = False

    edge_decay: bool = False
    overfit_risk: bool = False
    small_sample: bool = False

    index_aligned_long: bool = False
    index_aligned_short: bool = False
    sector_divergence: bool = False
    market_breadth_supportive_long: bool = False
    market_breadth_supportive_short: bool = False

    @model_validator(mode="after")
    def valid(self):
        if self.expires_ns <= self.available_ns:
            raise ValueError("RISK_CONTEXT_EXPIRY_MUST_FOLLOW_AVAILABILITY")
        if self.symbol != self.symbol.upper():
            raise ValueError("RISK_CONTEXT_SYMBOL_MUST_BE_CANONICAL_UPPERCASE")
        if self.index_aligned_long and self.index_aligned_short:
            raise ValueError("INDEX_ALIGNMENT_CANNOT_BE_LONG_AND_SHORT_SIMULTANEOUSLY")
        if self.market_breadth_supportive_long and self.market_breadth_supportive_short:
            raise ValueError("MARKET_BREADTH_CANNOT_SUPPORT_BOTH_SIDES_SIMULTANEOUSLY")
        return self


def _cap(ctx: RiskContextSnapshot, name: str, *, blocked: bool = False, reason: str = "") -> Capability:
    return Capability(
        name=name,
        available_ns=ctx.available_ns,
        expires_ns=ctx.expires_ns,
        status="BLOCKED" if blocked else "VALID",
        evidence_hash=digest((ctx.model_dump(mode="json"), name, blocked, reason)),
        blocks_new_entry=blocked,
        reason=reason[:300],
    )


def capabilities(ctx: RiskContextSnapshot) -> tuple[Capability, ...]:
    out: list[Capability] = [
        _cap(ctx, "RISK_CONTEXT", reason=f"verified structured risk context from {ctx.source_id}")
    ]
    facts = (
        (ctx.scheduled_result, "RESULT_DAY", False, "verified scheduled result/event calendar"),
        (ctx.rbi_mpc_window, "RBI_MPC_WINDOW", True, "verified RBI MPC decision window"),
        (ctx.budget_or_election_event, "MACRO_EVENT_DAY", True, "verified budget/election event window"),
        (ctx.ex_dividend_today, "EX_DIVIDEND", False, "verified ex-dividend date"),
        (ctx.unscheduled_news_shock_verified, "NEWS_SHOCK", True, "verified unscheduled news shock"),
        (ctx.circuit_locked, "CIRCUIT_LOCK", True, "exchange circuit lock"),
        (ctx.asm_gsm_t2t_restricted, "SURVEILLANCE_RESTRICTED", True, "ASM/GSM/T2T restriction"),
        (ctx.illiquid_or_slippage_risk, "ILLIQUID_OR_SLIPPAGE", True, "verified liquidity/slippage risk"),
        (ctx.fno_ban, "FNO_BAN", True, "exchange F&O ban"),
        (ctx.feed_lag, "FEED_LAG", True, "market-data feed lag"),
        (ctx.bad_tick_detected, "BAD_TICK", True, "bad tick or integrity anomaly"),
        (ctx.order_rejected, "ORDER_REJECTED", True, "paper/execution adapter rejection"),
        (ctx.broker_squareoff_risk, "BROKER_SQUAREOFF_RISK", True, "verified broker square-off constraint"),
        (ctx.point_in_time_violation, "PIT_VIOLATION", True, "point-in-time causality violation"),
        (ctx.replay_live_mismatch, "BACKTEST_LIVE_MISMATCH", True, "replay/live behavior mismatch"),
        (ctx.oi_wall_rejection, "OI_WALL_REJECTION", False, "verified OI wall rejection"),
        (ctx.gamma_squeeze_verified, "GAMMA_SQUEEZE", False, "verified gamma-squeeze condition"),
        (ctx.rollover_distortion, "ROLLOVER_DISTORTION", False, "verified rollover distortion"),
        (ctx.edge_decay, "EDGE_DECAY", True, "registered edge-decay monitor failed"),
        (ctx.overfit_risk, "OVERFIT_RISK", True, "registered overfit diagnostic failed"),
        (ctx.small_sample, "SMALL_SAMPLE", True, "minimum support/sample gate failed"),
        (ctx.sector_divergence, "SECTOR_DIVERGENCE", False, "sector diverges from candidate direction"),
    )
    for present, name, blocked, reason in facts:
        if present:
            out.append(_cap(ctx, name, blocked=blocked, reason=reason))
    if ctx.ex_dividend_today:
        if ctx.corporate_action_adjustment_verified:
            out.append(_cap(ctx, "EX_DIVIDEND_ADJUSTED", reason="corporate-action basis verified"))
        else:
            out.append(_cap(ctx, "EX_DIVIDEND_UNADJUSTED", blocked=True, reason="ex-dividend basis not verified"))
    if ctx.index_aligned_long:
        out.append(_cap(ctx, "INDEX_ALIGNED_LONG", reason="verified index alignment long"))
    if ctx.index_aligned_short:
        out.append(_cap(ctx, "INDEX_ALIGNED_SHORT", reason="verified index alignment short"))
    if ctx.market_breadth_supportive_long:
        out.append(_cap(ctx, "BREADTH_SUPPORTS_LONG", reason="verified market breadth supports long"))
    if ctx.market_breadth_supportive_short:
        out.append(_cap(ctx, "BREADTH_SUPPORTS_SHORT", reason="verified market breadth supports short"))
    return tuple(out)
