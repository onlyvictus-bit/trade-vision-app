# Trade Vision Campaign Plan

Last updated: 2026-09-03

## Milestone TV-SPINE-P0 / v1.87

Status: completed and verified

1. Reconcile current docs, routes, contracts, tests, and safety boundaries.
2. Add config-driven P0 thresholds.
3. Add typed Paper Guidance contracts.
4. Implement D1 safety gate and D2 strict snapshot freeze/hash.
5. Add the research-only API route and capability manifest item.
6. Add focused determinism, no-lookahead, quality, and no-routing tests.
7. Run focused and full backend regression.
8. Update status, API, architecture, test, context, graph, and next-target docs.

Acceptance:

- no D1 failure mints `snapshot_hash`;
- identical valid inputs produce identical response data;
- low evidence is capped below `ENTER_PAPER`;
- all supported timeframes use close-time validation;
- no execution surface is added.

Verification:

```text
focused Paper Guidance: 20 passed
existing Kronos/Twin snapshot: 9 passed
full backend: 598 passed
```

## Proposed Milestone TV-SPINE-P1 / v1.88

Status: completed and verified on 2026-07-24

### Intent

Turn the v1.87 D1/D2 foundation into one deterministic research-guidance
pipeline without allowing an engine to read a different candle snapshot or
produce a competing final decision.

### Evidence-Backed Constraints

- Reuse D1 and D2; do not weaken the close-time or no-routing rules.
- Invoke snapshot-native functions directly with the D2 frozen candles. Do not
  call `current` endpoints from the spine.
- The existing indicator runtime loads its own current candles and is excluded
  until a snapshot-native adapter exists.
- Fixture reliability is descriptive only and cannot increase confidence.
- Caller-provided historical match counts are not decision authority.
- The v1.75 arbiter must enforce the post-aggregation low-evidence cap itself.
- Kronos, ORB, OpenAlgo, broker routing, paper fills, and automatic approval are
  outside v1.88.

### Proposed Work

1. Add typed engine receipts that bind every result to the D2 snapshot hash,
   engine version, output hash, run status, and identity check.
2. Add optional independently frozen MTF inputs for `1m`, `3m`, `5m`, `15m`,
   `30m`, `1H`, `4H`, and `Daily`; incomplete HTF bars are excluded and missing
   required HTF evidence caps the result at `WATCH`.
3. Run snapshot-native D3a evidence in fixed order: chart reasoning, candle
   condition/context, and level context.
4. Run D3b from persisted, completed, point-in-time indicator history only.
   Fixture fallback and future-created records cannot count as evidence.
5. Reuse the snapshot-native market-structure/liquidity report and
   execution/event/OI risk report as D4 reduce/block evidence.
6. Harden D6 so it is the sole final-band producer. Low evidence, missing
   required MTF, missing entry-plan authority, or unavailable mandatory context
   prevents `ENTER_PAPER`.
7. Package one deterministic `PaperTradeGuidance`; optional engine failure
   becomes an explicit skip/warning and cannot boost the result.
8. Keep the frontend card for v1.89 after the backend contract is verified.

### Proposed Focused Tests

```text
TV-V188-001 fixed engine order
TV-V188-002 every engine receipt matches the D2 snapshot
TV-V188-003 output hashes and full guidance are deterministic
TV-V188-004 incomplete primary candle remains excluded
TV-V188-005 incomplete HTF candle remains excluded
TV-V188-006 all eight supported timeframe identities validate
TV-V188-007 indicators are recalculated per supplied timeframe
TV-V188-008 current/mock endpoint substitution is forbidden
TV-V188-009 fixture reliability cannot boost confidence
TV-V188-010 only completed persisted history counts
TV-V188-011 history created after decision time is excluded
TV-V188-012 caller match count cannot bypass D3b
TV-V188-013 low evidence caps D6 at WATCH after aggregation
TV-V188-014 missing required MTF caps at WATCH
TV-V188-015 unavailable event/OI/depth context cannot look clean
TV-V188-016 conflicts only reduce the final band
TV-V188-017 D6 is the only final-band authority
TV-V188-018 optional engine failure degrades safely
TV-V188-019 no Kronos/ORB/OpenAlgo/sim/broker import or call
TV-V188-020 OpenAPI, capability manifest, and safety literals remain valid
```

### Proposed Acceptance

- focused v1.88 tests pass;
- full backend regression passes;
- every engine proves one immutable snapshot identity;
- identical input returns identical guidance and hashes;
- low evidence, missing MTF, or missing entry-plan authority cannot produce
  `ENTER_PAPER`;
- no paper fill, order, credential, broker, OpenAlgo, Kronos, or ORB path is
  created.

[ASSUMPTION] v1.88 is allowed to remain `WAIT`/`WATCH` until a complete,
snapshot-bound entry/stop/target authority is implemented and separately
verified.

## Approved ORB-First Continuation / v1.89-v1.94

Status: approved on 2026-07-24

| Version | Approved milestone |
|---|---|
| **v1.89** | ORB-0/1 contracts, NSE session locking, and breakout/breakdown/reversal builders |
| **v1.90** | ORB-2 offline combination discovery with async jobs and trading costs |
| **v1.91** | ORB-3 OOS/walk-forward/consistency proof and playbook promotion |
| **v1.92** | ORB-4/5 primary Jarvis setup action and read-only playbook bridge |
| **v1.93** | Explicitly human-approved simulated paper record linked to guidance |
| **v1.94** | ORB outcome feedback, lifecycle evidence, monitoring, and production hardening |

Campaign invariant:

```text
ORB proposes the main setup.
D6 alone decides the final band.
Only explicit human approval creates a simulated paper record.
No live broker or OpenAlgo route is enabled.
```

Completion evidence:

```text
v1.88-v1.93 focused backend: 85 passed
v1.94 focused backend: 32 passed
v1.92-v1.94 focused backend: 54 passed
full backend: 715 passed
frontend typecheck/build: passed
browser RELIANCE 5m: WATCH / NO_PLAYBOOK / MTF ALIGNED / record + lifecycle disabled / store PASS
remaining: none in the approved v1.88-v1.94 campaign
```

## Approved Milestone TV-ORB-FEEDBACK / v1.94

Status: completed and verified on 2026-07-24

### Intent

Turn a v1.93 human-approved ORB paper intent into explicit, reproducible
simulation evidence after closed replay candles are supplied. Completed
point-in-time outcomes may update a separate ORB reliability report, but they
cannot promote a playbook, change model weights, create an order, or bypass D6.

### Options Considered

| Option | Result | Decision |
|---|---|---|
| Keep the intent-only ledger | No fill/result evidence; final operator journey remains incomplete | Rejected |
| Accept a manually typed outcome | Easy, but cannot prove fill or stop/target ordering | Rejected |
| Explicit replay observation + deterministic simulated lifecycle | Proves fill, costs, MFE/MAE, and outcome from closed OHLCV while preserving human control | Selected |

### Required Work

1. Add config-driven guidance, ledger, outcome, TTL, retention-preview,
   execution-cost, and feedback-threshold settings.
2. Replace silent JSON corruption fallback with a shared fail-closed atomic
   store that supports validated recovery and concurrent writers.
3. Reject expired guidance tickets at the paper-record boundary without using
   historical candle age as wall-clock freshness.
4. Add an explicit lifecycle observation request bound to
   `paper_record_id`, `guidance_id`, `playbook_id`, proof, symbol, timeframe,
   and source snapshot hash.
5. Validate monotonic, duplicate-free, closed post-decision candles. Reject
   identity mismatch, incomplete bars, future-to-observation bars, and
   insufficient causal evidence.
6. Simulate entry trigger and costs deterministically. A target/stop collision
   in one OHLCV bar is stop-first unless lower-timeframe ordering is supplied
   and separately verified.
7. Persist immutable outcome records with fill state, MFE/MAE, bars-to-fill,
   bars-to-target/stop, gross/net R, cost breakdown, and an integrity hash.
8. Build playbook reliability only from completed, non-orphaned,
   point-in-time outcomes. Low sample counts stay `LOW_EVIDENCE`; poor
   reliability may recommend quarantine but can never auto-retire/promote.
9. Add store health, orphan detection, integrity status, retention preview,
   stale-ticket count, and last-observation monitoring.
10. Extend Jarvis ORB guidance with paper lifecycle/result and reliability
    status. The UI remains operator-triggered and simulation-only.
11. Add release evidence, capability contracts, endpoint docs, graph/context
    updates, and full regression proof.

### [ASSUMPTION]

- v1.94 observes replay/downloaded OHLCV only after explicit operator action.
- A paper "fill" is a deterministic local simulation label, never an external
  order or broker acknowledgement.
- Retention is report-only in v1.94; no records are automatically deleted.
- Feedback is descriptive and reduce-only. It cannot increase a guidance band.
- The local atomic JSON boundary is retained to avoid an unapproved database
  migration or dependency on Stock App/OpenAlgo.

### Focused Tests

```text
TV-V194-001 configured storage paths are honored
TV-V194-002 malformed main store fails closed and is not overwritten
TV-V194-003 valid temporary store recovers only when main file is absent
TV-V194-004 concurrent writes retain every record
TV-V194-005 stale guidance ticket cannot create a paper record
TV-V194-006 replay-aged candle data does not itself make a freshly minted ticket stale
TV-V194-007 lifecycle requires an existing human-approved paper record
TV-V194-008 paper/guidance/playbook/proof/snapshot identity chain must match
TV-V194-009 duplicate or non-monotonic observation candles are rejected
TV-V194-010 incomplete or future-to-observation candles are rejected
TV-V194-011 observation candles must begin after the guidance decision
TV-V194-012 no-trigger path records NO_FILL without fabricating entry
TV-V194-013 gap-through entry applies conservative configured fill cost
TV-V194-014 target-first path records TARGET_HIT
TV-V194-015 stop-first path records STOP_HIT
TV-V194-016 same-bar target/stop collision records STOP_HIT conservatively
TV-V194-017 open lifecycle remains OPEN until completion evidence exists
TV-V194-018 time-window completion records TIME_EXIT
TV-V194-019 MFE/MAE and gross/net R are deterministic
TV-V194-020 duplicate lifecycle observation is idempotent
TV-V194-021 only completed point-in-time outcomes enter reliability
TV-V194-022 orphan or identity-broken outcome is excluded and reported
TV-V194-023 low sample feedback remains LOW_EVIDENCE
TV-V194-024 poor completed outcomes can only recommend quarantine
TV-V194-025 feedback cannot promote/retire a playbook or raise final band
TV-V194-026 monitoring reports integrity, counts, stale tickets, and retention preview
TV-V194-027 retention preview deletes nothing
TV-V194-028 every v1.94 contract keeps simulation/no-routing safety literals
TV-V194-029 OpenAPI and capability manifest expose lifecycle/feedback/monitoring
TV-V194-030 no broker, OpenAlgo, live route, or automatic fill path is introduced
TV-V194-031 Jarvis renders lifecycle outcome and reliability without hiding blockers
TV-V194-032 full backend, frontend typecheck/build, API smoke, and browser proof pass
```

### Acceptance

- The operator can explicitly evaluate a recorded paper intent against later
  closed replay candles and see fill/outcome/cost/R evidence.
- Same input produces the same lifecycle result and integrity hash.
- Corruption, stale tickets, identity breaks, incomplete bars, low evidence,
  and orphan feedback fail closed.
- Completed outcomes are linked to exactly one guidance and playbook.
- No automatic fill, order, broker credential, OpenAlgo route, model-weight
  update, playbook promotion, or live action exists.

## Proposed Milestone v1.95 - Active Evidence Loading And API Fast-Lane Hardening

Status: planned, not approved

### Intent

Stop hidden workspaces and hidden Jarvis subtabs from repeatedly consuming the
entire API evidence surface. Preserve the current fail-closed UI while making
health, time, mode, kill switch, freshness, and the active decision surface
responsive under normal local use.

### Evidence

- `App.tsx` currently builds one bounded queue containing nearly every
  workspace endpoint.
- The queue reruns every 30 seconds and is recreated when the active workspace
  changes.
- The v1.94 runtime check returned HTTP 200, but `/health` took 9.747 seconds
  while the frontend request wave was active; the storage monitor took 1.154
  seconds.
- The data state is one large object, so a naive replacement load could erase
  already loaded inactive-panel evidence.

### Options Considered

| Option | Result | Decision |
|---|---|---|
| Keep one global bounded queue | Simple, but hidden panels continue to consume backend capacity | Rejected |
| Increase API workers or browser concurrency | Masks the cause and can amplify storage/model contention | Rejected |
| Split global safety fast lane from active workspace/subtab loaders | Reduces work while retaining visible evidence and fail-closed safety | Recommended |

### [ASSUMPTION]

- Safety-critical global state is `time`, `mode`, `features`, `killswitch`,
  storage readiness, and realtime freshness/health.
- A workspace may retain its last successful evidence when hidden, but the UI
  must visibly mark it stale when revisited until its active loader completes.
- Jarvis `trade`, `evidence`, `execution`, and `vault` subtabs may load
  independently, while the sticky command ticket always receives its minimal
  decision/safety data.
- This milestone changes request scheduling only. It does not change trading
  calculations, thresholds, decision bands, or routing authority.

### Required Work

1. Replace the monolithic refresh task list with typed loader groups:
   `globalSafety`, one group per workspace, and one group per Jarvis subtab.
2. Run the global safety fast lane on the periodic timer.
3. Load the active workspace after the fast lane; for Jarvis, load the sticky
   ticket core plus the active Jarvis subtab only.
4. Merge partial loader results into existing state instead of replacing the
   whole state object.
5. Track group freshness, loading, error, last-success, and request counts.
6. Abort or ignore stale loader responses after workspace/subtab changes.
7. Keep every missing/failed group fail-closed and visible as stale/unavailable.
8. Make the Refresh button reload the global fast lane and current visible
   group only.
9. Add development-only request instrumentation for deterministic tests; do
   not expose credentials or raw provider payloads.
10. Preserve every existing workspace and all 71 Jarvis panels.

### Focused Tests

```text
TV-V195-001 startup loads global safety plus active workspace only
TV-V195-002 periodic timer never loads hidden workspaces
TV-V195-003 Jarvis trade tab loads sticky core plus trade group only
TV-V195-004 changing Jarvis subtab loads only the selected group
TV-V195-005 switching workspace preserves prior state and marks freshness
TV-V195-006 stale response cannot overwrite newer active-group data
TV-V195-007 one failed group does not mark the whole API offline
TV-V195-008 failed global safety fast lane produces safe offline state
TV-V195-009 explicit refresh reloads only visible and global groups
TV-V195-010 refresh-in-flight guard prevents overlapping same-group waves
TV-V195-011 all current workspaces remain reachable
TV-V195-012 all 71 Jarvis panels remain assigned and reachable
TV-V195-013 hidden provider/audit panels generate no periodic requests
TV-V195-014 kill-switch state remains globally current
TV-V195-015 inactive stale evidence cannot authorize a decision
TV-V195-016 no decision, risk, paper, broker, or OpenAlgo behavior changes
TV-V195-017 frontend typecheck and production build pass
TV-V195-018 browser desktop/mobile workspace switching has no blank state
TV-V195-019 API health p95 remains within the documented local budget under UI refresh
TV-V195-020 full backend regression remains green
```

### Acceptance

- Hidden workspaces and hidden Jarvis subtabs issue zero periodic evidence
  requests.
- The safety fast lane remains globally current.
- Active-panel failures are explicit and fail closed without blanking unrelated
  cached UI state.
- The active Jarvis trade surface remains complete and responsive.
- All existing panels remain accessible.
- No trading calculation or execution authority changes.

### Implementation Design

Current measured baseline:

```text
one root refresh queue: 164 unique API methods
queue concurrency: 4
timer: 30 seconds
visible workspaces at one time: 1 of 9
visible Jarvis subtabs at one time: 1 of 4
```

New frontend modules:

```text
apps/web/src/data/evidenceLoaderTypes.ts
  WorkspaceId
  JarvisTabId
  LoaderGroupId
  LoaderGroupState
  LoaderResult

apps/web/src/data/evidenceLoaderManifest.ts
  global safety task registry
  workspace task registries
  Jarvis sticky-core and subtab task registries
  output-key ownership validation

apps/web/src/hooks/useEvidenceLoader.ts
  per-group generation token
  in-flight deduplication
  partial AppData merge
  freshness/error counters
  periodic fast-lane scheduler
```

`App.tsx` remains the owner of `AppData`, active workspace, and active Jarvis
subtab, but no longer owns a 164-entry positional tuple. Every loader returns a
named `Partial<AppData>` so adding an endpoint cannot silently shift tuple
positions.

Required loader ownership:

| Group | Required data |
|---|---|
| `globalSafety` | `auth`, `time`, `mode`, `features`, `killswitch`, `storage` |
| `workspaceLayout` | `layout(active)` |
| `cockpit` | `decision`, `portfolio`, `risk`, `orderPath`, `integrity` |
| `marketdna` | `marketDna`, `microstructure`, `integrity` |
| `behavior` | all current Behavior contract, analysis, memory, validation, benchmark, release, and safety reports |
| `research` | chart/replay-indicator, lifecycle, runtime, Stock DNA, Kronos/Twin, deployment, and OpenAlgo research-proof reports currently rendered there |
| `replay` | `replay`, `replayArchive`, `execution`, `featureRegistry`, `integrity`, `snapshots` |
| `knowledge` | `graph` |
| `implementation` | `features` from the global result; no duplicate request |
| `system` | `aiCredentialStatus`, `pipeline`, `observability`, `audit`, `auditIntegrity`, plus global `storage` and active `layout` |
| `jarvisCore` | decision room/fusion/master, trading decision output, decision quality, realtime freshness, Daily Verified Data Authority, ORB guidance dependencies, and the sticky-ticket safety fields |
| `jarvisTrade` | chart, 9C, indicator/candle memory, MTF/history, AI/Kronos comparison, disagreement, paper reality, trust, usefulness, and action checklist evidence |
| `jarvisEvidence` | manipulated-wick proof, cache, chart QA, latency/cache freshness, replay determinism, export, certificate, and preflight proof |
| `jarvisExecution` | OpenAlgo adapter/handoff/paper-bridge/intent-preview and final paper-readiness evidence |
| `jarvisVault` | production blocker, provider management, refresh/intake/ledger, correction, and external-AI audit evidence |

Scheduling:

```text
startup:
  globalSafety -> workspaceLayout -> active workspace

every 5 seconds:
  time + mode + killswitch

every 30 seconds:
  remaining globalSafety fields + active workspace
  if Jarvis: jarvisCore + active Jarvis subtab

workspace/subtab change:
  increment generation
  mark selected group loading/stale
  load selected group immediately
  ignore responses from older generations

manual Refresh:
  same groups as the current visible surface
  no hidden-workspace request wave
```

State merge rules:

```text
setData(current => ({ ...current, ...successfulGroupPatch }))
undefined/error fields do not erase the last successful value
group status records the error and marks the retained value stale
globalSafety failure sets the root safe/offline banner
non-global group failure never marks unrelated groups offline
stale group data cannot enable a decision or paper action
```

The request manifest must fail tests when:

- one output key is owned by two non-shared groups;
- a rendered `AppData` key has no owner;
- a loader method is added without a group and freshness class;
- a safety key is moved outside `globalSafety`/`jarvisCore`;
- a hidden Jarvis tab method appears in the periodic active-tab request trace.

---

## Shipped ORB continuation v2.01 / v2.02-derivatives (+ plan-track v1.98-v2.00 renamed)

Status: v2.01 classifier + v2.02-derivatives subsystem SHIPPED 2026-09-07
(research-only). Old label `v1.98-v2.00` pre-dated the shipped renumber; the
remaining plan-track items (M2-M6: gap lock, CPR filter, PDH/PDL family, exit
realism, regime filter) still need separate approval + OOS proof. M1
(`orb/context.py`) is built standalone-only, not wired into `orb/core.py`.

1. M1 (v1.98) context-native core: new `orb/context.py` (gap/CPR/PDH-PDL/session-VWAP/ATR, PIT-guarded), `OrbBuildRequest.previous_day`, live-path prev-day wiring from the behavior pipeline, unknown-context fail-open policy, causal whitelist v0.15, per-day context precompute.
2. M2 (v1.98) gap bias-lock + large-gap trap protocol; M3 (v1.98) CPR wide/narrow family filter.
3. M4 (v1.99) `pdh_pdl_breakout` strategy family; prerequisite: unify `_backtest_day` stop semantics with signal stop (pre-existing reversal inconsistency).
4. M5 (v1.99) execution realism: 1R-half/trail exits, capital-risk `size_hint` upgrade, daily circuit breaker inside the explicit-approval paper flow, liquidity-tier slippage.
5. M6 (v2.00) OR-width regime filter, re-entry rule, raised proof thresholds (minimum overall trades >= 30).

Specs: `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` (milestones + §7–§10 addenda) · `docs/plans/ORB_STRATEGY_MEMORANDUM.md` **v2.4** (rule-level entry/stop/target, rule IDs incl. EVENT/UNIV/IDX/VIX/DERIV/EXP/AFT/VWAP/EXH/MKT/EXEC layers + calibration register §7A.7/§7A.9, worked examples) · `docs/plans/ORB_V2_JUDGE_FINDINGS.md` (six passes incl. 09-03 audit) · verbatim archives, all four submissions byte-exact: `ORB_V201_PRECODE_REVIEW_KIMI.md` (sub 1, retro) + `ORB_V201_NSE_REVIEW_KIMI.md` + `ORB_V201B_NSE_REVIEW_KIMI_PART2.md` + `ORB_V201C_NSE_REVIEW_KIMI_PART3.md` · `docs/plans/ORB_V201_VERIFIED_ANSWER.md` (§1–§9: four submissions verified + provenance note).

v2.2–v2.4 scope addition (three Kimi submissions): NSE Tuesday-expiry protocol (SEBI-verified 01-Sep-2025) + **EXP-07 calendar-file mandate** (no weekday constants), event/corporate-actions calendar gate (un-deferred), universe hygiene (shorts F&O-only; both-direction first-bar guards; chop guards; spread >0.1% + dual-source tick halt), index-alignment + sector-divergence gates, staged derivatives overlay (ALERT_ONLY until ledger-proven) incl. dividend/rollover basis mechanics + participant-OI weekly tag, separate afternoon playbook (3 variants to calibrate) with level-staleness principle, STOP-01 `or_width_conditional` stop default (triple-confirmed), sharpened REENTRY-01 trap signature (triple-confirmed), ENTRY-03/04 time-based entry rules (triple-confirmed), CHASE-01 no-chase, ORPDC-01 contested open, EXIT-07 post-breakout management, ORW-MID band, promotion bar n>=60 OOS; majority-prior mechanism for cross-submission thresholds.

Acceptance:

- cheapest pre-test run before engine code, **pre-registered** (H1/H2/H3 incl. the CPR-vs-close-location redundancy check; n>=30/cell; Mann-Whitney + effect size; Holm correction; per-layer go/no-go);
- rule spec is memo v2.2 — every test cites a rule ID (GAP/TRAP/CPR/ZONE/EXIT/CTX + EVENT/UNIV/IDX/VIX/DERIV/EXP/AFT);
- every gate output carries a measure code (SKIP_DAY / DELAY_ENTRY / HALF_SIZE / WIDEN_STOP / TIGHTEN_TARGET / VETO_DIRECTION / FLIP_BIAS / REDUCE_FREQUENCY / ALERT_ONLY) and a PIT stamp (@0915 / @SIG / EOD-OK / PARTIAL);
- no derivatives gate touches size until the ledger proves it (n>=30 OOS); GEX/charm stay ALERT_ONLY;
- backtester stop parity: each playbook's `stop_mode` is proven identical between `_backtest_day` and production rules;
- every new output stays research-only (`trade_allowed=false`, `live_trading_blocked=true`);
- leak-proof test proves no D-1 bar is ever used for a D decision;
- fail-open on unknown context, never fabricated context;
- all thresholds are repo constants or single config keys (no parallel constants);
- state.py feature rows + GATES/SPEC/TEST_PLAN/ARCHITECTURE updates per version.

---

## Approved campaign: ORB v2.02 Repair & Integration (Candidate 2, capture-first)

Status: APPROVED 2026-09-07 (user authorization in conversation). Implementation
NOT started. Full milestone plan: `docs/plans/ORB_V202_REPAIR_PLAN.md` (G0–G12,
each with purpose / files / preconditions / intent / tests / acceptance /
rollback / evidence / next-gate dependency).

Order: G0 capture oracle (BLOCKING) → G1–G4 provider/hardening → G5 PIT-critical
(+PIT-004 wrong-expiry) → G6–G8 replay/health/store → G9 v1.73 + G10 AFRE wiring
(only after G0–G8 green) → G11 provenance → G12 walls/policy → test wave → full
regression → SHADOW acceptance. Pivot: capture contradiction or no creds →
Candidate 3 (isolate-and-defer), no synthetic vendor fixtures. SHADOW invariants
hold throughout (AFRE OFF, derivatives OFF, no live profile, no order authority).
