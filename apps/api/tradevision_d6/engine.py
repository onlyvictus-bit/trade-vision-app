"""Deterministic paper-decision kernel. No network, training, clock reads or orders."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Context, Decimal, ROUND_FLOOR, ROUND_HALF_EVEN, localcontext

from .codec import fingerprint
from .models import (
    ContractError, Decision, ONE, RISK_NAMES, Request, ScenarioResult, Side,
    SideAssessment, Status, TradePlan, ZERO,
)
from .proofs import ProofVerifier


class D6Engine:
    def __init__(self, verifier: ProofVerifier) -> None:
        self.verifier = verifier

    def evaluate(self, request: Request) -> Decision:
        if not isinstance(request, Request):
            raise ContractError("Request required")
        # Keep external application Decimal settings from changing decisions.
        with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
            return self._evaluate(request)

    @staticmethod
    def _scores(request: Request) -> tuple[Decimal, Decimal]:
        values = {e.source: e for e in request.evidence}
        total_group_weight = sum((g.weight for g in request.policy.groups), ZERO)
        long = short = ZERO
        for group in request.policy.groups:
            sources = [s for s in request.policy.sources if s.group == group.name]
            denominator = sum((s.weight for s in sources), ZERO)
            group_long = group_short = ZERO
            for source in sources:
                row = values.get(source.name)
                if row is not None:
                    group_long += source.weight * row.long
                    group_short += source.weight * row.short
            long += group.weight * group_long / denominator
            short += group.weight * group_short / denominator
        return long / total_group_weight, short / total_group_weight

    @staticmethod
    def _global_gates(r: Request) -> tuple[str, ...]:
        s, p, a, now = r.snapshot, r.policy, r.portfolio, r.evaluation_at
        reasons: list[str] = []
        present = {e.source for e in r.evidence}
        for source in p.sources:
            if source.required and source.name not in present:
                reasons.append(f"REQUIRED_SOURCE_MISSING_{source.name}")
        for name in RISK_NAMES:
            if getattr(r.risks, name) > getattr(p.risk_caps, name):
                reasons.append(f"RISK_CAP_{name.upper()}")
        if s.quote_at < s.bar_closed_at:
            reasons.append("QUOTE_PRECEDES_SIGNAL_CLOSE")
        for value, label in (
            (s.bar_is_closed, "BAR_NOT_CLOSED"), (s.data_complete, "DATA_INCOMPLETE"),
            (s.corporate_actions_checked, "CORPORATE_ACTIONS_UNCHECKED"),
            (s.event_feed_ok, "EVENT_FEED_UNAVAILABLE"),
            (s.session_entry_allowed, "SESSION_ENTRY_BLOCKED"),
            (s.instrument_eligible, "INSTRUMENT_INELIGIBLE"),
            (a.account_entry_allowed, "ACCOUNT_ENTRY_BLOCKED"),
        ):
            if not value:
                reasons.append(label)
        if a.kill_switch:
            reasons.append("KILL_SWITCH")
        if a.conflicting_position:
            reasons.append("CONFLICTING_POSITION")
        if not s.bar_opened_at < s.bar_closed_at <= now:
            reasons.append("BAR_TIME_INVALID")
        if not s.bar_closed_at <= s.data_received_at <= s.feature_available_at <= now:
            reasons.append("DATA_AVAILABILITY_INVALID")
        if not s.feature_cutoff_at == s.bar_closed_at:
            reasons.append("FEATURE_CUTOFF_MISMATCH")
        for when, seconds, reason in (
            (s.bar_closed_at, p.max_bar_age_seconds, "BAR_STALE_OR_FUTURE"),
            (s.quote_at, p.max_quote_age_seconds, "QUOTE_STALE_OR_FUTURE"),
            (a.observed_at, p.max_portfolio_age_seconds, "PORTFOLIO_STALE_OR_FUTURE"),
        ):
            if not timedelta(0) <= now - when <= timedelta(seconds=seconds):
                reasons.append(reason)
        if a.daily_loss >= a.equity * p.daily_loss_fraction:
            reasons.append("DAILY_LOSS_LIMIT")
        if a.weekly_loss >= a.equity * p.weekly_loss_fraction:
            reasons.append("WEEKLY_LOSS_LIMIT")
        if a.open_modeled_risk >= a.equity * p.portfolio_risk_fraction:
            reasons.append("PORTFOLIO_RISK_LIMIT")
        return tuple(reasons)

    @staticmethod
    def _preferred(r: Request, long: Decimal, short: Decimal) -> tuple[Side | None, str | None]:
        exists = {plan.side for plan in r.plans}
        if not exists:
            return None, "NO_SETUP"
        if len(exists) == 1:
            side = next(iter(exists))
            evidence = long if side is Side.LONG else short
            opposing = short if side is Side.LONG else long
            if evidence < r.policy.minimum_evidence:
                return None, "INSUFFICIENT_DIRECTIONAL_EVIDENCE"
            # An absent opposing plan does not justify ignoring opposing evidence.
            if evidence - opposing < r.policy.minimum_direction_margin:
                return None, "DIRECTION_CONFLICT"
            return side, None
        if max(long, short) < r.policy.minimum_evidence:
            return None, "INSUFFICIENT_DIRECTIONAL_EVIDENCE"
        if abs(long - short) < r.policy.minimum_direction_margin:
            return None, "DIRECTION_CONFLICT"
        return (Side.LONG if long > short else Side.SHORT), None

    @staticmethod
    def _economics(r: Request, plan: TradePlan, probability: Decimal | None) -> tuple[ScenarioResult, ...]:
        gross_reward, gross_risk = abs(plan.target - plan.entry), abs(plan.entry - plan.stop)
        out: list[ScenarioResult] = []
        for scenario in r.policy.scenarios:
            cost = plan.costs.round_trip_per_unit * scenario.cost_multiplier
            gap = plan.costs.gap_allowance_per_unit * scenario.gap_multiplier
            win, loss = gross_reward - cost, gross_risk + cost + gap
            expectation = None if probability is None else probability * win - (ONE - probability) * loss
            out.append(ScenarioResult(scenario.name, win, loss, win / loss, expectation))
        return tuple(out)

    @staticmethod
    def _size(r: Request, plan: TradePlan, scenarios: tuple[ScenarioResult, ...]) -> int:
        a, p, s = r.portfolio, r.policy, r.snapshot
        budget = min(
            a.equity * p.risk_per_trade_fraction,
            a.equity * p.portfolio_risk_fraction - a.open_modeled_risk,
            a.equity * p.daily_loss_fraction - a.daily_loss,
            a.equity * p.weekly_loss_fraction - a.weekly_loss,
        )
        if budget <= ZERO:
            return 0
        loss = max(x.modeled_loss_per_unit for x in scenarios)
        risk_units = int((budget / loss).to_integral_value(rounding=ROUND_FLOOR))
        # Reserve modeled round-trip costs as well as notional, conservatively.
        worst_cost = max(plan.costs.round_trip_per_unit * x.cost_multiplier for x in p.scenarios)
        cash_units = int((a.available_notional / (plan.entry + worst_cost)).to_integral_value(rounding=ROUND_FLOOR))
        units = min(risk_units, cash_units, s.capacity_units)
        return (units // s.lot_size) * s.lot_size

    def _side(self, r: Request, side: Side, evidence: Decimal,
              global_reasons: tuple[str, ...]) -> SideAssessment:
        plan = next((p for p in r.plans if p.side is side), None)
        if plan is None:
            return SideAssessment(side, evidence, False, ZERO, ZERO, False, 0, False, (), (), ("NO_SETUP",))
        hard, watch = list(global_reasons), []
        survival = ONE
        for name in RISK_NAMES:
            risk = getattr(r.risks, name)
            survival *= ONE - risk
        quality = plan.quality * survival
        if quality < r.policy.minimum_quality:
            hard.append("QUALITY_BELOW_THRESHOLD")
        if evidence < r.policy.minimum_evidence:
            watch.append("INSUFFICIENT_DIRECTIONAL_EVIDENCE")
        if side is Side.SHORT and not r.snapshot.short_eligible:
            hard.append("SHORT_INELIGIBLE")
        if any(price % r.snapshot.tick_size != ZERO for price in (plan.entry, plan.stop, plan.target)):
            hard.append("PRICE_NOT_TICK_ALIGNED")
        quote = r.snapshot.ask if side is Side.LONG else r.snapshot.bid
        if abs(plan.entry - quote) / plan.entry * Decimal("10000") > r.policy.max_entry_drift_bps:
            hard.append("ENTRY_PRICE_DRIFT")
        age = r.evaluation_at - plan.costs.estimated_at
        if not timedelta(0) <= age <= timedelta(seconds=r.policy.max_cost_age_seconds):
            hard.append("COST_ESTIMATE_STALE_OR_FUTURE")
        if plan.costs.round_trip_per_unit < r.snapshot.ask - r.snapshot.bid:
            hard.append("COST_BELOW_OBSERVED_SPREAD")
        proof = next((p for p in r.proofs if p.side is side), None)
        proof_valid, probability = False, None
        if proof is None:
            watch.append("VALIDATION_PROOF_MISSING")
        else:
            proof_errors = self.verifier.verify(r, plan, proof)
            hard.extend(proof_errors)
            if not proof_errors:
                proof_valid, probability = True, proof.target_probability_lower_bound
        scenarios = self._economics(r, plan, probability)
        for scenario in scenarios:
            if scenario.net_win_per_unit <= ZERO:
                hard.append(f"SCENARIO_{scenario.name}_NET_WIN_NONPOSITIVE")
            if scenario.net_reward_risk < r.policy.minimum_net_reward_risk:
                hard.append(f"SCENARIO_{scenario.name}_REWARD_RISK_LOW")
            if scenario.modeled_expectancy_per_unit is not None and scenario.modeled_expectancy_per_unit < r.policy.minimum_modeled_expectancy:
                hard.append(f"SCENARIO_{scenario.name}_EXPECTANCY_LOW")
        quantity = self._size(r, plan, scenarios)
        if quantity == 0:
            hard.append("NO_SIZE_WITHIN_BUDGET")
        elif not plan.costs.valid_for_min_units <= quantity <= plan.costs.valid_for_max_units:
            hard.append("COST_SIZE_SCOPE_MISMATCH")
        eligible = not hard and not watch
        # Quantity is a proposal only, never an authorization. Suppress it if blocked.
        return SideAssessment(side, evidence, True, quality, quality if eligible else ZERO,
                              eligible, quantity if eligible else 0, proof_valid,
                              scenarios, tuple(hard), tuple(watch))

    def _evaluate(self, r: Request) -> Decision:
        global_reasons = self._global_gates(r)
        long_score, short_score = self._scores(r)
        preferred, preference_reason = self._preferred(r, long_score, short_score)
        long = self._side(r, Side.LONG, long_score, global_reasons)
        short = self._side(r, Side.SHORT, short_score, global_reasons)
        selected, permission, valid_until = None, ZERO, None
        if global_reasons:
            status, reasons = Status.WAIT, global_reasons
        elif preferred is None:
            status = Status.WAIT if preference_reason == "NO_SETUP" else Status.WATCH
            reasons = (preference_reason or "NO_PREFERRED_SIDE",)
        else:
            chosen = long if preferred is Side.LONG else short
            if chosen.hard_reasons:
                status, reasons = Status.WAIT, chosen.hard_reasons + chosen.watch_reasons
            elif chosen.watch_reasons:
                status, reasons = Status.WATCH, chosen.watch_reasons
            else:
                status, reasons = Status.PAPER_CANDIDATE, ("ALL_PAPER_GATES_PASSED",)
                selected, permission = preferred, chosen.permission
                plan = next(p for p in r.plans if p.side is selected)
                proof = next(p for p in r.proofs if p.side is selected)
                valid_until = min(
                    r.snapshot.quote_at + timedelta(seconds=r.policy.max_quote_age_seconds),
                    r.snapshot.bar_closed_at + timedelta(seconds=r.policy.max_bar_age_seconds),
                    r.portfolio.observed_at + timedelta(seconds=r.policy.max_portfolio_age_seconds),
                    plan.costs.estimated_at + timedelta(seconds=r.policy.max_cost_age_seconds),
                    proof.expires_at,
                )
                if valid_until <= r.evaluation_at:
                    status, reasons = Status.WAIT, ("CANDIDATE_LIFETIME_EXHAUSTED",)
                    selected, permission, valid_until = None, ZERO, None
        trace = (
            "STRICT_INPUT_CONTRACT", "POINT_IN_TIME_AND_ACCOUNT_GATES",
            "SEPARATE_LONG_SHORT_EVIDENCE", "EVIDENCE_ONLY_PREFERRED_SIDE",
            "MONOTONE_RISK_AND_SAFETY", "SIGNED_VALIDATION_CHECK",
            "FIXED_STRESS_ECONOMICS_AND_SIZING", "NO_OPPOSITE_SIDE_FALLBACK", "PAPER_ONLY",
        )
        return Decision(fingerprint({"engine": "tradevision-d6-v1", "request": r}),
                        r.snapshot.symbol, r.snapshot.horizon, status, long_score, short_score,
                        preferred, selected, permission, valid_until, long, short, tuple(reasons), trace)
