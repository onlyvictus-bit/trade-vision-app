"""Show the ORB working + thinking, live on real HSTRY data.

Prints each thinking step: data -> opening classification (v2.01) ->
OR lock + signal (v1.89 core) -> mini discovery (v1.90) ->
playbook match (v1.91/92) -> v2 preview (what M1/M2 would add, NOT enforced).

Usage: python scripts/show_orb_thinking.py [SYMBOL]  (default BEL)
"""

import sys
import time

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

import pandas as pd

from app.models import OrbBuildRequest, OrbDiscoveryRequest, OrbStrategyConfig
from app.orb import context as C
from app.orb.core import build_orb_candidate
from app.orb.discovery import run_orb_discovery
from app.orb.hstry_csv import load_hstry_series
from app.orb.proof import list_orb_playbooks

SYMBOL = (sys.argv[1] if len(sys.argv) > 1 else "BEL").strip().upper()
t0 = time.time()
print(f"{'=' * 66}\nORB THINKING TRACE: {SYMBOL} (real HSTRY 5m)\n{'=' * 66}")

# ---- STEP 1: data ----
series = load_hstry_series(SYMBOL, "5m", start_date="2025-06-01")
frame = pd.DataFrame(
    [{"open": b.open, "high": b.high, "low": b.low, "close": b.close,
      "volume": b.volume or 0.0} for b in series.bars],
    index=pd.to_datetime([b.timestamp_ns for b in series.bars]),
)
frame.index = frame.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
print(f"\n[1] DATA IN: {len(series.bars)} bars, "
      f"{frame.index[0].date()} .. {frame.index[-1].date()}")

# ---- STEP 2: opening classification (v2.01 brain) ----
daily = C.daily_from_intraday(frame)
dates = sorted({ts.strftime("%Y-%m-%d") for ts in frame.index})
opens = {}
for d in dates:
    bars = frame[frame.index.strftime("%Y-%m-%d") == d]
    if len(bars):
        opens[d] = float(bars.iloc[0]["open"])
records = C.classify_history(SYMBOL, daily, opens)
last = records[-1]
pred = C.predict_day_type(last)
print(f"[2] OPENING READ ({last['session_date']}): gap={last['gap_state']} "
      f"({last['gap_pct']:+.2f}%) | CPR={last['cpr_class']} "
      f"(width {last['width_atr']:.2f}xATR) | zone={last['zone_at_open']}")
print(f"    day-type guess: {pred['prediction']} {pred['direction']} "
      f"({' + '.join(pred['reasons'])[:110]})")

# ---- STEP 3: OR lock + signal (v1.89 core brain) ----
last_day = max(dates)
day_bars = [b for b in series.bars
            if pd.Timestamp(b.timestamp_ns, unit="ns", tz="UTC").tz_convert("Asia/Kolkata").strftime("%Y-%m-%d") == last_day]
from app.models import CandleSeries
day_series = CandleSeries(symbol=SYMBOL, timeframe="5m", bars=day_bars,
                          snapshot_id="demo", schema_version="candles.v1")
req = OrbBuildRequest(
    series=day_series,
    decision_time_ns=day_bars[-1].timestamp_ns,
    config=OrbStrategyConfig(
        strategy_family="orb_breakout", range_mode="clock_window",
        range_start="09:15", range_end="09:20", reward_risk_ratio=2.0),
)
cand = build_orb_candidate(req)
orr = cand.opening_range
sig = cand.signal
print(f"[3] OR LOCK ({last_day}): ORH={orr.opening_range_high:.2f} "
      f"ORL={orr.opening_range_low:.2f} locked={orr.locked}")
print(f"    SIGNAL: {sig.signal_type} side={sig.side}")

# ---- STEP 4: mini discovery (v1.90 brain, 1 combo, fast) ----
mini = OrbDiscoveryRequest(
    series=series, strategy_families=["orb_breakout"], orb_bar_counts=[3],
    clock_windows=[("09:15", "09:20")], reward_risk_grid=[2.0],
    volume_confirmation_grid=[False], maximum_combinations=10, minimum_trades=5)
t1 = time.time()
mini_result = run_orb_discovery(mini)
best = mini_result.best_composite
print(f"[4] MINI-DISCOVERY ({time.time() - t1:.0f}s): "
      f"{mini_result.combination_count} combos ranked, "
      f"best net_r={best.net_r:.2f} pf={best.profit_factor:.2f} "
      f"trades={best.trade_count}" if best else "[4] MINI-DISCOVERY: no combo passed")

# ---- STEP 5: playbook match (v1.91/92 memory) ----
pbs = [p for p in list_orb_playbooks() if p.symbol == SYMBOL]
if pbs:
    pb = pbs[0]
    print(f"[5] PLAYBOOK MATCH: {pb.playbook_id[:8]}... window="
          f"{pb.config.range_start}-{pb.config.range_end} RR={pb.config.reward_risk_ratio} "
          f"family={pb.config.strategy_family}")
else:
    print(f"[5] PLAYBOOK MATCH: none for {SYMBOL} (research-only; needs prove+promote)")

# ---- STEP 6: v2 preview (NOT enforced - shows what M1/M2 would add) ----
gap, cpr = last["gap_state"], last["cpr_class"]
would = []
if gap.startswith("LARGE"):
    would.append("GAP-02 trap protocol would arm (trend-vs-fill branch)")
if cpr == "NARROW":
    would.append("CPR-02 would switch breakouts ON, reversals OFF")
elif cpr == "WIDE":
    would.append("CPR-02 would switch reversals ON, cap targets 1.5R")
if last["zone_at_open"] == "Z3":
    would.append("Z3 rule would veto breakouts (inside-CPR no-man's land)")
print("[6] V2 PREVIEW (spec only, not enforced):")
for w in would or ["no v2 gate would fire on this open"]:
    print(f"    - {w}")

print(f"\n{'=' * 66}\nTRACE COMPLETE in {time.time() - t0:.0f}s\n{'=' * 66}")
