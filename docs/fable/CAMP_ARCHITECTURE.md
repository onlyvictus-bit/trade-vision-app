# Trade Vision Campaign Architecture

Last updated: 2026-07-24

## v1.87 Slice

```text
PaperGuidanceRequest
  -> D1 PaperGuidanceSafetyGate
       mode + kill switch + symbol/timeframe + finite OHLCV
       + data quality + point-in-time/closed-candle validation
       fail -> WAIT, no D2 hash
  -> D2 ClosedCandleSnapshot
       freeze exact closed bars
       canonical JSON
       SHA-256 snapshot_hash
  -> PaperTradeGuidance
       WATCH at most in P0
       deterministic identity and reason list
       execution safety literals locked
```

## Interfaces

- `POST /api/v1/paper-guidance/run`
- `PaperGuidanceRequest`
- `PaperGuidanceSafetyCheck`
- `PaperGuidanceSafetyGate`
- `ClosedCandleSnapshot`
- `PaperTradeGuidance`

## Design Decisions

- The existing v0.66 shared Kronos snapshot remains unchanged in v1.87.
- The new P0 snapshot uses strict candle-close semantics.
- The route accepts explicit OHLCV; data-source orchestration comes later.
- D1 safety failure is a valid fail-closed result, not a trading exception.
- Safety authority is encoded with Pydantic `Literal` fields.

## v1.88-v1.94 Completed ORB Paper Campaign

```text
D1/D2 frozen closed-candle snapshot
  -> D3-D5 evidence + NSE-session ORB candidate
  -> proof-backed promoted playbook lookup
  -> D6 sole final-band arbiter
  -> Jarvis ORB ticket
  -> explicit human-approved simulated paper record
  -> explicit replay/downloaded-bar lifecycle observation
  -> completed-only reliability + storage monitor
```

v1.94 adds atomic local ticket/ledger/outcome stores, exact identity-chain
validation, cost-aware deterministic local outcomes, conservative same-bar
stop-first handling, reduce-only reliability feedback, and Jarvis result
display. It creates no broker/OpenAlgo/live route and performs no automatic
fill or retention deletion.
