from __future__ import annotations

from datetime import datetime, timezone
from math import floor

from ..models import (
    AccountRiskSizingRecord,
    DailyWeeklyCooldownRecord,
    ExposureCapRecord,
    PortfolioHeatMemoryRecord,
    PositionPortfolioCooldownGate,
    PositionPortfolioCooldownReport,
    PositionPortfolioCooldownRequest,
    PositionPortfolioCooldownScenario,
)


VERSION = "position-portfolio-cooldown-memory.v0.82"
TRADE_CANDIDATES = {"BUY_BREAKOUT", "SELL_BREAKDOWN", "BUY_RETEST", "SELL_RETEST", "BUY_FADE", "SELL_FADE"}


def _risk_reward(entry: float, stop: float, target: float) -> float:
    risk = abs(entry - stop)
    reward = abs(target - entry)
    return round(reward / risk, 4) if risk > 0 else 0.0


def _adjusted_risk_pct(payload: PositionPortfolioCooldownRequest) -> float:
    if payload.decision not in TRADE_CANDIDATES:
        return 0.0
    confidence_factor = 0.15 + (payload.confidence_pct / 100.0) * 0.35
    liquidity_factor = 1.0 if payload.liquidity_score >= 0.75 else 0.65 if payload.liquidity_score >= 0.5 else 0.0
    slippage_factor = 1.0 if payload.slippage_risk_pct <= 0.1 else 0.75 if payload.slippage_risk_pct <= 0.25 else 0.45
    heat_factor = 0.75 if payload.current_sector_exposure_pct + payload.current_index_exposure_pct > payload.max_portfolio_heat_pct else 1.0
    return round(min(payload.max_risk_per_trade_pct, payload.max_risk_per_trade_pct * confidence_factor * liquidity_factor * slippage_factor * heat_factor), 4)


def _sizing(payload: PositionPortfolioCooldownRequest) -> AccountRiskSizingRecord:
    stop_distance = abs(payload.entry_price - payload.stop_loss)
    rr = _risk_reward(payload.entry_price, payload.stop_loss, payload.target)
    adjusted = _adjusted_risk_pct(payload)
    risk_amount = payload.account_equity * adjusted / 100.0
    raw_size = floor(risk_amount / stop_distance) if stop_distance > 0 else 0
    cap_size = floor((payload.account_equity * 0.10) / payload.entry_price)
    final = max(0, min(raw_size, cap_size))
    blocked = payload.decision not in TRADE_CANDIDATES or final <= 0 or rr < 1.5
    if blocked:
        final = 0
    return AccountRiskSizingRecord(
        sizing_id=f"SIZING-{payload.symbol.upper()}-{payload.decision}",
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        target=payload.target,
        stop_distance=round(stop_distance, 4),
        risk_reward=rr,
        adjusted_risk_pct=0.0 if blocked else adjusted,
        raw_position_size=raw_size,
        capital_cap_position_size=cap_size,
        final_position_size=final,
        capital_to_use=round(final * payload.entry_price, 2),
        max_loss_amount=round(final * stop_distance, 2),
        reward_amount=round(final * abs(payload.target - payload.entry_price), 2),
        sizing_blocked=blocked,
        reason="Sizing blocked by non-trade decision, zero size, or weak R:R." if blocked else "Sizing is capped by account risk and 10% capital cap.",
    )


def _cooldown(payload: PositionPortfolioCooldownRequest) -> DailyWeeklyCooldownRecord:
    daily_max = payload.account_equity * payload.max_daily_loss_pct / 100.0
    weekly_max = payload.account_equity * payload.max_weekly_loss_pct / 100.0
    daily_hit = payload.daily_pnl <= -daily_max
    weekly_hit = payload.weekly_pnl <= -weekly_max
    cooldown = daily_hit or weekly_hit or payload.consecutive_losses >= payload.cooldown_after_n_losses or payload.choppy_regime
    reasons: list[str] = []
    if daily_hit:
        reasons.append("Daily loss limit hit.")
    if weekly_hit:
        reasons.append("Weekly loss limit hit.")
    if payload.consecutive_losses >= payload.cooldown_after_n_losses:
        reasons.append(f"{payload.consecutive_losses} consecutive losses triggered cooldown.")
    if payload.choppy_regime:
        reasons.append("Choppy-regime cooldown active.")
    if not reasons:
        reasons.append("Daily, weekly, and cooldown gates are clear.")
    return DailyWeeklyCooldownRecord(
        daily_pnl=round(payload.daily_pnl, 2),
        weekly_pnl=round(payload.weekly_pnl, 2),
        max_daily_loss_amount=round(daily_max, 2),
        max_weekly_loss_amount=round(weekly_max, 2),
        daily_loss_limit_hit=daily_hit,
        weekly_loss_limit_hit=weekly_hit,
        consecutive_losses=payload.consecutive_losses,
        cooldown_after_n_losses=payload.cooldown_after_n_losses,
        choppy_regime=payload.choppy_regime,
        cooldown_active=cooldown,
        cooldown_minutes=payload.cooldown_minutes if cooldown else 0,
        reasons=reasons,
    )


def _portfolio(payload: PositionPortfolioCooldownRequest, sizing: AccountRiskSizingRecord) -> PortfolioHeatMemoryRecord:
    proposed_trade_heat = (sizing.capital_to_use / payload.account_equity) * 100.0 if payload.account_equity > 0 else 0.0
    projected_heat = payload.current_sector_exposure_pct + payload.current_index_exposure_pct + proposed_trade_heat
    reasons: list[str] = []
    if payload.current_sector_exposure_pct >= payload.max_sector_exposure_pct:
        reasons.append("Sector exposure cap reached.")
    if payload.current_index_exposure_pct >= payload.max_index_exposure_pct:
        reasons.append("Index exposure cap reached.")
    if payload.correlation_cluster_exposure_pct >= payload.max_correlation_cluster_exposure_pct:
        reasons.append("Correlation cluster exposure cap reached.")
    if projected_heat >= payload.max_portfolio_heat_pct:
        reasons.append("Portfolio heat cap reached.")
    if not reasons:
        reasons.append("Portfolio heat caps are clear.")
    return PortfolioHeatMemoryRecord(
        exposure_id=f"HEAT-{payload.symbol.upper()}-{payload.sector}-{payload.index}",
        sector=payload.sector,
        index=payload.index,
        sector_exposure_pct=round(payload.current_sector_exposure_pct, 4),
        index_exposure_pct=round(payload.current_index_exposure_pct, 4),
        correlation_cluster_exposure_pct=round(payload.correlation_cluster_exposure_pct, 4),
        proposed_trade_heat_pct=round(proposed_trade_heat, 4),
        projected_portfolio_heat_pct=round(projected_heat, 4),
        max_portfolio_heat_pct=round(payload.max_portfolio_heat_pct, 4),
        blocks_trade=any(reason != "Portfolio heat caps are clear." for reason in reasons),
        reasons=reasons,
    )


def _cap(cap_id: str, cap_type: str, current: float, proposed: float, max_allowed: float) -> ExposureCapRecord:
    passed = proposed < max_allowed
    action = "allow_research" if passed else "force_no_trade"
    if not passed and proposed - max_allowed < 3.0:
        action = "reduce_size"
    return ExposureCapRecord(
        cap_id=cap_id,
        cap_type=cap_type,  # type: ignore[arg-type]
        current_value_pct=round(current, 4),
        proposed_value_pct=round(proposed, 4),
        max_allowed_pct=round(max_allowed, 4),
        pass_cap=passed,
        action=action,  # type: ignore[arg-type]
        reason=f"{cap_type} proposed {round(proposed, 2)}% versus max {round(max_allowed, 2)}%.",
    )


def _caps(payload: PositionPortfolioCooldownRequest, portfolio: PortfolioHeatMemoryRecord) -> list[ExposureCapRecord]:
    return [
        _cap("CAP-SECTOR", "sector", payload.current_sector_exposure_pct, payload.current_sector_exposure_pct, payload.max_sector_exposure_pct),
        _cap("CAP-INDEX", "index", payload.current_index_exposure_pct, payload.current_index_exposure_pct, payload.max_index_exposure_pct),
        _cap("CAP-CORR", "correlation_cluster", payload.correlation_cluster_exposure_pct, payload.correlation_cluster_exposure_pct, payload.max_correlation_cluster_exposure_pct),
        _cap("CAP-HEAT", "portfolio_heat", portfolio.projected_portfolio_heat_pct, portfolio.projected_portfolio_heat_pct, payload.max_portfolio_heat_pct),
    ]


def _scenarios(
    sizing: AccountRiskSizingRecord,
    portfolio: PortfolioHeatMemoryRecord,
    cooldown: DailyWeeklyCooldownRecord,
    caps: list[ExposureCapRecord],
) -> list[PositionPortfolioCooldownScenario]:
    blockers = []
    if sizing.sizing_blocked:
        blockers.append("sizing_blocked")
    if portfolio.blocks_trade:
        blockers.append("portfolio_heat")
    if cooldown.daily_loss_limit_hit:
        blockers.append("daily_loss")
    if cooldown.weekly_loss_limit_hit:
        blockers.append("weekly_loss")
    if cooldown.cooldown_active:
        blockers.append("cooldown")
    if any(not cap.pass_cap for cap in caps):
        blockers.append("exposure_cap")
    allowed = not blockers
    return [
        PositionPortfolioCooldownScenario(
            scenario_id="RISK-SCENARIO-BASE",
            label="Base research sizing",
            position_size=sizing.final_position_size,
            projected_heat_pct=portfolio.projected_portfolio_heat_pct,
            daily_loss_limit_hit=cooldown.daily_loss_limit_hit,
            weekly_loss_limit_hit=cooldown.weekly_loss_limit_hit,
            cooldown_active=cooldown.cooldown_active,
            trade_allowed=False,
            next_safe_action="RESEARCH_ONLY" if allowed else "NO_TRADE",
            blocker_reasons=blockers or ["research_only_permission_lock"],
        ),
        PositionPortfolioCooldownScenario(
            scenario_id="RISK-SCENARIO-REDUCED",
            label="Reduced-size what-if",
            position_size=max(0, sizing.final_position_size // 2),
            projected_heat_pct=round(max(0.0, portfolio.projected_portfolio_heat_pct - portfolio.proposed_trade_heat_pct / 2), 4),
            daily_loss_limit_hit=cooldown.daily_loss_limit_hit,
            weekly_loss_limit_hit=cooldown.weekly_loss_limit_hit,
            cooldown_active=cooldown.cooldown_active,
            trade_allowed=False,
            next_safe_action="WAIT" if cooldown.cooldown_active else "REDUCE_SIZE",
            blocker_reasons=blockers or ["manual_review_required"],
        ),
    ]


def build_position_portfolio_cooldown_report(
    payload: PositionPortfolioCooldownRequest | None = None,
) -> PositionPortfolioCooldownReport:
    payload = payload or PositionPortfolioCooldownRequest()
    sizing = _sizing(payload)
    cooldown = _cooldown(payload)
    portfolio = _portfolio(payload, sizing)
    caps = _caps(payload, portfolio)
    scenarios = _scenarios(sizing, portfolio, cooldown, caps)
    exposure_caps_active = any(not cap.pass_cap for cap in caps)
    loss_gates = cooldown.daily_loss_limit_hit or cooldown.weekly_loss_limit_hit
    cooldown_active = cooldown.cooldown_active
    gates = [
        PositionPortfolioCooldownGate(gate_id="TV-V082-001", name="account-risk sizing present", passed=sizing.raw_position_size >= 0, evidence=f"raw_size={sizing.raw_position_size}"),
        PositionPortfolioCooldownGate(gate_id="TV-V082-002", name="exposure caps active", passed=exposure_caps_active, evidence=f"failed_caps={sum(1 for cap in caps if not cap.pass_cap)}"),
        PositionPortfolioCooldownGate(gate_id="TV-V082-003", name="daily weekly loss gates active", passed=loss_gates, evidence=f"daily_hit={cooldown.daily_loss_limit_hit}, weekly_hit={cooldown.weekly_loss_limit_hit}"),
        PositionPortfolioCooldownGate(gate_id="TV-V082-004", name="cooldown gate active", passed=cooldown_active, evidence=f"cooldown_minutes={cooldown.cooldown_minutes}"),
        PositionPortfolioCooldownGate(gate_id="TV-V082-005", name="research-only sizing estimate", passed=True, evidence="trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true"),
        PositionPortfolioCooldownGate(gate_id="TV-BI-036", name="daily loss limit blocks trade", passed=cooldown.daily_loss_limit_hit, evidence="daily loss status is explicit."),
        PositionPortfolioCooldownGate(gate_id="TV-BI-037", name="portfolio heat blocks correlated trades", passed=portfolio.blocks_trade, evidence="portfolio heat and exposure caps are explicit."),
    ]
    return PositionPortfolioCooldownReport(
        risk_memory_version=VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        decision=payload.decision,
        sizing=sizing,
        portfolio_heat=portfolio,
        cooldown=cooldown,
        exposure_caps=caps,
        scenarios=scenarios,
        account_risk_sizing_present=True,
        exposure_caps_active=exposure_caps_active,
        daily_weekly_loss_gates_active=loss_gates,
        cooldown_gate_active=cooldown_active,
        research_only_sizing_estimate=True,
        no_live_route_attempted=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.82 turns risk sizing, portfolio heat, and cooldown into explicit memory records.",
            "Sizing is a research estimate only and cannot route live orders.",
            "Daily/weekly loss, exposure caps, and cooldown always reduce action, never increase it.",
        ],
    )
