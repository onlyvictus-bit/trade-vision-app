# Trade Vision ORB Derivatives Intelligence v2.02

Production-oriented, research-only derivatives intelligence subsystem for `onlyvictus-bit/trade-vision-app`.

## What this bundle adds

- OpenAlgo broker-neutral data provider with bounded retry/backoff and batch Greeks.
- Immutable/PIT-safe `OptionChainSnapshot` and `FuturesSnapshot` contracts.
- Vectorized chain analytics: PCR-OI/volume, strike-aligned Delta-OI, OI walls and persistence, true payout-minimization Max Pain, ATM straddle expected move, horizon-IV expected move, 25-delta skew, term structure, IV rank/percentile, futures price/OI state and basis.
- OpenAlgo IV/Delta/Gamma/Theta/Vega/Rho consumption plus local Black-76-consistent Vanna and Charm support.
- Explicit **OI/Gamma exposure proxy** calculations. They are deliberately not called true dealer GEX because OI does not reveal dealer positioning.
- Deterministic counterfactual derivatives scenario controller that predicts failure modes and emits SUPPORT / CONFLICT / UNKNOWN / BLOCK.
- Existing v1.73 payload bridge and AFRE `Capability` bridge.
- SQLite WAL append-only snapshot/context history for D-1 and PIT replay.
- Fail-closed replay helpers and train-only / expanding-fold proof helpers.
- Environment-gated FastAPI mount: `off` (default), `shadow`, or `replay`; no live mode.
- NSE contract-rule helpers with current Tuesday-expiry and variable tick-size semantics, while provider/exchange contract master remains authoritative.

## Safety invariants

The derivatives layer **cannot create a trade, route an order, or enable live trading**. It can only challenge an existing ORB/AFRE price scenario, surface failure conditions, cap guidance, or require more evidence. Existing legacy ORB and AFRE remain unchanged unless the supplied integration patches are deliberately applied.

## Verification in this bundle

Run from `apps/api`:

```bash
pytest -q tests/test_orb_derivatives_v202.py
python -m compileall -q app/orb/derivatives
```

Current targeted result: **22 passed**. The bundle also includes a vectorized 401-strike performance guard.

This is not a claim that the repository's entire existing 891-test backend suite was rerun: the connected GitHub repository was available for source inspection but was not mounted as a writable working tree in this chat. Apply the bundle to a branch and run the full repo regression/proof suite before SHADOW promotion.

See `docs/ORB_DERIVATIVES_V202_INTEGRATION.md` for integration order and verified contract assumptions.
