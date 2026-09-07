# Trade Vision README

> **Filename:** `TRADE_VISION_README.md` — Trade Vision product entry.  
> **Not Stock App.** Stock App entry: `../STOCK_APP_README.md`.  
> **Architecture:** `ARCHITECTURE.md` (this folder).

---

Production research implementation copy for Trade Vision inside the current `stock-app` project.

Original source-of-truth design vault:

```text
D:\trade vision\our-design
```

Master plan:

```text
D:\trade vision\our-design\TRADE_VISION_MASTER_PRODUCTION_PLAN.md
```

## Current Project State

```text
latest_completed_version = v2.02-derivatives
latest_functional_version = v2.02-derivatives
current_mode = research / mock / paper-review only
live_trading = blocked
order_routing = blocked inside Trade Vision
broker_credentials = not created by Trade Vision
tip_authority = docs/IMPLEMENTATION_STATUS.md (this block defers to it on conflict)
```

`v1.87-v1.94` provide the strict closed-candle Paper Guidance spine,
snapshot-bound evidence, session-safe ORB generation, offline discovery/proof,
the Jarvis ORB guidance screen, and an explicitly human-approved local
simulated paper ledger. v1.94 adds explicit replay lifecycle observation,
cost-aware deterministic outcomes, completed-only reliability, and atomic
store monitoring. ORB proposes a setup; D6 remains final authority.

`v1.96-v1.99` add the Indicator Intelligence Catalog (94 evidence-backed
contracts), the ORB Timing Research engine (per-stock 09:20/09:30/09:35/09:40
clock-window study on local HSTRY history, with API + Research-tab panel),
real HSTRY candles in the 9C evidence path (synthetic fallback labelled),
and complete safe indicator coverage: 49 of 94 indicators compute at runtime,
registry 86 validated / 7 proxy / 1 blocked, and the silently-dead PTA marker
stack (v1.86-v1.98) is fixed.

`v2.01` adds the ORB opening classifier (`apps/api/app/orb/context.py`:
gap/CPR/PDH-PDL/session-VWAP/ATR, `classify_opening`, standalone research-only,
not yet wired into `orb/core.py`; 8 scenario gates passed).

`v2.02-derivatives` installs the ORB Derivatives Intelligence subsystem
(`apps/api/app/orb/derivatives/`, 15 modules, OFF-by-default dormant, ATR parity:
SMA-seeded Wilder canonical, IV/skew surfacing warn/info only; 22/22 gates
passed in host). No trading authority change: research-only, live blocked.

Verified 2026-09-07: full backend 1215 passed / 0 failed / 4 skipped (composition:
939 repair-wave baseline + 12 repair-test growth + 20 tradeplan kernel + 230 D6
vendored + 14 D6 adapter; tip authority IMPLEMENTATION_STATUS). D6 dormant,
vendor half parked for G0 capture. Frontend typecheck/build passed (v1.97;
no frontend change since).

## What Trade Vision Is

Trade Vision is a safety-first trading research cockpit. It is designed to answer:

```text
What is happening now?
Has this stock done this before?
What happened after that?
Which evidence agrees or conflicts?
Where is the trade wrong?
Should the operator WAIT, WATCH, or mark a PAPER-CANDIDATE?
```

It is not a live autonomous trading bot.

## Important Handoff Files

Read these first:

```text
TRADE_VISION_README.md              ← this file (includes AI handoff, merged)
docs\FILE_DOCUMENT_INDEX.md         ← single map (§0.6 Q→file · §7.4 ownership · Flow map pack)
ARCHITECTURE.md                     ← operator map + MASTER GUIDE
docs\plans\FINAL_REQUIRED_FLOW.md   ← required paper-guidance product spine
docs\IMPLEMENTATION_STATUS.md       ← latest tip + full ship log
docs\NEXT_BUILD_TARGET.md
docs\SAFETY_INVARIANTS.md
docs\context.md + docs\graph.md     ← deep domain / structure
```

## How the system flows (paper path)

Open these when you need the **Start → End** picture (not the full ship log):

```text
docs\TV_COMPLETE_FLOW_MAP.html   ← ALL-IN-ONE (Tabs 1–5)
  Tab 1 process · Tab 2 network · Tab 3 block details
  Tab 4 fit · Tab 5 code-truth + map audit + work log (merged MDs)
docs\PROJECT_BRAIN.html          ← 10-minute plain-English cards
docs\FILE_DOCUMENT_INDEX.md      ← Flow map pack + full doc router
```

| Need | File |
|------|------|
| Interactive map | `docs/TV_COMPLETE_FLOW_MAP.html` Tabs 1–2 |
| Fast “what is each block?” | `docs/PROJECT_BRAIN.html` or HTML Tab 3 |
| Exact Python spine | HTML **Tab 5** (former VERIFIED_…md merged) |
| Map audit / work history | HTML **Tab 5** (former implementation_plan + work log merged) |

Former MDs **removed after merge:** `FLOW_MAP_WORK_LOG.md`, `FLOW_MAP_NODE_EXPLAINER.md`, `VERIFIED_PAPER_FLOW_FROM_CODE.md`, graph `implementation_plan.md`.

Live trading stays **blocked**. TV local paper ledger ≠ Stock App `sim_trading.db`.

## AI / New-Chat Handoff (merged from former `docs/AI_HANDOFF_CONTEXT.md`)

> **Merged 2026-07-24 into this README.** Do **not** recreate `docs/AI_HANDOFF_CONTEXT.md`.  
> **Alignment check (2026-09-07):** former handoff tip said **v1.87** / next v1.88, later corrected to **v1.94** — both now **stale**. Current tip is **v2.02-derivatives** per `IMPLEMENTATION_STATUS` (914 passed).  
> **Safety rules** still live in short form in `docs/SAFETY_INVARIANTS.md` (do not merge law into ship log).  
> **Product spine requirement:** `docs/plans/FINAL_REQUIRED_FLOW.md`.  
> **Per-version ship diary authority:** `docs/IMPLEMENTATION_STATUS.md` (tip + full log). Historical notes below are preserved from the former handoff and may lag wording of the ship log — if conflict, **IMPLEMENTATION_STATUS wins**.

### Purpose

Give a new AI/chat the minimum context needed to continue this project without rereading the whole repository.

Prefer for full domain/structure: `docs/context.md` + `docs/graph.md` + `ARCHITECTURE.md`.

### Current working path

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app
```

### Current confirmed build state (aligned 2026-09-07; authority: docs/IMPLEMENTATION_STATUS.md)

```text
latest_completed_version = v2.02-derivatives
latest_completed_title = Derivatives Subsystem Live (dormant) - Greeks/chain analytics ready for future broker data
latest_completed_status = implemented-and-verified (derivatives 22/22; ATR parity DONE; repair wave 26 passed; D6 M2 adapter 14 green; full backend 1215 passed / 0 failed / 4 skipped)
last_full_backend_regression = 1215 passed (0 failed, 4 skipped), 2026-09-07
latest_focused = v2.02-repair 26 passed (vendor half parked for G0); v2.01 scenarios 8 passed; v1.97 timing 10 passed; BEL re-proof ELIGIBLE (combo ba1121c6, WF 3/4)
latest_ui = typecheck/build passed (v1.97; no frontend change since)
current_mode = research / mock / paper-review only
live_trading = blocked
order_routing = blocked inside Trade Vision
broker_credentials = not created by Trade Vision
OpenAlgo = external future execution / simulator boundary — not TV live authority
TrendForge = signed research intake only (loopback default, HMAC, safety envelope)
```

**Paper-guidance / ORB authority (FINAL_REQUIRED_FLOW + ARCHITECTURE v1.88–v1.94):**

```text
ORB proposes primary entry/stop/target setup (when playbook/evidence allows).
D6 final confluence arbiter alone produces final_band.
Human alone approves local simulated paper record (v1.93+).
No live broker order; no auto-write to Stock App sim_trading.db from TV.
```

**Spine entry points (still valid; extended after v1.87 P0):**

```text
POST /api/v1/paper-guidance/run
apps/api/app/behavior/paper_guidance_spine.py
apps/api/app/behavior/paper_guidance_config.py
apps/api/tests/test_paper_guidance_spine.py
apps/api/app/behavior/orb_guidance.py
apps/api/app/behavior/simulated_paper_ledger.py
apps/api/app/behavior/final_confluence_arbiter.py
```

**P0 D1/D2 behavior (still true):**

- D1 failure returns WAIT and mints no snapshot hash.
- D2 freezes only fully closed candles and produces a deterministic SHA-256 snapshot hash.
- P0-era band floor was WAIT/WATCH only; later versions add ORB ticket + human-approved local paper record with hard gates.
- No OpenAlgo live route, broker order, or live trade from these paths.

**Next build:** see `docs/NEXT_BUILD_TARGET.md` (as of 2026-07-24: **no approved next version**; proposed v1.95 active-evidence / API fast-lane — not locked).

### First files to read (new chat)

```text
1. TRADE_VISION_README.md  (this file — handoff + how-to map)
2. docs/IMPLEMENTATION_STATUS.md  (latest tip at top; one version section if needed)
3. docs/SAFETY_INVARIANTS.md
4. docs/NEXT_BUILD_TARGET.md
5. docs/plans/FINAL_REQUIRED_FLOW.md  (if paper-guidance product work)
6. docs/FILE_DOCUMENT_INDEX.md §0.6 then §7.4 as needed
7. docs/context.md + docs/graph.md + ARCHITECTURE.md for deep domain/structure
8. docs/API_ENDPOINT_INDEX.md / FRONTEND_PANEL_MAP.md if touching routes/UI
9. docs/plans/... only if implementing that roadmap slice
```

Do **not** start with `apps/api/app/main.py` or `apps/web/src/App.tsx` (too large).

### Product intent

Trade Vision is a research-first trading intelligence system. It should explain:

```text
What is happening now?
Has this stock done this before?
What happened after that?
Which evidence agrees or conflicts?
Where is the trade wrong?
Should the operator WAIT, WATCH, or mark a PAPER-CANDIDATE?
```

It must **not** act as an autonomous live trading bot.

### Current high-priority roadmap (completed sequence; tip = v1.94)

```text
v1.62 - Context maintenance and graph refresh
v1.63 - Real MTF Pullback Engine
v1.64 - Indicator Result Cache Completion
v1.65 - Indicator Cache Frontend Controls
v1.66 - Golden Fixture Regression Pack
v1.67 - TV-PROD-RED-001 Final Red-Team Gate
v1.68 - Performance and latency budget hardening
v1.69 - Release-readiness evidence refresh
v1.70-v1.75 - Max chart reasoning expansion
v1.76 - Full Indicator Intelligence Ontology (heritage → v1.80)
v1.77 - Indicator Reliability Memory (heritage → v1.81)
v1.78 - Sequential Indicator Causality Engine (preserve event_sequence_mining wiring)
v1.79 - Indicator Conflict and Redundancy Arbiter (preserve redundancy/confluence wiring)
v1.80 - Indicator Intelligence Contract + Ontology + Lag-Aware Voting
v1.81 - Per-Indicator Reliability Memory + Outcome Labeling Bridge
v1.82 - Full Timeframe Contract Expansion + Indicator Reliability UI Drilldown
v1.83-v1.85 - Indicator signal history store / ingest / complete-pending
v1.86 - Signed TrendForge research intake
v1.87 - Paper Guidance Spine P0 (D1/D2)
v1.88-v1.94 - Snapshot evidence, ORB campaign, Jarvis ticket, human paper record, lifecycle feedback
```

Authoritative detail per version: `docs/IMPLEMENTATION_STATUS.md`.

### Latest user requirements to preserve

- Use all indicator outputs intelligently, not just list them.
- Each indicator needs an intelligence contract: purpose, category, regime fit, timeframe fit, lag behavior, failure modes, conflict rules, confirmation rules, trade/risk/no-trade usage, reliability, and explanation/probability eligibility.
- Use `confirmation_delay_bars` as a vote weight. Late MACD/MA confirmation cannot create false confidence.
- Use Bayesian shrinkage and minimum sample gates before any per-indicator reliability can influence probability.
- Track sequential signal causality, not only same-candle agreement.
- Compare candle body/wick/no-wick ratios and prior candles as causes/effects for current candle behavior.
- Preserve 9-candle DNA, all-indicator feature bank, winner/failure memory, FAISS/analog fallback, batch-only model learning, calibrated probability, and WAIT-first safety.
- Show decision details with chart, indicators, entry, stop, target, invalidation, and explanation.
- External AI review must be display-only, evidence-bound, schema-checked, and unable to override Trade Vision safety.
- Paper path: one organized guidance spine (FINAL_REQUIRED_FLOW); human approve before simulated paper record; no live v1.

### Do not touch without explicit approval

```text
Do not enable live broker order routing.
Do not store browser sessions, cookies, or hidden login tokens.
Do not let Gemini, Grok, Kronos, OpenAlgo, or any model override no-trade/risk gates.
Do not delete legacy stock-app references.
Do not delete mock/replay paths when adding real paths.
Do not remove existing plan content while merging; append or clearly supersede.
Do not auto-POST Stock App sim_trading.db fills from Trade Vision without an explicit approved product design.
```

### Important current architecture (high-signal paths)

```text
apps/api/app/main.py                          Large FastAPI route surface
apps/api/app/models.py                        Contract models
apps/api/app/behavior/indicator_registry.py   Registry; confirmation_delay_bars
apps/api/app/behavior/real_mtf_pullback.py    Closed-candle MTF pullback/opposition
apps/api/app/behavior/indicator_result_cache.py  Reference-only cache
apps/api/app/behavior/final_confluence_arbiter.py  D6 reduce-only final band
apps/api/app/behavior/paper_guidance_spine.py D1/D2 paper guidance spine
apps/api/app/behavior/orb_guidance.py         ORB guidance ticket path
apps/api/app/behavior/simulated_paper_ledger.py  Human-approved local paper record
apps/web/src/App.tsx                          Main frontend shell (still large)
apps/web/src/components/                      Extracted frontend components
docs/IMPLEMENTATION_STATUS.md                 Latest tip + full ship log
docs/plans/FINAL_REQUIRED_FLOW.md             Required product spine
docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md  Long-range memory plan
docs/plans/TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md  Chart reasoning plan
docs/graph/project_graph.json                 Machine project graph
docs/FILE_DOCUMENT_INDEX.md                   Map: §0.6 Q→file · §7.4 ownership
docs/SAFETY_INVARIANTS.md                     Non-negotiable safety law
```

### Fast continuation rule + context maintenance (merged from `CONTEXT_MAINTENANCE_RUNBOOK.md`)

> **Merged 2026-07-24.** Do **not** recreate `docs/CONTEXT_MAINTENANCE_RUNBOOK.md`.  
> Purpose: keep handoff/docs fresh so future chats use fewer tokens and do not follow stale plans.

**Before coding:** confirm the next target from `docs/NEXT_BUILD_TARGET.md`.

**After every completed version, update:**

```text
docs/IMPLEMENTATION_STATUS.md          (latest tip block + append version section)
TRADE_VISION_README.md                 (this AI Handoff tip + MASTER GUIDE if needed)
docs/NEXT_BUILD_TARGET.md              (lock/clear next; verification snapshot)
```

**When structure changes (routes, panels, ownership, graph):**

```text
docs/graph/project_graph.json
docs/graph.md
docs/context.md
docs/FILE_DOCUMENT_INDEX.md            (§0.6 questions · §7.4 ownership as needed)
docs/FRONTEND_PANEL_MAP.md
docs/API_ENDPOINT_INDEX.md
docs/TEST_ID_INDEX.md
ARCHITECTURE.md / this README MASTER GUIDE if operator map or tip changes
```

**When requirements or plans change:**

```text
SPEC.md
ARCHITECTURE.md
TEST_PLAN.md
docs/plans/* only for the plan you are actively changing
docs/plans/FINAL_REQUIRED_FLOW.md if paper-guidance spine changes
```

**No-delete rule:** Do not delete old files during context maintenance.  
If data is duplicated: merge current facts into the living file, keep path notes in `FILE_DOCUMENT_INDEX`, mark stale, **ask before deleting or archiving**.

**Fast audit ideas:**

```text
Select-String -Path docs/IMPLEMENTATION_STATUS.md -Pattern "^## v" | Select-Object -Last 20
# routes:
#   search apps/api/app/main.py for @app.get / @app.post ...
```

### External AI credentials (current design)

Read first: `docs/runbooks/EXTERNAL_AI_CREDENTIALS_RUNBOOK.md`.

Gemini API keys are saved from `Jarvis -> Ops & Audit Vault -> AI Credential Vault` into the encrypted backend vault:

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\data\secrets\ai_credentials.enc
```

The vault is unlocked by:

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\data\secrets\tradevision_secret.key
```

Grok local gateway settings are stored in:

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\data\secrets\grok_gateway.local.json
```

Do **not** build Grok browser username/password, cookie capture, session capture, or hidden web replay into Trade Vision. Use API keys, a localhost gateway, or manual review paste-in only.

### Historical version notes (preserved from former AI_HANDOFF — detail authority = IMPLEMENTATION_STATUS)

The former handoff listed detailed endpoint/module notes for **v1.63 through v1.82** (MTF pullback, indicator cache, golden fixtures, red-team gate, final-audit cache, chart reasoning, regime feedback, structure/liquidity, execution risk, post-entry lifecycle, final confluence arbiter, lag voting, reliability memory, nine timeframes). Those notes remain **correct as historical design/ship notes** and are **fully superseded for “what is latest?”** by:

```text
docs/IMPLEMENTATION_STATUS.md  → Latest completed tip (v1.94) + Full ship log sections
ARCHITECTURE.md                → living contracts + v1.88–v1.94 sections
```

Do **not** treat the old “Next target is v1.88” sentence as current (removed).  
Full regression counts in the former handoff (471…533 passed era) are **historical**; current full backend cite is **715 passed (2026-07-24)** unless IMPLEMENTATION_STATUS tip is updated later.


## Product required spine (`FINAL_REQUIRED_FLOW`)

> **Authority:** `docs/plans/FINAL_REQUIRED_FLOW.md` is the **single product requirement** for one paper-guidance flow.  
> **Aligned 2026-07-24** with `ARCHITECTURE.md` + code (`paper_guidance_spine`, D6 arbiter, ORB guidance, `simulated_paper_ledger`).  
> **Merged into that file (full text):**  
> - **Appendix A** — former `PAPER_TRADE_SPINE_AI_BRIEF.md` (external-AI build pack)  
> - **Appendix B** — former `THINK_ENGINE_BEST_FLOW_REASONING.md` (engine order why/when)  
> **Do not recreate** those two plan files.  
> This README section is a **compass only** — full requirement/phases/gaps live in the plan file.

### One sentence

```text
Enter a stock → one organized analysis + label + decide pipeline
  → one paper-trade guidance (WAIT / WATCH / ENTER_PAPER / AVOID / SKIP)
  → optional human APPROVE → paper record/result (no live broker)
```

### Authority (v1.88–v1.94)

```text
ORB proposes primary setup (when playbook/evidence allows).
D6 arbiter alone produces final_band.
Human alone approves local simulated paper record (v1.93+).
No live broker order. No auto Stock App sim_trading.db fill from TV.
```

### Roles

| Role | Rule |
|------|------|
| Evidence | Vote only (chart, structure, ML, reliability, ORB playbook match…) |
| Gate | Block/reduce only (PIT, kill switch, liquidity, low evidence) |
| Arbiter | Only final band (D6) |
| Executor | After human approve only (TV local ledger and/or Stock App sim) |

### Where to read full detail

| Need | Open |
|------|------|
| Full requirement + gaps + phases | `docs/plans/FINAL_REQUIRED_FLOW.md` **body** |
| External-AI build-plan pack | same file **Appendix A** |
| Why/when engine order (Flow R/D) | same file **Appendix B** |
| Living contracts / operator map | `ARCHITECTURE.md` |
| What shipped | `docs/IMPLEMENTATION_STATUS.md` tip |

## System graph (how to use)

> **Full human graph + how-to:** `docs/graph.md` (includes former `graph.md §0` at §0).  
> **Machine twin:** `docs/graph/project_graph.json` via `GET /api/knowledge/graph`.  
> **Aligned 2026-07-24:** code `KNOWLEDGE_GRAPH_PATH` → project_graph.json; graph is **orientation only**.  
> **Not** the product spine — that is `FINAL_REQUIRED_FLOW.md`. **Not** live-trade authority.

```text
docs/graph.md                   human Mermaid / authority map
docs/graph/project_graph.json   machine map for Knowledge UI / API
```

**Use for orientation only.** For implementation detail read:

```text
TRADE_VISION_README.md § AI Handoff (this file)
docs/FILE_DOCUMENT_INDEX.md §0.6
docs/IMPLEMENTATION_STATUS.md
docs/plans/FINAL_REQUIRED_FLOW.md
ARCHITECTURE.md
```

**Refresh graph** when: major version ships, new panel/route family, new safety invariant, new external integration, or material roadmap change.  
**After ship:** README § AI Handoff → Fast continuation + context maintenance.

## TrendForge Integration

Trade Vision can pull signed TrendForge scanner evidence from
`http://127.0.0.1:8001`. Configure the same dedicated HMAC secret in
`TRENDFORGE_TRADEVISION_SHARED_SECRET` on TrendForge and
`TRADEVISION_TRENDFORGE_SHARED_SECRET` on Trade Vision.

```text
TrendForge scanner
  -> signed evidence packet
  -> POST /api/v1/integrations/trendforge/pull-latest
  -> validated, idempotent local intake
  -> research review only
```

This route does not submit orders. Rejected and WAIT candidates are retained
for audit/ML context. Only future confirmed candidates may be considered by a
separately authorized OpenAlgo Analyzer/paper execution phase.

Then read:

```text
docs\IMPLEMENTATION_STATUS.md
docs\plans\TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md
docs\plans\TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md
SPEC.md
ARCHITECTURE.md
TEST_PLAN.md
```

Machine-readable graph:

```text
docs\graph\project_graph.json
```

Graph guide:

```text
docs\graph.md (§0 how-to)
```

## Current Major Capabilities

- FastAPI backend with typed contracts.
- React + Vite + TypeScript workspace cockpit.
- Backend-owned time state.
- System mode watermark.
- Kill switch state and trigger/reset API.
- Capability manifest and safety gates.
- Deterministic replay and replay evidence panels.
- Point-in-time snapshots and feature versioning.
- Behavior intelligence endpoints.
- Jarvis decision room.
- Gemini/Grok external AI review surfaces, display-only and safety-bound.
- Kronos/Twin Machine research integration surface.
- OpenAlgo-safe paper-review handoff boundaries.
- Indicator registry, 9C DNA, indicator cache, analog/research route families.
- Persistent indicator signal history and explicit current-signal ingestion.
- Nine-timeframe backend contract: `1m`, `3m`, `5m`, `15m`, `30m`, `1H`, `4H`, `daily`, `weekly`.
- Closed-candle chart reasoning and volatility-regime evidence route.
- Market-regime, breadth, relative-strength, and Bayesian feedback evidence route.
- Context-maintenance handoff files for future AI/chat continuity.

## Current Future Roadmap Focus

```text
v1.70-v1.75 - Max chart reasoning expansion
v1.76 - Full Indicator Intelligence Ontology (requirement heritage; implemented by v1.80)
v1.77 - Indicator Reliability Memory (requirement heritage; implemented by v1.81)
v1.78 - Sequential Indicator Causality Engine (preserve existing event_sequence_mining.py wiring)
v1.79 - Indicator Conflict and Redundancy Arbiter (preserve existing redundancy/confluence wiring)
v1.80 - Indicator Intelligence Contract + Ontology + Lag-Aware Voting
v1.81 - Per-Indicator Reliability Memory + Outcome Labeling Bridge
v1.82 - Full Timeframe Contract Expansion + Indicator Reliability UI Drilldown
v1.83 - Persistent Indicator Signal History Store + Reliability Drilldown Frontend Rendering
v1.84 - Current Closed-Candle Indicator Signal History Ingestion
v1.85 - Pending Indicator History Outcome Completion
```

Critical indicator rule:

```text
confirmation_delay_bars must reduce late indicator voting power.
Lagging indicators cannot create false confidence.
```

Latest implemented reasoning layer:

```text
v1.85 - Pending Indicator History Outcome Completion
```

What it adds:

```text
Pending indicator history rows can be completed only from explicit future-bar evidence.
Rows stay pending when the supplied future bars do not complete the stored horizon.
Same-bar target/stop ambiguity uses conservative stop-first labeling.
Completed labels can feed research reliability but cannot approve a trade.
No timeframe, indicator, ingestion action, completion action, or reliability report can create live trading, broker routing, or external-AI override authority.
```

## Local Development

Backend:

```powershell
cd "D:\Projects\trading-platforms\stock-app\trade-vision-app"
py -m venv .venv
.\.venv\Scripts\pip install -r apps\api\requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir apps\api --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd "D:\Projects\trading-platforms\stock-app\trade-vision-app"
npm install
npm run dev
```

Build/test:

```powershell
npm run build
.\.venv\Scripts\python -m pytest apps\api\tests
```

## Safety Boundary

Trade Vision must remain:

```text
research-first
WAIT-first
paper-review only
no live broker routing
no hidden browser/session capture
no external-AI override
no model override of risk/no-trade gates
```

See:

```text
docs\SAFETY_INVARIANTS.md
```

---

---


---

## Appendix A — Historical version notes (from former `docs/AI_HANDOFF_CONTEXT.md`)

> **Preserved for zero data loss.** These sections document endpoints, modules, tests, and safety flags for **v1.63–v1.82** as written in the former handoff.  
> **Authority for “what shipped / is latest”:** docs/IMPLEMENTATION_STATUS.md (tip = **v1.94**).  
> **Do not** treat older “full backend N passed” counts below as the current regression tip (current tip: **715 passed**, 2026-07-24).  
> **Do not** treat “Next target is v1.88” (removed from live tip) as current — see NEXT_BUILD_TARGET.md.

## Latest v1.63 Additions

```text
GET  /api/v1/behavior/timeframes/pullback/current
POST /api/v1/behavior/timeframes/pullback
Behavior Real MTF Pullback Engine capability
Real MTF Pullback v1.63 behavior panel-map entry
tests: test_v163_* in apps/api/tests/test_api.py
```

What it does:

```text
Consumes the existing closed-bar timeframe matrix. The legacy field/route names may still say `seven-timeframe`, but v1.82 payloads now include `1m, 3m, 5m, 15m, 30m, 1H, 4H, daily, weekly`.
Classifies pullback_in_trend, trend_continuation, htf_opposition, developing_blocked, mixed_context, or range_or_unavailable.
Returns WAIT/WATCH/AVOID only.
Keeps trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.64-v1.65 Additions

```text
Indicator Result Cache module version: indicator-result-cache.v1.64
Indicator Cache frontend controls: v1.65 completed in Jarvis Evidence & Data Lab
ICACHE-001 through ICACHE-020 are executable and passing.
Cache rows are keyed by exact source snapshot, timeframe, registry version, feature manifest version, promoted indicator hash, and indicator ID.
Artifacts are SHA-verified before read/reuse.
Anomalous snapshots are quarantined.
Cache output is reference-only: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.66 Additions

```text
Golden replay regression pack seeds **16** deterministic fixtures (6 legacy + 10 `golden_9c_*` including fake_breakout).
Scenario coverage **family** list is **15** names in `REQUIRED_SCENARIO_FAMILIES` (no separate `fake_breakout` family token).
Scenario coverage version is behavior-scenario-coverage.v1.66.
New 9C/chart-risk fixtures include clean breakout, fake breakout, VWAP rejection, choppy, gap continuation, low volume, HTF lookahead trap, confluence support/resistance, and OOD unknown.
Focused v1.66 golden/scenario tests passed.
Broader release/golden subset passed.
Full backend regression passed with workspace TEMP/TMP override: 471 passed.
Fixtures are replay/mock evidence only and cannot promote probability, paper candidate, or live routing.
```

## Latest v1.67 Additions

```text
Final release audit version is tradevision-final-release-audit.v1.67.
TV-PROD-RED-001 is now a blocking final release audit gate.
The release manifest includes apps/api/app/behavior/red_team_final_gate.py.
A failed manipulated-wick red-team report blocks production_research_release_candidate.
Focused final-audit/red-team tests passed: 5 passed.
Full backend regression passed with workspace TEMP/TMP override: 472 passed.
Red-team output remains research-only and cannot promote probability, paper candidate, order routing, or live trading.
```

## Latest v1.68 Additions

```text
Final release audit version is tradevision-final-release-audit.v1.68.
Final audit now builds security/readiness/smoke evidence once and reuses it inside the audit.
A short-lived identity-aware final-audit cache was added for repeated Jarvis/release calls.
The cache key includes dependency function identities and relevant non-secret environment state.
Monkeypatched or changed TV-PROD-RED-001 failure evidence bypasses the cache and still blocks release.
Focused final-audit/red-team/performance subset passed: 7 passed.
Full backend regression passed with workspace TEMP/TMP override: 473 passed.
First uncached local final audit measurement: 7242.32 ms.
Cached repeated local final audit measurements: 0.40 ms and 0.33 ms.
```

## Latest v1.69 Additions

```text
New endpoint: GET /api/v1/release/readiness-evidence
New module: apps/api/app/behavior/release_readiness_evidence.py
New contracts: ReleaseReadinessEvidenceGate and ReleaseReadinessEvidenceReport
The report summarizes final audit, safety scan, release manifest, blocking gates, missing artifacts, final-audit cache TTL, and evidence source endpoints.
force_refresh=true bypasses the short-lived final-audit cache for an explicit evidence refresh.
Focused release-audit/readiness subset passed: 7 passed, 468 deselected.
Full backend regression passed: 475 passed.
Safety remains unchanged: trade_allowed=false, can_execute_orders=false, can_export_to_openalgo=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.70 Additions

```text
New endpoints:
POST /api/v1/behavior/chart/reasoning/analyze
GET /api/v1/behavior/chart/reasoning/current

New module:
apps/api/app/behavior/chart_reasoning_volatility.py

New contracts:
ChartReasoningRequest
ChartReasoningGate
ChartReasoningReport

The report computes closed-candle chart/volatility evidence:
rejection index, candle acceleration, candle mass index, micro-trend slope, EMA distance/tangled state, hidden divergence flags, oscillator exhaustion, Hurst exponent, fractal dimension/noise, ATR/HV/BB-width percentiles, volatility regime, VCP contraction, and volume dry-up.

Focused v1.70/candle/envelope subset passed: 7 passed, 472 deselected.
Full backend regression passed with workspace TEMP/TMP override: 479 passed.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.71 Additions

```text
New endpoints:
POST /api/v1/behavior/market-regime/feedback
GET /api/v1/behavior/market-regime/feedback/current

New module:
apps/api/app/behavior/market_regime_feedback.py

New contracts:
MarketRegimeFeedbackRequest
MarketRegimeFeedbackGate
MarketRegimeFeedbackReport

The report computes market-regime, breadth, relative-strength, and Bayesian feedback evidence:
market_context_status, trend_state, breadth_state, relative_strength_score, relative_strength_position, rolling_correlation_to_index, leading_lagging_state, posterior_confidence, stock_specific_edge, recent_failure_penalty, dynamic_confirmation_requirement, cooldown_active, and confidence_cap.

Focused v1.71/market-context/envelope subset passed: 8 passed, 476 deselected.
Full backend regression passed with workspace TEMP/TMP override: 484 passed.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true, no_live_weight_mutation=true.
```

## Latest v1.72 Additions

```text
New endpoints:
POST /api/v1/behavior/market-structure/liquidity/analyze
GET /api/v1/behavior/market-structure/liquidity/current

New module:
apps/api/app/behavior/market_structure_liquidity.py

New contracts:
MarketStructureLiquidityRequest
MarketStructureLiquidityGate
MarketStructureZone
MarketStructureLiquidityReport

The report computes Volume Profile POC/VAH/VAL/HVN/LVN, profile shape, TPO POC/value area/single prints, VSA effort-result state, equal-high/equal-low pools, sweep direction, order block, FVG, BOS/CHoCH, Wyckoff phase, trap score, stop-hunt score, and confidence cap.

Focused v1.72/envelope subset passed: 7 passed, 483 deselected.
Full backend regression passed: 490 passed, 1 warning.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.73 Additions

```text
New endpoints:
POST /api/v1/behavior/execution-event-oi/risk/analyze
GET /api/v1/behavior/execution-event-oi/risk/current

New module:
apps/api/app/behavior/execution_event_oi_risk.py

New contracts:
ExecutionEventOiRiskRequest
ExecutionEventOiRiskGate
ExecutionEventOiRiskReport

The report computes fill probability, slippage risk, impact cost percent, liquidity grade, execution plan status, depth status, single-wick entry risk, gap-through-entry risk, event risk score, earnings adjustment, expiry pinning risk, expected-move target cap, gamma-wall context, max-pain magnet, and confidence cap.

Focused v1.73/envelope subset passed: 7 passed, 489 deselected.
Full backend regression passed: 496 passed, 1 warning.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.74 Additions

```text
New endpoints:
POST /api/v1/behavior/post-entry/lifecycle/analyze
GET /api/v1/behavior/post-entry/lifecycle/current

New module:
apps/api/app/behavior/post_entry_lifecycle.py

New contracts:
PostEntryLifecycleRequest
PostEntryLifecycleGate
PostEntryLifecycleReport

The report computes trade_state, current_thesis_status, exit_plan, partial_exit_plan, current_stop_loss, trailing_stop, invalidation_trigger, thesis_downgrade_reason, add_on_allowed, confidence_adjustment, and simulation_actions after a hypothetical entry.

Focused v1.74/envelope subset passed: 7 passed, 495 deselected.
Full backend regression passed: 502 passed, 1 warning.
Safety remains unchanged: simulation_only=true, used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.75 Additions

```text
New endpoints:
POST /api/v1/behavior/final-confluence/arbiter/analyze
GET /api/v1/behavior/final-confluence/arbiter/current

New module:
apps/api/app/behavior/final_confluence_arbiter.py

New contracts:
FinalConfluenceVote
FinalConfluenceConflict
FinalConfluenceArbiterRequest
FinalConfluenceArbiterGate
FinalConfluenceArbiterReport

The report computes evidence_hierarchy, confluence_score, evidence_votes, conflicts_detected, dominant_blocker, decision_band, confidence_interval, final_decision, and human_reason_tree.

Focused v1.75/envelope subset passed: 9 passed, 501 deselected.
Full backend regression passed: 510 passed, 1 warning.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.
```

## Latest v1.80 Additions

```text
New endpoints:
GET /api/v1/behavior/indicators/{indicator_id}/ontology
POST /api/v1/behavior/indicators/lag-vote
GET /api/v1/behavior/indicators/intelligence-summary/{symbol}

New module:
apps/api/app/behavior/indicator_lag_voting.py

New/extended contracts:
BehaviorIndicatorRegistryEntry ontology fields
IndicatorLagVoteRequest
IndicatorLagVoteRecord
IndicatorLagVotingReport

The indicator registry now carries purpose, category, best/bad regime, best timeframe, signal type, direction meaning, lag behavior, sequential signal window, missing policy, false-positive conditions, confirmation rules, conflict rules, trade/risk/no-trade usage, reliability placeholders, and ontology version.

Lag voting uses:
lag_weight = 1 / (1 + confirmation_delay_bars)

The report proves lagging indicators can explain or support post-entry context but cannot promote WATCH to PAPER-CANDIDATE alone. Unknown indicators remain explanation-only.

Focused v1.80/v0.60/envelope subset passed: 12 passed, 508 deselected.
Full backend regression passed: 520 passed, 1 warning.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true, no_future_leakage=true.
```

## Latest v1.81 Additions

```text
New endpoints:
POST /api/v1/behavior/indicators/reliability/label-signal
GET /api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}

Updated endpoint:
GET /api/v1/behavior/indicators/intelligence-summary/{symbol}
  now includes reliability_preview

New module:
apps/api/app/behavior/indicator_reliability_memory.py

New contracts:
IndicatorSignalOutcomeLabelRequest
IndicatorSignalOutcomeLabel
IndicatorReliabilityBucket
IndicatorReliabilityReport

The report labels indicator signals against completed 3/5/9/12/20-candle horizons, excludes pending horizons from wins, applies conservative stop-first handling for same-bar target/stop ambiguity, Bayesian-shrinks low evidence, surfaces reciprocal warnings, and quarantines reliability under OOD/regime-shift flags.

Focused v1.81/v1.80/v0.60/envelope subset passed: 20 passed, 508 deselected.
Full backend regression passed: 528 passed, 1 warning.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true, no_future_leakage=true.
```

## Latest v1.82 Additions

```text
Changed canonical timeframe contract:
1m, 3m, 5m, 15m, 30m, 1H, 4H, daily, weekly

Changed modules:
apps/api/app/models.py
apps/api/app/behavior/indicator_registry.py
apps/api/app/behavior/timeframe_feature_builder.py
apps/api/app/behavior/point_in_time_guard.py
apps/api/app/behavior/shared_snapshot.py
apps/api/app/behavior/walk_forward_validation.py
apps/api/app/behavior/multi_timeframe_conflict.py
apps/api/app/behavior/pattern_by_timeframe.py
apps/api/app/behavior/feature_store.py
apps/api/app/behavior/frontend_panels.py
apps/api/app/behavior/indicator_reliability_memory.py
apps/api/app/state.py

Important compatibility note:
The route /api/v1/behavior/features/seven-timeframe/current is still named seven-timeframe for compatibility, but the payload now emits nine closed-bar timeframe records.

New panel-map entry:
indicator_reliability_drilldown_v182

IndicatorReliabilityReport now includes UI-facing purpose/category/confirmation_delay_bars/lag_weight fields.

Focused v1.82/v1.81/v1.80/v0.60/v0.61/v0.62/v0.72/v0.78 subset passed: 36 passed, 497 deselected.
Full backend regression passed: 533 passed, 1 warning.
Safety remains unchanged: used_for_probability=false, trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true, no_future_leakage=true.
```

# MASTER GUIDE — full reference for build and handoff

> **Last expanded:** 2026-07-24 · **Tip:** Trade Vision **v1.94** · research / explicit local paper simulation only · live blocked  
> **Deepest copy:** `ARCHITECTURE.md` § **MASTER GUIDE** (keep both updated together).  
> **No separate master-guide file** — this section + ARCHITECTURE section are the entry maps.  
> **Your required final flow (requirement doc):** `docs/plans/FINAL_REQUIRED_FLOW.md`

## 1. Two products

| Product | Path | Use | Live orders |
|---------|------|-----|-------------|
| Stock App | repo root `:8014` | Charts, ML, backtest, research jobs, **manual** paper sim (`sim_trading.db`) | No |
| Trade Vision | this folder | WAIT / WATCH / PAPER-CANDIDATE cockpit | **Blocked** |

## 2. Read order

```text
SHORT:
  MASTER GUIDE (here or ARCHITECTURE) → docs/IMPLEMENTATION_STATUS.md
  → docs/NEXT_BUILD_TARGET.md → docs/SAFETY_INVARIANTS.md → only needed source
  Lost? → docs/FILE_DOCUMENT_INDEX.md §0.6 (question → file)

FULL:
  MASTER GUIDE → docs/context.md → IMPLEMENTATION_STATUS → docs/graph.md
  → ARCHITECTURE.md (operator + paper flow) → SAFETY → NEXT_BUILD
  → FILE_DOCUMENT_INDEX §0.6 (Q→file) + §7.4 (ownership) as needed
  → API_ENDPOINT_INDEX / FRONTEND_PANEL_MAP → docs/plans/* if coding roadmap

STOCK APP ONLY:
  ../STOCK_APP_ARCHITECTURE.md → ../API.md → ../server.py / static/*
```

Avoid first: `apps/api/app/main.py`, `apps/web/src/App.tsx`, whole `IMPLEMENTATION_STATUS.md`, whole indicator-memory plan.

**Map file how-to:** see section **How to use `docs/FILE_DOCUMENT_INDEX.md`** above.

## 3. Purpose table (existing files)

| Need | File |
|------|------|
| Latest version | `docs/IMPLEMENTATION_STATUS.md` |
| Next build | `docs/NEXT_BUILD_TARGET.md` |
| Ship log | `docs/IMPLEMENTATION_STATUS.md` |
| Safety | `docs/SAFETY_INVARIANTS.md` |
| Domain | `docs/context.md` |
| Operator / paper flows | `ARCHITECTURE.md` |
| Graph | `docs/graph.md` + `docs/graph/project_graph.json` |
| AI / new-chat handoff | **this file** § AI / New-Chat Handoff (merged) |
| **Doc/code map (how to use)** | `docs/FILE_DOCUMENT_INDEX.md` — **§0.6** Q→file · **§7.4** ownership · §0/§12 full library |
| Q→file only | `docs/FILE_DOCUMENT_INDEX.md` §0.6 |
| Ownership only | `docs/FILE_DOCUMENT_INDEX.md` §7.4 |
| APIs / panels / tests | `docs/API_ENDPOINT_INDEX.md`, `FRONTEND_PANEL_MAP.md`, `TEST_ID_INDEX.md` |
| Spec / test plan | `SPEC.md`, `TEST_PLAN.md` |
| Chart reasoning plan | `docs/plans/TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md` |
| Memory mega plan | `docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md` |
| OpenAlgo remaining | `docs/plans/OPENALGO_PAPER_TO_LIVE_REMAINING_BUILD_PLAN.md` |
| Stock App | `../STOCK_APP_README.md`, `../STOCK_APP_ARCHITECTURE.md`, `../API.md` |

## 4. Stock App feature summary (sibling product)

Charts + classic/custom indicators · ML (RF/CB/XGB/LGBM/ensemble) · HMM · Backtrader · purged WF + CPCV · paper sim · portfolio · research engine · Discord regime alerts · WebSocket quotes · pages `/` `/research` `/backtest` `/portfolio` `/compare`.

## 5. How signals work (critical)

| Path | Output | Auto paper/live? |
|------|--------|------------------|
| Rule TA predict | BUY/SELL/HOLD | No |
| ML ensemble etc. | Direction + conf | No |
| Pattern overlays | Visual events | No |
| Verified trade signal | TRADE/NO TRADE (limited, e.g. INFY 5m gates) | No |
| Backtest strategies | Historical metrics | No |
| TV arbiter v1.75 | WAIT/WATCH/PAPER-CANDIDATE | No live; paper = review label |
| Stock App sim API | Fills in `sim_trading.db` | Only if **human** posts trade |

**One-click stock name → all calc + live paper fill + results: NOT built.**

## 6. Build sequence (Trade Vision actual)

```text
v0.x foundation (PIT, safety, behavior, replay, risk/sim)
→ v1.x Jarvis + external AI review + OpenAlgo intent safety
→ v1.47 paper_review_ready_live_blocked
→ v1.62–69 context/MTF/cache/red-team/perf
→ v1.70–75 chart reasoning stack (shipped evidence engines)
→ v1.80–85 indicator intelligence + signal history
→ v1.86 TrendForge signed research intake
→ v1.88-v1.93 ORB Paper Guidance + local simulated ledger
→ v1.94 outcome/lifecycle/operational hardening             ← current tip
```

### Version → key files

| Ver | Files under `apps/api/app/behavior/` (unless noted) |
|-----|------------------------------------------------------|
| 1.63 | `real_mtf_pullback.py` |
| 1.70 | `chart_reasoning_volatility.py` |
| 1.71 | `market_regime_feedback.py` |
| 1.72 | `market_structure_liquidity.py` |
| 1.73 | `execution_event_oi_risk.py` |
| 1.74 | `post_entry_lifecycle.py` |
| 1.75 | `final_confluence_arbiter.py` |
| 1.80 | `indicator_registry.py`, `indicator_lag_voting.py` |
| 1.81 | `indicator_reliability_memory.py` |
| 1.83–85 | history store + `indicator_signal_history_ingestion.py` + `..._completion.py` |
| 1.86 | `trendforge_bridge.py` |
| OA | `jarvis_openalgo_*`, `jarvis_paper_ready_safety_audit.py`, `apps/openalgo-adapter/` simulator |
| Shell | `main.py`, `apps/web/src/App.tsx` |

## 7. Plan audit (full)

| Plan | Correct? | Implemented? | Notes |
|------|----------|--------------|-------|
| **MAX_CHART_REASONING** | Yes | **Mostly yes** | v1.70–75 + 80–81 shipped; evidence-only; no live |
| **FULL_INDICATOR_MEMORY** | Yes as mega architecture | **Partial** | registry/store/similarity/outcomes/twin pieces; DoD (all validated groups, FAISS tier, full twin WF) open |
| **OPENALGO_PAPER_TO_LIVE** | Yes as remaining after v1.47 | **Mostly no** | 4.1–4.9 real paper→live not done; review/safety/transport/simulator yes |

OpenAlgo remaining: paper fill loop, result tracking, recon, risk governor, paper-to-live report, live preflight, tiny pilot, live audit, bot gate → **future**.

```text
Best executed plan → MAX_CHART_REASONING
Open backlog brain → FULL_INDICATOR_MEMORY
Open backlog execution → OPENALGO_PAPER_TO_LIVE
```

## 8. Quality rating

| As… | Rating |
|-----|--------|
| Research / learning lab | Strong |
| Single best trading signal product | Moderate |
| Live / one-click paper bot | Weak by design + unfinished OA path |

Issues: many signal sources; chart BUY/SELL vs TV WAIT language; no auto-fill; data often yfinance; verified path limited; docs/plans overlap if you skip this guide.

## 9. Flows

```text
Stock App: symbol → OHLCV+indicators → optional ML/patterns → human paper trade → sim DB
TV:       PIT evidence → engines → arbiter reduce-only → WAIT/WATCH/PAPER-CANDIDATE → OA preview only
```

## 10. Ship process + safety + maintenance

```text
NEXT_BUILD_TARGET → optional plan slice → implement/tests
→ IMPLEMENTATION_STATUS (tip + full log)
→ update this MASTER GUIDE if structure/tip/plan status changes
```

Safety: no live routing, no future-bar leakage, AI/Kronos cannot override risk/NO_TRADE, OpenAlgo not TV execution authority. See `docs/SAFETY_INVARIANTS.md`.

Prefer updating these README/ARCHITECTURE sections over adding new master files.
`v1.88-v1.94` now extend that spine through snapshot-bound evidence, a
session-safe ORB engine, offline discovery/proof, a Jarvis ORB guidance screen,
an explicitly human-approved local simulated paper ledger, and explicit
replay-only lifecycle outcomes. ORB is a setup candidate only; D6 remains final
authority, and no broker order is created.
