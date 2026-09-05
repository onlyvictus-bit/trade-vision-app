# FINAL REQUIRED FLOW

> **Status:** Product requirement spine — **partially implemented** through **v1.94** (ORB paper campaign + local sim ledger); full one-touch product acceptance still open.  
> **Owner need:** One organized flow that **guides a paper-trade decision** (and optionally books paper after human approve)  
> **Last written:** 2026-07-24 · **Alignment verified:** 2026-07-24 vs `ARCHITECTURE.md`, code modules, `IMPLEMENTATION_STATUS` tip  
> **Scope:** Monorepo = Stock App (root) + Trade Vision (`trade-vision-app/`)  
> **Mode today:** Research / mock / paper-review; **TV local simulated paper record** after explicit human approve (v1.93+); **no live broker**  
> **This file is the source of truth for the required end product flow.**  
> **Merged into this file (appendices):** former `FINAL_REQUIRED_FLOW.md Appendix A (AI Brief)` + `FINAL_REQUIRED_FLOW.md Appendix B (Think Engine)` (full text preserved).  
> **Do not recreate** those two plan files — update **this file** only.  
> **Doc map:** `docs/FILE_DOCUMENT_INDEX.md`

### Alignment notes (2026-07-24)

```text
ALIGNED with ARCHITECTURE + code:
  - D1/D2 paper_guidance_spine, D6 final_confluence_arbiter, ORB guidance, simulated_paper_ledger exist
  - Authority: ORB proposes · D6 final band · human approve · no live broker
  - live_trading_blocked / order_routing_enabled=false in TV paths
  - Stock App sim_trading.db remains separate multi-account book (manual)

STALE claims fixed when reading appendices:
  - AI Brief tip "v1.86" → use IMPLEMENTATION_STATUS tip (v1.94)
  - "TV paper fill = No fill / review label only" → still true for OpenAlgo live;
    v1.93+ adds TV *local* simulated paper record after exact human approve
  - FINAL §10 "next = Phase 0+1 only" → historical; campaign v1.88–v1.94 shipped;
    next = docs/NEXT_BUILD_TARGET.md (no approved version as of 2026-07-24)

IMPLEMENT LOCK (still authoritative for coding shape):
  TRADE_VISION_ARCHITECTURE_DESIGN.md §0 = OLD Flow D + only 3 patches
  (D2 snapshot_hash · D6 low_evidence max WATCH · Week4 prove+promote; bridge v1.1)
```

---
## Approved Versioned Delivery

```text
v1.88  snapshot-bound D3-D6 Paper Guidance
v1.89  ORB contracts/session lock/strategies
v1.90  offline ORB discovery
v1.91  OOS/WF proof and playbook promotion
v1.92  ORB as primary Jarvis setup action
v1.93  human-approved simulated paper record
v1.94  outcome feedback and production hardening
```

Approved authority:

```text
ORB proposes the primary entry/stop/target setup.
The D6 arbiter alone produces the final band.
The operator alone approves creation of a simulated paper record.
No live broker order is created by this flow.
```

---

## 1. My requirement (what I want)

### 1.1 One sentence

```text
Enter a stock name → system runs one organized analysis + labeling + decision pipeline
→ outputs one clear paper-trade guidance
→ (optional after human approve) books paper trade and shows result.
```

### 1.2 Required user outcome

The product must answer, in **one place**, for one symbol/time:

| Question | Required answer |
|----------|-----------------|
| What is happening now? | Structure, regime, levels, key indicators |
| Has this happened before? | Memory / analogs / reliability (or “low evidence”) |
| What should I do for paper? | **One** guidance: WAIT / WATCH / ENTER_PAPER / SKIP / AVOID |
| Why? | Reason tree (for + against + blockers) |
| If enter: where wrong? | Entry, stop, target, invalidation |
| What next action? | “Do nothing” or “Approve paper ticket” |
| After approve? | Paper fill recorded + result visible |

### 1.3 Non-negotiable constraints (keep)

```text
- No live broker orders in v1 of this spine
- No hidden auto live routing
- Human approve before any paper fill (default)
- No future-bar leakage into decision features
- Low evidence must block or cap confidence (WAIT / WATCH), not fake certainty
- External AI (Gemini/Grok) = review only; cannot override risk / NO_TRADE
- Kronos = research prior only; cannot override risk / NO_TRADE
```

### 1.4 What “success” means

| Success metric | Definition |
|----------------|------------|
| Single action | One API + one UI “Run paper guidance” for a symbol |
| Single decision language | One vocabulary (prefer TV-style bands; map Stock App BUY/SELL into it) |
| Single boss | One arbiter; all engines are evidence only until arbiter |
| Traceability | Output lists which engines voted and which blocked |
| Optional paper | Approve → **TV local** simulated paper record (v1.93+) → observe/outcome; Stock App `sim_trading.db` = separate optional bridge later |
| No silent engines | Engines not in the spine do not show as competing “final answers” |

---

## 2. What is present today (current state)

### 2.1 Two products (both real, not one spine)

| Product | Present | Role today |
|---------|---------|------------|
| **Stock App** (`server.py`, `static/*`, :8014) | Yes | Charts, ML BUY/SELL/HOLD, HMM, backtest, research jobs, **manual** paper sim |
| **Trade Vision** (`trade-vision-app/`) | Yes | Evidence engines, Jarvis, WAIT/WATCH/PAPER-CANDIDATE, safety locks |

### 2.2 Present analysis engines (examples)

| Engine family | Where | Present? |
|---------------|-------|----------|
| OHLCV + classic indicators | Stock App | Yes |
| Custom / pattern indicators | `indicators/`, `self_indc/` | Yes |
| Rule TA predictor | Stock App | Yes → BUY/SELL/HOLD |
| ML RF / boosters / ensemble | Stock App | Yes → direction + conf |
| HMM regime | Stock App | Yes |
| Verified trade signal | Stock App (limited e.g. INFY 5m) | Partial |
| Chart reasoning v1.70 | TV | Yes (evidence API) |
| Regime / RS / Bayes v1.71 | TV | Yes (often needs caller context) |
| Structure / liquidity v1.72 | TV | Yes |
| Exec / event / OI risk v1.73 | TV | Yes (missing data → unavailable/proxy) |
| Post-entry lifecycle v1.74 | TV | Yes (sim guidance only) |
| MTF / 9C / reliability / signal history | TV | Yes / partial |
| Kronos / twin | TV | Partial research path |
| TrendForge intake v1.86 | TV | Yes (research evidence only) |

### 2.3 Present decision / labeling pieces

| Piece | Present? | Notes |
|-------|----------|-------|
| Stock App BUY/SELL/HOLD | Yes | Independent of TV |
| TV Final confluence arbiter v1.75 | Yes | Best “boss” idea; evidence reduce-only |
| Jarvis decision room | Yes | Assembly + blockers + AI review |
| Indicator reliability / history labels | Partial | v1.80–v1.85 path |
| OpenAlgo intent / paper-ready audit | Partial | Review / simulator, not full paper fill loop |
| Stock App sim paper book | Yes | **Manual** POST trade only |

### 2.4 Present paper path

```text
Stock App: human creates sim account → human posts trade → sim_trading.db → history
Trade Vision: PAPER-CANDIDATE label → OpenAlgo package preview/dry-run → NO auto fill
OpenAlgo plan 4.1–4.9: mostly NOT implemented (future)
```

---

## 3. What the FINAL PRODUCT must be

### 3.1 Final product definition

```text
A single Paper Guidance Spine:

  INPUT:  symbol + timeframe + decision time (closed bars only)
  PROCESS: fixed engine order → memory labels → risk gates → ONE arbiter
  OUTPUT: PaperTradeGuidance (one object)
  ACTION: optional human Approve → paper fill (sim first) → PaperTradeResult
```

### 3.2 Final decision language (one only)

Prefer **Trade Vision bands** as the product language:

| Final band | Meaning for user |
|------------|------------------|
| **WAIT** | Not enough / blocked / unclear — do not paper enter |
| **WATCH** | Interesting; needs confirmation — do not paper enter yet |
| **ENTER_PAPER** (or PAPER-CANDIDATE + ready flags) | Guidance allows paper ticket if human approves |
| **AVOID / NO TRADE** | Explicit no-trade |
| **SKIP** | Valid setup quality low; pass |

Map legacy Stock App outputs into this language (do not show raw competing BUY next to WAIT as two finals).

### 3.3 Required final object: `PaperTradeGuidance`

```text
PaperTradeGuidance
  symbol, timeframe, decision_time
  final_band                 # WAIT | WATCH | ENTER_PAPER | AVOID | SKIP
  confidence_cap
  blockers[]                 # hard stops
  warnings[]
  reason_for[]
  reason_against[]
  entry_plan { side, entry, stop, target, invalidation, size_hint }
  evidence_votes[]          # engine_id, vote, weight, lag_penalty
  memory_summary             # reliability / analogs / low_evidence
  risk_summary               # liquidity, event, regime caps
  engines_run[]              # audit list
  next_action                # DO_NOTHING | OFFER_PAPER_TICKET
  live_trading_blocked=true
  order_routing_enabled=false
```

### 3.4 Required optional paper result: `PaperTradeResult`

```text
PaperTradeResult
  guidance_id
  paper_account_id
  fill_status, fill_price, qty
  expected_vs_actual (entry/sl/target slippage if known)
  open_pnl / closed_pnl when available
  link back to guidance reasons
```

### 3.5 Final UX (one primary action)

```text
[ Symbol ] [ TF ] [ Run paper guidance ]
        → one result card (band + why + plan)
        → [ Approve paper trade ] (only if ENTER_PAPER and no hard blockers)
        → paper result panel
```

Secondary panels (engines detail) allowed **only as drill-down**, not as second final answers.

---

## 4. What is missing / gaps / errors (honest)

### 4.1 Critical gaps (flow breaks)

| # | Gap | Effect |
|---|-----|--------|
| G1 | **No single spine API** | User cannot run one action end-to-end |
| G2 | **Multiple decision languages** | BUY/SELL vs WAIT/WATCH compete |
| G3 | **Multiple engines, no forced order** | Feels unorganized / inefficient |
| G4 | **No single boss output object** | Operator merges panels manually |
| G5 | **Decision not wired to paper book** | Guidance does not create sim trade |
| G6 | **OpenAlgo paper fill loop missing** | Plan 4.1–4.9 largely future |
| G7 | **Stock App and TV are islands** | Two products, one user need |
| G8 | **Memory/labels optional** | Not always required before decision |
| G9 | **Context feeds often missing** | Breadth/OI/index may be unavailable → caps not always user-visible as “why WAIT” |
| G10 | **One-click full package not built** | Symbol → all calc → paper → result absent |

### 4.2 Organization / efficiency problems (not always “code bugs”)

| Issue | Type | Description |
|-------|------|-------------|
| Engine soup | Design | Many analyzers exposed as equals |
| Dual product authority | Design | Sim paper lives in Stock App; decision language in TV |
| Plan layering | Process | Chart / memory / OpenAlgo plans not one spine |
| Version renumbering | Docs | Hard to see “what is the main path” |
| Verified path narrow | Coverage | e.g. INFY 5m style gates not universal |
| yfinance / proxy data | Data | Not exchange-grade; must not over-claim |
| Arbiter underused in UX | Integration | Best boss may not own the only final card |
| Auto paper not built | Product | Analysis ≠ action |

### 4.3 Errors / false expectations to stop

```text
ERROR (expectation): "System decides" means auto paper trade
TRUTH: System can label; paper fill is mostly manual or missing

ERROR (expectation): All engines already vote into one decision
TRUTH: Many engines are parallel tools / panels

ERROR (expectation): PAPER-CANDIDATE means paper position opened
TRUTH: It is a review band, not a fill

ERROR (expectation): OpenAlgo integration = paper trading works
TRUTH: Safety + simulator + preview; not full paper execution loop

ERROR (expectation): ML BUY is the product decision
TRUTH: Discretionary opinion; must map under one arbiter
```

### 4.4 What is NOT an error

```text
- Safety locks blocking live trade (correct)
- WAIT when evidence low (correct)
- Keeping human approve before paper (correct for v1)
- Having many research engines (OK if demoted to evidence-only)
```

---

## 5. Simple pictures

### 5.1 Required final flow (target)

```text
                    ┌─────────────────────────┐
                    │  INPUT: symbol + TF     │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │ 1. SNAPSHOT (closed bars│
                    │    only, one hash)      │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │ 2. ANALYSIS engines     │
                    │    (structure, TA, MTF, │
                    │     vol, patterns…)     │
                    │    = EVIDENCE only      │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │ 3. LABELING / MEMORY    │
                    │    reliability, analogs │
                    │    outcomes, low-ev     │
                    │    = EVIDENCE only      │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │ 4. RISK / SAFETY gates  │
                    │    liquidity, event,    │
                    │    kill switch, data    │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │ 5. ONE ARBITER (boss)   │
                    │    reduce-only merge    │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │ 6. PaperTradeGuidance   │
                    │    ONE final band+plan  │
                    └───────────┬─────────────┘
                         ┌──────┴──────┐
                         ▼             ▼
                   DO_NOTHING    OFFER_PAPER_TICKET
                         │             │
                         │             ▼
                         │      Human APPROVE?
                         │        │        │
                         │       No       Yes
                         │        │        ▼
                         │        │   7. PAPER FILL
                         │        │   (sim_trading.db v1)
                         │        │        ▼
                         │        │   8. PaperTradeResult
                         ▼        ▼
                      END (show guidance only / show result)
```

### 5.2 Present flow (broken / parallel)

```text
   Stock App                         Trade Vision
   --------                         ------------
   TA ──► BUY/SELL                  v1.70..74 ──► panels
   ML ──► BUY/SELL                  reliability ─► panels
   patterns ─► overlays             arbiter ──► WAIT/WATCH/PAPER-CANDIDATE
   verified ─► TRADE?               Jarvis ──► room
        │                                 │
        └──── human brain merges ─────────┘
                        │
            optional manual sim trade (Stock App only)
                        │
            OpenAlgo preview (no real fill loop)
```

### 5.3 Gap picture

```text
[Analysis engines]──┐
[Label engines]─────┼──X──► [ONE guidance]──X──► [Paper fill]──X──► [Result]
[Decision engines]──┘
         missing spine              missing wire         missing OA loop
```

---

## 6. How to achieve the required flow (build plan)

Build in **thin vertical slices**. Do not add more disconnected engines first.

### Phase 0 — Freeze the contract (docs + types)

```text
- Lock PaperTradeGuidance + PaperTradeResult schemas
- Lock final_band vocabulary
- Lock engine roles: evidence | gate | arbiter | executor
- Mark competing BUY/SELL UI as "legacy opinion" not final
Deliverable: this file + typed models + one empty endpoint contract
```

### Phase 1 — One spine endpoint (no new engines)

```text
POST /api/v1/paper-guidance/run
  { symbol, timeframe, decision_time? }

Server:
  1) build shared snapshot (closed bars)
  2) call EXISTING engines in fixed order (subset first)
  3) call EXISTING arbiter as only boss
  4) return PaperTradeGuidance

UI:
  one "Run paper guidance" button → one result card

Success: one action, one band, reason tree, no paper fill yet
```

**Suggested first engine order (reuse existing):**

```text
snapshot
→ data quality / PIT guard
→ chart reasoning (v1.70)
→ market regime feedback (v1.71) if context available else mark unavailable
→ structure liquidity (v1.72)
→ execution/event/oi risk (v1.73)
→ indicator lag vote + reliability summary (if any)
→ final confluence arbiter (v1.75)
→ package PaperTradeGuidance
```

Map Stock App ML/TA as **optional evidence votes** only (not parallel finals).

### Phase 2 — Human-approved paper record (three meanings)

```text
A. TV label only (pre-v1.93) — review ticket, no fill
B. TV local simulated paper ledger (v1.93–v1.94 SHIPPED for eligible ENTER_PAPER)
     UI shows [Approve paper trade] only when can_record_paper
     exact human approval phrase → server-stored local record
     observe / outcome / reliability feedback (v1.94)
     NO broker · NO OpenAlgo live · does NOT write Stock App sim_trading.db
C. Stock App multi-account sim (OPTIONAL later bridge — not required for tip)
     root server.py /api/sim/* → sim_trading.db
     only if a future plan wires TV approve → Stock App fill

Success (current product): decision → human approve → TV local record → observe/outcome
Still always: live_trading_blocked=true
```

### Phase 3 — Force organization / kill engine soup in UX

```text
- Final card always from spine only
- Other engines only under "Evidence detail"
- Hide or demote raw BUY/SELL as final
- Always show blockers + engines_run audit list
```

### Phase 4 — Memory required path (partial → real)

```text
- If reliability/analogs unavailable → cap at WATCH/WAIT (visible reason)
- Ingest/complete history where possible (existing v1.83–85 ideas)
- Do not invent high confidence without samples
```

### Phase 5 — OpenAlgo paper loop (only after Phase 2 solid)

```text
Use OPENALGO_PAPER_TO_LIVE plan, but spine remains the same:
  Guidance → intent package → OA paper simulator/real paper mode
  → fill callback → PaperTradeResult
Do not jump to live pilot until paper sample + recon gates pass
```

### Phase 6 — Optional later

```text
- Multi-symbol batch guidance
- Auto paper without approve (only with explicit user config + hard risk caps)
- Live preflight / tiny pilot (separate safety program — not default)
```

---

## 7. Engine role matrix (organization rule)

| Role | Rule | Examples |
|------|------|----------|
| **Evidence** | May vote; never final alone | v1.70–74, ML, TA, patterns, Kronos |
| **Gate** | Can only reduce / block | risk, PIT, kill switch, low evidence, liquidity C |
| **Arbiter** | Only producer of final_band | v1.75 + spine packager |
| **Executor** | Only after human approve (v1) | Stock App sim; later OA paper |
| **Display-only** | Cannot change band | Gemini/Grok narrative |

If a module is not in the spine order, it is **research optional**, not decision authority.

---

## 8. Acceptance checklist (definition of done for required flow)

The required flow is **done** only when all are **`[x]`**.  
Marks below reflect **2026-07-24** evidence (`BUILD_AUDIT.md` + code), not wishful completion.

```text
Legend: [x] met  [~] partial / wired but not product-closed  [ ] not met
```

```text
[~] One Run paper guidance action exists (API + UI)
    — API: POST /api/v1/paper-guidance/* family PASS
    — UI: client methods exist; primary path still multi-panel soup (not one clean card)
[~] One PaperTradeGuidance object returned every time
    — Typed guidance object exists; dual band language still coexists (see next)
[ ] Only one final_band vocabulary in primary UI
    — Arbiter PAPER-CANDIDATE maps to product ENTER_PAPER; both still appear in models/UI
[x] Arbiter is sole boss; engines listed as evidence votes
    — final_confluence_arbiter + ORB proposes only (orb_guidance maps to D6)
[~] Blockers visible when WAIT/AVOID
    — API returns blockers/warnings; primary UI consistency not fully closed
[~] ENTER_PAPER offers Approve paper trade
    — record-simulated + can_record_paper gate exist; often WATCH/NO_PLAYBOOK so approve disabled (fail-closed OK)
[~] Approve creates local simulated paper record + outcome path (TV ledger)
    — v1.93–v1.94: human-approved TV local ledger + observe/reliability (NOT Stock App sim_trading.db)
    — Stock App multi-account sim fill remains optional later bridge (see Phase 2 note)
[x] live_trading_blocked remains true
    — SYSTEM_MODE.allows_live_orders=False; capability flags live_trading_blocked=true
[ ] No second competing "final BUY" card in primary path
    — Multi-panel workspace still competes with ORB/paper primary ticket
[x] Low evidence cannot print high-confidence ENTER_PAPER
    — reliability 0/30, lag voting, NO_PLAYBOOK keep WATCH; low-evidence caps
[~] Documented engine order in code matches this file
    — Campaign D1–D7 / ORB+arbiter implemented in pieces; not one single linear FINAL table function
```

**Product acceptance still open** until remaining `[ ]` and critical `[~]` (one UI vocabulary + one primary card + evidence density) close.

---

## 9. Relation to existing plans

| Plan | Relation to this file |
|------|------------------------|
| `TRADE_VISION_MAX_CHART_REASONING_...` | **Evidence stack** for steps 2–5 (mostly present) |
| `TRADE_VISION_FULL_INDICATOR_MEMORY_...` | **Labeling/memory** for step 3 (partial) |
| `OPENALGO_PAPER_TO_LIVE_...` | **Executor upgrade** after sim Phase 2 (mostly missing) |
| `ORB_RESEARCH_ENGINE_PLAN.md` | **Parallel research track:** sweep ORB strategy × TF × orb candle count/window × filters for profit + **repeated success**; winners may later feed guidance evidence — **not** a substitute for Phase 0–2 spine; **no auto live** |
| `FINAL_REQUIRED_FLOW.md Appendix B (Think Engine)` | Question-driven engine order: Flow R (research) vs Flow D (decide/paper) |

```text
This file = the spine and product requirement.
Those plans = subsystem roadmaps that must plug into this spine.
ORB research = offline playbook discovery; does not auto-enter paper/live.
Do not implement more engines without plugging them as evidence into Phase 1+.
```

---

## 9b. ORB research track (appended detail — AI reference)

> Full authority: `ORB_RESEARCH_ENGINE_PLAN.md` (§0 placement, §0.8 vs Kronos/Vision).  
> This section ensures the **product spine file also carries ORB requirements** without replacing Phase 0–2.

### Why ORB is in the product picture

| Question | Answer |
|----------|--------|
| Why need ORB research? | User needs best **strategy / TF / orb candle count or clock window / combo** by **profit + repeated success** |
| Why not only inside paper click? | Grid search is slow; would destroy one-touch UX and overfit |
| How helps paper guidance later? | Proven **playbook** becomes optional **evidence vote** under arbiter |
| What must never happen? | ORB job auto paper/live; ORB boss over Kronos/risk/arbiter |

### Present vs need

| Present | Need |
|---------|------|
| `opening_range_reversal` + hybrid ORR | Full **ORB lab** sweep (breakout + ORR + hybrid) |
| Generic `research/` VectorBT discovery | `research/orb/*` TF × bars/window × filters grid |
| Chart ORR markers | Rank tables: best profit **and** best consistency |

### Best placement (pipeline)

```text
Discover (research/orb) → Prove (validation/OOS) → Playbook (research.db)
  → Decide (guidance: playbook match vote only)
  → Paper (sim after human approve)
```

### Relation to spine phases

| Spine phase | ORB interaction |
|-------------|-----------------|
| P0–P1 PaperTradeGuidance | No ORB grid on click; optional later evidence field |
| P2 Approve → sim | Unrelated to ORB job; human still approves |
| Parallel ORB-0…3 | Can build anytime on Stock App research stack |
| Week 4 | ORB **prove + promote + reports only** (not bridge) |
| ORB-5 bridge | **v1.1** — top playbook → D3a evidence vote only |

### Implement lock (all product docs)

```text
Authoritative coding shape:
  TRADE_VISION_ARCHITECTURE_DESIGN.md §0
  = OLD plan + ONLY 3 patches:
    1) snapshot_hash at D2 snapshot freeze
    2) D6 post-agg low_evidence → max WATCH
    3) Week 4 prove+promote; bridge v1.1
```

### Vs Kronos / Vision think engines

```text
ORB offline = research brain (does not run inside Kronos or v1.70–75 loop)
Vision + Kronos = decide-now brains (snapshot)
ORB influence online = weak optional playbook match vote only
Authority: ORB_RESEARCH_ENGINE_PLAN.md §0.8
```

---

## 10. Immediate next build recommendation

```text
HISTORICAL note (pre-ORB campaign planning): Phase 0+1 decision-only spine first.
ACTUAL shipped campaign (2026-07-24): v1.88–v1.94 ORB paper guidance + local sim ledger + lifecycle.
CURRENT next: see docs/NEXT_BUILD_TARGET.md (no new version approved as of tip date).
Out of scope still: live broker, OpenAlgo live fills as default product.
```

Update when a version ships:

```text
docs/NEXT_BUILD_TARGET.md
docs/IMPLEMENTATION_STATUS.md (tip + ship log)
MASTER GUIDE sections in ARCHITECTURE.md / TRADE_VISION_README.md
```

---

## 11. Bottom line (for future me / AI)

```text
REQUIREMENT: one organized analysis → labeling → decision spine that guides paper trade.
PRESENT: many engines + two products + manual sim + TV labels.
MISSING: single spine, single boss output, wire to paper result, efficient organization.
NOT A BUG ALONE: safety blocks on live; problem is product flow organization.
HOW TO ACHIEVE: Phase 0→1 spine first, then approve→sim fill, then memory harden, then OA paper loop.
```

**File path:** `trade-vision-app/docs/plans/FINAL_REQUIRED_FLOW.md`

---

## APPENDIX A — Paper Trade Spine AI Brief (former `PAPER_TRADE_SPINE_AI_BRIEF.md`)

> **Merged 2026-07-24 for zero data loss.**  
> **Use when:** asking external AIs (Gemini/Claude/Kimi/GLM/…) to **design a plan**.  
> **Also attach if zero context:** PROJECT_GOD_VIEW_FOR_AI.md.  
> **ORB lab detail:** ORB_RESEARCH_ENGINE_PLAN.md.  
> **Tip line in original said v1.86 — ignore; use IMPLEMENTATION_STATUS tip.**  
> **Authority:** Planning brief; coding order = ARCHITECTURE_DESIGN §0 + this file’s body.

# AI BRIEF — One-Touch Paper Trade Guidance Spine

> **Use this file** when asking Gemini / Claude / Kimi / GLM / others to **design a plan**.  
> **If the AI has zero context on indicators/engines:** also attach `PROJECT_GOD_VIEW_FOR_AI.md` (god skeleton).  
> **ORB research lab detail:** `ORB_RESEARCH_ENGINE_PLAN.md` (also summarized in §3b + parallel phases under §6 here).  
> **Think-engine best flow (why/when/what):** `FINAL_REQUIRED_FLOW.md Appendix B (Think Engine)`  
> **Implement lock (OLD plan + 3 patches only):** `TRADE_VISION_ARCHITECTURE_DESIGN.md` **§0**  
> **Do not** attach full `IMPLEMENTATION_STATUS`, mega memory plan, or whole monorepo.  
> **Date:** 2026-07-22 · **Product tip:** Trade Vision v1.86 · Stock App :8014  
> **Authority:** Planning brief; **coding order** follows ARCHITECTURE_DESIGN §0 (old pipeline + Patch 1–3 only).

---

## 0. Your job (what to produce)

Produce a **build plan** (not production code unless asked) for:

```text
User touches one action on a stock
  → system runs ONE organized pipeline (analysis → label → decide)
  → ONE paper-trade guidance (WAIT / WATCH / ENTER_PAPER / AVOID)
  → optional human APPROVE
  → paper fill in sim ledger + result shown
```

**Not:** live broker orders, autonomous bot, more disconnected indicator engines.

**Also in scope as a parallel track (optional section in your plan):**  
**ORB Research Engine** — backtest which ORB strategy × timeframe × ORB candle count/clock window × filter combo is best by **profit** and **most repeated success** (offline research; not auto-fill).

**Output format required from you (the planning AI):**

1. Goal + non-goals  
2. Target architecture (one spine, roles: evidence / gate / arbiter / executor)  
3. API + UI contracts (`PaperTradeGuidance`, `PaperTradeResult`)  
4. Phased build plan (P0–P2 minimum; later optional)  
5. Engine call order (reuse existing first)  
6. Gaps / risks / test list  
7. Explicit “what not to build yet”  
8. Acceptance checklist  
9. **Optional but preferred:** ORB research parallel track (phases, reuse `research/` + ORR, rank profit + consistency)  

---

## 1. Product reality (two islands today)

| Product | Path | What it does today | Paper fill? |
|---------|------|--------------------|-------------|
| **Stock App** | repo root `server.py` :8014 | Charts, ML BUY/SELL/HOLD, HMM, backtest, research jobs | **Manual** sim only (`sim_trading.db`) |
| **Trade Vision** | `trade-vision-app/` | Evidence engines, Jarvis, WAIT/WATCH/PAPER-CANDIDATE | **No fill** — review label only |

```text
Problem: many analysis/decision engines, NOT one spine.
Missing: single action → single guidance → wire to paper result.
False expectation: PAPER-CANDIDATE or ML BUY means a paper position opened. It does not.
```

---

## 2. Required final product (hard requirement)

### 2.1 One primary UX action

```text
[ Symbol ] [ TF ] [ Run paper guidance ]
  → one result card (band + why + entry/stop/target if any)
  → [ Approve paper trade ] only if ENTER_PAPER and no hard blockers
  → paper result panel (fill, pnl when available)
```

Secondary engine panels = **drill-down only**, never second “final answer.”

### 2.2 One decision language (prefer TV bands)

| Band | Meaning |
|------|---------|
| WAIT | Blocked / unclear — do not enter |
| WATCH | Interesting — do not enter yet |
| ENTER_PAPER | Guidance allows paper ticket if human approves |
| AVOID / NO TRADE | Explicit no |
| SKIP | Pass |

Map Stock App BUY/SELL/HOLD **into** this language as evidence votes, not competing finals.

### 2.3 Required objects

```text
PaperTradeGuidance {
  symbol, timeframe, decision_time
  final_band
  confidence_cap
  blockers[], warnings[]
  reason_for[], reason_against[]
  entry_plan { side, entry, stop, target, invalidation, size_hint }
  evidence_votes[] { engine_id, vote, weight, lag_penalty }
  memory_summary, risk_summary
  engines_run[]
  next_action  # DO_NOTHING | OFFER_PAPER_TICKET
  live_trading_blocked=true
  order_routing_enabled=false
}

PaperTradeResult {
  guidance_id, paper_account_id
  fill_status, fill_price, qty
  expected_vs_actual
  pnl fields when available
}
```

### 2.4 Target spine (architecture)

```text
INPUT symbol+TF
  → 1 SNAPSHOT (closed bars only, one hash)
  → 2 ANALYSIS engines = EVIDENCE only
  → 3 LABEL/MEMORY = EVIDENCE only
  → 4 RISK/SAFETY gates (reduce/block only)
  → 5 ONE ARBITER (sole final_band producer)
  → 6 PaperTradeGuidance
  → 7 Human APPROVE? (default required)
  → 8 PAPER FILL (sim_trading.db first)
  → 9 PaperTradeResult
```

**Roles:**

| Role | Rule | Examples already in codebase |
|------|------|------------------------------|
| Evidence | Vote only | chart reasoning v1.70, structure v1.72, ML/TA, reliability |
| Gate | Block/reduce only | PIT, kill switch, liquidity, low evidence |
| Arbiter | Only final band | final confluence arbiter v1.75 + spine packager |
| Executor | After approve only (v1) | Stock App `/api/sim/*` → `sim_trading.db` |

---

## 3. What already exists (reuse — do not reinvent)

### Stock App (root)

- OHLCV + indicators, ML ensemble, HMM, patterns  
- Sim: `POST /api/sim/accounts`, `.../trade`, history → `sim_trading.db`  
- Verified signal API (limited, e.g. INFY 5m gates) — optional evidence  
- Pages: `/`, `/backtest`, `/research`, etc.  
- **Opening Range Reversal (ORR)** + hybrid: `shared/indicators/self_indc.py`, Backtrader strategies in `server.py`  
- **Generic research discovery:** `research/engine/*` (VectorBT combo sweep → score → `research.db`)

### Trade Vision (behavior modules — evidence stack largely present)

| Version | Module idea | Role in spine |
|---------|-------------|-----------------|
| v1.70 | chart_reasoning_volatility | Evidence |
| v1.71 | market_regime_feedback | Evidence (context may be unavailable) |
| v1.72 | market_structure_liquidity | Evidence |
| v1.73 | execution_event_oi_risk | Gate-ish evidence |
| v1.74 | post_entry_lifecycle | Post-entry only (later) |
| v1.75 | final_confluence_arbiter | **Boss candidate** |
| v1.80–85 | registry, lag vote, reliability, signal history | Evidence / memory |
| v1.86 | TrendForge intake | Research evidence only |
| — | jarvis_*, openalgo_* | Review/package; **not** full paper fill loop |

### Plans status (do not re-argue)

| Plan | Status |
|------|--------|
| MAX_CHART_REASONING | Mostly shipped as evidence APIs |
| FULL_INDICATOR_MEMORY | Partial mega-spec — **do not require full DoD for v1 spine** |
| OPENALGO_PAPER_TO_LIVE | Mostly future — **after** sim spine works |
| FINAL_REQUIRED_FLOW | **Product requirement** for this spine |
| ORB_RESEARCH_ENGINE_PLAN | **Parallel research track** — ORB TF/bars/combo lab **not fully built** |
| PROJECT_GOD_VIEW_FOR_AI | Inventory + engines catalog for zero-context AIs |

---

## 3b. ORB Research Engine (parallel track — include in plans)

> Full detail: `ORB_RESEARCH_ENGINE_PLAN.md`. Summarized here so multi-AI packs always see it.

### User need

```text
Backtest stocks → find best:
  ORB strategy type
  + timeframe
  + ORB candle count OR clock window (which time range locks the OR)
  + entry window + filter combination
Rank by: profit metrics AND most repeated success (consistency / OOS), not luck year only.
```

### Present vs need

| Present | Need (lab) |
|---------|------------|
| ORR + hybrid ORR (fixed windows) | Full sweep of breakout + reversal families |
| Generic `research/` combo runner | `research/orb/*` grid: TF × orb_bars/window × filters × R:R |
| Single-strategy backtest in UI | Winner tables + heatmaps + consistency score |

### Combo dimensions (search space)

```text
strategy_family: orb_breakout | orr_reversal | hyb_orr
timeframe: 1m | 3m | 5m | 15m | …
orb: bar_count (3/5/15/30…) OR clock (e.g. 09:15–09:30)
entry_window after OR locks
filters: volume, vwap, rsi, atr, cooldown, regime
exits: R:R grid, OR-width targets, time exit
session: NSE 09:15 / US 09:30 etc. (must be explicit)
```

### Rules

```text
- OR high/low fixed only after last OR bar CLOSES (no lookahead)
- Costs always on
- Report: best profit, best consistency, best composite
- Does NOT auto paper/live trade winners
- May later feed top combo as EVIDENCE into PaperTradeGuidance only
```

### Best placement (do not dump everything in one place)

| Purpose | Best place |
|---------|------------|
| Search best strategy/TF/orb bars/combo | Stock App **`research/orb`** (VectorBT discovery) |
| Prove **repeated success** (not max profit only) | **`validation/` + OOS/WF** on **top-K** winners |
| Store recipe | **`research.db` playbook** rows |
| “Take ORB now?” one-touch | **Paper-guidance spine** reads playbook as **evidence vote** (no re-sweep on click) — **v1.1 bridge** |
| Paper fill | **sim** after human approve |
| Chart OR box | **self_indc / chart** visual only |

```text
Discover → Prove → Playbook store → (v1.1) Guidance evidence → Approve → Sim paper
```

Full reasoning: `ORB_RESEARCH_ENGINE_PLAN.md` §0.  
**ORB vs Kronos/Vision influence:** `ORB_RESEARCH_ENGINE_PLAN.md` **§0.8**.  
**Implement order lock:** `TRADE_VISION_ARCHITECTURE_DESIGN.md` **§0** = **OLD plan + only 3 patches:**

```text
PATCH 1: snapshot_hash minted at D2 snapshot freeze (not D1 gate)
PATCH 2: D6 post-agg if low_evidence_flag → max band WATCH (C-03)
PATCH 3: Week 4 = prove+promote+reports only; ORB→guidance bridge = v1.1
```

```text
ORB = research playbook brain (offline)
Vision engines + Kronos = decide-now brains (online snapshot)
Arbiter = boss; ORB only optional weak evidence vote when wired (v1.1)
Paper = human approve only — ORB job never auto-fills
```

### Suggested ORB phases (parallel to spine P0–P2)

| Phase | Deliverable |
|-------|-------------|
| ORB-0 | Schema + session tables |
| ORB-1 | Signal builders (breakout + wrap ORR/hybrid) |
| ORB-2 | Sweep on VectorBT + research.db (**Discover**) — Week 3 |
| ORB-3 | Consistency/OOS ranking (**Prove**) + promote + reports — **Week 4 only** [Patch 3] |
| ORB-4 | research.html ORB UI (optional, later) |
| ORB-5 | Guidance evidence bridge — **v1.1** [Patch 3], not Week-4 DoD |
---

## 4. Critical gaps (plan must close these)

```text
G1 No single spine API/UI action
G2 Dual decision languages (BUY/SELL vs WAIT/WATCH)
G3 Engines parallel, not forced order
G4 No single PaperTradeGuidance object as product contract
G5 Decision not wired to sim paper book
G6 OpenAlgo real paper fill loop missing (defer)
G7 Stock App and TV are islands
G8 Memory/reliability not always required before decision
G9 Missing market context must cap confidence, not invent data
G10 One-touch package not built
G11 ORB combo research lab missing (strategy×TF×orb length×filters; profit + repeated success)
```

---

## 5. Hard safety (never violate in plan)

```text
- live_trading_blocked = true for v1–v2 of this spine
- order_routing_enabled = false
- No broker credentials created by Trade Vision
- No future candle in decision features
- Incomplete higher-TF bar ≠ closed evidence
- External AI (Gemini/Grok/etc.) display/review only — cannot override risk/NO_TRADE
- Kronos research only — cannot override NO_TRADE
- Low evidence → WAIT/WATCH, not high-confidence ENTER_PAPER
- Human approve before paper fill (default)
- OpenAlgo adapter today is simulator/review boundary — not live broker
```

---

## 6. Recommended build phases (planning AIs should refine, not discard)

| Phase | Name | Deliverable | Out of scope |
|-------|------|-------------|--------------|
| **P0** | Contract lock | Schemas + engine role matrix + band vocabulary | New engines |
| **P1** | Spine decision only | `POST .../paper-guidance/run` + one UI card + fixed engine order + arbiter boss | Paper fill, live, OA fills |
| **P2** | Approve → sim fill | Human approve → Stock App sim trade → PaperTradeResult | Live, OA |
| **P3** | UX anti-soup | Demote raw BUY/SELL; evidence drill-down only | — |
| **P4** | Memory harden | Require reliability/analogs or cap band | Full mega memory plan |
| **P5** | OA paper loop | Only after P2 solid | Live pilot |
| **P6** | Live pilot | Separate safety program | Default product |

### Parallel track (ORB research — does not replace P0–P2)

| Phase | Name | Deliverable | Out of scope |
|-------|------|-------------|--------------|
| **ORB-0…2** | ORB foundation | Sweep grid + VectorBT (Week 3) | Auto paper/live |
| **ORB-3** | Prove + promote | OOS/WF/consistency + playbook table (**Week 4 only**) [Patch 3] | Guidance bridge in same week |
| **ORB-4** | UI reports | research.html later | — |
| **ORB-5** | Guidance bridge | D3a playbook match — **v1.1** [Patch 3] | Auto trade |

**Build note:** Spine P0–P2 and ORB-0…3 can run **in parallel**. Implement **OLD D-order** from `TRADE_VISION_ARCHITECTURE_DESIGN.md` §0.4 + **only Patch 1–3**.
**Suggested first engine order (reuse):**

```text
snapshot → PIT/data quality
→ chart reasoning (v1.70)
→ regime feedback (v1.71) if context else unavailable
→ structure liquidity (v1.72)
→ exec/event/oi risk (v1.73)
→ lag vote + reliability summary if present
→ optional Stock App ML/TA as votes only
→ final confluence arbiter (v1.75)
→ package PaperTradeGuidance
```

---

## 7. Acceptance (definition of done for “one-touch paper guidance”)

> **Authoritative marks:** main file **§8 Acceptance checklist** (updated 2026-07-24).  
> Appendix copy kept for history; do not treat unchecked boxes below as current status.

```text
See §8 (top of this file) for [x]/[~]/[ ] with evidence notes.
Summary 2026-07-24: API spine strong; product one-touch still open
  (dual band language + multi-panel UI + playbook density).
TV local paper ledger = shipped for eligible ENTER_PAPER (v1.93–v1.94).
Stock App sim_trading bridge = optional later. live_trading_blocked = true.
```

---

## 8. Repo anchors (paths only — optional second attach)

```text
IMPLEMENT LOCK: trade-vision-app/docs/plans/TRADE_VISION_ARCHITECTURE_DESIGN.md §0
                (OLD plan + Patch1 D2 hash + Patch2 D6 low_evidence + Patch3 Week4/bridge v1.1)
REQUIREMENT: trade-vision-app/docs/plans/FINAL_REQUIRED_FLOW.md
GOD VIEW:    trade-vision-app/docs/plans/PROJECT_GOD_VIEW_FOR_AI.md
ORB LAB:     trade-vision-app/docs/plans/ORB_RESEARCH_ENGINE_PLAN.md
FLOW WHY:    trade-vision-app/docs/plans/FINAL_REQUIRED_FLOW.md (Appendix B — Think Engine)
SAFETY:      trade-vision-app/docs/SAFETY_INVARIANTS.md
VERSION:     trade-vision-app/docs/IMPLEMENTATION_STATUS.md
NEXT:        trade-vision-app/docs/NEXT_BUILD_TARGET.md
STATUS LOG:  trade-vision-app/docs/IMPLEMENTATION_STATUS.md  (DO NOT attach whole file)
TV ARCH OP:  trade-vision-app/ARCHITECTURE.md  § OPERATOR MAP only if needed
STOCK SIM:   root server.py /api/sim/* , sim_trading.db
BRAIN CODE:  trade-vision-app/apps/api/app/behavior/
RESEARCH:    root research/engine/* , research.db , static/research.html
ORR CODE:    root shared/indicators/self_indc.py (opening_range_reversal, hyb_*)
ORB TARGET:  root research/orb/* (to build)
```

---

## 9. Anti-patterns (reject these plan ideas)

```text
- "Add 20 more indicators first"
- "Enable live trading to validate paper"
- "Let ensemble BUY be the final decision"
- "Auto paper without approve in v1"
- "Full OpenAlgo live pilot before sim spine"
- "Full indicator memory mega-plan before one guidance API"
- "Separate final answers per engine in main UI"
- "ORB max in-sample profit only (no OOS/consistency) = best strategy"
- "Auto-trade the ORB winner live or without approve"
- "Claim ORR single-strategy defaults are the full ORB research lab"
```

---

## 10. Success metric for the planning AI

A good plan is **small, ordered, testable**, and gets user to:

```text
PRIMARY:  touch → guidance → approve → sim paper result
PARALLEL: ORB sweep → best strategy/TF/orb length/combo by profit + repeated success
          (research only; optional later evidence into guidance)
```

in the **fewest phases**, reusing existing engines, without live trading.


---

## APPENDIX B — Think-Engine Best Flow Reasoning (former `THINK_ENGINE_BEST_FLOW_REASONING.md`)

> **Merged 2026-07-24 for zero data loss.**  
> **Use when:** deciding **why / when / how** engines are ordered (Flow R vs Flow D).  
> **Implement lock:** do not treat alternate “ideal” orders as overriding ARCHITECTURE_DESIGN §0 (OLD D + 3 patches).  
> **Companions:** body of this file, ORB plan §0.8, GOD_VIEW.

# Think-Engine Best Flow — Question-Driven Design

> **Purpose:** Before building more code, answer **why / what / when / how** so the flow is correct, not just large.  
> **Audience:** Humans + external AIs (Gemini, Claude, Kimi, GLM, …).  
> **Date:** 2026-07-22  
> **Requirements this serves:** one-touch paper guidance · organized engines · ORB research playbook · no live auto-trade  
> **Companions:** `FINAL_REQUIRED_FLOW.md`, `ORB_RESEARCH_ENGINE_PLAN.md` §0.8, `PROJECT_GOD_VIEW_FOR_AI.md`, `FINAL_REQUIRED_FLOW.md Appendix A (AI Brief)`  
> **IMPLEMENT LOCK:** Coding follows `TRADE_VISION_ARCHITECTURE_DESIGN.md` **§0** = **OLD plan + only 3 patches** (not a full re-order of this document’s “ideal” variants).

### Product implement order (authoritative — do not ignore)

```text
BASE = OLD Flow D:
  D1 GATE → D2 SNAPSHOT → D3a SETUP → D3b MEMORY → D4 STRUCTURE
  → D5 KRONOS? → D6 ARBITER → D7 JARVIS UI → D8 HUMAN → PAPER

ONLY 3 PATCHES (mandatory):
  1) snapshot_hash minted at D2 (not D1)
  2) D6 post-aggregation: low_evidence_flag → max WATCH (C-03)
  3) Week 4 = ORB prove+promote only; ORB→guidance bridge = v1.1
```

Reasoning sections below still explain *why* engines exist; **do not** treat alternate orders here as overriding §0 of the architecture design file.

---

## Method used in this document

At every stage we force:

```text
WHY   — reason to exist (if weak → do not put in critical path)
WHAT  — job, inputs, outputs, requirements
WHEN  — offline job vs online click vs after approve
WHERE — which product/layer owns it
HOW   — order relative to others
WHAT IF FAILS — failure mode / cap / block
WHO WINS — if conflict with another engine
```

**Rule:** Do not add an engine to the main path until its WHY is stronger than “we already built it.”

---

# PART A — Foundational questions (before any flow)

## A1. Why do we need a flow at all?

| Question | Answer |
|----------|--------|
| **Why not run all engines in parallel forever?** | Parallel soup creates conflicting BUY/WAIT answers; operator cannot act; paper has no single ticket. |
| **Why not one magic model only?** | Markets need structure, risk, session, costs; single model overfits and ignores safety. |
| **Why a flow (ordered pipeline)?** | Different engines answer different questions; some must **block** others; order encodes priority. |
| **What is the flow’s purpose?** | Turn many analyses into **one actionable band** (WAIT/WATCH/ENTER_PAPER/AVOID) with reasons, then optional paper. |
| **How does this help trade (paper)?** | Reduces false entries, forces risk/structure first, makes approve→sim measurable; research (ORB) finds playbooks offline so click stays fast. |
| **What fault if we skip this questioning?** | Build wrong spine (e.g. ORB grid on every click; Kronos as boss; auto paper). |

## A2. What is “success” for the user?

| Question | Answer |
|----------|--------|
| **What does the user want at research time?** | Best strategy/TF/orb length/combo by profit + **repeated** success. |
| **What does the user want at decision time?** | One clear band + why + entry/stop/invalidation idea. |
| **What does the user want at paper time?** | Controlled sim fill + result linked to that decision. |
| **What does the user NOT want?** | Live auto-trade, 20 final answers, slow multi-hour click. |

## A3. What must never be violated?

```text
WHY: capital and trust
WHAT: live_trading_blocked; no future-bar leakage; AI/Kronos cannot override risk/NO_TRADE
WHEN: always on decision and paper paths
FAULT IF IGNORED: unsafe product even if “smart”
```

---

# PART B — Arrange all think engines by job / function / output / purpose / requirement

Engines are grouped by **job class**. Within a class, they share when they should run.

## B0. Legend

| Field | Meaning |
|-------|---------|
| **Job** | One-line duty |
| **Function** | How it works in the system |
| **Output** | What it produces |
| **Purpose** | Why we keep it |
| **Requirement** | Rules when using it |
| **Cadence** | Offline / online / post-approve |

---

## B1. Class GATE — “May we even look?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Kill switch / order path guard | Hard stop | Block all trade-like paths | blocked / open | Safety | Always checked first | Online |
| PIT / data quality | Causal data only | Reject future/incomplete HTF | pass/fail + reasons | No leakage | Fail → WAIT/AVOID | Online |
| Live routing flags | Authority | Ensure no broker route | live_blocked=true | Product law | Never false in v1 | Online |

**Why first?**  
If data is illegal or kill is on, every other engine’s BUY is noise.

**What if skipped?**  
Lookahead, unsafe routing, false confidence.

---

## B2. Class DISCOVER (offline) — “What recipe worked in history?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Research discovery runner | Combo search | signals × params × backtest | ranked combos | Strategy search | Caps, costs | Offline job |
| **ORB lab** (planned) | ORB recipe search | TF × orb bars/window × strategy × filters | ranked ORB combos | Answer which ORB to run | No lookahead on OR lock | Offline job |
| ORR / hybrid builders | OR geometry signals | Fixed OR windows + filters | events / long-short | Present OR family | Session-correct open | Offline or chart |
| Backtrader single strategies | Deep path sim | One config, cost model | equity, trades | Audit finalists | Use after top-K | Offline |

**Why separate from decide?**  
Discovery is slow and multi-trial; decision must be one snapshot.

**What if put online?**  
Touch becomes hours; overfits “whatever finished last.”

---

## B3. Class PROVE (offline) — “Is success repeated?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| OOS split / holdout | Time split | Train vs future window | OOS metrics | Stop luck | Mandatory for “best” | Offline |
| Walk-forward / CPCV | Multiple paths | Purged folds / combinatorial | fold stats, CI | Repeated success | Top-K only | Offline |
| Cost / slippage stress | Reality | Worse costs | stressed PF/DD | Avoid paper fantasy | Always on promote | Offline |
| Consistency score | Stability | % profitable months, etc. | consistency | “Most repeated success” | Not max profit alone | Offline |

**Why after discover?**  
Proving every raw combo is impossible; prove **winners only**.

**What if skip prove?**  
ORB/playbook “best” is often overfit → bad paper guidance later.

---

## B4. Class PLAYBOOK (store) — “What recipe is approved?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| research.db / playbook rows | Persist recipes | Store params + metrics + version | playbook_id | Stable memory for decide | Only PROVE-passed | After prove |
| ORB playbook | ORB-specific recipe | symbol/TF/orb/strategy/filters | frozen combo | Fast decide input | Version + date range | After prove |

**Why not skip store?**  
Without store, decide must re-discover or use ad-hoc params.

---

## B5. Class CONTEXT (online) — “What is the market situation now?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Chart reasoning v1.70 | Candle/vol regime | Hurst, rejection, VCP, ATR%… | trend/chop/vol packet | Now-shape | Closed bars | Online |
| Market regime v1.71 | Breadth/RS/Bayes-ish | Index/sector context | regime scores, caps | Don’t fight tape | Unavailable → cap confidence | Online |
| Structure/liquidity v1.72 | Auction/structure | VP, sweeps, OB/FVG-style | structure scores | Levels beat raw signal | Chart-only OK | Online |
| MTF pullback / conflict | Multi-timeframe | HTF vs LTF | alignment/opposition | Avoid LTF vs HTF fight | Incomplete HTF ignored | Online |
| Session / calendar | Session phase | Open/OR/lunch/event | phase tags | ORB needs session | Correct exchange open | Online |
| Cross-market / event-ish | External stress | Event risk if present | caps | Avoid event death | Missing ≠ clean | Online |

**Why before indicators?**  
Structure and regime change the meaning of the same RSI/ORB break.

**What if indicators first?**  
Fake multi-confirmation in chop/bad structure.

---

## B6. Class SETUP / INDICATORS (online) — “Is there a pattern now?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Indicator runtime + registry | Compute si_*/pta_* | 94 groups ontology | markers/series | Setup library | Family cap, lag weight | Online subset |
| Indicator lag voting | Weight by lag | Late MACD weaker | votes | Stop late false promote | Lag cannot alone promote PAPER | Online |
| Reliability / signal history | Did this work before? | Labels → rates | reliability | Prefer proven signals | Min samples / shrinkage | Online if data |
| 9C / pattern memory / analogs | Historical similarity | Matches + outcomes | analog packet | “Has this happened?” | Min independent matches | Online if ready |
| Stock App ML ensemble | Direction model | Features → BUY/SELL/HOLD | opinion vote | Extra evidence | Map into WAIT/ENTER language | Online optional |
| **ORB playbook match** | Recipe vs today | Compare OR now to frozen combo | match score / no-match | Bring research into decide | Only proven playbooks | Online optional |
| Chart ORR markers | Visual OR geometry | Events on chart | overlays | Human see OR | Not final boss | Online |

**Why after context?**  
A breakout in bad structure is not a good setup.

**What if all 94 every click?**  
Noise, cost, false agreement — use **subset** + family caps.

---

## B7. Class RISK (online) — “Can we take it safely?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Exec/event/OI risk v1.73 | Fill & external risk | Liquidity grade, slippage, event | grade A/B/C, caps | Avoid unfillable/event trades | Missing depth → proxy, mark unavailable | Online |
| Risk engine / sizing | Size & heat | Position limits | size or zero | Don’t oversize | Zero size if blocked | Online |
| Cooldown / portfolio | After losses / exposure | Cooldown flags | block add | Stop revenge trade | Enforce before ENTER | Online |
| Post-entry lifecycle v1.74 | Manage after fill | BE/trail/invalidate **sim guidance** | plan | Manage paper later | Only after entry exists | Post-entry |

**Why after setup?**  
Risk does not invent setups; it **kills or shrinks** them.

**What if risk early only?**  
You still need risk again after setup forms (event/spread can change).

---

## B8. Class SCENARIO (online optional) — “What paths look plausible?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Kronos (+ proxy) | Path scenarios | Forecast on shared snapshot | path priors | Research what-if | Same hash; cannot execute | Online optional |
| Twin arbiter | Behavior vs Kronos | Compare / conflict | agree/conflict → reduce | Stop fantasy if conflict | Conflict → WAIT bias | Online optional |
| TrendForge intake | External scanner evidence | Signed packets | research evidence | Extra context | Research-only envelope | Online optional |

**Why optional / late?**  
Scenarios are uncertain; they **reduce** confidence more than promote.

**What if Kronos is boss?**  
Forecast error becomes auto-trade risk; violates safety design.

---

## B9. Class JUDGE (online) — “What is the one answer?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Final confluence arbiter v1.75 | Sole final band | Hierarchy + conflicts | WAIT/WATCH/PAPER-CANDIDATE/AVOID | One boss | Reduce-only; hierarchy fixed | Online |
| Jarvis room | Package for human | Assemble reasons, blockers, AI review | desk view | Operator trust | AI display-only | Online |
| Decision engine / quality gates | Extra no-trade logic | Blockers tree | NO_TRADE flags | Extra safety | Cannot enable live | Online |

**Why only one judge?**  
Multiple judges = multiple “final” answers (current fault).

---

## B10. Class EXECUTE (post-approve) — “Did we paper it?”

| Engine | Job | Function | Output | Purpose | Requirement | Cadence |
|--------|-----|----------|--------|---------|-------------|---------|
| Sim trade API | Paper fill | Cash/positions | fill, history | Practice | Human approve first | Post-approve |
| Execution simulator | Realistic fill model | Slippage/partial | sim quality | Honest paper | Label as simulation | Research/sim |
| OA paper loop | External paper | Future | fills | Later path | After sim spine solid | Future |

---

# PART C — Question-driven design of the BEST flow

We design **two flows** (because two cadences). Merging them into one click is a **fault**.

---

## C1. Flow R — RESEARCH / PLAYBOOK (offline)

### Step R0 — Why this flow exists?

| Q | A |
|---|---|
| Why? | User needs best ORB/strategy **recipes** without freezing the trading UI. |
| What purpose? | Discover + prove + store playbooks. |
| How helps trade? | Later decisions use **proven** recipes, not vibes. |
| Fault if missing? | Decide path invents params every day → inconsistent paper. |

### Step R1 — DISCOVER

| Q | A |
|---|---|
| Why now? | Need candidates before proof. |
| What runs? | `research/` + **ORB lab** + signal builders (ORR/breakout). |
| When? | Job/nightly/on-demand. |
| Output? | Ranked combos with profit metrics. |
| Fault? | Infinite grid → cap combos; no lookahead on OR. |

### Step R2 — PROVE

| Q | A |
|---|---|
| Why? | “Most repeated success” is the real requirement, not peak equity. |
| What runs? | OOS, WF/CPCV, cost stress, consistency. |
| When? | Only top-K from R1. |
| Output? | Passed / failed + stressed metrics. |
| Fault if skip? | Overfit playbook poisons decide path. |

### Step R3 — PLAYBOOK STORE

| Q | A |
|---|---|
| Why? | Decide path needs fast read. |
| What? | DB row: symbol, TF, orb definition, strategy, filters, metrics, version. |
| When? | Only PROVE pass. |
| Fault? | Overwriting without version → cannot audit paper losses. |

```text
FLOW R:
  [Job] → DISCOVER → PROVE → PLAYBOOK DB → Report UI
```

---

## C2. Flow D — DECIDE / PAPER (online) — best think-engine order

### Step D0 — Why this flow exists?

| Q | A |
|---|---|
| Why? | User needs **one** answer now for paper guidance. |
| What purpose? | Gate → context → setup → risk → scenario → judge → optional paper. |
| How helps trade? | Fewer false ENTERs; clear reasons; measurable sim. |
| Fault if all parallel? | Same problem you have today: multi-brain, no action. |

### Step D1 — GATE

| Q | A |
|---|---|
| Why first? | Illegal/unsafe data must stop everything. |
| What? | Kill switch, PIT, live_blocked. |
| Output? | CONTINUE or hard WAIT/AVOID. |
| What if fail? | **Stop.** Do not run ML/ORB/Kronos to “see if bullish.” |
| Note | **Does not** mint `snapshot_hash` (Patch 1 — hash at D2). |

### Step D2 — SNAPSHOT (+ context engines as in product lock)

| Q | A |
|---|---|
| Why freeze here? | All voters must see identical bars. |
| What? | Freeze OHLCV → **`snapshot_hash` (Patch 1)**; run context engines per old design. |
| Output? | Snapshot + context packet + caps. |
| What if regime missing? | Cap confidence; do not invent index data. |

### Step D3 — SETUP / EVIDENCE

| Q | A |
|---|---|
| Why after context? | Setups are interpreted under context. |
| What? | Subset of indicators (lag-aware), reliability if any, optional ML vote, **optional ORB playbook match**, pattern/9C if ready. |
| Why not full 94? | Noise and family inflation. |
| Why ORB playbook here not discover? | Discover already answered offline; here only “does today match recipe?” |
| Output? | Evidence votes (family-capped). |

### Step D4 — RISK

| Q | A |
|---|---|
| Why after setup? | Only risk **real** candidates; still must block bad fills. |
| What? | v1.73 liquidity/event, risk size, cooldown. |
| Output? | Block / shrink / allow with caps. |
| What if liquidity C? | Cannot promote to ENTER_PAPER regardless of ORB playbook. |

### Step D5 — SCENARIO (optional)

| Q | A |
|---|---|
| Why optional? | Latency, uncertainty; research prior. |
| What? | Kronos + twin on **same snapshot hash**. |
| How influences? | **Reduce only** on conflict/weakness. |
| Why not before risk? | Risk is harder constraint than scenario preference. |
| What if Kronos fails? | Continue with WAIT bias; do not crash guidance. |

### Step D6 — JUDGE

| Q | A |
|---|---|
| Why one judge? | Single actionability. |
| What? | Final confluence arbiter + Jarvis package. |
| Hierarchy why this order? | Safety > data > liquidity > regime > structure > volume > RS > indicators/ORB playbook > external AI. |
| Output? | **One** final_band + reason tree + engines_run. |
| **Patch 2 (mandatory):** | After aggregation, if `low_evidence_flag` → **max WATCH** (cannot ENTER_PAPER). Prevents structure/setup from bypassing memory. |

### Step D7 — HUMAN

| Q | A |
|---|---|
| Why human? | Paper still needs accountability; system not oracle. |
| What? | Approve / reject ENTER_PAPER. |
| Fault if auto? | Research errors become sim spam; later live temptation. |

### Step D8 — PAPER

| Q | A |
|---|---|
| Why last? | Only after decision + approve. |
| What? | Sim trade → PaperTradeResult. |
| Why not ORB job fill? | Different purpose (research vs practice execution). |

```text
FLOW D (best online order):

  GATE
    → CONTEXT (chart/regime/structure/MTF/session)
      → SETUP (indicators lag-aware + optional ORB playbook match + optional ML)
        → RISK (liquidity/event/size/cooldown)
          → SCENARIO optional (Kronos/twin reduce-only)
            → JUDGE (arbiter + Jarvis)
              → HUMAN approve?
                → PAPER sim
```

---

## C3. How the two flows connect (best overall system)

```text
        FLOW R (offline)                    FLOW D (online)
        ────────────────                    ────────────────
        Discover engines                    Gate
        Prove engines                       Context engines
        Playbook store ──────────────────►  Setup (playbook match vote)
                                            Risk
                                            Kronos optional
                                            Arbiter
                                            Human → Paper

Cross-influence rules:
  R → D : playbook evidence only (weak, optional)
  D → R : none required (optional: log outcomes to improve prove later)
  Kronos ↛ R by default
  ORB discover ↛ D directly (never full grid on click)
```

---

## C4. “Why this order?” stress test (fault avoidance)

| Alternative order | Why rejected |
|-------------------|--------------|
| Indicators first | Confirms nonsense in bad regime/structure |
| Kronos first | Forecast bias before hard safety/data checks |
| ORB discover on click | UX death + overfit temptation |
| Risk last after arbiter | Arbiter might ENTER then risk says impossible — flip-flop |
| ML BUY as final | Dual language; skips structure/risk hierarchy |
| Paper before human | Violates trust; couples research noise to ledger |
| Prove before any discover | No candidates; empty science |
| Discover without prove as “best” | Repeated-success requirement fails |

---

## C5. Minimal engine set for v1 (efficiency)

**Online Flow D (must):**  
Gate · chart v1.70 · structure v1.72 · risk v1.73 · arbiter v1.75 · Jarvis · sim after approve  

**Online Flow D (should):**  
Regime v1.71 if available · MTF · lag vote subset · playbook match if playbook exists  

**Online Flow D (optional):**  
Kronos/twin · full reliability · analogs  

**Offline Flow R (ORB track):**  
ORB discover · prove top-K · playbook store  

**Defer:**  
OA live · full 94 every click · post-entry until paper entry exists  

---

# PART D — Requirement coverage checklist

| Your requirement | Flow / step that fulfills it |
|------------------|------------------------------|
| Organized think engines | Class order GATE→…→JUDGE |
| One decision language | D6 arbiter bands |
| One-touch guidance | Flow D |
| Paper after control | D7–D8 |
| ORB best strategy/TF/bars/combo | Flow R1 |
| Profit ranking | Flow R1 metrics |
| Most repeated success | Flow R2 prove |
| Use ORB without breaking Vision | Playbook vote only in D3 |
| Kronos present but safe | D5 reduce-only |
| Avoid multi-final-answers fault | Single judge D6 |
| Avoid slow click fault | No R1 inside D |

---

# PART E — Questions every AI/builder must answer before coding a change

Copy this gate for any PR:

```text
1. WHY does this engine exist in the path (not just in the repo)?
2. WHAT job/output/requirement does it own?
3. WHEN does it run (offline/online/post-approve)?
4. WHERE does it sit in Flow R vs Flow D?
5. HOW does it influence the arbiter (block / reduce / vote / display)?
6. WHAT IF it fails or data missing?
7. WHO WINS if it conflicts with risk / Kronos / ORB playbook?
8. DOES it create a second “final answer” UI? (must be no)
9. DOES it auto paper/live? (must be no for v1)
10. HOW is it tested for the failure mode in Q6?
```

If any answer is vague → **do not merge into critical path**.

---

# PART F — Bottom line

```text
BEST FLOW = TWO CADENCES:

  R: Discover → Prove → Playbook     (ORB + research brains)
  D: Gate → Context → Setup(+playbook) → Risk → Scenario? → Judge → Human → Paper

ARRANGE ENGINES BY JOB CLASS, NOT BY “who coded last.”
ASK WHY/WHAT/WHEN BEFORE BUILDING — avoids soup, overfit, and unsafe auto-trade.
```

**Path:** `trade-vision-app/docs/plans/FINAL_REQUIRED_FLOW.md (Appendix B — Think Engine)`

