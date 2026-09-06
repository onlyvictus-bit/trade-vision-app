"""v2.01 ORB opening-scenario gates (TV-V201-001..006).

Every opening possibility classified explicitly: gap direction/size x
position vs prev-day levels x CPR width class. Unit boundaries + real HSTRY
coverage proof. Hermetic except the real-data invariant (read-only HSTRY).
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.behavior.context_engines import _gap_type
from app.models import OrbOpeningScenario
from app.orb import context as C
from app.orb.hstry_csv import load_hstry_series


def _scenario(**kwargs):
    base = dict(
        symbol="TEST",
        session_date="2024-01-02",
        prev_high=1010.0,
        prev_low=995.0,
        prev_close=1002.0,
        today_open=1003.0,
        atr14=12.0,
    )
    base.update(kwargs)
    return C.classify_opening(**base)


def _scenario_dict(**kwargs):
    return {
        "gap_state": "FLAT", "cpr_class": "NORMAL", "zone_at_open": "Z2",
        "context_suspect": False, "suspect_reason": None, **kwargs,
    }


def test_tv_v201_007_predict_day_type_branches() -> None:
    large = C.predict_day_type(_scenario_dict(gap_state="LARGE_GAP_UP"))
    assert large["prediction"] == "TREND_DAY" and large["direction"] == "up"
    assert any("GAP-02" in r for r in large["reasons"])
    large_down = C.predict_day_type(_scenario_dict(gap_state="LARGE_GAP_DOWN"))
    assert large_down["prediction"] == "TREND_DAY" and large_down["direction"] == "down"
    inside = C.predict_day_type(_scenario_dict(zone_at_open="Z3"))
    assert inside["prediction"] == "RANGE_DAY"
    narrow = C.predict_day_type(_scenario_dict(gap_state="FLAT", cpr_class="NARROW"))
    assert narrow["prediction"] == "TREND_DAY" and narrow["direction"] == "either"
    narrow_long = C.predict_day_type(_scenario_dict(gap_state="GAP_UP", cpr_class="NARROW"))
    assert narrow_long["direction"] == "up"
    wide = C.predict_day_type(_scenario_dict(cpr_class="WIDE"))
    assert wide["prediction"] == "RANGE_DAY"
    plain = C.predict_day_type(_scenario_dict())
    assert plain["prediction"] == "UNCLASSIFIED"
    suspect = C.predict_day_type(_scenario_dict(context_suspect=True, suspect_reason="x"))
    assert suspect["prediction"] == "UNCLASSIFIED"


def test_tv_v201_008_label_day_outcome_boundaries() -> None:
    assert C.label_day_outcome(day_high=110.0, day_low=100.0, day_close=108.0, atr14=10.0) == "TREND_DAY"
    assert C.label_day_outcome(day_high=110.0, day_low=100.0, day_close=102.0, atr14=10.0) == "TREND_DAY"
    assert C.label_day_outcome(day_high=110.0, day_low=100.0, day_close=105.0, atr14=10.0) == "MIXED"
    assert C.label_day_outcome(day_high=105.0, day_low=100.0, day_close=103.0, atr14=10.0) == "RANGE_DAY"
    assert C.label_day_outcome(day_high=110.0, day_low=100.0, day_close=105.0, atr14=0.0) == "MIXED"


def test_tv_v201_001_gap_boundaries() -> None:
    assert _scenario(today_open=1002.5)["gap_state"] == "FLAT"          # +0.05%
    assert _scenario(today_open=1007.0)["gap_state"] == "GAP_UP"        # +0.50%
    assert _scenario(today_open=997.0)["gap_state"] == "GAP_DOWN"       # -0.50%
    assert _scenario(today_open=1022.0)["gap_state"] == "LARGE_GAP_UP"  # +1.996% over max(1, 1.68)
    assert _scenario(today_open=982.0)["gap_state"] == "LARGE_GAP_DOWN"
    # small ATR lowers nothing below the 1.0 floor
    assert _scenario(today_open=1014.0, atr14=5.0)["gap_state"] == "LARGE_GAP_UP"  # +1.196% over 1.0
    assert _scenario(today_open=1007.0, atr14=5.0)["gap_state"] == "GAP_UP"


def test_tv_v201_002_cpr_precedence_partition() -> None:
    assert C.cpr_class(0.11, 0.13) == "NARROW"
    assert C.cpr_class(0.67, 0.81) == "WIDE"     # B3 case: wide via width_pct
    assert C.cpr_class(0.67, 0.40) == "NORMAL"
    # precedence: NARROW checked first even when width_pct screams WIDE
    assert C.cpr_class(0.30, 0.90) == "NARROW"
    assert C.cpr_class(1.20, 0.10) == "WIDE"     # wide via width_atr
    pivot, tc, bc = C.cpr_levels(1010.0, 995.0, 1002.0)
    assert tc < bc and pivot == pytest.approx(1002.3333, abs=1e-3)


def test_tv_v201_003_zones_exclusive_partition() -> None:
    pdh, pdl, tc, bc = 1010.0, 995.0, 1000.0, 1005.0
    assert C.zone_at(1010.0, pdh, pdl, tc, bc) == "Z1"
    assert C.zone_at(1015.0, pdh, pdl, tc, bc) == "Z1"
    assert C.zone_at(1005.0, pdh, pdl, tc, bc) == "Z2"
    assert C.zone_at(1007.0, pdh, pdl, tc, bc) == "Z2"
    assert C.zone_at(1000.0, pdh, pdl, tc, bc) == "Z3"
    assert C.zone_at(1002.0, pdh, pdl, tc, bc) == "Z3"
    assert C.zone_at(995.0, pdh, pdl, tc, bc) == "Z4"
    assert C.zone_at(997.0, pdh, pdl, tc, bc) == "Z4"
    assert C.zone_at(990.0, pdh, pdl, tc, bc) == "Z5"


def test_tv_v201_004_gap_parity_with_repo_classifier() -> None:
    cases = [
        (0.05, 1.0), (-0.05, 1.0), (0.5, 1.0), (-0.5, 2.0),
        (1.68, 1.2), (-1.68, 1.2), (2.5, 1.0), (-0.3, 0.4),
        (0.09, 5.0), (1.0, 0.5), (0.0, 1.0),
    ]
    mapping = {"flat_gap": "FLAT", "gap_up": "GAP_UP", "gap_down": "GAP_DOWN"}
    for gap_pct, atr_pct in cases:
        ours = C.gap_state(gap_pct, atr_pct)
        # _gap_type takes the ATR *value*; atr_pct% of close 1000 => value atr_pct*10
        theirs = _gap_type(gap_pct, atr_pct * 10.0, 1000.0)
        expected = mapping.get(theirs, "LARGE")
        mine = "LARGE" if ours.startswith("LARGE") else ours
        assert mine == expected, (gap_pct, atr_pct, ours, theirs)


def test_tv_v201_005_suspect_guards() -> None:
    bad_gap = _scenario(today_open=1300.0)
    assert bad_gap["context_suspect"] is True and "corporate_action" in bad_gap["suspect_reason"]
    flat_day = _scenario(prev_high=1000.0, prev_low=1000.0, prev_close=1000.0)
    assert flat_day["context_suspect"] is True and "degenerate" in flat_day["suspect_reason"]
    zero_atr = _scenario(atr14=0.0)
    assert zero_atr["context_suspect"] is True  # no ZeroDivisionError
    clean = _scenario()
    assert clean["context_suspect"] is False
    OrbOpeningScenario.model_validate(clean)


def test_tv_v201_006_real_data_partition_invariant_and_coverage() -> None:
    gap_states: set[str] = set()
    classes: set[str] = set()
    zones: set[str] = set()
    total = 0
    for symbol in ("RELIANCE", "BEL", "TCS"):
        series = load_hstry_series(symbol, "5m", start_date="2024-01-01")
        frame = pd.DataFrame(
            [
                {
                    "open": b.open, "high": b.high, "low": b.low,
                    "close": b.close, "volume": b.volume or 0.0,
                }
                for b in series.bars
            ],
            index=pd.to_datetime([b.timestamp_ns for b in series.bars]),
        )
        frame.index = (frame.index.tz_localize("UTC") if frame.index.tz is None else frame.index).tz_convert("Asia/Kolkata")
        daily = C.daily_from_intraday(frame)
        session_dates = sorted({ts.strftime("%Y-%m-%d") for ts in frame.index})
        opens = {d: float(frame.loc[d].iloc[0]["open"]) for d in session_dates if d in set(frame.index.strftime("%Y-%m-%d"))}
        records = C.classify_history(symbol, daily, opens)
        assert records, f"no classified sessions for {symbol}"
        for r in records:
            OrbOpeningScenario.model_validate(r)  # every record fits the contract
            assert r["gap_state"] in {"FLAT", "GAP_UP", "GAP_DOWN", "LARGE_GAP_UP", "LARGE_GAP_DOWN"}
            assert r["cpr_class"] in {"NARROW", "NORMAL", "WIDE"}
            assert r["zone_at_open"] in {"Z1", "Z2", "Z3", "Z4", "Z5"}
            gap_states.add(r["gap_state"].split("_")[-1] if r["gap_state"] != "FLAT" else "FLAT")
            classes.add(r["cpr_class"])
            zones.add(r["zone_at_open"])
            total += 1
    print(f"\ncoverage over {total} sessions: gaps={sorted(gap_states)} classes={sorted(classes)} zones={sorted(zones)}")
    assert {"FLAT", "UP", "DOWN"} <= gap_states
    # 2026-08-26 observation: on RELIANCE/BEL/TCS, median width_atr is 0.147 -
    # NARROW (<0.5) absorbs ~97% of days, so NORMAL is data-absent here.
    # NORMAL reachability is proven by construction in test 002; threshold
    # calibration belongs to discovery (memo CPR-04/H3), not to this gate.
    assert {"NARROW", "WIDE"} <= classes
    assert len(zones) >= 4
