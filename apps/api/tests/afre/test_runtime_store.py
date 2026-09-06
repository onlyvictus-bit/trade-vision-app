import concurrent.futures
import json
import sqlite3
import pytest
from app.orb.adaptive.service import Service
from app.orb.adaptive.store import Store, Conflict, StoreError
from app.orb.adaptive.runtime import *
from .helpers import *


def make_service(tmp_path,paper=False):
    clock=[clock_ns(DAY,555)]
    s=Service(Store(tmp_path/'events.db'),controller(),safety=lambda:SAFE,clock=lambda:clock[0],paper_enabled=paper)
    if paper:
        # Test authority injection isolates atomic approval behavior. This is
        # NOT a market-proven artifact and is never shipped as an active model.
        s._proof=lambda state,now:(True,'TEST_ONLY_PROOF')
    s.start(DAY,(prior(),),'start')
    for i in range(4):
        b=bar(i);clock[0]=b.available_ns
        s.ingest(DAY,EventBatch(event_id=f'e{i}',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))
    return s,clock


def test_restart_recovers_exact_checkpoint_and_audit(tmp_path):
    s,clock=make_service(tmp_path)
    before=s.store.load('fixture',DAY)
    after=Store(tmp_path/'events.db').load('fixture',DAY)
    assert before==after and s.store.audit('fixture',DAY)['events']==5

def test_duplicate_event_same_content_same_response(tmp_path):
    s,clock=make_service(tmp_path)
    b=bar(3);event=EventBatch(event_id='e3',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,))
    a=s.ingest(DAY,event); b=s.ingest(DAY,event)
    assert a==b and s.store.audit('fixture',DAY)['events']==5

def test_duplicate_event_different_content_fails_closed(tmp_path):
    s,clock=make_service(tmp_path)
    b=evolve(bar(3),volume=1001)
    with pytest.raises(Conflict): s.ingest(DAY,EventBatch(event_id='e3',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))

def test_revision_preserves_old_bar_and_quarantines(tmp_path):
    s,clock=make_service(tmp_path)
    old=s.store.load('fixture',DAY).feature_prefixes['TEST'][-1]
    b=evolve(old,volume=1100)
    s.ingest(DAY,EventBatch(event_id='revision',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))
    state=s.store.load('fixture',DAY)
    assert state.feature_prefixes['TEST'][-1]==old and state.quarantine
    assert state.active_proposal is None

def test_shadow_cannot_approve_despite_eligible_geometry(tmp_path):
    s,clock=make_service(tmp_path)
    plan=s.store.load('fixture',DAY).active_proposal
    clock[0]+=NS
    with pytest.raises(ValueError,match='CURRENT_EXACT_PROOF'): s.approve(DAY,'approval',plan.proposal_id,digest(plan),1,APPROVAL_PHRASE,'tester')

def test_simultaneous_approval_race_one_acceptance(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    plan=s.store.load('fixture',DAY).active_proposal; clock[0]+=NS
    def attempt(i):
        try:
            s.approve(DAY,f'approve{i}',plan.proposal_id,digest(plan),1,APPROVAL_PHRASE,'tester')
            return True
        except ValueError: return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        outcomes=list(pool.map(attempt,range(16)))
    assert sum(outcomes)==1
    assert s.store.load('fixture',DAY).approval_accepted
    assert s.store.audit('fixture',DAY)['events']==6

def test_approval_retry_is_acknowledgement_not_second_trade(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    p=s.store.load('fixture',DAY).active_proposal;clock[0]+=NS
    args=(DAY,'approval',p.proposal_id,digest(p),1,APPROVAL_PHRASE,'tester')
    first=s.approve(*args);clock[0]+=NS
    assert s.approve(*args)==first
    assert s.store.audit('fixture',DAY)['events']==6

def test_superseded_proposal_cannot_be_approved(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    old=s.store.load('fixture',DAY).active_proposal
    b=bar(4,(101.98,102,101.90,101.95));clock[0]=b.available_ns
    s.ingest(DAY,EventBatch(event_id='new',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))
    clock[0]+=NS
    with pytest.raises(ValueError,match='STALE_OR_TAMPERED'):
        s.approve(DAY,'stale',old.proposal_id,digest(old),1,APPROVAL_PHRASE,'tester')

def test_timer_expires_without_a_new_candle(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    state=s.store.load('fixture',DAY);clock[0]=state.active_proposal.expires_ns
    result=s.timer(DAY,'expiry')
    assert result['active_proposal'] is None
    assert all(d['public_ticket']!='PAPER-CANDIDATE' for d in result['decisions'].values())

def test_timer_retry_does_not_regenerate_evidence(tmp_path):
    s,clock=make_service(tmp_path)
    clock[0]+=NS; result=s.timer(DAY,'tick')
    clock[0]+=NS; again=s.timer(DAY,'tick')
    assert result==again

def test_timers_do_not_refresh_proposal_creation_time(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    original=s.store.load('fixture',DAY).active_proposal
    clock[0]+=10*NS;s.timer(DAY,'tick')
    assert s.store.load('fixture',DAY).active_proposal==original

def test_proof_revocation_cancels_pending_no_new_candidate(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    p=s.store.load('fixture',DAY).active_proposal;clock[0]+=NS
    s.approve(DAY,'a',p.proposal_id,digest(p),1,APPROVAL_PHRASE,'tester')
    s._proof=lambda state,now:(False,None)
    clock[0]+=NS; result=s.timer(DAY,'revoked')
    assert result['position']['status']=='NO_FILL' and result['approval_accepted']
    assert result['active_proposal'] is None

def test_one_attempt_is_not_reset_after_no_fill(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    p=s.store.load('fixture',DAY).active_proposal;clock[0]+=NS
    s.approve(DAY,'a',p.proposal_id,digest(p),1,APPROVAL_PHRASE,'tester')
    for i,row in [(4,(101.98,102,101.90,101.95)),(5,(101,101.1,100.8,101))]:
        b=bar(i,row);clock[0]=b.available_ns
        result=s.ingest(DAY,EventBatch(event_id=f'e{i}',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))
    assert result['position']['status']=='NO_FILL'
    assert result['approval_accepted'] and not result['filled_entry_used'] and result['active_proposal'] is None

def test_filled_trade_keeps_accounting_when_entry_safety_blocked(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    p=s.store.load('fixture',DAY).active_proposal;clock[0]+=NS
    s.approve(DAY,'a',p.proposal_id,digest(p),1,APPROVAL_PHRASE,'tester')
    for i,row in [(4,(101.98,102,101.90,101.95)),(5,(101.95,102,101.4,101.5))]:
        b=bar(i,row);clock[0]=b.available_ns
        s.ingest(DAY,EventBatch(event_id=f'e{i}',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))
    s.safety=lambda:SafetyState(mode='MOCK',kill_switch_armed=False,data_gate_passed=True)
    b=bar(6,(101.5,103.2,101.4,103));clock[0]=b.available_ns
    result=s.ingest(DAY,EventBatch(event_id='exit',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)))
    assert result['position']['status']=='CLOSED' and result['position']['net_pnl']<0
    assert result['filled_entry_used'] and result['active_proposal'] is None

def test_same_account_cannot_start_different_symbol_session(tmp_path):
    s,clock=make_service(tmp_path)
    with pytest.raises(Conflict): s.start(DAY,(prior('OTHER'),),'second')

def test_missing_execution_timer_returns_unknown_not_harmless_no_fill(tmp_path):
    s,clock=make_service(tmp_path,paper=True)
    p=s.store.load('fixture',DAY).active_proposal;clock[0]+=NS
    s.approve(DAY,'a',p.proposal_id,digest(p),1,APPROVAL_PHRASE,'tester')
    clock[0]=clock_ns(DAY,587)
    result=s.timer(DAY,'missing')
    assert result['position']['status']=='UNKNOWN' and result['position']['net_pnl'] is None

def test_checkpoint_tamper_detected(tmp_path):
    s,clock=make_service(tmp_path)
    with __import__("contextlib").closing(sqlite3.connect(tmp_path/'events.db')) as db:
        db.execute("UPDATE sessions SET state_json='{}'")
        db.commit()
    with pytest.raises(StoreError): s.store.load('fixture',DAY)

def test_backup_uses_consistent_sqlite_snapshot(tmp_path):
    s,clock=make_service(tmp_path)
    dest=tmp_path/'backup.db';s.store.backup(dest)
    assert Store(dest).load('fixture',DAY)==s.store.load('fixture',DAY)

def test_single_holdout_record_cannot_be_finished_twice(tmp_path):
    s,clock=make_service(tmp_path)
    s.store.register_trial('trial',{'policies':['a'],'sealed_test':['2026-01-01']})
    s.store.finish_trial('trial',{'result':'UNKNOWN'})
    with pytest.raises(Conflict): s.store.finish_trial('trial',{'result':'PASS'})
    with pytest.raises(Conflict): s.store.register_trial('trial',{'policies':['b']})
