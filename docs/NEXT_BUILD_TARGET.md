# Next Build Target

Last reviewed: 2026-09-08

## Latest Completed Engineering Milestone

```text
AFRE v4 production hardening — MERGED to main
merge commit: 83070628bf153557ac6f5f54a025866bd484f76d
PR #1: merged 2026-09-08
```

AFRE v4 now provides the adaptive ORB evidence/risk layer that was previously
only planned in the old v2.00 context-native roadmap:

- all 18 registered ORB variants are assessed from the same causal snapshot;
- all 30 source A-G failure scenarios are detected with explicit
  `OBSERVED`, `RISK_ARMED`, `NOT_OBSERVED`, and `UNOBSERVABLE` semantics;
- deterministic derivatives calculations cover VIX/IV/PCR/OI/max-pain/GEX/
  basis/rollover/GIFT/FII evidence;
- `DerivativesSnapshot` and `RiskContextSnapshot` enter the existing reducer
  and become `Capability[]` rather than creating a separate BUY/SELL engine;
- strict large-gap semantics remain `gap > 1.5 x prior ATR`;
- dealer-signed GEX remains unavailable unless dealer-position sign is
  explicitly supplied;
- hard controller vetoes survive runtime/public-ticket projection;
- paper promotion remains proof + authority + synchronized-universe + safety
  + human-approval gated;
- no live broker route was introduced.

## Verification Snapshot

```text
AFRE CI run #18 (2026-09-08): SUCCESS
AFRE targeted: 144 passed, 4 skipped, 0 failed

Dynamic full-suite regression gate:
  base main d5d7e8b1: 5 failed, 887 passed, 4 skipped
  AFRE PR candidate: 5 failed, 899 passed, 4 skipped
  new PR failure IDs: 0

The five remaining failures are inherited baseline failures:
  1. 9C real-runtime computed-count mismatch
  2. PTA marker output-count mismatch
  3. IndicatorFeatureBlock synthetic_fallback literal mismatch
  4. missing HSTRY RELIANCE_NSE_5m.csv fixture in CI
  5. Windows PowerShell parser test on Ubuntu
```

The CI gate compares the PR's complete pytest failure set with the exact base
revision. It does not hide failures through a permanent hard-coded deselect
list.

### Proof/fingerprint status

The AFRE code fingerprint now recursively includes decision-relevant
`.py/.json/.toml/.yaml/.yml` files beneath `app/orb/adaptive`, including future
nested subpackages. This is intentionally fail-closed:

```text
AFRE code changed
    -> old reviewed code fingerprint no longer matches
    -> old reviewed proof cannot authorize paper promotion
    -> fresh real-data proof + review is required
```

Do not treat the merge itself as a new proven trading edge or paper authority.

---

## Current Highest-Value Engineering Target

# Canonical Decision Spine / Brain Orchestration

The project has enough specialist intelligence. The next architecture problem
is authority and wiring: several modules can look like they produce a final
decision even though the product requirement calls for one organized pipeline,
one boss arbiter, one decision language, and one `PaperTradeGuidance` result.

Build this on a **new branch / PR**, not by reopening AFRE PR #1.

Recommended branch name:

```text
decision-spine-orchestration-v1
```

Target flow:

```text
ALL VERIFIED DATA
        |
        v
CANONICAL MARKET SNAPSHOT
        |
        v
CALCULATORS / FEATURES
        |
   +----+----+
   |    |    |
   v    v    v
Price Context Memory
   |    |    |
   +----+----+
        |
        v
HYPOTHESES
        |
        v
STRATEGY / ORB / AFRE
        |
        v
DERIVATIVES / EVENTS
        |
        v
FAILURE ENGINE
        |
        v
EXECUTION + RISK REALITY
        |
        v
FINAL CONFLUENCE
ONE FINAL-BAND AUTHORITY
        |
        v
PROOF / SAFETY GATE
        |
        v
FINAL DECISION
        |
        v
JARVIS READ-ONLY PRESENTATION
```

## Ordered Build Sequence

### 1. Engine Authority Registry

Classify every engine before changing wiring.

Minimum fields:

```text
engine_id
module
classification
may_propose
may_veto
may_downgrade
may_set_final_band
may_execute
authority_rank
canonical_consumer
legacy_or_current
```

Target authority model:

| Engine | Role | Propose? | Veto? | Final band? |
|---|---|---:|---:|---:|
| Candle Anatomy | calculator | No | No | No |
| Condition Classifier | evidence | No | limited | No |
| Session / Pattern Memory | memory evidence | No | No | No |
| Hypothesis Engine | scenario evidence | No | No | No |
| ORB / AFRE | strategy/scenario | Yes | Yes | No |
| Derivatives / RiskContext | evidence/risk | No | Yes | No |
| Failure Detector | risk/veto | No | Yes | No |
| Execution/Event/OI Risk | execution-risk gate | No | Yes | No |
| Risk Engine | risk gate | No | Yes | No |
| Kronos | reviewer/prior | No | No | No |
| Gemini / Grok | reviewer | No | No | No |
| Twin Arbiter | conflict/downgrade evidence | No | downgrade | No |
| Jarvis Arbiter/Fusion | compatibility/aggregation during migration | No | no upgrade | No |
| Jarvis Master Panel | presenter | No | No | No |
| **Final Confluence Arbiter / D6** | **final authority** | **Yes** | **Yes** | **YES** |
| Jarvis Trading Decision Output | presenter | No | No | No |

### 2. Canonical `DecisionContext`

One point-in-time evidence contract should contain:

```text
identity: symbol / timeframe / decision_time / snapshot_hash / watermark
input_integrity: data_quality / PIT / freshness / quarantine
price_structure / candle_anatomy / levels / regime / session
index / sector / relative_strength
indicators
memory / historical_analogs
hypotheses
strategy_candidates / orb_variants / afre_scenarios
derivatives / events / failure_scenarios
execution_quality / portfolio_risk
blockers / warnings
proof_status / paper_authority
provenance / engines_run / evidence_versions / capability_sources
```

No final arbiter or reviewer should secretly fetch and reconstruct a different
market worldview while deciding.

### 3. Canonical `FinalDecision` / `PaperTradeGuidance`

One product result should contain at least:

```text
action: WAIT | WATCH | AVOID | PAPER-CANDIDATE
bias: LONG | SHORT | NEUTRAL
market_story
primary_setup + state
alternative_scenarios[]
derivatives_summary
failure_check[]
historical_evidence
entry_plan: side / zone / trigger / stop / targets / invalidation / RR
wait_for[]
avoid_if[]
main_blocker
evidence_confidence
data_quality / PIT / proof_status / paper_authority
reason_for[] / reason_against[] / warnings[] / hard_blockers[]
engines_run[]
live_trading_blocked = true
order_routing_enabled = false
```

### 4. Sole final authority

Make Final Confluence / D6 the only component that sets the product final band.
During migration, preserve old outputs as read-only comparison evidence until
replay tests prove safe equivalence/downgrades.

### 5. Real derivatives/risk providers

The AFRE calculators are implemented, but real upstream population remains a
separate integration task.

Correct flow:

```text
OpenAlgo / verified NSE sources
        -> provider adapters
        -> canonical option/futures/VIX/FII/event snapshots
        -> DerivativesSnapshot / RiskContextSnapshot
        -> existing calculators
        -> Capability[]
        -> same DecisionContext
```

Do not create a second derivatives BUY/SELL engine.

Every provider must preserve source identity, exchange/instrument identity,
observation/receive timestamps, expiry/session identity, freshness/TTL,
completeness, normalization version, provenance/hash where practical, and
fail-closed missing/invalid behavior.

### 6. Integration tests

Before retiring duplicate authority paths, test:

- contradictory bullish indicators vs hard structure/risk veto;
- external AI disagreement cannot upgrade hard WAIT/NO_TRADE;
- Kronos cannot override risk;
- AFRE confirmed variant cannot bypass proof;
- `UNOBSERVABLE` derivative/event input stays unobservable;
- stale/future capability cannot influence a decision;
- identical `DecisionContext` hash replays deterministically;
- hard veto survives every API/UI projection;
- no code path can set `order_routing_enabled=true` or enable live broker use.

---

## Proof Milestone After Wiring

Only after the decision spine and real evidence wiring are stable, run the
**gap-morning focused historical experiment**.

Factor grid:

```text
Gap size
x CPR width/location
x OR width
x ORB variant
x VWAP
x Nifty alignment
x sector alignment
x volume
x VIX
x PCR/OI
x expiry state
x failure scenarios
```

Minimum measurements:

```text
Win rate
Expectancy
Profit factor
Max drawdown
False-break rate
Stop-out rate
MFE
MAE
Time-to-target
Failure type
Regime dependency
Sample count
OOS consistency
Walk-forward consistency
transaction-cost sensitivity
slippage sensitivity
```

Selection remains train-only, followed by unseen holdout and expanding/repeated
walk-forward proof. Do not promote an in-sample winner directly.

Then:

```text
historical replay
 -> unseen holdout
 -> walk-forward
 -> approved playbook
 -> real-market observation
 -> WAIT / WATCH / PAPER-CANDIDATE
 -> human approve
 -> paper result
 -> outcome memory
 -> edge-decay monitoring
```

No automatic live trading.

---

## Standing Operational Work (Does Not Block The Architecture Milestone)

- Continue daily ORB timing runs on TrendForge picks when useful.
- Continue accumulating completed paper outcomes for memory maturity.
- Keep latency/proxy-indicator cleanup as bounded maintenance work.
- Keep baseline 9C/PTA, HSTRY-fixture and PowerShell/Linux failures visible;
  fix them in their owning milestones rather than changing AFRE trading logic.

## Source Documents

Read in this order for the next architecture build:

1. `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`
2. `docs/plans/FINAL_REQUIRED_FLOW.md`
3. `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md`
4. `docs/SAFETY_INVARIANTS.md`
5. this file

Current dated AFRE merge/status evidence:

- `docs/AFRE_V4_MERGE_STATUS_2026-09-08.md`
