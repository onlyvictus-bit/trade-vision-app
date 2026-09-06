import pytest
from app.orb.adaptive.execution import *
from .helpers import *


def opened(side=Side.LONG,entry=100,stop=95,rr=1):
    pl=plan(side=side,entry=entry,stop=stop,rr=rr)
    return start_position(pl,limits(),clock_ns(DAY,581),10,'tester',research=True)

def execution_bar(pos,row):
    i=(pos.expected_open_ns-clock_ns(DAY,555))//(5*MINUTE)
    return bar(i,row)


def test_actual_gap_fill_pnl_not_original_trigger():
    pos=opened()
    b=execution_bar(pos,(105,110,104,110))
    pos=advance_position(pos,b,as_of_ns=b.available_ns)
    assert pos.fill_price==105 and pos.initial_risk_per_unit==10
    # Fixed 1R target is 115, not old trigger's 105; force scheduled exit at110.
    from app.orb.adaptive.execution import _close
    closed=_close(pos,110,b.close_ns,'TIME_EXIT')
    assert closed.gross_pnl==50 and closed.net_r==.5

def test_gap_beyond_stop_loses_more_than_one_r():
    pos=opened()
    b=execution_bar(pos,(100,102,99,101))
    pos=advance_position(pos,b,as_of_ns=b.available_ns)
    later=execution_bar(pos,(90,91,88,90))
    pos=advance_position(pos,later,as_of_ns=later.available_ns)
    assert pos.label=='STOP_GAP' and pos.exit_price==90 and pos.net_r==-2

def test_wrong_side_stop_fill_is_rejected_not_profitable_stop():
    pos=opened()
    b=execution_bar(pos,(94,96,93,95))
    result=advance_position(pos,b,as_of_ns=b.available_ns)
    assert result.status=='NO_FILL' and result.fill_price is None
    assert result.label=='STOP_ON_WRONG_SIDE_OF_ACTUAL_FILL'

def test_fixed_stop_retained_for_fade_and_retest():
    state,c=state_to_fade()
    pl=state.active_proposal
    assert pl.stop==102.96
    pos=start_position(pl,c.limits,pl.created_ns+NS,10,'tester',research=True)
    b=execution_bar(pos,(101.95,102,101.4,101.5))
    result=advance_position(pos,b,as_of_ns=b.available_ns)
    assert result.plan.stop==pl.stop

def test_same_bar_stop_target_uses_conservative_stop_first():
    pos=opened()
    b=execution_bar(pos,(100,107,94,101))
    result=advance_position(pos,b,as_of_ns=b.available_ns)
    assert result.label=='STOP_FIRST' and result.same_bar_ambiguous and result.net_r==-1
    assert result.exit_time_precision=='OBSERVATION_ENDPOINT'

def test_after_exit_candles_cannot_rewrite_pnl_or_excursions():
    pos=opened(); b=execution_bar(pos,(100,107,94,101))
    result=advance_position(pos,b,as_of_ns=b.available_ns)
    later=bar(10,(101,1000,1,100))
    assert advance_position(result,later,as_of_ns=later.available_ns)==result
    assert result.mfe_lower<=result.mfe_upper and result.mae_lower<=result.mae_upper

def test_fill_cannot_use_bar_start_before_approval():
    pos=opened()
    old=bar(5,(100,200,1,100))
    assert advance_position(pos,old,as_of_ns=old.available_ns)==pos

def test_next_open_envelope_violation_is_no_fill_no_price_shopping():
    pos=opened()
    b=execution_bar(pos,(110,111,99,100))
    result=advance_position(pos,b,as_of_ns=b.available_ns)
    assert result.label=='ACTUAL_FILL_OUTSIDE_APPROVED_ENVELOPE'
    later=execution_bar(result,(100,101,99,100))
    assert advance_position(result,later,as_of_ns=later.available_ns)==result

def test_missing_execution_interval_is_unknown_not_zero():
    pos=opened()
    b=bar(10,(100,101,99,100))
    result=advance_position(pos,b,as_of_ns=b.available_ns)
    assert result.status=='UNKNOWN' and result.net_pnl is None and result.net_r is None

def test_costs_once_and_actual_direction_symmetry():
    for side,stop,row in [(Side.LONG,95,(100,101,99,100)),(Side.SHORT,105,(100,101,99,100))]:
        pl=plan(side=side,stop=stop,cost_model=Costs(spread_bps=1,slippage_bps=1,impact_bps=.5,fee_bps_per_side=1))
        pos=start_position(pl,limits(),clock_ns(DAY,581),10,'tester',research=True)
        b=execution_bar(pos,row); pos=advance_position(pos,b,as_of_ns=b.available_ns)
        from app.orb.adaptive.execution import _close
        result=_close(pos,100,b.close_ns,'TIME_EXIT')
        expected=round((result.exit_price-result.fill_price)*side.sign*10,8)
        assert abs(result.gross_pnl-expected)<1e-8
        assert result.net_pnl==pytest.approx(expected-result.fees)
        assert result.net_pnl<0

def test_no_approval_after_deadline():
    pl=plan()
    with pytest.raises(ValueError): start_position(pl,limits(),clock_ns(DAY,616),1,'tester')

@pytest.mark.parametrize('quantity',[0,-1,11,True,1.5])
def test_quantity_bound(quantity):
    with pytest.raises(ValueError): start_position(plan(),limits(),clock_ns(DAY,581),quantity,'tester')

def test_scheduled_flat_close_is_observed_not_interpolated():
    pos=opened()
    b=execution_bar(pos,(100,101,99,100));pos=advance_position(pos,b,as_of_ns=b.available_ns)
    for index in range(7,71):
        b=bar(index,(100,101,99,100));pos=advance_position(pos,b,as_of_ns=b.available_ns)
    assert pos.status=='CLOSED' and pos.label=='TIME_EXIT'
    assert pos.exit_ns==clock_ns(DAY,910)
