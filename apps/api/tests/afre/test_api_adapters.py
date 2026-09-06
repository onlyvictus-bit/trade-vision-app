import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.orb.adaptive.api import create_app
from app.orb.adaptive.integration import ExclusivePaperBoundary,mount
from app.orb.adaptive.adapters import from_candle_series,aggregate_verified_finer
from app.orb.adaptive.wake import next_deadline,install_timer_lifespan
from .helpers import *
from .test_runtime_store import make_service

TOKEN='T'*48
HEADER={'Authorization':'Bearer '+TOKEN}
BASE='/api/v1/orb/adaptive'

def test_api_authentication_and_extra_authority_fields(tmp_path):
    service,clock=make_service(tmp_path)
    client=TestClient(create_app(service,TOKEN))
    assert client.get(BASE+'/status').status_code==401
    assert client.get(BASE+'/status',headers=HEADER).status_code==200
    body={'event_id':'attack','proposal_id':'x','proposal_hash':'0'*64,'quantity':1,'approval_phrase':APPROVAL_PHRASE,
          'paper_enabled':True,'decision_time_ns':1,'proof_passed':True}
    response=client.post(BASE+f'/sessions/{DAY}/approve',headers=HEADER,json=body)
    assert response.status_code==422

def test_api_body_limit_prevents_unbounded_parsing(tmp_path):
    service,_=make_service(tmp_path)
    client=TestClient(create_app(service,TOKEN))
    response=client.post(BASE+f'/sessions/{DAY}/events',headers=HEADER,content=b'X'*2_000_001)
    assert response.status_code==413

def test_api_shadow_approval_and_stale_clock_cannot_bypass(tmp_path):
    service,clock=make_service(tmp_path)
    plan=service.store.load('fixture',DAY).active_proposal
    client=TestClient(create_app(service,TOKEN))
    response=client.post(BASE+f'/sessions/{DAY}/approve',headers=HEADER,json=dict(event_id='nope',proposal_id=plan.proposal_id,
                        proposal_hash=digest(plan),quantity=1,approval_phrase=APPROVAL_PHRASE))
    assert response.status_code==422
    b=bar(4,(101.98,102,101.9,101.95))
    event=EventBatch(event_id='future',available_ns=b.available_ns,feature_bars=(b,))
    assert client.post(BASE+f'/sessions/{DAY}/events',headers=HEADER,json=event.model_dump(mode='json')).status_code==422

def test_off_profile_changes_no_routes_and_opens_no_store(monkeypatch):
    monkeypatch.setenv('TRADEVISION_AFRE_PROFILE','off')
    app=FastAPI();before=tuple(app.routes);mount(app)
    assert tuple(app.routes)==before and not hasattr(app.state,'afre_service')

def test_exclusive_profile_blocks_legacy_writes_but_not_reads():
    app=FastAPI();app.add_middleware(ExclusivePaperBoundary)
    @app.post('/legacy/approve')
    def approve():return {'unsafe':'should be unreachable'}
    @app.get('/legacy/read')
    def read():return {'ok':True}
    client=TestClient(app)
    assert client.post('/legacy/approve').status_code==423
    assert client.get('/legacy/read').status_code==200

def test_expiry_scheduler_has_finite_event_driven_deadlines():
    state,c=state_to_fade()
    assert next_deadline(state,c.policy)==state.active_proposal.expires_ns
    state=evolve(state,watermark_ns=clock_ns(DAY,616),active_proposal=None)
    assert next_deadline(state,c.policy) is None

def test_timer_preserves_existing_lifespan_cleanup(tmp_path):
    service,clock=make_service(tmp_path)
    events=[]
    @asynccontextmanager
    async def existing(app):
        events.append('start');yield;events.append('stop')
    app=FastAPI(lifespan=existing)
    install_timer_lifespan(app,service)
    with TestClient(app):
        assert events==['start']
    assert events==['start','stop']

def test_existing_series_adapter_requires_volume_and_availability():
    b=bar(0)
    raw=SimpleNamespace(symbol='TEST',timeframe='5m',timestamp_ns=b.open_ns,open=b.open,high=b.high,low=b.low,close=b.close,volume=1000)
    series=SimpleNamespace(symbol='TEST',timeframe='5m',bars=[raw])
    kw=dict(source_id='existing-hstry',price_basis='basis',verified_native_minutes=5)
    with pytest.raises(ValueError):from_candle_series(series,availability_ns={},**kw)
    result=from_candle_series(series,availability_ns={b.open_ns:b.available_ns},**kw)
    assert result[0].close==b.close
    raw.volume=None
    with pytest.raises(ValueError):from_candle_series(series,availability_ns={b.open_ns:b.available_ns},**kw)

def test_real_finer_bars_resample_but_5m_cannot_reconstruct_3m():
    fine=tuple(bar(i,(100,102,99,101),minutes=1) for i in range(15))
    three=aggregate_verified_finer(fine,3)
    five=aggregate_verified_finer(fine,5)
    assert len(three)==5 and len(five)==3
    assert three[0].volume==3000 and three[0].available_ns==fine[2].available_ns
    with pytest.raises(ValueError):aggregate_verified_finer(five,3)
    with pytest.raises(ValueError):aggregate_verified_finer(fine[1:],3)

def test_registered_host_d1_is_shared_by_direct_and_research_paths():
    class Gate:
        source_hash='test-gate-source'
        def __call__(self,s):return False
        def is_current(self):return True
    p=policy(host_d1_source_hash='test-gate-source')
    c=Controller(p,limits(),data_guard=Gate())
    assert c.evaluate(snapshot()).selected_plan is None
    from app.orb.adaptive.research import replay_day
    result=replay_day(synthetic_day(),c)
    assert not result.entry_filled
    with pytest.raises(ValueError):Controller(p,limits())
