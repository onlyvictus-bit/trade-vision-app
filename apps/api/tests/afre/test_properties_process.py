import concurrent.futures
import multiprocessing
import random
import pytest
from app.orb.adaptive.execution import start_position,advance_position
from app.orb.adaptive.service import Service
from app.orb.adaptive.store import Store
from .helpers import *
from .test_runtime_store import make_service


def _process_approval(args):
    path,proposal_id,proposal_hash,stamp,i=args
    service=Service(Store(path),controller(),safety=lambda:SAFE,clock=lambda:stamp,paper_enabled=True)
    service._proof=lambda state,now:(True,'TEST_ONLY_PROOF')
    try:
        service.approve(DAY,f'process-{i}',proposal_id,proposal_hash,1,APPROVAL_PHRASE,'TEST_ONLY')
        return True
    except ValueError:return False


def test_separate_processes_cannot_accept_two_approvals(tmp_path):
    service,clock=make_service(tmp_path,paper=True)
    pl=service.store.load('fixture',DAY).active_proposal
    args=[(str(tmp_path/'events.db'),pl.proposal_id,digest(pl),clock[0]+NS,i) for i in range(8)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as executor:
        result=list(executor.map(_process_approval,args))
    assert sum(result)==1 and service.store.audit('fixture',DAY)['events']==6


def test_300_mirrored_random_valid_paths_preserve_side_economics():
    rng=random.Random(507)
    zero=Costs(spread_bps=0,slippage_bps=0,impact_bps=0,fee_bps_per_side=0)
    for case in range(300):
        long_plan=plan(cost_model=zero,minimum_entry=99,maximum_entry=101)
        short_plan=plan(side=Side.SHORT,stop=105,cost_model=zero,minimum_entry=99,maximum_entry=101)
        long=start_position(long_plan,limits(),clock_ns(DAY,581),10,'property-test',research=True)
        short=start_position(short_plan,limits(),clock_ns(DAY,581),10,'property-test',research=True)
        price=100.
        for j in range(6,16):
            opening=price if j>6 else 100.
            close=round(opening+rng.uniform(-4,4),2)
            high=round(max(opening,close)+rng.uniform(0,2),2)
            low=round(min(opening,close)-rng.uniform(0,2),2)
            b=bar(j,(opening,high,low,close))
            mirrored=bar(j,(200-opening,200-low,200-high,200-close))
            long=advance_position(long,b,as_of_ns=b.available_ns)
            short=advance_position(short,mirrored,as_of_ns=mirrored.available_ns)
            assert long.status==short.status and long.label==short.label
            if long.net_pnl is not None:
                assert long.net_pnl==pytest.approx(short.net_pnl,abs=1e-7)
                assert long.net_r==pytest.approx(short.net_r,abs=1e-7)
            price=close


def test_gap_up_fade_and_gap_down_fade_mirror_before_permission():
    zero=Costs(spread_bps=0,slippage_bps=0,impact_bps=0,fee_bps_per_side=0)
    c=controller(policy(costs=zero))
    up=c.evaluate(snapshot())
    rows=[(200-o,200-lo,200-hi,200-cl) for o,hi,lo,cl in ROWS]
    down=c.evaluate(snapshot(rows=rows))
    assert up.selected_plan.template==down.selected_plan.template==Template.GAP_FADE
    assert up.selected_plan.side==Side.SHORT and down.selected_plan.side==Side.LONG
    assert up.selected_plan.stop+down.selected_plan.stop==pytest.approx(200)


def test_higher_friction_cannot_create_new_trigger_or_inverse_side():
    for friction in (0,1,2,4,8,16,32,64):
        costs=Costs(spread_bps=friction,slippage_bps=friction,impact_bps=friction,fee_bps_per_side=friction)
        decision=controller(policy(costs=costs)).evaluate(snapshot())
        if decision.selected_plan:
            assert decision.selected_plan.template==Template.GAP_FADE and decision.selected_plan.side==Side.SHORT
        assert decision.observed_failure_episodes==1


def test_account_limit_and_policy_changes_cannot_mutate_running_session():
    state,c=state_to_fade()
    b=bar(4,(101.98,102,101.9,101.95))
    changed=Controller(policy(),limits('different-account'))
    with pytest.raises(ValueError):advance_session(state,EventBatch(event_id='changed',available_ns=b.available_ns,feature_bars=(b,)),changed,SAFE)
