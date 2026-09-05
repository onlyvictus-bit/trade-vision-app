"""v1.97 ORB Timing Research gates (ORB-T197-001..).

M1 scope: loader correctness (001-002), aggregation math (003),
checkpoint resume + end-to-end determinism (004). Hermetic: synthetic CSVs
in tmp_path, never the real HSTRY directory, never network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.orb import timing_research as tr
from app.orb.hstry_csv import HstryCsvNotFound, load_hstry_series, hstry_csv_path
from app.models import OrbTimingResearchRequest, OrbTimingWindowRow

CSV_HEADER = "date,time,open,high,low,close,volume,oi"


def _write_symbol_csv(base_dir, symbol: str, token: str, days: int, rising: bool = True,
                      start: str = "2024-01-02") -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    lines = [CSV_HEADER]
    day0 = pd.Timestamp(start)
    price = 100.0
    for d in range(days):
        date = (day0 + pd.Timedelta(days=d)).strftime("%Y-%m-%d")
        # skip weekends so every day is a real trading day pattern
        if pd.Timestamp(date).weekday() >= 5:
            continue
        for minute in range(9 * 60 + 15, 14 * 60 + 1, 5):
            hh, mm = divmod(minute, 60)
            step = 0.4 if rising else -0.4
            o = round(price, 2)
            c = round(price + step, 2)
            h = round(max(o, c) + 0.3, 2)
            low = round(min(o, c) - 0.3, 2)
            lines.append(f"{date},{hh:02d}:{mm:02d}:00,{o},{h},{low},{c},1000.0,0")
            price = c
    (base_dir / f"{symbol}_NSE_{token}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_orb_t197_001_loader_timezone_round_trip(tmp_path) -> None:
    _write_symbol_csv(tmp_path, "TESTA", "5m", days=2)
    series = load_hstry_series("testa", "5m", base_dir=tmp_path)
    assert len(series.bars) > 0
    first = series.bars[0]
    # 2024-01-02 09:15 IST == 2024-01-02 03:45 UTC -> epoch 1704167100
    assert first.timestamp_ns == 1704167100 * 10**9
    # sequence numbers are contiguous and 1-based
    assert [b.sequence_number for b in series.bars[:3]] == [1, 2, 3]
    assert all(b.source == "user_csv" for b in series.bars)


def test_orb_t197_002_session_filter_alias_and_missing(tmp_path) -> None:
    base_dir = tmp_path
    _write_symbol_csv(base_dir, "TESTB", "5m", days=1)
    path = base_dir / "TESTB_NSE_5m.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    # inject out-of-session rows: 09:00 (before open) and 15:30 (at close boundary)
    lines.insert(1, "2024-01-02,09:00:00,100,101,99,100,500.0,0")
    lines.append("2024-01-02,15:30:00,110,111,109,110,500.0,0")
    lines.append("2024-01-02,15:25:00,109,110,108,109,500.0,0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    series = load_hstry_series("TESTB", "5m", base_dir=base_dir)
    stamps = [(b.timestamp_ns // 10**9) % 86400 for b in series.bars]  # seconds-of-UTC-day
    # 09:15 IST = 03:45 UTC = 13500 s ; 15:25 IST = 09:55 UTC = 35700 s
    assert min(stamps) == 13500
    assert max(stamps) == 35700

    # timeframe alias: models tf "3m" must read file token "03m"
    _write_symbol_csv(base_dir, "TESTC", "03m", days=1)
    series_c = load_hstry_series("TESTC", "3m", base_dir=base_dir)
    assert len(series_c.bars) > 0
    assert hstry_csv_path("TESTC", "3m", base_dir=base_dir).name == "TESTC_NSE_03m.csv"

    with pytest.raises(HstryCsvNotFound):
        load_hstry_series("NOSUCH", "5m", base_dir=base_dir)


def _row(symbol: str, window: tuple[str, str], *, comp: float, passes: bool) -> OrbTimingWindowRow:
    return OrbTimingWindowRow(
        symbol=symbol,
        clock_window=window,
        trade_count=50 if passes else 2,
        win_rate=0.5,
        profit_factor=1.2,
        net_r=comp,
        consistency=0.6 if window[1] == "09:20" else 0.4,
        max_drawdown_r=1.0,
        composite_score=comp,
        minimum_trades_pass=passes,
    )


def test_orb_t197_003_aggregator_hand_computed() -> None:
    w20 = ("09:15", "09:20")
    w30 = ("09:15", "09:30")
    rows_by_symbol = {
        "AAA": [_row("AAA", w20, comp=5.0, passes=True), _row("AAA", w30, comp=4.0, passes=True)],
        "BBB": [_row("BBB", w20, comp=3.0, passes=True), _row("BBB", w30, comp=2.8, passes=True)],
        "CCC": [_row("CCC", w20, comp=1.0, passes=False), _row("CCC", w30, comp=0.5, passes=False)],
    }
    leaderboard, counts = tr.aggregate_leaderboard(rows_by_symbol, {"AAA": 100, "BBB": 90, "CCC": 80})
    by_symbol = {e.symbol: e for e in leaderboard}

    aaa = by_symbol["AAA"]
    assert aaa.best_window_composite == w20
    assert aaa.verdict == "OK"  # spread exactly 1.0 R is significant
    assert aaa.best_window_consistency == w20  # consistency 0.6 beats 0.4
    assert aaa.best_window_net_r == w20

    bbb = by_symbol["BBB"]
    assert bbb.verdict == "NO_SIGNIFICANT_DIFFERENCE"  # spread 0.2 < 1.0
    assert bbb.best_window_consistency == w20

    ccc = by_symbol["CCC"]
    assert ccc.verdict == "INSUFFICIENT_DATA"

    assert counts == {"09:15-09:20": 1}


def test_orb_t197_004_checkpoint_resume_and_determinism(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "hstry"
    _write_symbol_csv(base_dir, "TESTD", "5m", days=6, rising=True)
    _write_symbol_csv(base_dir, "TESTE", "5m", days=6, rising=False)

    request = OrbTimingResearchRequest(
        symbols_source="explicit",
        symbols=["TESTD", "TESTE"],
        timeframe="5m",
        clock_windows=[("09:15", "09:20"), ("09:15", "09:30")],
        reward_risk_grid=[2.0],
        volume_confirmation_grid=[False],
        strategy_families=["orb_breakout"],
        minimum_trades=1,
        start_date="2024-01-01",
    )

    calls = {"n": 0}
    real_discovery = tr.run_orb_discovery

    def counting(request_model):
        calls["n"] += 1
        return real_discovery(request_model)

    monkeypatch.setattr(tr, "run_orb_discovery", counting)

    # point checkpoints at tmp so the real data dir is untouched
    monkeypatch.setattr(tr, "_checkpoint_path", lambda h: tmp_path / f"cp_{h[:16]}.json")

    first = tr.run_timing_research(request, base_dir=base_dir)
    assert calls["n"] == 2
    assert set(first.symbols_completed) == {"TESTD", "TESTE"}
    assert len(first.rows) == 4  # 2 symbols x 2 windows
    assert all(row.no_future_leakage for row in first.rows)
    assert first.research_only is True and first.trade_allowed is False
    assert first.live_trading_blocked is True

    second = tr.run_timing_research(request, base_dir=base_dir)
    assert calls["n"] == 2  # resume served everything from checkpoint
    assert second.deterministic_hash == first.deterministic_hash

    payload = json.loads((tmp_path / f"cp_{first.request_hash[:16]}.json").read_text(encoding="utf-8"))
    assert set(payload["rows"]) == {"TESTD", "TESTE"}


# ---------------- M2: persistence + exports (ORB-T197-005..007) ----------------


@pytest.fixture()
def isolated_storage(monkeypatch, tmp_path):
    from app import storage

    db_path = tmp_path / "orb_timing_test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage._INITIALIZED_DB_TARGETS.discard(str(db_path))
    # state.py runs storage.init_db() once at import time against the real DB;
    # an isolated tmp DB must be initialized explicitly or middleware writes fail.
    storage.init_db()
    return storage


def test_orb_t197_005_persistence_round_trip(isolated_storage, tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "hstry"
    _write_symbol_csv(base_dir, "TESTF", "5m", days=6, rising=True)
    request = OrbTimingResearchRequest(
        symbols_source="explicit",
        symbols=["TESTF"],
        clock_windows=[("09:15", "09:20"), ("09:15", "09:30")],
        reward_risk_grid=[2.0],
        volume_confirmation_grid=[False],
        strategy_families=["orb_breakout"],
        minimum_trades=1,
    )
    monkeypatch.setattr(tr, "_checkpoint_path", lambda h: tmp_path / f"cp_{h[:16]}.json")
    result = tr.run_timing_research(request, base_dir=base_dir)

    tr.persist_run(result)
    tr.persist_run(result)  # idempotent by run_id

    fetched = isolated_storage.get_orb_timing_run(result.run_id)
    assert fetched is not None
    assert fetched["deterministic_hash"] == result.deterministic_hash
    assert fetched["trade_allowed"] is False and fetched["live_trading_blocked"] is True
    assert len(fetched["rows"]) == len(result.rows)

    runs = isolated_storage.list_orb_timing_runs(limit=10)
    assert any(r["run_id"] == result.run_id for r in runs)


def test_orb_t197_006_export_csv_byte_stable(isolated_storage, tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "hstry"
    _write_symbol_csv(base_dir, "TESTG", "5m", days=6, rising=True)
    request = OrbTimingResearchRequest(
        symbols_source="explicit",
        symbols=["TESTG"],
        clock_windows=[("09:15", "09:20"), ("09:15", "09:30")],
        reward_risk_grid=[2.0],
        volume_confirmation_grid=[False],
        strategy_families=["orb_breakout"],
        minimum_trades=1,
    )
    monkeypatch.setattr(tr, "_checkpoint_path", lambda h: tmp_path / f"cp_{h[:16]}.json")
    result = tr.run_timing_research(request, base_dir=base_dir)

    first = tr.export_csv_bytes(result)
    second = tr.export_csv_bytes(result)
    assert first == second
    assert first.endswith(b"\n")
    header = first.split(b"\n")[0].decode("utf-8")
    assert header.startswith("symbol,window,family,rr,volume,trades")

    exports = tr.write_run_exports(result, out_dir=tmp_path / "exports")
    assert exports["csv"].read_bytes() == first
    reloaded = json.loads(exports["json"].read_text(encoding="utf-8"))
    assert reloaded["run_id"] == result.run_id
    summary = exports["summary"].read_text(encoding="utf-8")
    assert "TESTG" in summary and "research_only=true" in summary


def test_orb_t197_007_no_leak_and_research_only_persisted(isolated_storage, tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "hstry"
    _write_symbol_csv(base_dir, "TESTH", "5m", days=6, rising=False)
    request = OrbTimingResearchRequest(
        symbols_source="explicit",
        symbols=["TESTH"],
        clock_windows=[("09:15", "09:20"), ("09:15", "09:30"), ("09:15", "09:35")],
        reward_risk_grid=[1.0, 2.0],
        volume_confirmation_grid=[False],
        strategy_families=["orb_breakout", "orr_reversal"],
        minimum_trades=1,
    )
    monkeypatch.setattr(tr, "_checkpoint_path", lambda h: tmp_path / f"cp_{h[:16]}.json")
    result = tr.run_timing_research(request, base_dir=base_dir)
    tr.persist_run(result)

    assert all(row.no_future_leakage for row in result.rows)
    assert len(result.rows) == 3  # symbols x windows
    assert result.order_routing_enabled is False

    stored = isolated_storage.get_orb_timing_run(result.run_id)
    assert stored["research_only"] is True
    assert stored["order_routing_enabled"] is False

    with isolated_storage.connect() as conn:
        flags = conn.execute(
            "SELECT DISTINCT no_future_leakage FROM orb_timing_rows WHERE run_id = ?",
            (result.run_id,),
        ).fetchall()
    assert [dict(f)["no_future_leakage"] for f in flags] == [1]


# ---------------- M3: API surface (ORB-T197-008..010) ----------------


def test_orb_t197_008_api_submit_poll_result(tmp_path, monkeypatch, isolated_storage) -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    base_dir = tmp_path / "hstry"
    _write_symbol_csv(base_dir, "TESTI", "5m", days=6, rising=True)
    monkeypatch.setattr(tr, "_checkpoint_path", lambda h: tmp_path / f"cp_{h[:16]}.json")
    # keep job-side exports (persist + write_run_exports) inside tmp
    monkeypatch.setattr(tr, "_DATA_DIR", tmp_path / "exports_default")

    client = TestClient(app)
    payload = {
        "symbols_source": "explicit",
        "symbols": ["TESTI"],
        "timeframe": "5m",
        "clock_windows": [["09:15", "09:20"], ["09:15", "09:30"]],
        "reward_risk_grid": [2.0],
        "volume_confirmation_grid": [False],
        "strategy_families": ["orb_breakout"],
        "minimum_trades": 1,
    }

    def _patched_load(symbol, timeframe="5m", **kwargs):
        kwargs.pop("base_dir", None)
        return tr.load_hstry_series(symbol, timeframe, base_dir=base_dir, **kwargs)

    monkeypatch.setattr(tr, "load_hstry_series", _patched_load)

    submit_response = client.post("/api/v1/orb/timing-research", json=payload)
    assert submit_response.status_code == 200
    envelope = submit_response.json()
    job = envelope["data"]
    assert job["status"] in {"queued", "running", "completed"}
    assert job["research_only"] is True and job["live_trading_blocked"] is True

    job_id = job["job_id"]
    status_response = client.get(f"/api/v1/orb/timing-research/jobs/{job_id}")
    assert status_response.status_code == 200

    # background task runs synchronously under TestClient when the response returns
    final = client.get(f"/api/v1/orb/timing-research/jobs/{job_id}").json()["data"]
    if final["status"] == "completed":
        assert final["result"]["run_id"]
        run_id = final["result"]["run_id"]
        runs = client.get("/api/v1/orb/timing-research/runs?limit=5")
        assert runs.status_code == 200
        csv_response = client.get(f"/api/v1/orb/timing-research/runs/{run_id}/export.csv")
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"].startswith("text/csv")
        assert b"symbol,window,family" in csv_response.content
    else:
        assert final["error"] is not None or final["status"] in {"queued", "running"}

    missing = client.get("/api/v1/orb/timing-research/jobs/nonexistent-job")
    assert missing.status_code == 404
    missing_run = client.get("/api/v1/orb/timing-research/runs/nonexistent-run")
    assert missing_run.status_code == 404


def test_orb_t197_009_trendforge_symbol_source(monkeypatch, isolated_storage) -> None:
    fake_intake = {
        "packet": {
            "evidence": {
                "candidates": [
                    {"symbol": "RELIANCE", "state": "READY"},
                    {"symbol": "SBIN", "state": "PRIORITY_RADAR"},
                    {"symbol": "SKIPME", "state": "WATCH"},
                ]
            }
        }
    }
    monkeypatch.setattr(isolated_storage, "list_trendforge_intakes", lambda limit=5: [fake_intake])
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    symbols = tr.resolve_symbols(request)
    assert symbols == ["RELIANCE", "SBIN"]


def test_orb_t197_010_index_entries_exist() -> None:
    docs = Path(__file__).resolve().parents[3] / "docs"
    api_index = (docs / "API_ENDPOINT_INDEX.md").read_text(encoding="utf-8")
    panel_map = (docs / "FRONTEND_PANEL_MAP.md").read_text(encoding="utf-8")
    assert "/api/v1/orb/timing-research" in api_index
    assert "ORB Timing Lab" in panel_map
