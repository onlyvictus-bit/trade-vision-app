from __future__ import annotations

from math import floor

from ..models import (
    BehaviorRiskRequest,
    DailyLossLimitRecord,
    PortfolioExposureRecord,
    RiskSizingResult,
)


RISK_ENGINE_VERSION = "behavior-risk-engine.v0.21"
TRADE_CANDIDATE_SIGNALS = {
    "BUY_BREAKOUT",
    "SELL_BREAKDOWN",
    "BUY_RETEST",
    "SELL_RETEST",
    "BUY_FADE",
    "SELL_FADE",
}


def evaluate_behavior_risk(request: BehaviorRiskRequest) -> RiskSizingResult:
    """Convert a behavior decision into risk, size, portfolio heat, and cooldown output."""

    side_risk = abs(request.entry_price - request.stop_loss)
    reward = abs(request.target - request.entry_price)
    risk_reward = round(reward / side_risk, 4) if side_risk > 0 else 0.0
    daily = _daily_loss_record(request)
    portfolio = _portfolio_record(request)
    base_risk_pct = _risk_pct(request)
    risk_amount = request.account_equity * (base_risk_pct / 100.0)
    raw_size = floor(risk_amount / side_risk) if side_risk > 0 else 0
    capital_cap = request.account_equity * 0.10
    capital_cap_size = floor(capital_cap / request.entry_price)
    position_size = max(0, min(raw_size, capital_cap_size))
    capital_to_use = round(position_size * request.entry_price, 2)
    max_loss_amount = round(position_size * side_risk, 2)
    reward_amount = round(position_size * reward, 2)
    block_reasons = _block_reasons(request, daily, portfolio, risk_reward, position_size)
    trade_allowed = not block_reasons and request.decision in TRADE_CANDIDATE_SIGNALS
    if not trade_allowed:
        position_size = 0
        capital_to_use = 0.0
        max_loss_amount = 0.0
        reward_amount = 0.0
        base_risk_pct = 0.0
    return RiskSizingResult(
        risk_version=RISK_ENGINE_VERSION,
        symbol=request.symbol.upper(),
        decision=request.decision,
        position_size=position_size,
        risk_per_trade_pct=round(base_risk_pct, 4),
        capital_to_use=capital_to_use,
        max_loss_amount=max_loss_amount,
        reward_amount=reward_amount,
        risk_reward=risk_reward,
        portfolio=portfolio,
        daily_loss=daily,
        trade_allowed=trade_allowed,
        block_reasons=block_reasons,
        sizing_formula=(
            "position_size = floor((account_equity * adjusted_risk_pct) / abs(entry_price - stop_loss)), "
            "capped at 10% account capital; output is simulation-only."
        ),
        no_live_route_attempted=True,
    )


def _risk_pct(request: BehaviorRiskRequest) -> float:
    if request.decision not in TRADE_CANDIDATE_SIGNALS:
        return 0.0
    confidence_factor = 0.15 + (request.confidence_pct / 100.0) * 0.35
    liquidity_factor = 1.0 if request.liquidity_score >= 0.75 else 0.65 if request.liquidity_score >= 0.5 else 0.0
    slippage_factor = 1.0 if request.slippage_risk_pct <= 0.1 else 0.75 if request.slippage_risk_pct <= 0.25 else 0.45
    correlation_factor = {"low": 1.0, "medium": 0.7, "high": 0.4}[request.correlation_risk]
    return min(request.max_risk_per_trade_pct, request.max_risk_per_trade_pct * confidence_factor * liquidity_factor * slippage_factor * correlation_factor)


def _daily_loss_record(request: BehaviorRiskRequest) -> DailyLossLimitRecord:
    max_loss = request.account_equity * (request.max_daily_loss_pct / 100.0)
    daily_limit_hit = request.daily_pnl <= -max_loss
    cooldown = request.consecutive_losses >= request.cooldown_after_n_losses or request.choppy_regime
    reasons: list[str] = []
    if daily_limit_hit:
        reasons.append("Daily loss limit hit; stop trading for the day.")
    if request.consecutive_losses >= request.cooldown_after_n_losses:
        reasons.append(f"{request.consecutive_losses} consecutive losses triggered cooldown.")
    if request.choppy_regime:
        reasons.append("Choppy regime active; cooldown required.")
    if not reasons:
        reasons.append("Daily loss and cooldown gates are clear.")
    return DailyLossLimitRecord(
        daily_pnl=round(request.daily_pnl, 2),
        max_daily_loss_amount=round(max_loss, 2),
        daily_loss_limit_hit=daily_limit_hit,
        cooldown_active=cooldown,
        cooldown_minutes=request.cooldown_minutes if cooldown else 0,
        reasons=reasons,
    )


def _portfolio_record(request: BehaviorRiskRequest) -> PortfolioExposureRecord:
    proposed_heat = request.current_index_exposure_pct + request.current_sector_exposure_pct
    blocks = (
        request.current_sector_exposure_pct >= request.max_sector_exposure_pct
        or request.current_index_exposure_pct >= request.max_index_exposure_pct
        or proposed_heat >= request.max_portfolio_heat_pct
        or request.correlation_risk == "high"
    )
    reasons: list[str] = []
    if request.current_sector_exposure_pct >= request.max_sector_exposure_pct:
        reasons.append("Sector exposure limit reached.")
    if request.current_index_exposure_pct >= request.max_index_exposure_pct:
        reasons.append("Index exposure limit reached.")
    if proposed_heat >= request.max_portfolio_heat_pct:
        reasons.append("Portfolio heat limit reached.")
    if request.correlation_risk == "high":
        reasons.append("Correlation cluster risk is high.")
    if not reasons:
        reasons.append("Portfolio exposure gates are clear.")
    return PortfolioExposureRecord(
        sector=request.sector,
        index=request.index,
        sector_exposure_pct=round(request.current_sector_exposure_pct, 4),
        index_exposure_pct=round(request.current_index_exposure_pct, 4),
        correlation_risk=request.correlation_risk,
        portfolio_heat_pct=round(proposed_heat, 4),
        blocks_trade=blocks,
        reasons=reasons,
    )


def _block_reasons(
    request: BehaviorRiskRequest,
    daily: DailyLossLimitRecord,
    portfolio: PortfolioExposureRecord,
    risk_reward: float,
    position_size: int,
) -> list[str]:
    reasons: list[str] = []
    if request.decision not in TRADE_CANDIDATE_SIGNALS:
        reasons.append(f"Decision {request.decision} is not a trade candidate.")
    if daily.daily_loss_limit_hit:
        reasons.append("Daily loss limit hit.")
    if daily.cooldown_active:
        reasons.append("Cooldown active.")
    if portfolio.blocks_trade:
        reasons.append("Portfolio exposure gate blocks trade.")
    if risk_reward < 1.5:
        reasons.append("Risk/reward is below 1.5R.")
    if request.liquidity_score < 0.5:
        reasons.append("Liquidity score is below minimum.")
    if request.slippage_risk_pct > 0.35:
        reasons.append("Slippage risk is above maximum.")
    if position_size <= 0 and request.decision in TRADE_CANDIDATE_SIGNALS:
        reasons.append("Position size resolves to zero after risk caps.")
    return reasons
