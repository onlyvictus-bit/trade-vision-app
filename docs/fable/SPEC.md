# Trade Vision Campaign Specification

Last updated: 2026-09-07

## Outcome

Make Trade Vision a production-ready research and paper-guidance system while
keeping live broker execution outside Trade Vision.

ORB status through v2.02-derivatives (coded + finished, research-only): ORB core
v1.89, discovery v1.90, proof v1.91 (BEL ELIGIBLE, playbook a1c78a28 ACTIVE),
guidance v1.92, ledger v1.93, lifecycle/feedback v1.94, catalog v1.96, timing
v1.97, opening classifier v2.01 (standalone), derivatives v2.02 (OFF-by-default
dormant). v1.87/v1.94 sections below are frozen history.

## Approved Milestone

### TV-SPINE-P0 / v1.87 - Paper Guidance Spine P0

Required:

- D1 fail-closed safety gate.
- D2 closed-candle snapshot freeze.
- D2-owned deterministic `snapshot_hash`.
- Typed `PaperTradeGuidance` research contract.
- Explainable and reproducible output.
- Low evidence cannot produce `ENTER_PAPER`.
- No order routing, broker call, paper fill, or live-trading authority.

## Safety Invariants

- `live_trading_blocked` is always `true`.
- `order_routing_enabled` is always `false`.
- `broker_order_created` is always `false`.
- `auto_paper_fill_enabled` is always `false`.
- Candle timestamps are open times; a candle is usable only after its close.
- D1 does not mint a market snapshot hash.
- A D1 failure returns fail-closed guidance and does not run D2.
- v1.87 cannot produce `ENTER_PAPER`.

## Non-Goals

- Live broker integration, order routing, or auto-fill from Trade Vision.
- Wiring `orb/context.py` v2.01 classifier into live `orb/core.py` (needs
  separate approved milestone + OOS proof).
- Enabling derivatives beyond OFF/shadow/replay (needs ledger proof n>=30 OOS).
- Rewriting existing evidence engines.

## Observable Success

- Focused v1.87 tests pass.
- Full backend regression passes.
- Identical input produces identical guidance data and `snapshot_hash`.
- Future, incomplete, duplicate, invalid, or low-quality input cannot advance.
- OpenAPI exposes `/api/v1/paper-guidance/run`.

### TV-ORB-FEEDBACK / v1.94 - Completed Paper Lifecycle Feedback

Required:

- explicit replay/downloaded-bar observation after a human-approved record;
- point-in-time, closed, consecutive post-decision candle validation;
- deterministic simulated fill/outcome with costs, MFE, MAE, and net R;
- conservative stop-first handling when one OHLC bar touches target and stop;
- immutable outcome identity and integrity hash;
- completed-only, reduce-only ORB reliability;
- atomic fail-closed local stores and read-only operational monitor;
- Jarvis lifecycle, reliability, and storage-health display;
- no automatic fill, broker order, OpenAlgo route, live trading, or automatic
  retention deletion.
