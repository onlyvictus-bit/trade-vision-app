"""Stock verification: run the full Trade Vision flow for one symbol on real
HSTRY data and print the result at EVERY step.

Usage: python scripts/stock_verify.py [SYMBOL]   (default TCS)
"""

import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

SYMBOL = (sys.argv[1] if len(sys.argv) > 1 else "TCS").strip().upper()
IST = timezone(timedelta(hours=5, minutes=30))

print(f"{'=' * 64}")
print(f"STEP-BY-STEP VERIFICATION: {SYMBOL}")
print(f"{'=' * 64}")

# ---- STEP 1: BLOCK 1 - market data in ----
print("\n[STEP 1] BLOCK 1 - load real HSTRY data (5m, bounded 5000)")
t0 = time.time()
from app.orb.hstry_csv import load_hstry_series

series = load_hstry_series(SYMBOL, "5m", max_bars=5000)
first_day = datetime.fromtimestamp(series.bars[0].timestamp_ns / 1e9, tz=IST).date()
last_day = datetime.fromtimestamp(series.bars[-1].timestamp_ns / 1e9, tz=IST).date()
print(f"  OK  bars={len(series.bars)}  range={first_day} .. {last_day}  ({time.time() - t0:.1f}s)")

# ---- STEP 2: BLOCK 2 - D1 safety gate ----
print("\n[STEP 2] BLOCK 2 - D1 safety gate (9 checks)")
from app.behavior.paper_guidance_spine import run_paper_guidance_p1
from app.models import PaperGuidanceRequest
from app.state import KILL_SWITCH, SYSTEM_MODE

req = PaperGuidanceRequest(symbol=SYMBOL, timeframe="5m", series=series, direction="long")
g = run_paper_guidance_p1(req, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH)
gate = g.safety_gate
for check in gate.checks:
    print(f"  [{'PASS' if check.passed else 'FAIL'}] {check.check_id} :: {check.evidence[:110]}")
print(f"  D1 passed={gate.passed}")

if not gate.passed:
    print("\n  Flow correctly STOPPED at D1 (fail -> WAIT). Blockers:")
    for b in g.blockers:
        print(f"    - {b[:130]}")
    sys.exit(0)

# ---- STEP 3: BLOCK 2 - D2 snapshot ----
print("\n[STEP 3] BLOCK 2 - D2 closed-candle snapshot")
print(f"  OK  snapshot_id={g.snapshot.snapshot_id}")
print(f"  OK  snapshot_hash={g.snapshot_hash[:24]}... (immutable, PIT)")

# ---- STEP 4: BLOCKS 3-6 - engines ----
print("\n[STEP 4] BLOCKS 3-6 - engine receipts")
completed = degraded = 0
for r in g.engine_receipts:
    print(f"  {r.engine_id:30s} {r.stage:12s} {r.status}")
    completed += r.status == "completed"
    degraded += r.status == "degraded"
print(f"  -> {completed} completed, {degraded} degraded (degraded reasons are disclosed in warnings)")
for r in g.engine_receipts:
    if r.status == "degraded":
        for w in r.warnings[:2]:
            print(f"     degraded note: {w[:130]}")

# ---- STEP 5: BLOCKS 7-8 - final result ----
print("\n[STEP 5] BLOCKS 7-8 - final result")
print(f"  final_band={g.final_band}  research_only={g.research_only}  live_trading_blocked={g.live_trading_blocked}")
for b in g.blockers:
    print(f"  blocker: {b[:130]}")

# ---- STEP 5b: FULL DESIGNED OUTPUT (the Jarvis ticket) ----
print("\n[STEP 5b] FULL DESIGNED OUTPUT (every field the flow produces)")
d = g.model_dump()

def _get(path, obj=None):
    cur = obj if obj is not None else d
    for key in path.split("."):
        if cur is None:
            return None
        cur = cur.get(key) if isinstance(cur, dict) else getattr(cur, key, None)
    return cur

print("  ACTION      :", d.get("final_band"), "| next_action:", d.get("next_action"))
cc = _get("engine_receipts") or []
def _summary(engine_id):
    for r in cc:
        if r["engine_id"] == engine_id:
            return r.get("output_summary") or {}
    return {}
chart = _summary("CHART_REASONING")
candle = _summary("CANDLE_CONDITION")
levels = _summary("LEVEL_CONTEXT")
struct = _summary("MARKET_STRUCTURE_LIQUIDITY")
exec_risk = _summary("EXECUTION_EVENT_OI_RISK")
arb = _summary("FINAL_CONFLUENCE_ARBITER")
mtf = _summary("MTF_CONFIRMATION")
memory = _summary("PERSISTED_INDICATOR_MEMORY")
snap = _summary("SNAPSHOT_INDICATOR_RUNTIME")

print("  DIRECTION   :", "market_state=", candle.get("market_state"),
      "| signal_bias=", candle.get("signal_bias"),
      "| trend_health=", chart.get("trend_health"),
      "| chop_risk=", chart.get("chop_risk"))
print("  MTF         :", "confirmed=", mtf.get("confirmed"),
      "| usable=", mtf.get("usable_timeframes"),
      "| missing=", mtf.get("missing_required_timeframes"))
print("  LEVELS      :", "vwap_state=", levels.get("vwap_state"),
      "| opening_range=", levels.get("opening_range_state"),
      "| level_respect=", levels.get("level_respect_score"))
print("  STRUCTURE   :", "auction=", struct.get("auction_state"),
      "| profile=", struct.get("profile_shape"),
      "| value_area=", struct.get("value_area_position"),
      "| trap_score=", struct.get("trap_score"))
print("  EXECUTION   :", "liquidity_grade=", exec_risk.get("liquidity_grade"),
      "| fill_prob=", exec_risk.get("fill_probability"),
      "| slippage_risk=", exec_risk.get("slippage_risk"))
print("  INDICATORS  :", "computed=", snap.get("computed_count"),
      "of", len(snap.get("promoted_indicator_ids") or []),
      "| window_bars=", snap.get("compute_window_bars"))
print("  HISTORY     :", "matches=", memory.get("historical_match_count"),
      "| low_evidence=", memory.get("low_evidence_flag"),
      "| source=", memory.get("history_source"))
print("  CONFIDENCE  :", "confluence_score=", arb.get("confluence_score"),
      "| confidence_cap=", d.get("confidence_cap"),
      "| dominant_blocker=", arb.get("dominant_blocker"))
print("  REASON FOR  :", str(d.get("reason_for"))[:160])
print("  REASON AGAINST:", str(d.get("reason_against"))[:160])
ep = d.get("entry_plan")
print("  ENTRY PLAN  :", str(ep)[:200] if ep else "None (needs proven playbook + evidence)")
print("  VOLATILITY  :", "regime=", chart.get("volatility_regime"),
      "| persistence=", chart.get("trend_persistence_score"))

# ---- STEP 6: ORB playbook status ----
print("\n[STEP 6] ORB playbook status (v1.92 guidance path)")
from app.behavior.orb_guidance import run_paper_guidance_with_orb

g2 = run_paper_guidance_with_orb(req, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH)
ticket = g2.orb_ticket
if ticket is None:
    print(f"  orb_ticket=None  -> no active playbook for {SYMBOL} (expected for non-proven stocks)")
else:
    d = ticket.model_dump()
    print(f"  orb_ticket present: playbook={d.get('playbook_id')}")
    for k in ("signal_type", "side", "entry_price", "stop_price", "target_price"):
        if k in d:
            print(f"    {k} = {d[k]}")
print(f"  final_band={g2.final_band}")

# ---- STEP 7: ORB timing research (per-stock window answer) ----
print("\n[STEP 7] ORB timing research - which window wins for this stock? (4 windows, 5m)")
from app.models import OrbDiscoveryRequest, OrbTimingWindowRow
from app.orb.discovery import run_orb_discovery

t0 = time.time()
discovery_request = OrbDiscoveryRequest(
    series=series,
    strategy_families=["orb_breakout", "orr_reversal", "hybrid_orb"],
    orb_bar_counts=[3],
    clock_windows=[("09:15", "09:20"), ("09:15", "09:30"), ("09:15", "09:35"), ("09:15", "09:40")],
    reward_risk_grid=[1.0, 2.0, 3.0],
    volume_confirmation_grid=[False, True],
    maximum_combinations=250,
    minimum_trades=10,
)
discovery = run_orb_discovery(discovery_request)
print(f"  computed in {time.time() - t0:.0f}s  no_future_leakage={discovery.no_future_leakage}")
ranked = [m.model_dump() for m in discovery.ranked_combinations]

by_window: dict[tuple, list] = {}
for m in ranked:
    if m.get("minimum_trades_pass") and m.get("clock_window"):
        by_window.setdefault(tuple(m["clock_window"]), []).append(m)
print(f"  {'window':16s} {'best_pf':>8s} {'net_r':>8s} {'trades':>7s} {'consistency':>11s} {'family':>14s}")
for w in discovery_request.clock_windows:
    rows = by_window.get(tuple(w)) or []
    if not rows:
        print(f"  {w[0]}-{w[1]:8s} {'-':>8s} {'-':>8s} {'-':>7s} {'-':>11s} {'insufficient':>14s}")
        continue
    best = max(rows, key=lambda m: m["composite_score"])
    print(f"  {w[0]}-{w[1]:8s} {best['profit_factor']:8.2f} {best['net_r']:8.2f} {best['trade_count']:7d} "
          f"{best['profitable_period_rate']:11.2f} {best['strategy_family']:>14s}")
winner = max(
    (max(rows, key=lambda m: m["composite_score"]) for rows in by_window.values() if rows),
    key=lambda m: m["composite_score"],
    default=None,
)
if winner:
    print(f"\n  ANSWER for {SYMBOL}: best window = {winner['clock_window'][0]}-{winner['clock_window'][1]} "
          f"(composite {winner['composite_score']:.2f})")
    print(f"  promotion note: research answer only - walk-forward prove required before any playbook")

print(f"\n{'=' * 64}")
print(f"VERIFICATION COMPLETE: {SYMBOL}")
print(f"{'=' * 64}")
