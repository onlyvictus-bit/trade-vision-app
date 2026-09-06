"""v1.99 flow re-audit: run the FULL D1-D8 spine on real HSTRY data and
observe every stage receipt — the definitive 'flow from the start' check."""

import sys

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

from app.behavior.paper_guidance_spine import run_paper_guidance_p1
from app.models import PaperGuidanceRequest
from app.orb.hstry_csv import load_hstry_series
from app.state import KILL_SWITCH, SYSTEM_MODE

# --- Block 1: GIVE IT MARKET DATA (real HSTRY 5m bars, bounded per D1-005) ---
import sys

SYMBOL = (sys.argv[1] if len(sys.argv) > 1 else "RELIANCE").strip().upper()

series = load_hstry_series(SYMBOL, "5m", max_bars=5000)
print(f"BLOCK 1 data: {series.symbol} {series.timeframe} bars={len(series.bars)} "
      f"first_ts={series.bars[0].timestamp_ns}")

request = PaperGuidanceRequest(
    symbol=SYMBOL,
    timeframe="5m",
    series=series,
    direction="long",
)

# --- Blocks 2-9: the spine runs D1..D8 ---
guidance = run_paper_guidance_p1(request, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH)

print("\n=== BLOCK 2: D1 SAFETY GATE ===")
gate = guidance.safety_gate
print(f"passed={gate.passed}")
for check in gate.checks:
    mark = "PASS" if check.passed else "FAIL"
    print(f"  [{mark}] {check.check_id}: {check.name} ({check.severity}) :: {check.evidence}")

print("\n=== BLOCK 2: D2 SNAPSHOT ===")
print(f"snapshot_id={guidance.snapshot.snapshot_id if guidance.snapshot else None}")
print(f"snapshot_hash={guidance.snapshot_hash}")

print("\n=== BLOCKS 3-6: ENGINE RECEIPTS ===")
for r in guidance.engine_receipts:
    print(f"  {r.engine_id:22s} stage={r.stage:12s} status={r.status}")

print("\n=== BLOCK 7-8: FINAL RESULT ===")
print(f"final_band   = {guidance.final_band}")
print(f"research_only={guidance.research_only} trade_allowed={guidance.trade_allowed} "
      f"live_trading_blocked={guidance.live_trading_blocked}")
if guidance.blockers:
    print(f"blockers: {guidance.blockers}")
print(f"warnings: {len(guidance.warnings)}")
