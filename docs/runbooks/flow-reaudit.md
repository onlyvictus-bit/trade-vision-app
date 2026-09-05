# Flow Re-Audit Runbook (real-data end-to-end check)

Purpose: verify the full D1-D8 trading flow works on real market data, stage by
stage. This is the FIRST check to run when any flow behaviour looks wrong.

## Procedure

1. Activate the project venv (`stock-app/.venv`).
2. Run `python scripts/flow_reaudit.py` from `trade-vision-app/`.
3. Read the output top to bottom:

```text
BLOCK 1   loader reports symbol / timeframe / bar count (bounded <= 5000)
BLOCK 2   D1 safety gate: 9 checks, all must be PASS
          PG-D1-005 bar-count bound, PG-D1-007 quality >= 0.85,
          PG-D1-008 closed + point-in-time safe
D2        snapshot_id + snapshot_hash must be non-null
D3A-D6    nine engine receipts; expect status=completed
          (PERSISTED_INDICATOR_MEMORY is degraded until 30 completed
           paper outcomes exist - honest, not a defect)
BLOCK 7-8 final_band (WAIT/WATCH/PAPER-CANDIDATE) + safety flags
          research_only=true, live_trading_blocked=true must always hold
```

4. Any FAIL: read the check evidence line; the blocker names the exact stage.

## Known-good baseline (2026-08-26)

```text
RELIANCE 5m x5000 HSTRY bars -> D1 9/9 PASS (quality 1.0000)
-> snapshot hash f910d011... -> 8/9 receipts completed
-> final_band=WATCH, blockers = P0 stage + 0/30 outcomes + playbook pending
```

## Rules

- Never raise the 5000-bar bound or lower the 0.85 quality threshold to make a
  run pass; fix the data instead.
- Session-closure gaps (overnight/weekend/holiday) are info-level
  (`session_closure_gap_count`); only intraday gaps are quality warnings.
- Indicator evidence computes on the last 400 bars
  (`SNAPSHOT_INDICATOR_WINDOW_BARS`); the D2 hash still covers the full series.
