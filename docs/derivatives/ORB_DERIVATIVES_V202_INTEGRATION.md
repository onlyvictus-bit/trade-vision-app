# ORB Derivatives Intelligence v2.02

> Status SHIPPED 2026-09-07 (v2.02-derivatives, 22/22 gates, 914 full backend).
> OFF-by-default dormant research subsystem. ATR parity DONE below.

Research-only, fail-closed derivatives context for Trade Vision ORB/AFRE.

## Runtime flow

```text
OpenAlgo -> canonical snapshots -> vectorized calculators -> DerivativesContext
                                                     |-> v1.73 overlay
                                                     |-> AFRE Capability facts
                                                     |-> scenario challenge controller
```

The subsystem never creates a trade. It can support an existing price scenario, mark conflict/unknown, block stale/unavailable context, cap a target, or predict a concrete failure mode.

## Current exchange assumptions verified 2026-09-07

* NSE equity-derivative contracts expiring on/after 2025-09-01 use Tuesday expiry; holiday -> previous trading day.
* Current NSE contract specs publish variable index-futures tick size: 0.05 up to 15,000; 0.10 above 15,000 through 30,000; 0.20 above 30,000. NSE reviews the applicable tier monthly from the prescribed month-end reference, so live code must use contract-master `tick_size`, not switch intraday from spot.
* Index-option tick is 0.05.
* Stock-option tick is 0.01 for the below-250 monthly reference tier and 0.05 at/above 250, effective 2025-11-03; NSE reviews it monthly. Stock-futures have additional current tiers (0.01/0.05/0.10/0.50/1.00/5.00). Contract-master `tick_size` is authoritative.
* Strike schemes, lot sizes and freeze quantities are dynamic. Use OpenAlgo/NSE master contract metadata; do not hard-code them.
* OpenAlgo OptionChain provides LTP/bid/ask/volume/OI/lot/tick. MultiOptionGreeks provides IV + Delta/Gamma/Theta/Vega/Rho using OpenAlgo's Black-76 implementation.
* NSE's public LPP documentation currently states Black-Scholes is used for theoretical option reference prices. Therefore this subsystem labels Black-76 outputs as the **OpenAlgo model**, not as an NSE-mandated pricing formula.

## Integration steps

1. Copy `apps/api/app/orb/derivatives/` into the repository.
2. Add a provider singleton using env vars `OPENALGO_BASE_URL` and `OPENALGO_API_KEY`. Never commit the key.
3. Create `DerivativesStore(data/orb_derivatives.db)`.
4. Construct `DerivativesService`.
5. Mount `derivatives.api.router(...)` in `main.py` only in research/shadow modes.
6. Use `v173_payload_overlay()` before validating `ExecutionEventOiRiskRequest`.
7. Convert `afre_capability_payloads()` to AFRE `Capability` objects and append to `MarketSnapshot.capabilities`.
8. Keep `TRADEVISION_AFRE_PROFILE=off` until replay/proof passes; then use `shadow` first.

## ORB math parity — DONE (v2.02)

Canonical implementation is the explicit SMA-seeded Wilder recurrence (was
duplicated: `orb/context.py` pandas EWM vs `adaptive/features.py` Wilder).
Parity-tested in the v2.02 bundle (22/22). Gap boundary policy stays at the
existing 0.1% rule unless a future approved spec changes it.

## Proof discipline

Derivatives features must be generated strictly from snapshots available at each historical decision timestamp. Selection must stay train-only and walk-forward folds must use expanding prior training prefixes, matching the repaired ORB proof framework. Never compute IV rank, OI deltas, wall persistence, or term structure from future snapshots.

* Static lot-size examples in third-party documentation can become stale. Never hard-code NIFTY/BANKNIFTY lots; consume the current OpenAlgo/NSE contract master for each actual contract.
