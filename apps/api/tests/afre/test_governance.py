from datetime import date,timedelta
import pytest
from app.orb.adaptive.governance import *
from app.orb.adaptive.research import *
from app.orb.adaptive.monitor import *
from app.orb.adaptive.store import Store,Conflict
from .helpers import *


def _report():
    # Controlled successful math fixture. These are NOT real-market data and
    # this test artifact is never exported to the deployment package.
    data=tuple(evolve(synthetic_day((date(2026,1,1)+timedelta(days=i)).isoformat()),source_origin='REAL_ATTESTED') for i in range(15))
    return prove_policies(data,(controller(),),holdout_start=data[10].session_date,code_hash=code_fingerprint(),
                          thresholds=ProofThresholds(minimum_development_dates=10,minimum_holdout_dates=5,minimum_holdout_fills=3))

def test_positive_proof_report_hash_and_signed_operator_contract():
    report=_report()
    assert report.promotion_eligible
    validate_report(report)
    stamp=clock_ns(DAY,555)
    review=sign_review(report,b'a'*48,'TEST_ONLY',stamp,stamp+1000*NS,'I_REVIEWED_REAL_DATA_POLICY_AND_HOLDOUT')
    assert verify_review(review,b'a'*48,policy(),limits(),('TEST',),stamp+NS,DAY)==report.proof_hash
    with pytest.raises(ValueError):verify_review(review,b'b'*48,policy(),limits(),('TEST',),stamp+NS,DAY)
    with pytest.raises(ValueError):verify_review(review,b'a'*48,policy(),limits(),('OTHER',),stamp+NS,DAY)
    with pytest.raises(ValueError):verify_review(review,b'a'*48,policy(),limits(),('TEST',),stamp+1001*NS,DAY)
    with pytest.raises(ValueError):verify_review(review,b'a'*48,policy(max_extension_or=2),limits(),('TEST',),stamp+NS,DAY)
    with pytest.raises(ValueError):verify_review(evolve(review,reviewer='CHANGED'),b'a'*48,policy(),limits(),('TEST',),stamp+NS,DAY)

def test_proof_hash_does_not_authorize_synthetic_or_edited_performance():
    report=_report()
    with pytest.raises(ValueError):validate_report(evolve(report,source_origin='SYNTHETIC'))
    with pytest.raises(ValueError):validate_report(evolve(report,holdout_metrics=report.holdout_metrics|{'net_budget_units':999999}))

def test_holdout_dates_cannot_be_reused_under_a_new_study_id(tmp_path):
    store=Store(tmp_path/'study.db')
    store.register_trial('first',{'holdout_dates':['2026-01-01','2026-01-02']})
    with pytest.raises(Conflict):store.register_trial('second',{'holdout_dates':['2026-01-02','2026-01-03']})

def test_monitor_cannot_learn_from_unmatured_or_synthetic_outcomes():
    rows=[]
    for i in range(30):
        day=(date(2025,1,1)+timedelta(days=i)).isoformat()
        rows.append(OutcomeEvidence(outcome_id=str(i),account_id='fixture',session_date=day,policy_hash=policy().policy_hash,
                                    available_ns=clock_ns(day,910),net_budget_units=-.1,origin='SYNTHETIC'))
    m=monitor(tuple(rows),policy_hash=policy().policy_hash,as_of_ns=clock_ns(DAY,555))
    assert m.unique_dates==0 and m.status=='INSUFFICIENT_DATA'
    real=tuple(evolve(x,origin='ATTESTED_REAL_PAPER') for x in rows)
    m=monitor(real,policy_hash=policy().policy_hash,as_of_ns=clock_ns(DAY,555))
    assert m.status=='REVIEW_DUE' and not m.model_changed and not m.automatic_promotion
    unknown=real[:-1]+(evolve(real[-1],net_budget_units=None),)
    assert monitor(unknown,policy_hash=policy().policy_hash,as_of_ns=clock_ns(DAY,555)).status=='DATA_UNRESOLVED'
    with pytest.raises(ValueError):monitor(real+(evolve(real[0],outcome_id='different'),),policy_hash=policy().policy_hash,as_of_ns=clock_ns(DAY,555))
