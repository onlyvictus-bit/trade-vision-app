# Design Evidence Ledger — ORB Intraday Formation Extension

## Source-backed requirements from `docs/ORB_FORMATION_REFERENCE_2026-09-19/SOURCE_INTRADAY_FORMATION_PLAN_2026-09-19.md`

- arbitrary intraday `decision_as_of` reasoning;
- deterministic anchors known by the decision time;
- multi-scale formation identity;
- explicit formation lifecycle;
- discriminator-complete competing hypotheses;
- prefix-safe historical analogue retrieval;
- facts→relationships→behaviour→structure→optional alias grammar;
- formation transition history;
- dependency-family lineage / anti-double-counting;
- versioned geometry/tolerance policy;
- legal `NO_STABLE_FORMATION`;
- provisional-only treatment for incomplete higher-timeframe candles;
- screenshots as examples, not canonical market data;
- pattern-fishing controls;
- B14 adversarial tests for future append, hindsight anchors, analogue outcome leakage, scale coexistence, alias dependence, incomplete candles and pattern-search leakage.

## Previously verified repository ownership reused by this plan

These come from the prior reconciliation evidence, not from the new attachment:

- D2 / canonical snapshot path owns closed-candle facts and snapshot lineage;
- BUILD-1 owns candidate identity/provenance;
- BUILD-2 owns market/session/contract/calendar identity;
- BUILD-3 owns typed prior-session reference facts;
- M3.1 owns canonical candle/price/structure/level facts;
- M3.3 is the first canonical historical memory/analogue path;
- D6 `FINAL_CONFLUENCE_ARBITER` remains final guidance-band authority;
- B4 opening-sequence work is zero authority and research-only.

## Architecture placement decisions introduced here

These are design decisions, not claims of existing implementation:

- place `OrbIntradayFormationViewV1` beside/after the existing opening-sequence composition seam rather than creating a separate pattern engine;
- keep B6 as lifecycle/state owner rather than letting B4 own a second state machine;
- keep B7 as geometry/tolerance parameter owner;
- use B8 for chronology/OOS/holdout proof and anti-pattern-fishing controls;
- keep M3.3 first for analogue retrieval and B9 for optional challenger research;
- use B11 dependency lineage to stop correlated aliases from becoming false confluence;
- use B14 as the adversarial lock for causal replay and leakage attacks.

## Deliberately unresolved / not invented

The documentation does **not** choose or invent:

- a winning timeframe or timeframe set;
- anchor precedence;
- pivot-prominence thresholds;
- touch-count thresholds;
- slope thresholds;
- compression thresholds;
- retracement thresholds;
- alias acceptance thresholds;
- STUMPY/DTW adoption;
- calibrated success probability;
- profitability claims;
- live feed/broker/execution behavior.

Candidate anchor names such as `VWAP_RECLAIM` are treated as unavailable unless a canonical owner/provenance is verified in the runtime build. This avoids turning an example vocabulary item into a fabricated repository fact.