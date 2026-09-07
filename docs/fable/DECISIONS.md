# Trade Vision Campaign Decisions

Last updated: 2026-07-24

## TV-ADR-001 - Spine Before ORB

Status: accepted by user objective.

Build Paper Guidance P0-P2 before the ORB research lab.

## TV-ADR-002 - Strict Candle-Close Semantics

Status: accepted for v1.87.

Treat `CandleBar.timestamp_ns` as candle-open time. A bar is closed only when
`timestamp_ns + timeframe_duration_ns <= decision_time_ns`.

## TV-ADR-003 - P0 Cannot Enter Paper

Status: accepted for v1.87.

P0 has no setup/memory/structure/arbiter authority. A valid D1/D2 result is at
most `WATCH`; unsafe input is `WAIT`.

## TV-ADR-004 - Explicit OHLCV Input

Status: accepted for v1.87.

The P0 route accepts explicit `CandleSeries`. Automatic local/live data loading
is deferred so the contract has no hardcoded path or broker dependency.

## TV-ADR-005 - ORB Is Primary Setup, Not Final Authority

Status: approved by the user for v1.88-v1.93 on 2026-07-24.

After D1 safety and D2 immutable closed-candle snapshot freeze, ORB is the
primary D3a setup candidate generator. D3b memory/MTF evidence, D4
structure/liquidity/execution checks, optional D5 Kronos disagreement, and the
D6 sole final arbiter may preserve or downgrade the candidate. They may not
silently upgrade a blocked candidate.

ORB cannot bypass the kill switch, point-in-time guard, low-evidence cap,
required higher-timeframe confirmation, liquidity/risk checks, or D6. Offline
ORB discovery is never run in the Jarvis click path.

## TV-ADR-006 - Paper Recording Requires Explicit Human Approval

Status: approved by the user for v1.93 on 2026-07-24.

Jarvis may display an ORB paper guidance ticket, but no simulated paper record
is created until the operator performs a separate explicit approval action.
Approval records the guidance id, D2 snapshot hash, arbiter result, entry,
stop, target, quantity/risk inputs, and immutable audit metadata. Live broker
or OpenAlgo routing remains out of scope.

## TV-ADR-007 - Paper Outcome Requires Explicit Replay Observation

Status: approved by the user for v1.94 on 2026-07-24.

A v1.93 paper record is an intent, not a fill. v1.94 may calculate a local
simulated fill and lifecycle outcome only after the operator explicitly submits
later closed replay/downloaded bars. The outcome remains bound to the original
guidance, proof-backed playbook, snapshot hash, symbol, and timeframe.

Same-bar target/stop ambiguity is stop-first. Costs are configured. Completed
outcomes freeze with an integrity hash. Reliability counts only completed,
non-orphaned, identity-valid outcomes and is reduce/quarantine-only. Ticket,
ledger, and outcome stores use atomic JSON replacement rather than an
unapproved database migration. Retention is preview-only. No broker/OpenAlgo
route or automatic fill is introduced.

## TV-ADR-008 - ORB Opening Classifier Ships Standalone (v2.01)

Status: implemented 2026-09-07 (`orb/context.py`, 8 scenario gates).

`classify_opening` (gap/CPR/zone) is research-only and NOT wired into live
`orb/core.py` until a separate approved milestone + OOS proof passes.

## TV-ADR-009 - Derivatives Ships Dormant OFF-by-Default (v2.02-derivatives)

Status: implemented 2026-09-07 (`orb/derivatives/`, 22/22 gates).

Mount gated by `TRADEVISION_DERIVATIVES_PROFILE=off|shadow|replay`; no LIVE
profile; shadow requires `OPENALGO_*`. ATR parity canonical: SMA-seeded Wilder.
No trading-authority change.
