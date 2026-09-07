from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D, Inexact, localcontext

import pytest

from tradevision_d6 import DirectionalEvidence, Horizon, Side, SourceSpec, Status
from tradevision_d6.demo import attach_synthetic_proofs


def test_synthetic_candidate(engine, proven):
    out = engine.evaluate(proven)
    assert out.status is Status.PAPER_CANDIDATE
    assert out.selected_side is Side.LONG
    assert out.long_evidence == D("0.85")
    assert out.short_evidence == D("0.10")
    assert out.trade_permission == D("0.735091890625")
    assert out.long.quantity == 178
    assert out.short.quantity == 0
    assert out.long.proof_valid


def test_no_proof_is_watch_not_fabricated_probability(engine, request_base):
    out = engine.evaluate(request_base)
    assert out.status is Status.WATCH and out.trade_permission == 0
    assert "VALIDATION_PROOF_MISSING" in out.reasons
    assert all(x.modeled_expectancy_per_unit is None for x in out.long.scenarios)


@pytest.mark.parametrize("name,reason", [
    ("bar_is_closed", "BAR_NOT_CLOSED"), ("data_complete", "DATA_INCOMPLETE"),
    ("corporate_actions_checked", "CORPORATE_ACTIONS_UNCHECKED"),
    ("event_feed_ok", "EVENT_FEED_UNAVAILABLE"),
    ("session_entry_allowed", "SESSION_ENTRY_BLOCKED"),
    ("instrument_eligible", "INSTRUMENT_INELIGIBLE"),
])
def test_boolean_global_gates(engine, proven, name, reason):
    req = replace(proven, snapshot=replace(proven.snapshot, **{name: False}))
    out = engine.evaluate(attach_synthetic_proofs(req))
    assert out.status is Status.WAIT and out.trade_permission == 0
    assert reason in out.reasons


@pytest.mark.parametrize("name,value,reason", [
    ("kill_switch", True, "KILL_SWITCH"), ("conflicting_position", True, "CONFLICTING_POSITION"),
    ("account_entry_allowed", False, "ACCOUNT_ENTRY_BLOCKED"),
    ("daily_loss", D("2000"), "DAILY_LOSS_LIMIT"),
    ("weekly_loss", D("5000"), "WEEKLY_LOSS_LIMIT"),
    ("open_modeled_risk", D("2000"), "PORTFOLIO_RISK_LIMIT"),
])
def test_account_gates(engine, proven, name, value, reason):
    out = engine.evaluate(replace(proven, portfolio=replace(proven.portfolio, **{name: value})))
    assert out.status is Status.WAIT and reason in out.reasons


@pytest.mark.parametrize("name,offset,reason", [
    ("quote_at", -6, "QUOTE_STALE_OR_FUTURE"), ("quote_at", 1, "QUOTE_STALE_OR_FUTURE"),
    ("quote_at", -3, "QUOTE_PRECEDES_SIGNAL_CLOSE"),
    ("bar_closed_at", 1, "BAR_TIME_INVALID"),
    ("bar_closed_at", -601, "BAR_STALE_OR_FUTURE"),
    ("data_received_at", 1, "DATA_AVAILABILITY_INVALID"),
    ("feature_available_at", 1, "DATA_AVAILABILITY_INVALID"),
    ("feature_cutoff_at", 1, "FEATURE_CUTOFF_MISMATCH"),
    ("feature_cutoff_at", -3, "FEATURE_CUTOFF_MISMATCH"),
])
def test_time_gates(engine, proven, name, offset, reason):
    s = replace(proven.snapshot, **{name: proven.evaluation_at+timedelta(seconds=offset)})
    out = engine.evaluate(attach_synthetic_proofs(replace(proven, snapshot=s)))
    assert out.status is Status.WAIT and reason in out.reasons


@pytest.mark.parametrize("offset", [-6, 1])
def test_portfolio_freshness(engine, proven, offset):
    a = replace(proven.portfolio, observed_at=proven.evaluation_at+timedelta(seconds=offset))
    out = engine.evaluate(replace(proven, portfolio=a))
    assert "PORTFOLIO_STALE_OR_FUTURE" in out.reasons


def test_missing_required_source_blocks(engine, proven):
    req = attach_synthetic_proofs(replace(proven, evidence=proven.evidence[1:]))
    out = engine.evaluate(req)
    assert out.status is Status.WAIT
    assert "REQUIRED_SOURCE_MISSING_trend" in out.reasons
    assert out.long_evidence < engine.evaluate(proven).long_evidence


def test_missing_optional_weak_source_cannot_boost_score(engine, request_base):
    p = replace(request_base.policy, sources=tuple(replace(s, required=False) for s in request_base.policy.sources))
    ev = (replace(request_base.evidence[0], long=D("0.01")),) + request_base.evidence[1:]
    full = replace(request_base, policy=p, evidence=ev)
    missing = replace(full, evidence=ev[1:])
    assert engine.evaluate(missing).long_evidence <= engine.evaluate(full).long_evidence


def test_correlated_group_weight_is_fixed(engine, request_base):
    # Splitting a trend source into equal copies cannot increase the trend group's authority.
    p = request_base.policy
    sources = tuple(s for s in p.sources if s.name != "trend") + tuple(SourceSpec(f"trend{i}", "trend", D("1")) for i in range(20))
    evidence = tuple(e for e in request_base.evidence if e.source != "trend") + tuple(DirectionalEvidence(f"trend{i}", D("0.85"), D("0.10")) for i in range(20))
    req = replace(request_base, policy=replace(p, sources=sources), evidence=evidence)
    assert engine.evaluate(req).long_evidence == engine.evaluate(request_base).long_evidence


def test_no_setup_or_weak_or_conflicting_direction(engine, request_base):
    assert engine.evaluate(replace(request_base, plans=())).status is Status.WAIT
    for long, short, reason in ((".2", ".1", "INSUFFICIENT_DIRECTIONAL_EVIDENCE"),
                               (".8", ".8", "DIRECTION_CONFLICT")):
        ev = tuple(replace(e, long=D(long), short=D(short)) for e in request_base.evidence)
        result = engine.evaluate(replace(request_base, evidence=ev))
        assert result.status is Status.WATCH and reason in result.reasons


@pytest.mark.parametrize("scores,expected", [((".85", ".1"), Side.LONG), ((".1", ".85"), Side.SHORT)])
def test_long_short_symmetry(engine, proven, scores, expected):
    ev = tuple(replace(e, long=D(scores[0]), short=D(scores[1])) for e in proven.evidence)
    out = engine.evaluate(attach_synthetic_proofs(replace(proven, evidence=ev)))
    assert out.selected_side is expected
    chosen = out.long if expected is Side.LONG else out.short
    assert chosen.quantity == 178 and chosen.permission == D("0.735091890625")


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_single_plan_does_not_ignore_opposing_evidence(engine, request_base, side):
    plan = next(p for p in request_base.plans if p.side is side)
    ev = tuple(replace(e, long=D(".8"), short=D(".8")) for e in request_base.evidence)
    out = engine.evaluate(replace(request_base, plans=(plan,), evidence=ev))
    assert out.status is Status.WATCH and "DIRECTION_CONFLICT" in out.reasons


def test_short_eligibility_is_explicit(engine, proven):
    ev = tuple(replace(e, long=D(".1"), short=D(".85")) for e in proven.evidence)
    req = replace(proven, evidence=ev, snapshot=replace(proven.snapshot, short_eligible=False))
    out = engine.evaluate(attach_synthetic_proofs(req))
    assert out.status is Status.WAIT and "SHORT_INELIGIBLE" in out.reasons


def test_no_opposite_fallback_when_risk_blocks_preferred(engine, proven):
    ev = tuple(replace(e, long=D(".85"), short=D(".70")) for e in proven.evidence)
    plans = (replace(proven.plans[0], quality=D(".8")), replace(proven.plans[1], quality=D("1")))
    no_risk = replace(proven.risks, **{k: D("0") for k in ("event", "trap", "data_uncertainty", "liquidity", "execution")})
    req = attach_synthetic_proofs(replace(proven, evidence=ev, plans=plans, risks=no_risk))
    assert engine.evaluate(req).selected_side is Side.LONG
    out = engine.evaluate(replace(req, risks=replace(no_risk, event=D(".4"))))
    assert out.short.eligible  # An attractive opposite setup still cannot become a fallback.
    assert out.preferred_side is Side.LONG
    assert out.selected_side is None and out.status is Status.WAIT


@pytest.mark.parametrize("offset", [-11, 1])
def test_stale_future_costs(engine, proven, offset):
    plan = proven.plans[0]
    costs = replace(plan.costs, estimated_at=proven.evaluation_at+timedelta(seconds=offset))
    req = replace(proven, plans=(replace(plan, costs=costs), proven.plans[1]))
    out = engine.evaluate(attach_synthetic_proofs(req))
    assert "COST_ESTIMATE_STALE_OR_FUTURE" in out.reasons


def test_ticks_drift_and_spread_floor(engine, proven):
    plan = proven.plans[0]
    for edited, reason in (
        (replace(plan, entry=D("100.01")), "PRICE_NOT_TICK_ALIGNED"),
        (replace(plan, entry=D("101")), "ENTRY_PRICE_DRIFT"),
        (replace(plan, costs=replace(plan.costs, round_trip_per_unit=D(".01"))), "COST_BELOW_OBSERVED_SPREAD"),
    ):
        out = engine.evaluate(attach_synthetic_proofs(replace(proven, plans=(edited, proven.plans[1]))))
        assert out.status is Status.WAIT and reason in out.reasons


def test_cost_shock_can_veto_positive_base_economics(engine, proven):
    plan = replace(proven.plans[0], costs=replace(proven.plans[0].costs, round_trip_per_unit=D("1")))
    req = attach_synthetic_proofs(replace(proven, plans=(plan, proven.plans[1])))
    out = engine.evaluate(req)
    assert out.long.scenarios[0].net_reward_risk > proven.policy.minimum_net_reward_risk
    assert out.status is Status.WAIT
    assert "SCENARIO_COST_SHOCK_REWARD_RISK_LOW" in out.reasons


def test_negative_net_win_is_blocked(engine, proven):
    plan = replace(proven.plans[0], costs=replace(proven.plans[0].costs, round_trip_per_unit=D("7")))
    out = engine.evaluate(attach_synthetic_proofs(replace(proven, plans=(plan, proven.plans[1]))))
    assert out.status is Status.WAIT
    assert "SCENARIO_BASE_NET_WIN_NONPOSITIVE" in out.reasons


def test_negative_modeled_expectancy_is_blocked(engine, proven):
    out = engine.evaluate(attach_synthetic_proofs(proven, probability=D(".1")))
    assert out.status is Status.WAIT
    assert "SCENARIO_BASE_EXPECTANCY_LOW" in out.reasons


def test_size_uses_worst_stress_and_all_budgets(engine, proven):
    out = engine.evaluate(proven)
    q = out.long.quantity
    worst_loss = max(x.modeled_loss_per_unit for x in out.long.scenarios)
    assert q*worst_loss <= proven.portfolio.equity*proven.policy.risk_per_trade_fraction
    assert (q+1)*worst_loss > proven.portfolio.equity*proven.policy.risk_per_trade_fraction
    for field, value in (("daily_loss", D("1990")), ("weekly_loss", D("4990")), ("open_modeled_risk", D("1990"))):
        small = engine.evaluate(replace(proven, portfolio=replace(proven.portfolio, **{field: value})))
        assert small.long.quantity*worst_loss <= D("10")
        assert small.long.quantity < q
    cash = engine.evaluate(replace(proven, portfolio=replace(proven.portfolio, available_notional=D("1000"))))
    assert cash.long.quantity == 9  # Costs are reserved, not just share notional.


def test_whole_lots_capacity_and_zero_budget(engine, proven):
    req = replace(proven, snapshot=replace(proven.snapshot, lot_size=25, capacity_units=99))
    out = engine.evaluate(attach_synthetic_proofs(req))
    assert out.long.quantity == 75
    req = replace(proven, snapshot=replace(proven.snapshot, capacity_units=0))
    out = engine.evaluate(attach_synthetic_proofs(req))
    assert out.status is Status.WAIT and "NO_SIZE_WITHIN_BUDGET" in out.reasons
    out = engine.evaluate(replace(proven, portfolio=replace(proven.portfolio, available_notional=D("0"))))
    assert out.status is Status.WAIT


def test_determinism_independent_of_decimal_context(engine, proven):
    expected = engine.evaluate(proven)
    with localcontext() as ctx:
        ctx.prec = 6
        ctx.traps[Inexact] = True
        assert engine.evaluate(proven) == expected
    assert engine.evaluate(proven) == expected


def test_swing_policy_requires_horizon_specific_binding(engine, proven):
    req = replace(proven, snapshot=replace(proven.snapshot, horizon=Horizon.SWING),
                  policy=replace(proven.policy, horizon=Horizon.SWING, revision="SWING-DEMO"))
    out = engine.evaluate(req)
    assert "PROOF_BINDING_MISMATCH" in out.reasons
    assert engine.evaluate(attach_synthetic_proofs(req)).horizon is Horizon.SWING


def test_candidate_expires_at_earliest_dependency(engine, proven):
    out = engine.evaluate(proven)
    assert out.valid_until == proven.snapshot.quote_at+timedelta(seconds=proven.policy.max_quote_age_seconds)
    assert out.valid_until > proven.evaluation_at
    assert engine.evaluate(replace(proven, proofs=())).valid_until is None


def test_zero_lifetime_cannot_be_a_candidate(engine, proven):
    p = replace(proven.policy, max_portfolio_age_seconds=1)
    out = engine.evaluate(attach_synthetic_proofs(replace(proven, policy=p)))
    assert out.status is Status.WAIT and out.valid_until is None
    assert "CANDIDATE_LIFETIME_EXHAUSTED" in out.reasons


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_single_setup_success_and_weak_evidence(engine, request_base, side):
    plan = next(p for p in request_base.plans if p.side is side)
    ev = tuple(replace(e, long=D(".85") if side is Side.LONG else D(".1"),
                       short=D(".85") if side is Side.SHORT else D(".1")) for e in request_base.evidence)
    req = attach_synthetic_proofs(replace(request_base, plans=(plan,), evidence=ev))
    assert engine.evaluate(req).selected_side is side
    weak = tuple(replace(e, long=D(".1"), short=D(".1")) for e in ev)
    out = engine.evaluate(replace(req, evidence=weak))
    assert "INSUFFICIENT_DIRECTIONAL_EVIDENCE" in out.reasons


def test_raw_engine_rejects_wrong_type(engine):
    with pytest.raises(ValueError): engine.evaluate({})


@pytest.mark.parametrize("limits", [(200, 1000), (1, 100)])
def test_costs_must_cover_proposed_quantity(engine, proven, limits):
    plan = proven.plans[0]
    costs = replace(plan.costs, valid_for_min_units=limits[0], valid_for_max_units=limits[1])
    req = attach_synthetic_proofs(replace(proven, plans=(replace(plan, costs=costs), proven.plans[1])))
    out = engine.evaluate(req)
    assert out.status is Status.WAIT and "COST_SIZE_SCOPE_MISMATCH" in out.reasons
