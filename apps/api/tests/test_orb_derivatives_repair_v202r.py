"""ORB v2.02 repair gates (vendor-independent half + G1/G2 provisional-model).

Covers: STORE-001, health matrix, OPENALGO-001..006 (001/002 against the
PROVISIONAL model — synthetic-shaped, clearly labeled, NOT vendor proof),
PIT-001..004, REQUIRED/OPTIONAL policy, REPLAY-001/002, wall top_k/persistence,
provenance mutation. G0 capture still required to confirm the provisional model.
"""
from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from app.orb.derivatives import integration as dintegration
from app.orb.derivatives.api import router
from app.orb.derivatives.calculators import build_context, dominant_oi_wall
from app.orb.derivatives.contracts import (
    DerivativesIdentityError,
    DerivativesPolicy,
    EvidenceRelation,
    FuturesSnapshot,
    Greeks,
    OptionChainSnapshot,
    OptionQuote,
    OptionStrike,
    OptionType,
    PriceScenario,
    ScenarioKind,
    Side,
    Wall,
    digest,
)
from app.orb.derivatives.fixtures import FixtureDerivativesProvider, load_chain_csv, record_replay_fixture
from app.orb.derivatives.openalgo import (
    OpenAlgoAuthError,
    OpenAlgoDataProvider,
    OpenAlgoError,
    OpenAlgoProtocolError,
    OpenAlgoUnavailable,
)
from app.orb.derivatives.reasoning import DerivativesScenarioController
from app.orb.derivatives.replay import ReplayPoint, evaluate_replay
from app.orb.derivatives.service import DerivativesService
from app.orb.derivatives.store import DerivativesStore

# --- Minimal AFRE fixtures (self-contained: tests/afre/helpers is not importable
# from the repo root, and cross-test imports couple suites). Shapes mirror the
# documented AFRE helper conventions; all values are synthetic, never market evidence.
from datetime import timedelta

from app.orb.adaptive.contracts import (
    AccountLimits,
    Bar,
    MarketSnapshot,
    MINUTE,
    NS,
    Policy,
    PriorContext,
    SafetyState,
)
from app.orb.adaptive.controller import Controller
from app.orb.adaptive.runtime import EventBatch, advance_session, new_session

AFRE_DAY = "2026-09-04"
AFRE_ROWS = [(102, 102.6, 101.8, 102.2), (102.2, 102.95, 102.1, 102.72),
             (102.72, 102.8, 102.3, 102.42), (102.4, 102.45, 101.95, 101.98)]
AFRE_SAFE = SafetyState(mode="MOCK", kill_switch_armed=True, data_gate_passed=True)


def _afre_limits(account="fixture"):
    return AccountLimits(account_id=account, risk_budget=1000, maximum_notional=100000, maximum_quantity=500)


def _afre_policy(**kwargs):
    return Policy(range_minutes=5, reward_risk=1, **kwargs)


def _afre_prior(symbol="TEST", day=AFRE_DAY, **kwargs):
    from app.orb.adaptive.contracts import clock_ns

    prev = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    fields = dict(symbol=symbol, session_date=prev, available_ns=clock_ns(prev, 930), high=102, low=98, close=100,
                  atr14=2, tick_size=.01, source_id="fixture", price_basis="basis",
                  verified_prior_session=True, basis_verified=True)
    return PriorContext(**(fields | kwargs))


def _afre_bar(i, row=None, *, day=AFRE_DAY, symbol="TEST", minutes=5, lag=0, **kwargs):
    from app.orb.adaptive.contracts import clock_ns

    row = AFRE_ROWS[i] if row is None else row
    t = clock_ns(day, 555) + i * minutes * MINUTE
    fields = dict(symbol=symbol, minutes=minutes, open_ns=t, close_ns=t + minutes * MINUTE,
                  available_ns=t + minutes * MINUTE + lag * NS, open=row[0], high=row[1], low=row[2], close=row[3],
                  volume=1000, source_id="fixture", price_basis="basis")
    return Bar(**(fields | kwargs))


def _afre_snapshot(rows=AFRE_ROWS, *, day=AFRE_DAY, symbol="TEST", **kwargs):
    bars = tuple(_afre_bar(i, r, day=day, symbol=symbol) for i, r in enumerate(rows))
    return MarketSnapshot(**(dict(session_date=day, as_of_ns=bars[-1].available_ns,
                                  prior=_afre_prior(symbol, day), bars=bars) | kwargs))


def _afre_controller(p=None, account="fixture"):
    return Controller(p or _afre_policy(), _afre_limits(account))

NOW = 1_800_000_000_000_000_000
EXP = date(2026, 9, 29)
EXP2 = date(2026, 10, 6)
T = 10_000_000_000  # 10s in ns


def q(strike, kind, *, oi, vol=1000, ltp=10, lot=25, symbol=None):
    return OptionQuote(symbol=symbol or f"NIFTY29SEP26{int(strike)}{kind}", option_type=OptionType(kind), strike=strike,
                       ltp=ltp, bid=max(0, ltp - .1), ask=ltp + .1, volume=vol, oi=oi, lot_size=lot, tick_size=.05)


def chain(spot=100.0, ois=None, ns=NOW, expiry=EXP):
    strikes = [80, 90, 100, 110, 120]
    ois = ois or [(10, 50), (20, 80), (100, 100), (80, 20), (50, 10)]
    rows = tuple(OptionStrike(strike=s, ce=q(s, "CE", oi=co, ltp=max(1, 8 - abs(s - 100) * .2)),
                              pe=q(s, "PE", oi=po, ltp=max(1, 8 - abs(s - 100) * .2)))
                 for s, (co, po) in zip(strikes, ois))
    return OptionChainSnapshot(underlying="NIFTY", underlying_exchange="NSE_INDEX", options_exchange="NFO",
                               expiry_date=expiry, underlying_ltp=spot, atm_strike=100,
                               as_of_ns=ns, received_ns=ns, rows=rows,
                               provider_payload_hash=digest({"ns": ns, "ois": ois}))


def greeks():
    out = []
    for s in [80, 90, 100, 110, 120]:
        cd = {80: .90, 90: .70, 100: .50, 110: .26, 120: .10}[s]
        pd = {80: -.10, 90: -.24, 100: -.50, 110: -.72, 120: -.90}[s]
        for kind, d, iv in [(OptionType.CE, cd, 18 + (s - 100) * .02), (OptionType.PE, pd, 20 - (s - 100) * .01)]:
            out.append(Greeks(symbol=f"NIFTY29SEP26{s}{kind.value}", strike=s, option_type=kind, days_to_expiry=22,
                              forward_price=100, option_price=8, implied_volatility_pct=iv, delta=d,
                              gamma=.02 if s == 100 else .01, theta_per_day=-1, vega_per_vol_point=1.2, rho=.1))
    return tuple(out)


def fut(ltp=101, oi=1000, ns=NOW):
    return FuturesSnapshot(symbol="NIFTY29SEP26FUT", ltp=ltp, prev_close=100, oi=oi, volume=10000,
                           as_of_ns=ns, received_ns=ns, provider_payload_hash=digest({"ltp": ltp, "oi": oi, "ns": ns}))


def scen(symbol="NIFTY", ns=NOW, expiry=None, **kw):
    base = dict(symbol=symbol, session_date=date(2026, 9, 7), as_of_ns=ns, kind=ScenarioKind.CONTINUATION,
                side=Side.LONG, entry=100, target=105)
    base.update(kw)
    if expiry is not None:
        base["expiry_date"] = expiry
    return PriceScenario(**base)


def avail_ctx(ns=NOW, expiry=EXP):
    return build_context(chain(ns=ns, expiry=expiry), greeks(), now_ns=ns,
                         policy=DerivativesPolicy(minimum_chain_rows=5))


# STORE-001 -------------------------------------------------------------------

def test_store_memory_roundtrip():
    st = DerivativesStore(":memory:")
    try:
        c1, c2 = chain(ns=NOW - 10), chain(ns=NOW)
        st.put_chain(c1)
        st.put_chain(c2)
        got = st.previous_chain("NIFTY", EXP.isoformat(), NOW)
        assert got is not None and got.snapshot_hash == c1.snapshot_hash
        st.put_futures(fut())
        assert st.previous_futures("NIFTY29SEP26FUT", NOW + 1) is not None
        ctx = avail_ctx()
        st.put_context(ctx)
        assert st.iv_history("NIFTY", before_ns=NOW + 1) == (ctx.atm_iv_pct,)
        ctx2 = build_context(chain(ns=NOW + 5), greeks(), now_ns=NOW + 5,
                             policy=DerivativesPolicy(minimum_chain_rows=5))
        assert ctx2.atm_iv_pct is not None
        st.put_context(ctx2)
        assert len(st.iv_history("NIFTY", before_ns=NOW + 6)) == 2
    finally:
        st.close()


# G7 health matrix --------------------------------------------------------------

def _health(provider):
    r = router(provider)
    route = [rt for rt in r.routes if rt.path.endswith("/health")][0]
    return route.endpoint()


class _Svc:
    def __init__(self, provider=True, store=True):
        self.provider = object() if provider else None
        self.store = object() if store else None


def test_health_ready():
    out = _health(lambda: _Svc())
    assert out["status"] == "ready" and out["provider_ready"] is True and out["store_ready"] is True
    assert out["live_trading_blocked"] is True and "profile" in out


def test_health_degraded_on_construction_failure():
    def boom():
        raise KeyError("OPENALGO_BASE_URL")

    out = _health(boom)
    assert out["status"] == "degraded" and out["provider_ready"] is False
    assert "reason" in out


def test_health_degraded_on_missing_provider():
    out = _health(lambda: _Svc(provider=False))
    assert out["status"] == "degraded" and out["provider_ready"] is False


# G3 error boundary ---------------------------------------------------------------

class _FakeClient:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def post(self, url, json=None, timeout=None):
        self.calls += 1
        code = self.statuses[min(self.calls - 1, len(self.statuses) - 1)]
        return httpx.Response(code, json={"status": "success"}, request=httpx.Request("POST", url))


def _prov(statuses, **kw):
    args = dict(base_url="http://127.0.0.1:9", api_key="SECRETKEY", max_retries=2, backoff_seconds=0)
    args.update(kw)
    return OpenAlgoDataProvider(client=_FakeClient(statuses), **args)


def test_openalgo_400_is_protocol_error_without_key():
    p = _prov([400])
    with pytest.raises(OpenAlgoProtocolError) as ei:
        p._post("quotes", {})
    assert "SECRETKEY" not in str(ei.value)


def test_openalgo_401_is_auth_error():
    p = _prov([401])
    with pytest.raises(OpenAlgoAuthError):
        p._post("quotes", {})


def test_openalgo_non_json_body_is_protocol_error():
    class _BadJsonClient:
        def post(self, url, json=None, timeout=None):
            return httpx.Response(200, content=b"<html>not json</html>",
                                  request=httpx.Request("POST", url))

    p = OpenAlgoDataProvider(base_url="http://127.0.0.1:9", api_key="K", client=_BadJsonClient())
    with pytest.raises(OpenAlgoProtocolError, match="non-JSON"):
        p._post("quotes", {})


def test_openalgo_429_retries_bounded_then_unavailable():
    p = _prov([429, 429, 429])
    with pytest.raises(OpenAlgoUnavailable):
        p._post("quotes", {})
    assert p._client.calls == 3


def test_openalgo_500_retries_bounded_then_unavailable():
    p = _prov([500, 500, 500])
    with pytest.raises(OpenAlgoUnavailable):
        p._post("quotes", {})
    assert p._client.calls == 3


# G4 metadata fail-closed -----------------------------------------------------------

class _ChainClient:
    def __init__(self, payload):
        self.payload = payload

    def post(self, url, json=None, timeout=None):
        return httpx.Response(200, json=self.payload, request=httpx.Request("POST", url))


def test_openalgo_chain_missing_lotsize_rejected():
    payload = {"status": "success", "expiry_date": "29SEP26", "underlying_ltp": 100, "atm_strike": 100,
               "chain": [{"strike": 100, "ce": {"symbol": "A", "ltp": 5}, "pe": None}]}
    p = OpenAlgoDataProvider(base_url="http://127.0.0.1:9", api_key="K", client=_ChainClient(payload))
    with pytest.raises(OpenAlgoProtocolError, match="CONTRACT_METADATA_MISSING"):
        p.option_chain(underlying="NIFTY", exchange="NFO", expiry_date=EXP)


def test_csv_fixture_missing_tick_rejected(tmp_path):
    csvp = tmp_path / "c.csv"
    csvp.write_text("strike,ce_symbol,ce_ltp,ce_bid,ce_ask,ce_volume,ce_oi,ce_lotsize,ce_tick,"
                    "pe_symbol,pe_ltp,pe_bid,pe_ask,pe_volume,pe_oi,pe_lotsize,pe_tick\n"
                    "100,AAA,5,4.9,5.1,10,20,25,,BBBB,4,3.9,4.1,9,19,25,.05\n", encoding="utf-8")
    with pytest.raises(LookupError, match="CONTRACT_METADATA_MISSING"):
        load_chain_csv(csvp, underlying="NIFTY", underlying_exchange="NSE_INDEX", expiry_date=EXP,
                       underlying_ltp=100, atm_strike=100, as_of_ns=NOW)


# G5 PIT identity ---------------------------------------------------------------------

def test_pit001_symbol_mismatch_rejected():
    ctx = avail_ctx()
    with pytest.raises(DerivativesIdentityError, match="DERIVATIVES_SYMBOL_IDENTITY_MISMATCH"):
        DerivativesScenarioController().evaluate(scen(symbol="BANKNIFTY"), ctx)


def test_pit002_future_context_rejected():
    ctx = avail_ctx(ns=NOW + T)
    with pytest.raises(DerivativesIdentityError, match="DERIVATIVES_CONTEXT_FROM_FUTURE"):
        DerivativesScenarioController().evaluate(scen(ns=NOW), ctx)


def test_pit004_wrong_expiry_rejected():
    ctx = avail_ctx(expiry=EXP2)
    with pytest.raises(DerivativesIdentityError, match="DERIVATIVES_EXPIRY_MISMATCH"):
        DerivativesScenarioController().evaluate(scen(expiry=EXP), ctx)


def test_assessment_as_of_is_decision_time_not_max():
    ctx = avail_ctx(ns=NOW - 5)
    a = DerivativesScenarioController().evaluate(scen(ns=NOW), ctx)
    assert a.as_of_ns == NOW


def test_pit003_stale_required_blocks_and_harness_skips_future():
    stale = build_context(chain(ns=NOW - 60_000_000_000), greeks(), now_ns=NOW,
                          policy=DerivativesPolicy(minimum_chain_rows=5))
    assert stale.status == "STALE"
    a = DerivativesScenarioController().evaluate(scen(), stale, derivatives_required=True)
    assert a.relation == EvidenceRelation.BLOCK and a.public_ticket_cap == "WAIT"
    good = ReplayPoint(session_date=date(2026, 9, 7), decision_ns=NOW, scenario=scen(), context=avail_ctx())
    bad = ReplayPoint(session_date=date(2026, 9, 7), decision_ns=NOW, scenario=scen(), context=avail_ctx(ns=NOW + T))
    out = evaluate_replay([good, bad])
    assert len(out) == 1 and out[0].pit_safe is True


def test_replay_harness_rejects_expiry_mismatch():
    pt = ReplayPoint(session_date=date(2026, 9, 7), decision_ns=NOW, scenario=scen(expiry=EXP),
                     context=avail_ctx(expiry=EXP2))
    assert evaluate_replay([pt]) == ()


# G12 REQUIRED/OPTIONAL policy ----------------------------------------------------------------

def _unavailable_ctx():
    return build_context(chain(ois=[(0, 0)] * 5), greeks(), now_ns=NOW,
                         policy=DerivativesPolicy(minimum_chain_rows=5))


def test_optional_unavailable_is_unknown_not_clean():
    a = DerivativesScenarioController().evaluate(scen(), _unavailable_ctx(), derivatives_required=False)
    assert a.relation == EvidenceRelation.UNKNOWN
    assert a.public_ticket_cap == "WATCH"
    assert a.support_families == () and a.conflict_families == ()
    assert "DERIVATIVES_UNAVAILABLE" in a.reason_codes


def test_required_unavailable_blocks():
    a = DerivativesScenarioController().evaluate(scen(), _unavailable_ctx(), derivatives_required=True)
    assert a.relation == EvidenceRelation.BLOCK and a.public_ticket_cap == "WAIT"
    assert "DERIVATIVES_REQUIRED_UNAVAILABLE" in a.reason_codes


# G6 replay provider ------------------------------------------------------------------------------

def _record(tmp_path):
    d = tmp_path / "replay"
    record_replay_fixture(d, chain=chain(), futures=fut(), greeks=greeks())
    return d


def test_replay_profile_needs_no_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALGO_BASE_URL", raising=False)
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_PROFILE", "replay")
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_REPLAY_DIR", str(_record(tmp_path)))
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_DB", str(tmp_path / "r.db"))
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_MIN_CHAIN_ROWS", "5")
    old = dintegration._SERVICE
    dintegration._SERVICE = None
    try:
        svc = dintegration.build_service(tmp_path)
        assert isinstance(svc.provider, FixtureDerivativesProvider)
        bundle = svc.refresh(underlying="NIFTY", underlying_exchange="NSE_INDEX", expiry_date=EXP,
                             scenario=scen())
        assert bundle.context.symbol == "NIFTY" and bundle.assessment is not None
    finally:
        dintegration._SERVICE = old


def test_replay_determinism(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALGO_BASE_URL", raising=False)
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_PROFILE", "replay")
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_MIN_CHAIN_ROWS", "5")
    rep = _record(tmp_path)
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_REPLAY_DIR", str(rep))
    hashes = []
    old = dintegration._SERVICE
    try:
        for i in range(2):
            monkeypatch.setenv("TRADEVISION_DERIVATIVES_DB", str(tmp_path / f"r{i}.db"))
            dintegration._SERVICE = None
            svc = dintegration.build_service(tmp_path)
            b = svc.refresh(underlying="NIFTY", underlying_exchange="NSE_INDEX", expiry_date=EXP,
                            scenario=scen())
            hashes.append((b.context.context_hash, b.assessment))
    finally:
        dintegration._SERVICE = old
    assert hashes[0][0] == hashes[1][0] and hashes[0][1] == hashes[1][1]


def test_fixture_provider_missing_is_fail_closed(tmp_path):
    from app.orb.derivatives.fixtures import _ReplayMissing

    with pytest.raises(_ReplayMissing):
        FixtureDerivativesProvider(tmp_path / "empty").option_chain(
            underlying="NIFTY", exchange="NFO", expiry_date=EXP)


# G12 walls ------------------------------------------------------------------------------------------

def test_wall_top_k_bounds_candidates():
    import numpy as np

    strikes = np.array([90.0, 100.0, 110.0])
    # top_k=1 always selects the max-OI strike.
    w1 = dominant_oi_wall(strikes, np.array([50.0, 400.0, 1000.0]), np.array([0.0, 2000.0, 0.0]),
                          100.0, side="CALL", top_k=1, distance_decay_pct=2.0)
    assert w1 is not None and w1.strike == 110.0
    # Property: the winner is always inside the top-k set by OI, for any k.
    rng = np.random.RandomState(20260207)
    for _ in range(25):
        oi = rng.uniform(1.0, 5000.0, size=7)
        chg = rng.uniform(-500.0, 500.0, size=7)
        s = np.array([80.0, 90.0, 95.0, 100.0, 105.0, 110.0, 120.0])
        for k in (1, 2, 3, 7, 99):
            w = dominant_oi_wall(s, oi, chg, 100.0, side="CALL", top_k=k, distance_decay_pct=2.0)
            kk = max(1, min(k, len(s)))
            top = set(np.argsort(oi)[-kk:].tolist())
            assert w is not None and int(np.argmin(np.abs(s - w.strike))) in top
    # k >= n behaves as unbounded selection.
    w_all = dominant_oi_wall(strikes, np.array([50.0, 400.0, 1000.0]), np.array([0.0, 2000.0, 0.0]),
                             100.0, side="CALL", top_k=99, distance_decay_pct=2.0)
    assert w_all is not None and w_all.strike == 110.0


def test_wall_persistence_one_step():
    c1, c2 = chain(ns=NOW - 10), chain(ns=NOW)
    ctx = build_context(c2, greeks(), previous_chain=c1, now_ns=NOW,
                        policy=DerivativesPolicy(minimum_chain_rows=5))
    assert ctx.call_oi_wall is not None and ctx.call_oi_wall.persistence == 1
    ctx0 = build_context(c2, greeks(), now_ns=NOW, policy=DerivativesPolicy(minimum_chain_rows=5))
    assert ctx0.call_oi_wall is not None and ctx0.call_oi_wall.persistence == 0
    other = Wall(strike=1.0, strength=1.0, distance_pct=1.0, oi=1.0)
    import numpy as np

    w = dominant_oi_wall(np.array([100.0]), np.array([10.0]), np.array([1.0]), 100.0,
                         side="CALL", top_k=1, distance_decay_pct=2.0, previous_wall=other)
    assert w is not None and w.persistence == 0


# G11 provenance ---------------------------------------------------------------------------------------

def test_provenance_mutation_isolation():
    g1, g2 = greeks(), greeks()
    h1 = digest([g.model_dump(mode="json") for g in g1])
    mod = [g.model_copy(update={"implied_volatility_pct": g.implied_volatility_pct + 5.0}) if i == 0 else g
           for i, g in enumerate(g2)]
    h2 = digest([g.model_dump(mode="json") for g in mod])
    assert h1 != h2
    c1 = build_context(chain(), g1, now_ns=NOW, policy=DerivativesPolicy(minimum_chain_rows=5),
                       greeks_snapshot_hash=h1)
    c2 = build_context(chain(), mod, now_ns=NOW, policy=DerivativesPolicy(minimum_chain_rows=5),
                       greeks_snapshot_hash=h2)
    assert c1.chain_snapshot_hash == c2.chain_snapshot_hash
    assert c1.greeks_snapshot_hash != c2.greeks_snapshot_hash
    assert c1.context_hash != c2.context_hash
    assert c1.iv_history_hash is None
    c3 = build_context(chain(), g1, now_ns=NOW, policy=DerivativesPolicy(minimum_chain_rows=5),
                       iv_history=(18.0, 19.0))
    assert c3.iv_history_hash is not None and len(c3.iv_history_hash) == 64


# api mapping ---------------------------------------------------------------------------------------------

def test_api_identity_error_is_422_and_provider_error_is_503():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.orb.derivatives.contracts import DerivativesIdentityError as DIE

    def raiser_identity():
        raise DIE("DERIVATIVES_SYMBOL_IDENTITY_MISMATCH: x")

    app = FastAPI()
    app.include_router(router(raiser_identity))
    body = {"underlying": "NIFTY", "expiry_date": "2026-09-29", "scenario": None}
    assert TestClient(app).post("/api/v1/orb/derivatives/analyze", json=body).status_code == 422

    def raiser_provider():
        raise OpenAlgoError("down")

    app2 = FastAPI()
    app2.include_router(router(raiser_provider))
    assert TestClient(app2).post("/api/v1/orb/derivatives/analyze", json=body).status_code == 503


# G1/G2 provisional-model enforcement (synthetic-shaped, NOT vendor proof) -----

def _legs(*symbols):
    return {s: {"strike": 100.0, "option_type": "CE", "days_to_expiry": 5.0,
                "forward_price": 100.0, "option_price": 5.0} for s in symbols}


class _BatchClient:
    """Counts wire calls and serves provisional-model batch rows."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = 0
        self.payloads = []

    def post(self, url, json=None, timeout=None):
        import httpx as _httpx

        self.calls += 1
        self.payloads.append(json)
        wanted = {it["symbol"] for it in (json or {}).get("symbols", [])}
        rows = [r for r in self.rows if r.get("symbol") in wanted] or self.rows
        return _httpx.Response(200, json={"status": "success", "data": rows},
                               request=_httpx.Request("POST", url))


def _greeks_row(symbol, iv=20.0):
    return {"status": "success", "symbol": symbol, "implied_volatility": iv,
            "greeks": {"delta": .5, "gamma": .02, "theta": -1, "vega": 1, "rho": .1}}


def test_openalgo_001_provisional_join_and_report():
    from app.orb.derivatives.openalgo import OPENALGO_MULTI_GREEKS_MAX_BATCH

    assert OPENALGO_MULTI_GREEKS_MAX_BATCH == 50
    client = _BatchClient([_greeks_row("A"), _greeks_row("B")])
    p = OpenAlgoDataProvider(base_url="http://127.0.0.1:9", api_key="K", client=client)
    rep = {}
    out = p.multi_option_greeks([("A", "NFO"), ("B", "NFO")], chain_legs=_legs("A", "B"), report=rep)
    assert len(out) == 2 and rep["parsed"] == 2 and rep["failed"] == 0 and rep["chunks"] == 1


def test_openalgo_002_51_symbols_chunked_with_top_level_expiry():
    syms = [(f"S{i:03d}", "NFO") for i in range(51)]
    client = _BatchClient([_greeks_row(f"S{i:03d}") for i in range(51)])
    p = OpenAlgoDataProvider(base_url="http://127.0.0.1:9", api_key="K", client=client)
    rep = {}
    out = p.multi_option_greeks(syms, chain_legs=_legs(*[f"S{i:03d}" for i in range(51)]),
                                expiry_time="2026-09-29T15:30:00+05:30", report=rep)
    assert len(out) == 51 and client.calls == 2 and rep["chunks"] == 2
    assert all(pl["expiry_time"] == "2026-09-29T15:30:00+05:30" for pl in client.payloads)
    assert all("forward_price" not in it and "expiry_time" not in it
               for pl in client.payloads for it in pl["symbols"])
    with pytest.raises(ValueError, match=r"1\.\.50"):
        p.multi_option_greeks(syms[:1], chain_legs=_legs(syms[0][0]), batch_size=51)


def test_openalgo_join_failures_are_loud():
    client = _BatchClient([_greeks_row("GHOST")])
    p = OpenAlgoDataProvider(base_url="http://127.0.0.1:9", api_key="K", client=client)
    with pytest.raises(OpenAlgoProtocolError, match="UNJOINED_GREEKS_ROWS"):
        p.multi_option_greeks([("GHOST", "NFO")], chain_legs=_legs("OTHER"))
    with pytest.raises(OpenAlgoProtocolError, match="chain_legs is required"):
        p.multi_option_greeks([("A", "NFO")])
    empty = _BatchClient([{"status": "error", "symbol": "A"}])
    p2 = OpenAlgoDataProvider(base_url="http://127.0.0.1:9", api_key="K", client=empty)
    with pytest.raises(OpenAlgoProtocolError, match="zero usable"):
        p2.multi_option_greeks([("A", "NFO")], chain_legs=_legs("A"))


def test_validate_live_contract_ok_and_deviation():
    from app.orb.derivatives.openalgo import validate_live_contract

    good_chain = {"chain": [{"strike": 100, "ce": {"symbol": "A", "ltp": 5, "oi": 10,
                                                   "lotsize": 25, "tick_size": .05}}]}
    good_greeks = {"data": [{"symbol": "A", "implied_volatility": 20, "greeks": {"delta": .5}}]}
    assert validate_live_contract(good_chain, good_greeks) == (True, "provisional shape holds")
    hybrid = {"data": [{"symbol": "A", "strike": 100, "option_type": "CE", "implied_volatility": 20,
                        "greeks": {"delta": .5}}]}
    ok, reason = validate_live_contract(good_chain, hybrid)
    assert ok is False and "chain fields" in reason
    assert validate_live_contract({}, {})[0] is False


# G9 v1.73 runtime wiring ---------------------------------------------------------

def _v173_request():
    from app.behavior.execution_event_oi_risk import ExecutionEventOiRiskRequest
    from app.models import CandleBar, CandleSeries

    bars = [CandleBar(symbol="NIFTY", timeframe="5m", timestamp_ns=NOW - (40 - i) * 300_000_000_000,
                      open=100.0, high=100.5, low=99.5, close=100.0 + (i % 3) * 0.05,
                      volume=1000.0, source="mock", sequence_number=i + 1) for i in range(40)]
    return ExecutionEventOiRiskRequest(series=CandleSeries(symbol="NIFTY", timeframe="5m", bars=bars),
                                       entry_price=100.0, stop_loss=99.0, target=101.5,
                                       spread_pct=0.05, average_slippage_pct=0.02,
                                       depth_available=True, visible_depth_value=1_000_000.0,
                                       event_context_status="available",
                                       options_context_status="unavailable")


def test_bridge001_context_populates_real_request():
    from app.behavior.execution_event_oi_risk import (
        build_execution_event_oi_risk_report,
        build_report_with_derivatives_context,
    )

    ctx = avail_ctx()
    assert ctx.status == "AVAILABLE"
    base = build_execution_event_oi_risk_report(_v173_request())
    assert base.options_context_status == "unavailable"
    fed = build_report_with_derivatives_context(_v173_request(), ctx)
    assert fed.options_context_status == "available"
    assert fed.expected_move_pct == (ctx.iv_horizon_expected_move_pct or ctx.atm_straddle_expected_move_pct)
    assert fed.max_pain_magnet in ("active_pin_zone", "nearby_magnet", "distant")
    assert fed.trade_allowed is False and fed.live_trading_blocked is True


def test_bridge002_resolver_off_by_default_and_replay_backed(tmp_path, monkeypatch):
    from app.orb.derivatives.integration import resolve_context_for_symbol

    monkeypatch.delenv("TRADEVISION_V173_DERIVATIVES", raising=False)
    assert resolve_context_for_symbol("NIFTY", tmp_path) is None
    # Flag on + replay profile: real context flows with zero vendor credentials.
    monkeypatch.delenv("OPENALGO_BASE_URL", raising=False)
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_V173_DERIVATIVES", "on")
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_PROFILE", "replay")
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_REPLAY_DIR", str(_record(tmp_path)))
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_DB", str(tmp_path / "g9.db"))
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_MIN_CHAIN_ROWS", "5")
    old = dintegration._SERVICE
    dintegration._SERVICE = None
    try:
        ctx = resolve_context_for_symbol("NIFTY", tmp_path)
        assert ctx is not None and ctx.symbol == "NIFTY"
        fed_req = _v173_request()
        from app.behavior.execution_event_oi_risk import build_report_with_derivatives_context

        fed = build_report_with_derivatives_context(fed_req, ctx)
        assert fed.options_context_status == "available"
    finally:
        dintegration._SERVICE = old


# G10 AFRE EventBatch wiring ----------------------------------------------------------

def _afre_ctx(ns):
    return build_context(chain(ns=ns), greeks(), now_ns=ns, policy=DerivativesPolicy(minimum_chain_rows=5))


def test_afre001_capability_enters_eventbatch():
    from app.orb.derivatives.bridges import derivatives_event_batch_capabilities

    ns = _afre_bar(0).available_ns
    ctx = _afre_ctx(ns)
    a = DerivativesScenarioController().evaluate(scen(ns=ns), ctx)
    merged = derivatives_event_batch_capabilities(ctx, a)
    assert set(merged) == {"NIFTY"} and merged["NIFTY"][0].name == "DERIVATIVES_CONTEXT_VALID"
    c = _afre_controller()
    state = new_session("2026-09-04", (_afre_prior(),), c.policy, c.limits)
    b = _afre_bar(0)
    state = advance_session(state, EventBatch(event_id="e-cap", available_ns=b.available_ns,
                                              feature_bars=(b,), execution_bars=(b,),
                                              capabilities={"TEST": merged["NIFTY"]}), c, AFRE_SAFE)
    snap_caps = dict(state.capabilities)
    assert "TEST" in snap_caps and snap_caps["TEST"][0].name == "DERIVATIVES_CONTEXT_VALID"


def test_afre002_reaches_snapshot_and_satisfies_required():
    from app.orb.derivatives.bridges import derivatives_event_batch_capabilities

    base = _afre_snapshot()
    t0 = base.as_of_ns
    ctx = _afre_ctx(t0)
    a = DerivativesScenarioController().evaluate(scen(ns=t0), ctx)
    caps = derivatives_event_batch_capabilities(ctx, a)["NIFTY"]
    enriched = MarketSnapshot(session_date=base.session_date, as_of_ns=t0,
                              prior=base.prior, bars=base.bars, capabilities=caps)
    d = _afre_controller(_afre_policy(required_capabilities=("DERIVATIVES_CONTEXT_VALID",))).evaluate(enriched)
    assert "REQUIRED_CAPABILITY_UNAVAILABLE:DERIVATIVES_CONTEXT_VALID" not in d.reason_codes


def test_afre003_blocked_capability_blocks_candidate():
    from app.orb.derivatives.bridges import derivatives_event_batch_capabilities

    base = _afre_snapshot()
    t0 = base.as_of_ns
    # STALE by 25s against a 20s policy: caps stay in-window at t0, so the block
    # path (not expiry) is what stops the candidate.
    stale = build_context(chain(ns=t0 - 25_000_000_000), greeks(), now_ns=t0,
                          policy=DerivativesPolicy(minimum_chain_rows=5, max_chain_age_seconds=20))
    assert stale.status == "STALE"
    a = DerivativesScenarioController().evaluate(scen(ns=t0), stale)
    caps = derivatives_event_batch_capabilities(stale, a)["NIFTY"]
    assert caps[0].status == "BLOCKED" and caps[0].blocks_new_entry is True
    blocked = [c for c in caps if c.blocks_new_entry]
    assert blocked, "STALE context must yield at least one entry-blocking capability"
    from app.orb.adaptive.contracts import MarketSnapshot

    cap = blocked[0]
    in_window = MarketSnapshot(session_date=base.session_date, as_of_ns=t0,
                               prior=base.prior, bars=base.bars, capabilities=(cap,))
    d = _afre_controller().evaluate(in_window)
    assert any(r.startswith("VERIFIED_REFERENCE_BLOCK") for r in d.reason_codes)


def test_afre004_support_alone_creates_nothing():
    # Capabilities must never manufacture or alter a plan: identical snapshot with
    # and without SUPPORT caps yields the same trading outcome.
    from datetime import date

    from app.orb.derivatives.bridges import derivatives_event_batch_capabilities

    base = _afre_snapshot()
    plain = _afre_controller().evaluate(base)
    t0 = base.as_of_ns
    ctx = build_context(chain(ns=t0), greeks(), now_ns=t0, policy=DerivativesPolicy(minimum_chain_rows=5))
    a = DerivativesScenarioController().evaluate(scen(ns=t0, session_date=date(2026, 9, 7)), ctx)
    caps = derivatives_event_batch_capabilities(ctx, a)["NIFTY"]
    assert not any(c.blocks_new_entry for c in caps if c.name == "DERIVATIVES_SCENARIO_SUPPORT")
    enriched = MarketSnapshot(session_date=base.session_date, as_of_ns=base.as_of_ns,
                              prior=base.prior, bars=base.bars, capabilities=caps)
    got, want = _afre_controller().evaluate(enriched).selected_plan, plain.selected_plan
    # Capabilities ride along (snapshot hash legitimately differs) but must not
    # change the trading outcome: same presence, same template/side/levels.
    assert (got is None) == (want is None)
    if got is not None and want is not None:
        assert (got.template, got.side, got.reference_entry, got.stop) == \
               (want.template, want.side, want.reference_entry, want.stop)


# E2E-001 provisional chain (fixture-backed, clearly labeled) ------------------------

def test_e2e001_provisional_chain_fixture_to_afre(tmp_path, monkeypatch):
    """Provisional E2E (NOT vendor proof): recorded fixture -> context -> v1.73 ->
    AFRE capabilities -> MarketSnapshot. G0 capture still required for vendor truth."""
    from app.behavior.execution_event_oi_risk import build_report_with_derivatives_context
    from app.orb.derivatives.bridges import derivatives_event_batch_capabilities

    monkeypatch.delenv("OPENALGO_BASE_URL", raising=False)
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_PROFILE", "replay")
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_REPLAY_DIR", str(_record(tmp_path)))
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_DB", str(tmp_path / "e2e.db"))
    monkeypatch.setenv("TRADEVISION_DERIVATIVES_MIN_CHAIN_ROWS", "5")
    old = dintegration._SERVICE
    dintegration._SERVICE = None
    try:
        svc = dintegration.build_service(tmp_path)
        bundle = svc.refresh(underlying="NIFTY", underlying_exchange="NSE_INDEX", expiry_date=EXP,
                             scenario=scen())
        assert bundle.assessment is not None
        fed = build_report_with_derivatives_context(_v173_request(), bundle.context)
        assert fed.options_context_status == "available"
        caps = derivatives_event_batch_capabilities(bundle.context, bundle.assessment)
        assert caps["NIFTY"] and all(getattr(c, "status", None) in ("VALID", "BLOCKED") for c in caps["NIFTY"])
    finally:
        dintegration._SERVICE = old
