from datetime import date, timedelta
import pytest
from app.orb.adaptive.research import *
from app.orb.adaptive.forecasting import *
from app.orb.adaptive.datasets import structural_dataset,action_dataset
from app.orb.adaptive.governance import code_fingerprint,sign_review,verify_review,validate_report
from app.orb.adaptive.value import *
from .helpers import *


def days(n=15):
    return tuple(synthetic_day((date(2026,1,1)+timedelta(days=i)).isoformat()) for i in range(n))

def test_exact_full_replay_consumes_only_one_attempt():
    result=replay_day(synthetic_day(),controller())
    assert result.status=='COMPLETE' and result.entry_filled
    assert result.end_state.position.origin=='RESEARCH_REPLAY'
    assert result.end_state.position.plan.template==Template.GAP_FADE
    assert result.end_state.position.status=='CLOSED'

def test_replay_unknowns_are_not_zero_returns():
    r=replay_day(synthetic_day(variant='missing'),controller())
    assert r.net_budget_units is None and r.status=='UNKNOWN'

def test_holdout_mutations_do_not_change_training_selection():
    inputs=days()
    controllers=(controller(),controller(Policy(range_minutes=5,reward_risk=2)))
    t=ProofThresholds(minimum_development_dates=10,minimum_holdout_dates=5,minimum_holdout_fills=3)
    a=prove_policies(inputs,controllers,holdout_start=inputs[10].session_date,code_hash='test-only',thresholds=t)
    changed=inputs[:10]+tuple(synthetic_day(d.session_date,variant='loss') for d in inputs[10:])
    b=prove_policies(changed,controllers,holdout_start=inputs[10].session_date,code_hash='test-only',thresholds=t)
    assert a.selected_policy_hash==b.selected_policy_hash
    assert a.development_scores==b.development_scores and a.walk_forward==b.walk_forward
    assert a.holdout_metrics!=b.holdout_metrics
    for fold in a.walk_forward:
        assert max(fold['train_dates'])<min(fold['test_dates'])
        assert not set(fold['test_dates'])&set(a.holdout_dates)
    assert not a.promotion_eligible and 'SYNTHETIC_DATA_CANNOT_AUTHORIZE_PAPER_POLICY' in a.blockers
    with pytest.raises(ValueError): sign_review(a,b'x'*32,'tester',clock_ns(DAY,600),clock_ns(DAY,930),'I_REVIEWED_REAL_DATA_POLICY_AND_HOLDOUT')

def test_structural_label_kept_separate_from_trade_profit():
    s=snapshot(rows=ROWS[:2]); d=controller().evaluate(s)
    f=next(f for f in d.forecasts if f.event=='RETURN_INSIDE_OR')
    lab=label_structural(f,s,snapshot().bars[2:],d.features,rules_hash=policy().rules_hash,source_origin='SYNTHETIC')
    assert lab.outcome==1 and lab.event=='RETURN_INSIDE_OR'
    assert lab.event_observed_ns>lab.issued_ns
    unknown=label_structural(f,s,(),d.features,rules_hash=policy().rules_hash,source_origin='SYNTHETIC')
    assert unknown.status=='CENSORED' and unknown.outcome is None

def test_failure_is_not_reissued_as_a_prediction_after_detection():
    d=controller().evaluate(snapshot(rows=ROWS[:3]))
    assert 'RETURN_INSIDE_OR' not in [f.event for f in d.forecasts]

def test_future_horizon_dataset_builder_produces_matured_labels():
    records=structural_dataset((synthetic_day(),),controller())
    assert records and all(x.matured_ns>x.issued_ns for x in records)
    assert {x.event for x in records}<={'RETURN_INSIDE_OR','PDC_TOUCH'}

def training_labels(start,n,origin='SYNTHETIC'):
    out=[]
    for i in range(start,start+n):
        day=(date(2025,1,1)+timedelta(days=i)).isoformat()
        issued=clock_ns(day,565)
        out.append(Label(forecast_id=f'f{i}',episode_id=f'ep{i}',session_date=day,symbol='TEST',event='PDC_TOUCH',
                         horizon_minutes=10,issued_ns=issued,matured_ns=issued+10*MINUTE,
                         event_observed_ns=issued+5*MINUTE if i%2 else None,status='KNOWN',outcome=i%2,
                         context_key='LONG:NEAR:INITIAL:CLOCK_0',rules_hash=policy().rules_hash,source_origin=origin))
    return tuple(out)

def test_calibration_chronology_rejects_overlap_and_future_labels():
    a,b,c=training_labels(0,20),training_labels(20,20),training_labels(40,20)
    with pytest.raises(ValueError): fit_frequency_model(b,a,c)
    a=(evolve(a[0],matured_ns=c[0].issued_ns),)+a[1:]
    with pytest.raises(ValueError): fit_frequency_model(a,b,c)

def test_no_synthetic_probability_authority_even_when_scores_good():
    a,b,c=training_labels(0,20),training_labels(20,20),training_labels(40,20)
    model=fit_frequency_model(a,b,c)
    assert model.status=='UNSUPPORTED'
    predictor=FrequencyForecaster(model,policy().rules_hash)
    s=snapshot(rows=ROWS[:1]); f=next(f for f in controller().evaluate(s).forecasts if f.event=='PDC_TOUCH')
    result=predictor.estimate(f,{'gap_direction':'LONG','extension_or':0,'failure_count':0,'elapsed_minutes':5})
    assert result.probability is None

def test_supported_model_scope_and_artifact_hash_are_enforced():
    # A mathematically controlled REAL_ATTESTED tag fixture tests the model
    # contract only. It is NOT independent actual market/calibration evidence.
    model=fit_frequency_model(training_labels(0,20,'REAL_ATTESTED'),training_labels(20,20,'REAL_ATTESTED'),training_labels(40,20,'REAL_ATTESTED'))
    assert model.status=='SUPPORTED_BY_DECLARED_TESTS'
    pred=FrequencyForecaster(model,policy().rules_hash)
    f=next(f for f in controller().evaluate(snapshot(rows=ROWS[:1])).forecasts if f.event=='PDC_TOUCH')
    x={'gap_direction':'LONG','extension_or':0,'failure_count':0,'elapsed_minutes':5}
    assert pred.estimate(f,x).probability==.5
    assert pred.estimate(evolve(f,symbol='UNSEEN'),x).probability is None
    assert pred.estimate(f,x|{'extension_or':5}).probability is None
    with pytest.raises(ValueError): FrequencyForecaster(evolve(model,baseline_probability=.9),policy().rules_hash)

def test_duplicate_episodes_do_not_inflate_forecast_metrics():
    s=snapshot(rows=ROWS[:2]); d=controller().evaluate(s)
    f=next(f for f in d.forecasts if f.event=='RETURN_INSIDE_OR')
    f=evolve(f,forecast_status='ESTIMATED',probability=.5,model_hash='test-only')
    l=label_structural(f,s,snapshot().bars[2:],d.features,rules_hash=policy().rules_hash,source_origin='SYNTHETIC')
    scored=score_forecasts((f,f),(l,),known_at_ns=l.matured_ns)
    assert scored['count']==1 and scored['skipped']['duplicate_episode']==1
    assert score_forecasts((f,),(l,),known_at_ns=l.matured_ns-1)['count']==0
    with pytest.raises(ValueError): score_forecasts((f,),(evolve(l,event_observed_ns=f.issued_ns),),known_at_ns=l.matured_ns)

def test_shadow_wait_policies_share_initial_information_and_do_not_create_market_dates():
    rows=action_dataset((synthetic_day(),),controller(),anchor_minute=565)
    assert len(rows)==len(policy().templates)
    assert len({x.snapshot_hash for x in rows})==1 and len({x.session_date for x in rows})==1
    assert all(x.rules_hash==policy().rules_hash for x in rows)

def test_action_model_rejects_duplicate_date_samples_and_synthetic_promotion():
    base=action_dataset((synthetic_day(),),controller(),anchor_minute=565)[0]
    def action_rows(start):
        result=[]
        for i in range(start,start+4):
            day=(date(2025,1,1)+timedelta(days=i)).isoformat()
            result.append(evolve(base,row_id=f'action{i}',session_date=day,issued_ns=clock_ns(day,565),label_available_ns=clock_ns(day,910),net_budget_units=.1))
        return tuple(result)
    a,b=action_rows(0),action_rows(4)
    with pytest.raises(ValueError): fit_value_model(a+a[:1],b,minimum_dates=2)
    model=fit_value_model(a,b,minimum_dates=2)
    assert model.status=='UNSUPPORTED'
    EmpiricalActionValue(model,policy().rules_hash,digest(limits()))
    with pytest.raises(ValueError): EmpiricalActionValue(model,policy().rules_hash,'different-budget')
