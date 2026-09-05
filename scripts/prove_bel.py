"""Prove the BEL 09:15-09:20 ORB combo (v1.99 campaign).

Re-runs the exact BEL discovery from run d70a4a6a, then applies the v1.91
proof layer: chronological 75/25 train/holdout split + 4 walk-forward folds +
thresholds. Prints decisive tokens for the GATES.md ledger.

Research-only: the proof can gate promotion eligibility, never trade.
"""

import sys

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

from app.models import OrbDiscoveryRequest, OrbProofRequest
from app.orb import run_orb_proof
from app.orb.discovery import run_orb_discovery
from app.orb.hstry_csv import load_hstry_series

SYMBOL = "BEL"

series = load_hstry_series(SYMBOL, "5m", start_date="2024-01-01")
print(f"DATA {SYMBOL} 5m bars={len(series.bars)}")

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
best = discovery.best_composite
if best is None:
    print("PROOF_COMPLETE")
    print("ELIGIBLE_COMBOS=0")
    print("VERDICT=BLOCKED")
    print("REASON=no discovery combo passed minimum trades")
    sys.exit(0)
print(f"DISCOVERY best_composite={best.combo_id} net_r={best.net_r} pf={best.profit_factor} "
      f"window={best.clock_window} family={best.strategy_family} rr={best.reward_risk_ratio}")

proof_request = OrbProofRequest(
    discovery_request=discovery_request,
    top_k=5,
    holdout_fraction=0.25,
    walk_forward_folds=4,
)
report = run_orb_proof(proof_request)

print("PROOF_COMPLETE")
print(f"PROOF_ID={report.proof_id}")
print(f"ELIGIBLE_COMBOS={len(report.eligible_combo_ids)}")
print(f"TRAIN_DAYS={len(report.train_dates)} HOLDOUT_DAYS={len(report.holdout_dates)}")

winner = None
for proof in report.combo_proofs:
    if proof.combo_id == best.combo_id:
        winner = proof
        break
if winner is None:
    print("VERDICT=BLOCKED")
    print("REASON=winner combo not in proven top_k")
    sys.exit(0)

om = winner.overall_metrics
hm = winner.holdout_metrics
print(f"WINNER combo={winner.combo_id}")
print(f"WINNER_OVERALL trades={om.trade_count} wr={om.win_rate:.3f} pf={om.profit_factor:.3f} "
      f"net_r={om.net_r:.2f} consistency={om.profitable_period_rate:.3f}")
if hm is not None:
    print(f"WINNER_HOLDOUT trades={hm.trade_count} wr={hm.win_rate:.3f} pf={hm.profit_factor:.3f} "
          f"net_r={hm.net_r:.2f}")
else:
    print("WINNER_HOLDOUT trades=0 (no holdout trades)")
print(f"WALK_FORWARD_FOLDS={len(winner.walk_forward_folds)} "
      f"pass_rate={winner.walk_forward_pass_rate:.3f}")
for fold in winner.walk_forward_folds:
    m = fold.metrics
    detail = f"trades={m.trade_count} pf={m.profit_factor:.2f} net_r={m.net_r:.2f}" if m else "no metrics"
    print(f"  FOLD {fold.fold_id} {fold.start_date}..{fold.end_date} passed={fold.passed} {detail}")
print(f"OOS_PASSED={winner.oos_passed} REPEATED_SUCCESS={winner.repeated_success_passed} "
      f"PROMOTION_ELIGIBLE={winner.promotion_eligible}")
for reason in winner.reasons:
    print(f"  REASON: {reason}")

verdict = "ELIGIBLE" if winner.promotion_eligible else "BLOCKED"
print(f"VERDICT={verdict}")
print(f"SAFETY research_only={report.research_only} trade_allowed={report.trade_allowed} "
      f"live_trading_blocked={report.live_trading_blocked}")
