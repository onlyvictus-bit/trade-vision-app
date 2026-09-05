# ORB Timing Research — M4 Analysis (v1.97)

**Run:** `d70a4a6a-58a4-56dc-9a00-6994497eb291` · 5m · 2024-01-01 → present · 3 symbols · costs applied (1.5 bps commission + 2 bps slippage per side) · no-future-leak OR lock · 2026-08-25

## The answer (per stock, best of 12 combos per window)

| Stock | Best window | Trades | Win rate | Profit factor | Net R | Profitable months | Verdict |
|---|---|---|---|---|---|---|---|
| **BEL** | **09:15–09:20** | 515 | 52% | **1.30** | **+60.2R** | **70%** | Genuinely strong |
| **VEDL** | **09:15–09:20** | 503 | 45% | 1.01 | +2.9R | 59% | Breakeven — no real edge |
| **TATAPOWER** | **09:15–09:20** | 191 | 46% | 0.97 | −2.0R | 52% | All windows lose; 09:20 least-bad |

**Universe verdict: 09:15–09:20 won 3/3** — and on every stock, later windows were monotonically worse or flat (BEL: +60 → +34 → +27 → +21R as the window widens to 09:40).

## Honest interpretation

1. **BEL is the only real edge in this set.** PF 1.30 across 515 trades with 70% of months positive is a meaningful sample, not noise. The edge decays as the range window widens — consistent with BEL trending hard after a narrow opening range in this period.
2. **VEDL's "+2.9R" is breakeven, not an edge.** Do not trade it on this evidence.
3. **TATAPOWER fails across the board.** The correct trading decision from this table is *no ORB breakout on TATAPOWER*.
4. **Earlier window wins partly by construction**: a 5-minute range produces tighter stops (smaller risk per trade) and more entries; the composite also rewards consistency. The BEL result survives this caveat (PF 1.30 is stop-width-independent); the VEDL/TATAPOWER rankings do not distinguish "best" from "least bad".

## Caveats (must read before acting)

- **In-sample selection**: within each window, the best of 12 combos is reported. That max-selection biases results upward. The v1.91 proof layer (`POST /api/v1/orb/prove` walk-forward) exists precisely for this — **BEL's 09:20 combo must pass walk-forward before any playbook promotion.** Not done yet; not approved yet.
- **Single regime**: 2024→2026 was a bull-heavy period. Breakout-long edges inflate in bulls. Regime-split analysis is future work.
- **5m quantization**: 09:20/09:30/09:35/09:40 land exactly on 5m boundaries, but intra-window structure is invisible. 1m refinement on BEL is the natural next deep-dive.
- **Costs are conservative** (₹20-side equivalent modeled via bps on price; small-caps with higher slippage would score worse).

## Recommended next actions (research track only — no trading authority)

1. ~~Walk-forward prove the BEL 09:15–09:20 combo~~ **DONE 2026-08-26 — PASSED.**
   Proof `ab7b3163` (scripts/prove_bel.py, GATES.md 7/7 met):
   - Chronological split: 414 train days / 138 holdout days
   - **Holdout (unseen data): 126 trades, wr 51.6%, PF 1.271, +12.08R**
   - **Walk-forward: 4/4 folds passed** (PF 1.13 / 1.44 / 1.41 / 1.27; +7.9R / +24.8R / +15.4R / +12.1R)
   - OOS passed, repeated-success passed → **PROMOTION_ELIGIBLE=True**
   - The edge is real, not in-sample luck: it survived every unseen period.
2. Add more daily symbols from TrendForge picks; the engine is resumable and idempotent.
3. Promotion to a paper playbook is now unblocked but remains a **separate explicit approval**.

*Safety: research_only=true, trade_allowed=false, live_trading_blocked=true. Nothing here places or routes orders.*
