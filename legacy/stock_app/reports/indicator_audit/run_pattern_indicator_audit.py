from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "indicator_audit"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reports.indicator_audit.run_10_indicator_readiness import load_infy_5m
from shared.indicators.self_indc import compute_all

INDICATORS = {
    "si_outside_rev": ("Outside Reversal", "pattern", "filter only"),
    "si_three_inside": ("Three Inside", "pattern", "filter only"),
    "si_dark_cloud": ("Dark Cloud/Piercing", "pattern", "filter only"),
    "si_vol_exh": ("Vol Exhaustion", "volume", "filter only"),
    "si_rsi_div": ("RSI Divergence", "momentum", "subpanel/filter"),
    "si_cpr": ("CPR Levels", "trend", "levels only"),
    "si_swing_str": ("Swing Structure", "pattern", "filter only"),
    "si_bos": ("BOS", "pattern", "filter only"),
    "si_choch": ("CHoCH", "pattern", "filter only"),
    "si_inside_out": ("Inside/Outside Bar", "pattern", "filter only"),
    "si_sfp": ("SFP", "pattern", "filter only"),
    "si_cdl_mb": ("CDL Multi-Bar", "pattern", "filter only"),
    "si_fractal": ("Fractal H/L", "pattern", "filter only"),
    "si_bb_break": ("BB Breakout", "volatility", "setup only"),
    "si_bahai": ("Bahai Reversal", "pattern", "filter only"),
    "si_hs": ("Head & Shoulders", "pattern", "filter only"),
    "si_dbl": ("Double Top/Bottom", "pattern", "filter only"),
    "si_rev_radar": ("Reversal Radar", "momentum", "filter only"),
    "si_nbar": ("N-Bar Reversal", "pattern", "filter only"),
    "si_impulse": ("Impulse Trend BOS", "pattern", "filter only"),
    "si_hourly_pvt": ("Hourly Pivots", "trend", "levels only"),
    "si_fib": ("Fibonacci Levels", "trend", "filter only"),
}


def _session_open_times(index: pd.DatetimeIndex) -> set[str]:
    out = set()
    for i, ts in enumerate(index):
        if i == 0 or index[i - 1].date() != ts.date():
            out.add(ts.strftime("%Y-%m-%d %H:%M"))
    return out


def _events_from_payload(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("signals"), list):
        return [x for x in payload["signals"] if isinstance(x, dict)]
    return []


def _has_visual(payload) -> bool:
    if isinstance(payload, list):
        return len(payload) > 0
    if isinstance(payload, dict):
        if payload.get("signals"):
            return True
        for value in payload.values():
            if isinstance(value, list) and len(value) > 0:
                return True
            if value not in (None, "", [], {}):
                return True
    return False


def audit() -> dict:
    df = load_infy_5m().tail(12000)
    payload = compute_all(df.rename(columns={
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
    }))
    open_times = _session_open_times(df.index)
    rows = []
    for key, (label, category, role) in INDICATORS.items():
        value = payload.get(key)
        events = _events_from_payload(value)
        by_time = {}
        for event in events:
            by_time.setdefault(event.get("time"), set()).add(event.get("direction"))
        conflicts = sum(1 for dirs in by_time.values() if "bull" in dirs and "bear" in dirs)
        first_open = sum(1 for event in events if event.get("time") in open_times)
        status = "PASS"
        issues = []
        if not _has_visual(value):
            status = "CHECK"
            issues.append("no visual output in tested window")
        if first_open:
            status = "FAIL"
            issues.append(f"{first_open} first-candle markers")
        if conflicts:
            status = "FAIL"
            issues.append(f"{conflicts} bull+bear same candle conflicts")
        if len(events) > len(df) * 0.10:
            status = "CHECK"
            issues.append("too many markers; use as filter only")
        rows.append({
            "key": key,
            "indicator": label,
            "category": category,
            "trader_role": role,
            "status": status,
            "events": len(events),
            "first_candle_events": first_open,
            "same_candle_conflicts": conflicts,
            "has_visual_output": _has_visual(value),
            "issue": "; ".join(issues),
            "action_done": "sanitized, cooldown, no first session candle, no bull+bear same candle",
        })
    return {
        "symbol": "INFY",
        "tf": "5m_from_1m",
        "rows": len(df),
        "start": str(df.index[0]),
        "end": str(df.index[-1]),
        "indicators": rows,
    }


def main() -> None:
    result = audit()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / "INFY_5m_pattern_indicator_audit.csv"
    out_json = OUT_DIR / "INFY_5m_pattern_indicator_audit.json"
    out_md = OUT_DIR / "INFY_5m_pattern_indicator_audit.md"
    rows = result["indicators"]
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# INFY 5m Pattern/Structure Indicator Production Audit",
        "",
        f"Rows tested: {result['rows']}",
        f"Range: {result['start']} to {result['end']}",
        "",
        "Rule: no duplicate junk, no first-candle marker, no same-candle buy+sell. These are filters/visuals unless backtest gates pass.",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['indicator']}: {row['status']} events={row['events']} "
            f"first={row['first_candle_events']} conflict={row['same_candle_conflicts']} role={row['trader_role']} issue={row['issue'] or '-'}"
        )
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "rows": result["rows"],
        "pass": sum(1 for r in rows if r["status"] == "PASS"),
        "check": sum(1 for r in rows if r["status"] == "CHECK"),
        "fail": sum(1 for r in rows if r["status"] == "FAIL"),
        "csv": str(out_csv.resolve()),
        "md": str(out_md.resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
