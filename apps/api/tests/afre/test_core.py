import math
import pytest
from pydantic import ValidationError
from app.orb.adaptive.contracts import *
from app.orb.adaptive.features import extract, wilder_atr, validate_prefix
from app.orb.adaptive.registry import source_registry
from .helpers import *

@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf'),-float('inf')])
@pytest.mark.parametrize('field',['open','high','low','close'])
def test_invalid_prices_rejected(field,value):
    with pytest.raises(ValidationError): bar(0,**{field:value})

@pytest.mark.parametrize('field',['close','atr14','tick_size'])
@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf')])
def test_invalid_prior_rejected(field,value):
    with pytest.raises(ValidationError): prior(**{field:value})

def test_safety_literals_cannot_be_overridden():
    with pytest.raises(ValidationError): SafeOutput(trade_allowed=True)

def test_future_and_nonclosed_rejected():
    b=bar(0)
    with pytest.raises(ValidationError): evolve(b,available_ns=b.open_ns)
    with pytest.raises(ValidationError): snapshot(rows=ROWS[:1],as_of_ns=b.close_ns-1)

def test_prior_is_strictly_earlier_and_known_before_open():
    with pytest.raises(ValidationError): snapshot(prior=prior(session_date=DAY))
    with pytest.raises(ValidationError): snapshot(prior=prior(available_ns=clock_ns(DAY,556)))

@pytest.mark.parametrize('kwargs',[dict(feature_minutes=3,execution_minutes=3),dict(feature_minutes=3,execution_minutes=5),dict(range_minutes=4),dict(feature_minutes=5,execution_minutes=3)])
def test_bad_clock_contract(kwargs):
    with pytest.raises(ValidationError): Policy(**kwargs)

def test_native_three_minute_explicit_exit_policies():
    assert Policy(feature_minutes=3,execution_minutes=1).flat_minute==910
    assert Policy(feature_minutes=3,execution_minutes=3,flat_minute=909).flat_minute==909

def test_missing_opening_interval_blocks_whole_decision():
    s=snapshot()
    s=evolve(s,bars=s.bars[1:])
    d=controller().evaluate(s)
    assert d.public_ticket=='WAIT' and d.selected_plan is None
    assert 'MISSING_DUPLICATE_OR_REORDERED_FEATURE_INTERVAL' in d.reason_codes

def test_missing_bar_never_turns_into_fake_3m():
    s=snapshot(); p=Policy(feature_minutes=3,execution_minutes=1)
    assert 'NATIVE_FEATURE_RESOLUTION_MISMATCH' in validate_prefix(s,p)

@pytest.mark.parametrize('opening,expected',[(100.1,'FLAT'),(99.9,'FLAT'),(100.11,'GAP_UP'),(99.89,'GAP_DOWN')])
def test_gap_boundary(opening,expected):
    s=snapshot(rows=[(opening,opening+.05,opening-.05,opening)])
    assert extract(s,policy())['gap_class']==expected

def test_cpr_sorted_and_atr_uses_previous_close_true_range():
    f=extract(snapshot(),policy())
    assert f['cpr_lower']<=f['cpr_upper']
    assert wilder_atr(((101,99,100),(111,109,110),(112,108,111)),2)==7.5

def test_scenario_failure_to_fade_independent_trigger():
    c=controller()
    before=c.evaluate(snapshot(rows=ROWS[:2]))
    failed=c.evaluate(snapshot(rows=ROWS[:3]))
    faded=c.evaluate(snapshot())
    assert before.observed_failure_episodes==0
    assert failed.observed_failure_episodes==1
    assert failed.selected_plan is None
    assert faded.selected_plan.template==Template.GAP_FADE
    assert faded.selected_plan.side==Side.SHORT
    assert faded.public_ticket=='WATCH' # absence of proof is not fake READY
    assert len(faded.branches)==8 and len(faded.candidates)<=6
    assert all(f.probability is None for f in faded.forecasts)

def test_reclaim_cancels_unapproved_fade_hypothesis():
    rows=ROWS[:3]+[(102.42,103.,102.35,102.78),(102.78,103.05,102.7,102.90)]
    d=controller().evaluate(snapshot(rows=rows))
    assert d.selected_plan.template==Template.RECLAIM
    assert d.selected_plan.side==Side.LONG
    assert next(b for b in d.branches if b.branch_id=='UNFILLED_GAP_FADE').state=='REFUTED'

def test_inside_buffer_is_not_return_inside_range_failure():
    rows=ROWS[:2]+[(102.72,102.8,102.59,102.605)]
    d=controller().evaluate(snapshot(rows=rows))
    assert d.observed_failure_episodes==0

def test_retest_is_not_a_failed_breakout():
    rows=ROWS[:2]+[(102.72,102.9,102.59,102.8)]
    d=controller(policy(costs=Costs(spread_bps=0,slippage_bps=0,impact_bps=0,fee_bps_per_side=0))).evaluate(snapshot(rows=rows))
    assert d.features['retest_ready'] and d.observed_failure_episodes==0
    assert d.selected_plan.template==Template.RETEST_HOLD

def test_gap_touch_is_sticky_and_forbids_original_fade():
    rows=ROWS+[(101.98,102.0,99.9,101.8),(101.8,101.9,101.3,101.5)]
    d=controller().evaluate(snapshot(rows=rows))
    assert d.gap_ever_touched_pdc
    assert all(c.plan is None or not c.plan.requires_gap_unfilled for c in d.candidates)

def test_fixed_2r_fade_rejected_not_silently_changed_to_1r():
    p=Policy(range_minutes=5,reward_risk=2)
    d=controller(p).evaluate(snapshot())
    fade=next(c for c in d.candidates if c.template==Template.GAP_FADE)
    assert fade.status=='REJECTED' and 'FIXED_FADE_TARGET_DOES_NOT_FIT_BEFORE_PDC' in fade.reasons

def test_timer_cutoff_blocks_even_old_good_signal():
    s=evolve(snapshot(),as_of_ns=clock_ns(DAY,616))
    d=controller().evaluate(s)
    assert d.selected_plan is None and d.public_ticket=='WAIT'

def test_bad_data_not_an_inverse_trade():
    d=controller().evaluate(evolve(snapshot(),data_blockers=('UNVERIFIED_PRICE_BASIS',)))
    assert d.selected_plan is None and not d.forecasts
    assert d.gap_ever_touched_pdc is None
    assert d.scenario_status['B01']=='UNOBSERVABLE_INVALID_INPUT'

def test_all_source_and_controller_cases_present():
    d=controller().evaluate(snapshot())
    assert len(source_registry())==30 and len(d.scenario_status)==50
    assert d.scenario_status['F02']=='UNOBSERVABLE_EXTERNAL_INPUT'

def test_required_missing_context_is_not_neutral():
    d=controller(policy(required_capabilities=('VIX',))).evaluate(snapshot())
    assert d.selected_plan is None and 'REQUIRED_CAPABILITY_UNAVAILABLE:VIX' in d.reason_codes

def test_same_snapshot_is_byte_deterministic_and_no_bel_authority():
    a=controller().evaluate(snapshot()); b=controller().evaluate(snapshot())
    assert canonical(a)==canonical(b) and a.proof_hash is None

def test_adding_future_input_does_not_change_already_frozen_decision():
    s=snapshot(rows=ROWS[:2]); a=controller().evaluate(s)
    later=controller().evaluate(snapshot())
    assert canonical(a)==canonical(controller().evaluate(s))
    assert a.snapshot_hash!=later.snapshot_hash
