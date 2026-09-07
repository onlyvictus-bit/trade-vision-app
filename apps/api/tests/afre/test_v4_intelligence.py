from datetime import date

import pytest

from app.orb.adaptive.contracts import clock_ns
from app.orb.adaptive.derivatives import (
    DerivativesSnapshot,
    FuturesLeg,
    OIBuildup,
    OptionContract,
    OptionType,
    calculate,
    capabilities as derivative_capabilities,
)
from app.orb.adaptive.features import extract
from app.orb.adaptive.risk_context import RiskContextSnapshot, capabilities as risk_capabilities
from app.orb.adaptive.runtime import EventBatch, advance_session, new_session
from app.orb.adaptive.scenario_detection import detect
from app.orb.adaptive.service import _durable_event_payload
from app.orb.adaptive.variants import CATALOGUE, assess
from .helpers import DAY, SAFE, controller, policy, prior, snapshot


def _derivatives(*, dealer_sign=-1):
    near = date(2026, 9, 8)
    far = date(2026, 9, 15)
    options = (
        OptionContract(symbol="TEST", expiry=near, strike=100, option_type=OptionType.CALL,
                       open_interest=100, implied_volatility=.40, delta=.25, gamma=.02,
                       vanna=.10, charm=-.10, dealer_position_sign=dealer_sign),
        OptionContract(symbol="TEST", expiry=near, strike=100, option_type=OptionType.PUT,
                       open_interest=200, implied_volatility=.46, delta=-.25, gamma=.02,
                       vanna=-.10, charm=-.10, dealer_position_sign=dealer_sign),
        OptionContract(symbol="TEST", expiry=far, strike=100, option_type=OptionType.CALL,
                       open_interest=9999, implied_volatility=.30, delta=.25, gamma=.01),
        OptionContract(symbol="TEST", expiry=far, strike=100, option_type=OptionType.PUT,
                       open_interest=1, implied_volatility=.32, delta=-.25, gamma=.01),
    )
    futures = (
        FuturesLeg(symbol="TEST", expiry=near, price=101, open_interest=100,
                   previous_price=100, previous_open_interest=90),
        FuturesLeg(symbol="TEST", expiry=far, price=101.5, open_interest=900,
                   previous_price=101, previous_open_interest=800),
    )
    return DerivativesSnapshot(
        symbol="TEST", session_date=date.fromisoformat(DAY),
        available_ns=clock_ns(DAY, 600), expires_ns=clock_ns(DAY, 700),
        source_id="verified-derivatives-fixture", spot=100.2, prior_close=100, atr14=2,
        vix=22, previous_vix=20,
        iv_history=tuple(.20 + i * .01 for i in range(20)), previous_atm_iv=.60,
        options=options, futures=futures, gift_reference=103.5,
        index_open=103, index_prior_close=100, index_atr14=2,
        fii_index_futures_long=10, fii_index_futures_short=90,
        is_weekly_expiry=True,
    )


def _risk_context(**updates):
    base = dict(
        symbol="TEST", session_date=date.fromisoformat(DAY),
        available_ns=clock_ns(DAY, 600), expires_ns=clock_ns(DAY, 700),
        source_id="verified-risk-fixture",
    )
    base.update(updates)
    return RiskContextSnapshot(**base)


def test_large_gap_is_exactly_one_point_five_atr_without_hidden_percent_floor():
    p = policy()
    at_boundary = snapshot(rows=[(103.0, 103.2, 102.8, 103.0)])
    below = snapshot(rows=[(102.99, 103.1, 102.8, 103.0)])
    a = extract(at_boundary, p)
    b = extract(below, p)
    assert a["gap_atr"] == pytest.approx(1.5)
    assert a["gap_class"] == "LARGE_GAP_UP"
    assert a["large_gap_threshold_pct"] == pytest.approx(3.0)
    assert b["gap_atr"] < 1.5
    assert b["gap_class"] == "GAP_UP"


def test_derivatives_overlay_calculates_full_registered_task3_metrics_on_front_expiry():
    ctx = calculate(_derivatives())
    assert ctx.vix_change_pct == pytest.approx(10.0)
    assert ctx.iv_rank == pytest.approx(100.0)
    assert ctx.term_structure_inverted is True
    assert ctx.term_structure_points == pytest.approx(12.0)
    assert ctx.skew_25d_points == pytest.approx(6.0)
    # Far-expiry OI is intentionally excluded from front-expiry PCR.
    assert ctx.pcr_oi == pytest.approx(2.0)
    assert ctx.max_pain_strike == pytest.approx(100.0)
    assert ctx.near_max_pain is True
    assert ctx.oi_buildup == OIBuildup.LONG_BUILDUP
    assert ctx.rollover_pct == pytest.approx(90.0)
    assert ctx.positive_basis_rollover is True
    assert ctx.dealer_signed_gex is not None and ctx.dealer_signed_gex < 0
    assert ctx.aggregate_vanna is not None
    assert ctx.aggregate_charm is not None
    assert ctx.gift_gap_atr == pytest.approx(1.75)
    assert ctx.index_gap_pct == pytest.approx(3.0)
    assert ctx.fii_short_pct == pytest.approx(90.0)

    names = {c.name for c in derivative_capabilities(ctx)}
    expected = {
        "DERIVATIVES_CONTEXT", "VIX", "VIX_HIGH", "VIX_SPIKE", "IV_RANK_HIGH",
        "IV_TERM_INVERSION", "IV_CRUSH", "SKEW_25D", "PCR_EXTREME_HIGH",
        "OI_LONG_BUILDUP", "MAX_PAIN_NEAR", "DEALER_GEX", "NEGATIVE_DEALER_GAMMA",
        "EXPIRY_DAY", "ROLLOVER_STRONG_POSITIVE_BASIS", "FUTURES_BASIS_POSITIVE",
        "GIFT_GAP_EXTREME", "INDEX_GAP_EXTREME", "FII_SHORT_EXTREME",
    }
    assert expected <= names


def test_dealer_gex_never_infers_dealer_side_from_open_interest():
    ctx = calculate(_derivatives(dealer_sign=None))
    assert ctx.unsigned_gex is not None
    assert ctx.dealer_signed_gex is None
    assert "DEALER_SIGNED_GEX_UNOBSERVABLE_WITHOUT_DEALER_POSITION_SIGN" in ctx.warnings
    assert "DEALER_GEX" not in {c.name for c in derivative_capabilities(ctx)}


def test_all_30_failure_scenarios_become_observable_when_required_inputs_are_supplied():
    dctx = calculate(_derivatives())
    rctx = _risk_context(
        scheduled_result=True, rbi_mpc_window=True, budget_or_election_event=True,
        ex_dividend_today=True, corporate_action_adjustment_verified=False,
        unscheduled_news_shock_verified=True, circuit_locked=True,
        asm_gsm_t2t_restricted=True, illiquid_or_slippage_risk=True, fno_ban=True,
        feed_lag=True, bad_tick_detected=True, order_rejected=True,
        broker_squareoff_risk=True, point_in_time_violation=True,
        replay_live_mismatch=True, oi_wall_rejection=True, gamma_squeeze_verified=True,
        rollover_distortion=True, edge_decay=True, overfit_risk=True, small_sample=True,
    )
    caps = derivative_capabilities(dctx) + risk_capabilities(rctx)
    features = {
        "chop_risk": True, "gap_atr": 1.6, "gap_class": "LARGE_GAP_UP",
        "failure_count": 2, "two_sided_bar": True, "observed_expansion": 2.5,
        "range_locked": True, "or_width_atr": 1.2, "first_bar_range_atr": 2.2,
        "elapsed_minutes": 140,
    }
    states = detect(features, (), caps, clock_ns(DAY, 610))
    expected_ids = {
        f"{group}{i:02d}"
        for group, n in (("A", 5), ("B", 6), ("C", 4), ("D", 4), ("E", 4), ("F", 4), ("G", 3))
        for i in range(1, n + 1)
    }
    assert set(states) == expected_ids
    assert len(states) == 30
    assert not any(value.startswith("UNOBSERVABLE") for value in states.values())


def test_complete_18_variant_catalogue_is_evaluated_and_wired_into_decision_features():
    p = policy()
    s = snapshot()
    f = extract(s, p)
    rows = assess(s, f, p)
    assert len(rows) == 18
    assert {x.variant_id for x in rows} == {x[0] for x in CATALOGUE}

    decision = controller(p).evaluate(s)
    for i in range(1, 19):
        prefix = f"v{i:02d}"
        assert f"{prefix}_state" in decision.features
        assert f"{prefix}_side" in decision.features
        assert f"{prefix}_template" in decision.features
        assert f"{prefix}_reason" in decision.features


def test_raw_contexts_flow_through_event_batch_into_existing_capability_and_scenario_path():
    c = controller()
    state = new_session(DAY, (prior(),), c.policy, c.limits)
    event = EventBatch(
        event_id="context-only-1",
        available_ns=clock_ns(DAY, 600),
        derivatives={"TEST": _derivatives()},
        risk_contexts={"TEST": _risk_context(scheduled_result=True, index_aligned_long=True)},
    )
    state = advance_session(state, event, c, SAFE)
    names = {x.name for x in state.capabilities["TEST"]}
    assert {"DERIVATIVES_CONTEXT", "VIX", "VIX_SPIKE", "RISK_CONTEXT", "RESULT_DAY", "INDEX_ALIGNED_LONG"} <= names
    decision = state.decisions["TEST"]
    assert decision.scenario_status["A03"] == "OBSERVED_EXTERNAL_FLAG"
    assert decision.scenario_status["C01"] == "RISK_ARMED_EXTERNAL"
    # Delta-VIX shock is a blocking capability. The same existing fail-closed
    # controller path must therefore prevent a paper proposal.
    assert decision.selected_plan is None
    assert decision.public_ticket == "WAIT"
    assert any(code == "VERIFIED_REFERENCE_BLOCK:VIX_SPIKE" for code in decision.reason_codes)


def test_independent_context_refresh_does_not_erase_other_still_valid_family():
    c = controller()
    state = new_session(DAY, (prior(),), c.policy, c.limits)
    state = advance_session(
        state,
        EventBatch(
            event_id="risk-1", available_ns=clock_ns(DAY, 600),
            risk_contexts={"TEST": _risk_context(scheduled_result=True, index_aligned_long=True)},
        ),
        c, SAFE,
    )
    assert {"RISK_CONTEXT", "RESULT_DAY", "INDEX_ALIGNED_LONG"} <= {x.name for x in state.capabilities["TEST"]}

    state = advance_session(
        state,
        EventBatch(
            event_id="derivatives-1", available_ns=clock_ns(DAY, 601),
            derivatives={"TEST": _derivatives()},
        ),
        c, SAFE,
    )
    names = {x.name for x in state.capabilities["TEST"]}
    assert {"RISK_CONTEXT", "RESULT_DAY", "INDEX_ALIGNED_LONG", "DERIVATIVES_CONTEXT", "VIX"} <= names


def test_legacy_bar_only_event_payload_does_not_gain_empty_v4_context_fields():
    legacy = EventBatch(event_id="legacy-shape", available_ns=clock_ns(DAY, 600))
    payload = _durable_event_payload(legacy)
    assert "derivatives" not in payload
    assert "risk_contexts" not in payload

    enriched = EventBatch(
        event_id="v4-shape", available_ns=clock_ns(DAY, 600),
        risk_contexts={"TEST": _risk_context()},
    )
    assert "risk_contexts" in _durable_event_payload(enriched)


def test_existing_safety_contract_remains_research_only():
    decision = controller().evaluate(snapshot())
    assert decision.research_only is True
    assert decision.trade_allowed is False
    assert decision.live_trading_blocked is True
    assert decision.order_routing_enabled is False
