# Trade Vision — Canonical Build Status

> **Purpose:** durable repository source of truth for controlled completion of Trade Vision.
>
> **Program rule:** one milestone -> implement -> test -> adversarial/replay/parity -> full regression -> authority audit -> commit -> GREEN -> lock.

**Last audited:** 2026-09-09  
**Active branch:** `m3-2-context-intelligence`  
**Controlling M3.2 spec:** `docs/M3_2_CANONICAL_CONTEXT_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md`  
**M3.2-B verified source head:** `5c944ac0f727767f5494af4c23b9334366860a8d`  
**M3.2-B verification:** `M3.2 Canonical Context Intelligence` run `34321289260` — **SUCCESS**

The M3.2 workflow checks out the exact triggering `${{ github.sha }}` and verifies `git rev-parse HEAD == GITHUB_SHA`; branch-tip drift is not accepted as lock evidence.

---

## 1. Locked semantics and authority

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral

future data != evidence
unfinished candle != evidence
stale != fresh
provider identity must be proven
source identity must be independently hashed
available_at must be causal
source close time must be causal

D1 outranks every predictor/reviewer
no incomplete-bar authority
all M2+ evidence is D2-causal
specialists cannot set final band
FINAL_CONFLUENCE_ARBITER / D6 is sole final-band authority
zero execution authority
RAW FACT CALCULATED ONCE; many may interpret; every interpretation traceable
```

Safety boundary remains:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

Canonical intelligence layers improve observation, provenance, uncertainty and contradiction handling. They do not prove trading edge and do not authorize live trading.

---

## 2. Milestone truth

| Step | Milestone | State | Boundary |
|---|---|---|---|
| M0 | Stage-2 integrity | **GREEN / LOCKED** | truthful evidence accounting and fail-closed pre-D6 integrity |
| M1 | Authority Registry | **FOUNDATION GREEN / SCOPE LOCKED** | exactly one final-band authority; zero execution authority |
| M2 | Canonical DecisionContext | **GREEN / LOCKED** | deterministic D2-causal context before unchanged D6 |
| M3 | Brain migration | **IN BUILD** | specialist families migrate behind canonical contracts |
| M3.1 | Canonical Price Intelligence | **GREEN / LOCKED** | A-F complete; D6 semantics unchanged |
| M3.1-A | Snapshot Feature Kernel | **GREEN / LOCKED** | immutable calculate-once D2 feature substrate |
| M3.1-B | Canonical Candle Intelligence | **GREEN / LOCKED** | one Anatomy computation; shared Condition/Chart facts |
| M3.1-C | Canonical Level Intelligence | **GREEN / LOCKED** | session VWAP, OR5/15/30, PIT-safe previous-session levels/CPR |
| M3.1-D | Canonical Indicator Intelligence | **GREEN / LOCKED** | typed indicator evidence, dependency/family/correlation metadata |
| M3.1-E | PIT-safe MTF Intelligence | **GREEN / LOCKED** | independently hashed closed-only HTF facts |
| M3.1-F | Price Evidence Fusion / DAG / parity | **GREEN / LOCKED** | bounded contradiction-preserving zero-authority price world-state |
| M3.2 | Canonical Context Intelligence | **IN BUILD** | context world; D6 unchanged |
| M3.2-A | Context Source Contract | **GREEN / LOCKED** | causal provider/source identity, missingness, freshness and zero authority |
| M3.2-B | Canonical Session Intelligence | **GREEN / LOCKED** | closed-bar session facts; calendar uncertainty degrades honestly |
| M3.2-C | Canonical Index/Sector Context | **ACTIVE / IN BUILD** | benchmark registry, independent observations, price-basis lineage, contradictions |
| M3.2-D | Canonical Relative Strength | **NOT STARTED** | stock vs sector vs broad market relationships |
| M3.2-E | Canonical Market Regime | **NOT STARTED** | confidence, uncertainty and hysteresis required |
| M3.2-F | Context Fusion / Receipts / Lock | **NOT STARTED** | bounded canonical context world wired before unchanged D6 |
| M3.3 | Canonical Memory Intelligence | **DESIGN STAGED / RUNTIME NOT ACTIVE** | do not activate before M3.2 lock |
| M4 | D6 orchestration redesign | **NOT STARTED / D6 EXISTS** | no M3.2 semantic redesign of D6 |
| M5-M12 | FinalDecision through independent release gate | **NOT STARTED** | later canonical program stages |

---

## 3. Locked M3.1 predecessor

M3.1 remains immutable unless a separately authorized correction is proven. Its exact pre-documentation verification remains:

```text
source head: a346ca62ddc960e0402b7df661bb3215cfa45a7b
workflow:    M3.1 Canonical Price Intelligence
run:         34254621808 — SUCCESS
```

Primary M3.1 production boundaries remain:

```text
apps/api/app/behavior/decision_spine/snapshot_feature_kernel.py
apps/api/app/behavior/decision_spine/canonical_level_intelligence.py
apps/api/app/behavior/real_indicator_adapter.py
apps/api/app/behavior/decision_spine/canonical_mtf_intelligence.py
apps/api/app/behavior/decision_spine/price_structure_evidence.py
apps/api/app/behavior/paper_guidance_spine_m3_1_impl.py
apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py
```

Locked M3.1 guarantees continue to include closed-candle causality, calculate-once/reuse-many raw facts, deterministic hashes, explicit missingness, independent MTF identities, contradiction preservation, bounded receipts, D6 parity and zero execution authority.

---

## 4. M3.2-A — Context Source Contract — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/decision_spine/canonical_context_intelligence.py`

Tests:

`apps/api/tests/decision_spine/test_m3_2_context_contract.py`

Locked guarantees include:

- missing/unavailable/error states never become neutral/false/zero;
- synthetic evidence is distinguishable from real provider evidence;
- future observations and unfinished bars have zero evidence authority;
- provider identity, contract version, source identity and independent source hash are explicit;
- `available_at_ns` and source close time must be causal to D2 decision time;
- freshness/clock-skew state is explicit;
- M3.2 evidence cannot propose, set final band or execute.

---

## 5. M3.2-B — Canonical Session Intelligence — GREEN / LOCKED

Primary implementation:

`apps/api/app/behavior/decision_spine/canonical_session_intelligence.py`

Tests:

`apps/api/tests/decision_spine/test_m3_2_session.py`

The canonical session layer consumes the approved D2/M3.1 closed-bar world rather than legacy open-timestamp availability logic. It refuses to treat an unfinished candle as session evidence.

Until an authoritative versioned NSE calendar artifact exists, observed regular-session facts may be present while authoritative session-calendar availability remains degraded. Static regular hours are not silently promoted into exchange-calendar truth.

### Exact lock evidence

Verified source head:

`5c944ac0f727767f5494af4c23b9334366860a8d`

Workflow:

`M3.2 Canonical Context Intelligence`

Run:

`34321289260` — **SUCCESS**

The exact-head run passed all required gates:

```text
Compile M3.2 and locked Decision Spine modules                 PASS
M3.2-A canonical context source contract                      PASS
M3.2-B canonical session intelligence                         PASS
Final release audit cache-isolation regression                PASS
Locked M3.1 price-intelligence regression                     PASS
Locked M2 DecisionContext regressions                         PASS
Locked M0 Stage2 integrity regression                         PASS
Paper Guidance v1.88 regression                               PASS
Historical tests/test_api.py                                  PASS
Entire apps/api/tests tree                                    PASS
Decision Spine authority / sole-D6 / zero-execution audit    PASS
Exact triggering-commit checkout                              PASS
```

### Full-tree state-isolation defect closed before lock

The pre-lock full-tree failure in `test_v059_critical_transport_resilience_blocks_release` was traced to the final release audit cache key retaining only `id(callable)` integers for monkeypatchable dependencies. A released callable's address could be reused while a cached audit remained inside its TTL, allowing stale healthy evidence to survive a changed resilience dependency.

The production cache key now holds strong callable identities. A dedicated regression proves that a cached healthy audit cannot survive replacement of the resilience dependency with critical evidence.

Primary files:

```text
apps/api/app/behavior/final_release_audit.py
apps/api/tests/test_final_release_audit_cache_isolation.py
```

This fix is state-isolation infrastructure; it does not alter trading calculations or M3.1 semantics.

---

## 6. M3.2-C — Canonical Index + Sector Context — ACTIVE

M3.2-C is now legitimately eligible because M3.2-B has exact-head GREEN lock evidence.

Required production properties:

1. versioned effective-dated benchmark registry: `stock -> sector benchmark -> broad benchmark`;
2. mapping lineage including source, mapping version, effective dates and rebalance/effective-date identity;
3. independent broad-index and sector observations with provider/source contract identity;
4. independently frozen source snapshot hashes and bounded causal receipts;
5. versioned provider-specific freshness and clock-skew policies;
6. explicit price/adjustment basis lineage (`RAW`, adjusted variants, or `UNKNOWN` when unproven);
7. corporate-action/source-adjustment identity without fabricated adjusted values;
8. explicit missing/ambiguous/stale/wrong-identity states rather than neutral defaults;
9. preservation of contradictions such as stock bullish / index bullish / sector bearish;
10. deterministic output hashes that exclude non-causal operational telemetry unless contractually part of evidence;
11. no probability authority, proposal authority, final-band authority or execution authority;
12. adversarial, replay, order-independence, duplicate-source, future-data, stale-source, identity, bounded-payload and locked-regression coverage.

M3.2-C must create canonical facts. It must not prematurely collapse them into a final score.

---

## 7. Higher-intelligence direction

The approved architecture reference remains:

`docs/M3_INTELLIGENCE_UPGRADE_REFERENCE_2026-09-08.md`

Engineering direction includes multi-hypothesis reasoning, falsifiers, counterfactuals, calibrated self-knowledge, OOD/novelty handling, failure-prediction receipts, explanation receipts and later PIT-safe memory. These are architecture goals for broader adaptive reasoning, not a claim of literal AGI or guaranteed trading correctness.

Uncertainty, contradiction, OOD and missing evidence must reduce confidence/authority, never increase it.

---

## 8. Remaining epistemic/provider caveats

Green software gates do not establish:

- authoritative NSE holiday, special-session, Muhurat or exception-session calendar coverage;
- authoritative benchmark constituent/sector mapping without a versioned source artifact;
- corporate-action adjustment provenance across every provider;
- external market-feed freshness / clock-skew proof unless a provider contract proves it;
- empirical trading edge, profitability, walk-forward robustness or realistic-cost performance.

These remain explicit provider/validation work and must fail closed or degrade honestly.

---

## 9. Next boundary

M3.2-C is the active build. Do not begin M3.2-D until canonical Index/Sector Context is implemented, adversarially tested, full-tree green and authority-audited.

Do not use M3.2 progress as permission to redesign D6, activate live execution, or jump into M3.3 memory runtime.
