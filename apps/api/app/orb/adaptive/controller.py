"""One bounded, deterministic scenario/contingency controller.

No language model, no repeated debate, no online fitting. Reconstructing
scenario state from a bounded immutable prefix makes replay identical to the
observation path and prevents multiplying correlated, overlapping evidence.
"""
from __future__ import annotations

from typing import Protocol
from .contracts import (
    AccountLimits, Branch, Candidate, Decision, Evidence, Forecast,
    MarketSnapshot, Policy, Side, Template, MINUTE, clock_ns, digest, evolve,
)
from .execution import build_plan, estimated_cost_r
from .features import extract, validate_prefix
from .registry import coverage


class ForecastProvider(Protocol):
    model_hash: str
    def estimate(self, forecast: Forecast, features: dict) -> Forecast: ...


class ValueProvider(Protocol):
    model_hash: str
    def annotate(self, candidate: Candidate, snapshot: MarketSnapshot, features: dict) -> Candidate: ...


class Controller:
    def __init__(self, policy: Policy, limits: AccountLimits,
                 forecaster: ForecastProvider | None = None, values: ValueProvider | None = None, data_guard=None):
        self.policy, self.limits = policy, limits
        self.forecaster, self.values = forecaster, values
        self.data_guard = data_guard
        if (getattr(data_guard, "source_hash", None) if data_guard else None) != policy.host_d1_source_hash:
            raise ValueError("EXACT_SHARED_HOST_D1_BINDING_REQUIRED")
        if (forecaster.model_hash if forecaster else None) != policy.forecast_model_hash:
            raise ValueError("FORECAST_MODEL_BINDING_MISMATCH")
        if values and getattr(values, "limits_hash", None) != digest(limits):
            raise ValueError("VALUE_ACCOUNT_BUDGET_BINDING_MISMATCH")
        if (values.model_hash if values else None) != policy.value_model_hash:
            raise ValueError("VALUE_MODEL_BINDING_MISMATCH")

    def evaluate(self, snapshot: MarketSnapshot) -> Decision:
        p = self.policy
        errors = validate_prefix(snapshot, p)
        if self.data_guard is not None and not self.data_guard(snapshot):
            errors += ("REGISTERED_HOST_D1_DATA_GATE_FAILED",)
        f = extract(snapshot, p) if not errors else {"range_locked": False, "failure_count": 0, "gap_ever_touched_pdc": None}
        cutoff = clock_ns(snapshot.session_date, p.last_entry_minute)
        expired = snapshot.as_of_ns >= cutoff
        branches = self._branches(snapshot, f, bool(errors), expired)
        evidence = self._evidence(snapshot, f) if not errors else ()
        candidates: tuple[Candidate, ...] = ()
        reasons: list[str] = list(errors)
        if not errors and not expired and f.get("range_locked") and f.get("gap_class") != "FLAT":
            candidates = self._candidates(snapshot, f)
        if expired:
            reasons.append("ENTRY_WINDOW_EXPIRED")
        if not f.get("range_locked"):
            reasons.append("OPENING_RANGE_NOT_COMPLETE")
        if f.get("gap_class") == "FLAT":
            reasons.append("GAP_DAY_POLICY_EXCLUDES_FLAT_SESSION")
        feasible = [c for c in candidates if c.status == "FEASIBLE"]
        if self.values:
            candidates = tuple(self.values.annotate(c, snapshot, f) for c in candidates)
            # SKIP has zero trade value. Unsupported estimates do not vote.
            feasible = sorted((c for c in candidates if c.status == "FEASIBLE" and c.lower_bound is not None and c.lower_bound > 0),
                              key=lambda c: (-c.lower_bound, p.templates.index(c.template)))
            if not feasible:
                reasons.append("NO_SUPPORTED_ACTION_BEATS_SKIP")
        elif feasible:
            reasons.append("FROZEN_RULE_PRIORITY_NOT_EXPECTED_VALUE_OPTIMAL")
        chosen = feasible[0].plan if feasible else None
        forecasts = self._forecasts(snapshot, f, evidence, chosen) if not errors else ()
        if self.forecaster:
            forecasts = tuple(self.forecaster.estimate(x, f) for x in forecasts)
        if chosen:
            reasons.extend(("EXACT_CONTROLLER_PROOF_REQUIRED", "HUMAN_APPROVAL_REQUIRED"))
            action = "SHADOW_RESEARCH_ONLY"
        elif errors:
            action = "HALT_AFFECTED_DECISIONS_FOR_DATA"
        elif expired or f.get("gap_class") == "FLAT":
            action = "SKIP_SESSION"
        elif f.get("failure_count", 0) or f.get("failure_index", -1) >= 0:
            action = "WAIT_FOR_REJECTION_OR_RECLAIM_CONFIRMATION"
        elif f.get("outside_count", 0):
            action = "WAIT_FOR_RETEST_HOLD_OR_NEXT_CLOSE"
        else:
            action = "WAIT_FOR_NEXT_CLOSE"
        if not chosen and candidates:
            reasons.extend(r for c in candidates for r in c.reasons)
        public = "WAIT" if errors or expired or f.get("gap_class") == "FLAT" else "WATCH"
        identity = [snapshot.snapshot_hash, p.policy_hash, self.limits.model_dump(mode="json")]
        return Decision(
            decision_id=digest(identity), policy_hash=p.policy_hash, snapshot_hash=snapshot.snapshot_hash,
            session_date=snapshot.session_date, symbol=snapshot.prior.symbol,
            as_of_ns=snapshot.as_of_ns, public_ticket=public, internal_action=action,
            reason_codes=tuple(dict.fromkeys(reasons)), evidence=evidence, branches=branches,
            forecasts=forecasts, candidates=candidates, selected_plan=chosen,
            gap_ever_touched_pdc=f.get("gap_ever_touched_pdc"),
            observed_failure_episodes=int(f.get("failure_count", 0)), features=f,
            scenario_status=coverage(f, errors, snapshot.as_of_ns, cutoff),
            next_triggers=("NEXT_AVAILABLE_CLOSED_FEATURE_BAR", "VERIFIED_REFERENCE_UPDATE", "PROPOSAL_OR_ENTRY_TIMER"),
        )

    def _branches(self, s: MarketSnapshot, f: dict, invalid: bool, expired: bool) -> tuple[Branch, ...]:
        end = clock_ns(s.session_date, self.policy.last_entry_minute)
        last = s.bars[-1].event_id if s.bars else "NO_OBSERVATION"
        failure = f.get("last_failure_event")
        def branch(name: str, state: str, support: bool, contrary: bool, nxt: str, refute: str) -> Branch:
            actual = "UNOBSERVABLE" if invalid else "EXPIRED" if expired else state
            support_ids = (tuple(dict.fromkeys((failure,last))) if failure and name in {"FAILED_BREAK", "UNFILLED_GAP_FADE", "FAILURE_RECLAIMS"} else (last,))
            return Branch(branch_id=name, state=actual, supports=support_ids if support else (),
                          contradicts=(last,) if contrary else (), next_required=nxt, refute_on=refute, expires_ns=end)
        count = f.get("outside_count", 0)
        return (
            branch("ACCEPTED_CONTINUATION", "CONFIRMED" if count >= self.policy.accepted_closes else "WATCHING", count > 0, bool(failure) and count == 0,
                   "Registered consecutive outside closes or a valid retest", "Completed close back inside locked range"),
            branch("ORDERLY_RETEST", "CONFIRMED" if f.get("retest_ready") else "POSSIBLE", bool(f.get("retest_ready")), bool(failure) and count == 0,
                   "Boundary touch within frozen tolerance and outside close", "Deep structural penetration or inside close"),
            branch("FAILED_BREAK", "CONFIRMED" if f.get("failure_count", 0) else "POSSIBLE", bool(failure), count >= self.policy.accepted_closes,
                   "Observe close returning inside after an outside close", "Reclaim refutes ongoing failure, not the historical observed event"),
            branch("UNFILLED_GAP_FADE", "REFUTED" if f.get("gap_ever_touched_pdc") or count else "ARMED" if f.get("fade_ready") else "WATCHING", bool(failure) and not count, bool(f.get("gap_ever_touched_pdc")) or count > 0,
                   "Later independent rejection beyond failed-bar extreme and session open", "PDC touched, OR reclaimed, target room lost, or expiry"),
            branch("FAILURE_RECLAIMS", "CONFIRMED" if failure and count >= self.policy.accepted_closes else "WATCHING" if failure else "POSSIBLE", bool(failure) and count > 0, bool(failure) and count == 0,
                   "New persistent outside acceptance after observed rejection", "A new inside close, excessive extension, or expiry"),
            branch("TWO_SIDED_CHOP", "WATCHING" if f.get("chop_risk") else "POSSIBLE", bool(f.get("chop_risk")), count >= self.policy.accepted_closes + self.policy.chop_extra_closes,
                   "Distinct failures versus sustained accepted escape", "Later acceptance can weaken the current chop interpretation"),
            branch("EXTENSION_EXHAUSTION_RISK", "WATCHING" if f.get("extension_or", 0) > self.policy.max_extension_or else "POSSIBLE", f.get("extension_or", 0) > self.policy.max_extension_or, bool(f.get("retest_ready")),
                   "Rejection versus continued hold; gap size alone cannot choose", "Valid held retest or continuing acceptance; no automatic fade"),
            branch("UNKNOWN_OR_UNSUPPORTED", "UNSUPPORTED", invalid, False,
                   "Verified data and independent support for this exact state", "No finite scenario list eliminates unknown risks"),
        )

    def _evidence(self, s: MarketSnapshot, f: dict) -> tuple[Evidence, ...]:
        rows = []
        # One bar event, one geometry family. Engulfing/body/wicks are not
        # independent likelihood observations and never multiplied together.
        selected = {b.event_id: b for b in s.bars[:self.policy.range_minutes//self.policy.feature_minutes] + s.bars[-6:]}
        for b in s.bars:
            if b.event_id == f.get("last_failure_event"):
                selected[b.event_id] = b
        rows.append(Evidence(event_id=digest(s.prior), known_at_ns=s.prior.available_ns, family="PRIOR_SESSION_REFERENCE",
                             facts=("VERIFIED_COMPARABLE_PRIOR_LEVELS_AND_ATR",)))
        for b in sorted(selected.values(), key=lambda b:b.open_ns):
            tags = (f"CLOSED_OHLCV:{b.open_ns}:{b.close_ns}",)
            rows.append(Evidence(event_id=b.event_id, known_at_ns=b.available_ns, family="PRICE_GEOMETRY", facts=tags))
        if s.bars:
            facts = ["PDC_TOUCHED_STICKY" if f.get("gap_ever_touched_pdc") else "PDC_UNTOUCHED_IN_COMPLETE_PREFIX"]
            if f.get("failure_count", 0):
                facts.append("BREAKOUT_FAILURE_ALREADY_OBSERVED_NOT_A_PREDICTION")
            rows[-1] = evolve(rows[-1], facts=rows[-1].facts + tuple(facts))
        return tuple(rows)

    def _candidates(self, s: MarketSnapshot, f: dict) -> tuple[Candidate, ...]:
        p = self.policy
        last = s.bars[-1]
        side = Side(f["gap_direction"])
        sign, tick = side.sign, s.prior.tick_size
        count = int(f.get("outside_count", 0))
        needed = p.accepted_closes + (p.chop_extra_closes if f.get("chop_risk") else 0)
        expiry = min(s.as_of_ns + p.proposal_ttl_seconds * 1_000_000_000, clock_ns(s.session_date, p.last_entry_minute))
        results = []
        for template in p.templates:
            target_side = Side.SHORT if side == Side.LONG else Side.LONG
            ready = False
            target_side = target_side if template == Template.GAP_FADE else side
            stop = (f["or_low"] - p.stop_buffer_ticks*tick if sign > 0 else f["or_high"] + p.stop_buffer_ticks*tick)
            nxt = "Completed registered trigger before expiry"
            refute = "Opposing close, failed geometry, unavailable data, or expiry"
            if template == Template.FIRST_BREAK:
                ready = count == 1 and f.get("failure_count", 0) == 0
                nxt = "First gap-direction close outside OR"
            elif template == Template.ACCEPTANCE:
                ready = count >= needed and f.get("failure_count", 0) == 0
                nxt = f"{needed} consecutive outside closes"
            elif template == Template.RETEST_HOLD:
                ready = bool(f.get("retest_ready"))
                stop = last.low - p.stop_buffer_ticks*tick if sign > 0 else last.high + p.stop_buffer_ticks*tick
                nxt = "Orderly boundary retest with outside close"
            elif template == Template.RECLAIM:
                ready = f.get("failure_index", -1) >= 0 and count >= needed
                nxt = f"{needed} new outside closes after failed break/rejection"
            elif template == Template.GAP_FADE:
                ready = bool(f.get("fade_ready"))
                stop = f.get("excursion", f["or_high"] if sign > 0 else f["or_low"]) + sign*p.stop_buffer_ticks*tick
                nxt = "Independent later rejection beyond failure-bar extreme and session open"
                refute = "PDC touch, gap-direction OR reclaim, insufficient fixed-target room"
            elif template == Template.PD_LEVEL_BREAK:
                level = s.prior.high if sign > 0 else s.prior.low
                ready = count >= needed and (level - f["boundary"])*sign > 0 and (last.close-level)*sign > 0
                stop = min(level, f["or_high"]) - tick if sign > 0 else max(level, f["or_low"]) + tick
                nxt = "Accepted break of both OR and genuinely exterior prior-session level"
            reasons = []
            if not ready:
                results.append(Candidate(template=template, status="WAITING", reasons=("TRIGGER_NOT_CONFIRMED",), next_trigger=nxt, refutation=refute, expiry_ns=expiry))
                continue
            if f.get("two_sided_bar"):
                reasons.append("TWO_SIDED_BAR_PATH_ORDER_UNKNOWN")
            if f.get("gap_ever_touched_pdc") and (template == Template.GAP_FADE or not p.allow_continuation_after_gap_fill):
                reasons.append("PDC_TOUCH_INVALIDATES_THIS_RECIPE")
            if template != Template.GAP_FADE and f.get("extension_or", 0) > p.max_extension_or:
                reasons.append("NO_CHASE_EXTENSION_LIMIT")
            vwap = f.get("session_vwap")
            if p.require_session_vwap and (vwap is None or (last.close-vwap)*target_side.sign < 0):
                reasons.append("SESSION_VWAP_MISSING_OR_OPPOSES_CANDIDATE_SIDE")
            if p.require_volume_confirmation and f.get("volume_ratio", 0) < p.minimum_volume_ratio:
                reasons.append("REGISTERED_VOLUME_CONFIRMATION_FAILED")
            plan = None
            if not reasons:
                plan, extra = build_plan(s, p, self.limits, template, target_side, stop, f["boundary"],
                                         ("INDEPENDENT_TRIGGER_CONFIRMED", template.value))
                reasons.extend(extra)
            challenge = (
                "This alternative can fail; rejection is not opposite-side profit evidence.",
                "Entry delay can expire the plan or move the actual fill outside its envelope.",
                "A stop gap can lose more than the nominal risk budget.",
                "OHLCV cannot identify news, dealers, spread, depth, or a guaranteed executable price.",
            )
            if plan:
                stressed = evolve(p.costs, spread_bps=min(1000, p.costs.spread_bps*2),
                                  slippage_bps=min(1000, p.costs.slippage_bps*2), impact_bps=min(1000, p.costs.impact_bps*2),
                                  fee_bps_per_side=min(1000, p.costs.fee_bps_per_side*2))
                ratio = estimated_cost_r(plan.reference_entry, plan.stop, plan.side, tick, stressed)
                challenge += (f"DOUBLE_COST_STRESS_COST_R={ratio:.6f}; diagnostic, not a probability",)
            results.append(Candidate(template=template, status="FEASIBLE" if plan else "REJECTED",
                                     reasons=tuple(reasons), plan=plan, next_trigger=nxt,
                                     refutation=refute, expiry_ns=expiry, challenge=challenge))
        return tuple(results[:p.max_candidates])

    def _forecasts(self, s: MarketSnapshot, f: dict, evidence: tuple[Evidence, ...], plan) -> tuple[Forecast, ...]:
        p = self.policy
        if not f.get("range_locked") or not s.bars:
            return ()
        targets = []
        if f.get("outside_count", 0):
            targets.append(("RETURN_INSIDE_OR", 2, "PREDICTION"))
        if not f.get("gap_ever_touched_pdc"):
            targets.append(("PDC_TOUCH", 2, "PREDICTION"))
        remain = max(0, (clock_ns(s.session_date, p.last_entry_minute)-s.bars[-1].close_ns)//(p.feature_minutes*MINUTE))
        if remain:
            targets.extend((("RETEST_VALID_FILL_BEFORE_CUTOFF", remain, "UNESTIMATED"),
                            ("WAIT_MISSES_ALL_ELIGIBLE_ENTRIES", remain, "UNESTIMATED"),
                            ("ENTRY_ECONOMICS_INVALIDATED", remain, "UNESTIMATED")))
        if plan:
            horizon = max(1, (plan.flat_ns-s.bars[-1].close_ns)//(p.feature_minutes*MINUTE))
            targets.append(("EXACT_PLAN_STOP_BEFORE_TARGET", horizon, "UNESTIMATED"))
        result = []
        for event, bars, _ in targets:
            endpoint = s.bars[-1].close_ns + bars*p.feature_minutes*MINUTE
            if s.as_of_ns >= endpoint:
                continue
            identity = [s.snapshot_hash, p.policy_hash, event, bars]
            result.append(Forecast(forecast_id=digest(identity), snapshot_hash=s.snapshot_hash,
                                  policy_hash=p.policy_hash, symbol=s.prior.symbol,
                                  session_date=s.session_date, event=event, issued_ns=s.as_of_ns,
                                  horizon_bars=int(bars), horizon_minutes=int(bars*p.feature_minutes),
                                  effective_end_ns=endpoint,
                                  horizon_kind="FEATURE_BARS" if event in {"RETURN_INSIDE_OR", "PDC_TOUCH"} else "WALL_CLOCK",
                                  requested_end_ns=(plan.flat_ns if event == "EXACT_PLAN_STOP_BEFORE_TARGET" else clock_ns(s.session_date,p.last_entry_minute)) if event not in {"RETURN_INSIDE_OR", "PDC_TOUCH"} else endpoint,
                                  action_policy_id=p.policy_id, plan_proposal_id=plan.proposal_id if plan and event=="EXACT_PLAN_STOP_BEFORE_TARGET" else None,
                                  episode_id=str(f.get("episode_id", s.bars[-1].event_id)),
                                  evidence_event_ids=tuple(x.event_id for x in evidence)))
        return tuple(result)
