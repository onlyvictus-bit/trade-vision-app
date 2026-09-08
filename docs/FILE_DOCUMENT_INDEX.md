# FILE & DOCUMENT INDEX

> **Purpose of this file (single map):**  
> 1) **Question → which file?** (former `CONTEXT_INDEX.md`)  
> 2) **Which code/doc owns what?** (former `FILE_OWNERSHIP_MAP.md`)  
> 3) **Full library catalog** of docs/folders, read order, plans, audit  
> **Last updated: 2026-09-08 (application brain/skeleton/wiring reference indexed; AFRE v4 architecture understanding captured)**  
> **Monorepo root:** `D:\Projects\trading-platforms\stock-app`  
> **Trade Vision root:** `...\stock-app\trade-vision-app`  
> **Do not treat this as code source of truth** — code truth is implementation; this is the **map to all maps**.  
> **Audit rule:** §12 must list every project `.md` (excluding noise) and every product folder; if missing, index is incomplete.  
> **Do not recreate** separate `CONTEXT_INDEX.md` or `FILE_OWNERSHIP_MAP.md` — update **this file** only.

---

## How to use this index (start here — no confusion)

**This is the only map file you need for navigation.**  
Do **not** look for `CONTEXT_INDEX.md` or `FILE_OWNERSHIP_MAP.md` (merged here).

### Three jobs — three places

| Your need | Open this section | What you get |
|-----------|-------------------|--------------|
| **1. “I have a question — which file?”** | **§0.6** Question → file router | Short table: Need X → read Y first |
| **2. “Which code/doc owns this?”** | **§7.4** File ownership map | High-signal modules (backend / frontend / docs) |
| **3. Full library / onboarding / audit** | **§0** read order · **§2–§6** docs · **§7.1–7.3** folders · **§8** missed · **§12** audit | Catalog of all product docs + folders |

### Simple rules

```text
Lost / new chat / "where is X?"     → §0.6 first
Coding / "who owns reliability?"    → §7.4 first
Deep onboarding / every doc named?  → §0 then §12 (do not read whole file if you only need one answer)
```

### Related files (not this map)

| Job | File |
|-----|------|
| Latest version + full ship log | `docs/IMPLEMENTATION_STATUS.md` (tip at top) |
| What to build next | `docs/NEXT_BUILD_TARGET.md` |
| Product spine requirement | `docs/plans/FINAL_REQUIRED_FLOW.md` |
| **Application brain / skeleton / engine authority / future wiring reference** | **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** |
| Safety never break | `docs/SAFETY_INVARIANTS.md` |
| Screen → API architecture | `ARCHITECTURE.md` |
| Plan vs code build audit | `docs/BUILD_AUDIT.md` |
| **How the system flows (visual + code-true pack)** | **§ Flow map pack** (below) |

### Flow map pack (canonical — do not scatter)

> **All flow-map MD content is merged into HTML.**  
> Former files removed: `FLOW_MAP_WORK_LOG.md`, `FLOW_MAP_NODE_EXPLAINER.md`, `VERIFIED_PAPER_FLOW_FROM_CODE.md`, `implementation_plan.md` (graph audit — not product plans under `docs/plans/`).

| Priority | File | Use when |
|----------|------|----------|
| **1 · open first** | **`docs/TV_COMPLETE_FLOW_MAP.html`** | Tabs 1–5: process · network · block details · fit · **code-truth + audit + work log** |
| **2 · 10-min brain** | **`docs/PROJECT_BRAIN.html`** | Caveman cards for every major block (new teammate) |
| **3 · architecture brain reference** | **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** | Plain-English specialist brains, authority hierarchy, AFRE/ORB/Jarvis wiring, final-output contract, and future-upgrade rules |
| Support | `docs/REMAINING_PY_INVENTORY.md` | Other `.py` lanes not on the paper spine line |
| Support | `docs/ENGINE_BLOCK_ACTION_INVENTORY.md` | Named engine/block/action families |
| Support | `docs/BUILD_AUDIT.md` | Earlier multi-brain / FINAL-vs-code product audit |

**Full Windows paths:**

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\docs\TV_COMPLETE_FLOW_MAP.html
D:\Projects\trading-platforms\stock-app\trade-vision-app\docs\PROJECT_BRAIN.html
D:\Projects\trading-platforms\stock-app\trade-vision-app\docs\APPLICATION_BRAIN_SKELETON_AND_WIRING.md
```

Also linked from: `TRADE_VISION_README.md` (short) · `ARCHITECTURE.md` MASTER GUIDE (see also).

### Jump table (detail)

| If you need… | Start at |
|--------------|----------|
| “I have a question — which file?” | **§0.6** Question → file router |
| “Which module owns X?” | **§7.4** File ownership map (code + docs) |
| **“What brains exist, how do they connect, and who has final authority?”** | **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** |
| First-time orientation | §0 Read order |
| Product requirement (paper guidance spine) | `docs/plans/FINAL_REQUIRED_FLOW.md` |
| Flow map / how blocks connect | **§ Flow map pack** (above) |
| Doc purpose / field tables | §2–§6 |
| Code folders | §7.1–§7.3 |
| What people usually forget | §8 Missed details |
| Which plan is done | §5 Plans |
| Full audit / every doc named? | **§12 FULL FILESYSTEM AUDIT** |
| God-view for external AIs (indicators+engines)? | `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md` (§5.5) |
| Token-light multi-AI plan pack? | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` (§5.6) |
| ORB research (best TF / candle count / combo)? | `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` (§5.7) |
ORB_TIMING_RESEARCH_V197 (docs/plans/)  - per-stock ORB clock-window timing research build spec (v1.97, gates ORB-T197-001..010)
ORB_CONTEXT_NATIVE_PLAN_V2 (docs/plans/)  - v2.00 ORB upgrade plan: gap bias-lock + CPR wide/narrow + PDH/PDL family + execution realism (PROPOSED, milestones M1-M6, awaiting approval)  [+ v2.01-track amendment 2026-09-04: renumbered off shipped versions, M0, staged adoption, S5 fix, BEL default]
ORB_GAP_TRADING_EXTERNAL_REVIEW_BRIEF (docs/plans/)  - self-contained brief + copy-paste prompt for outside-AI gap-morning review
ORB_SIMPLE_FLOW (docs/)  - 9-box plain-English flow map: exact Python file + detail doc + built/needed per box; start here when lost
ORB_STRATEGY_MEMORANDUM (docs/plans/)  - rule-level ORB v2 trade spec: entry/stop/target per gap×CPR×price-zone combo + worked examples (1A/1B/2/3/4)
ORB_V2_JUDGE_FINDINGS (docs/plans/)  - adversarial verification of the v2 plan: 2 errors + 5 gaps found and integrated; incl. live-path prev-day flow problem
ORB_V201_PRECODE_REVIEW_KIMI (docs/plans/)  - VERBATIM archive of the FIRST submission (2026-09-01 pre-code review: B1-B8/S-A/S-B/S1-S10/P1-P3/V1-V4; retro-archived in the 09-03 audit; byte-exact)
ORB_V201_NSE_REVIEW_KIMI (docs/plans/)  - VERBATIM archive of the second external review (NSE Tuesday-expiry regime, 18 ORB variants, ~40 failure scenarios, derivatives overlay, top-10; byte-identical, 0 diffs)
ORB_V201B_NSE_REVIEW_KIMI_PART2 (docs/plans/)  - VERBATIM archive of the 2nd Kimi submission (Task 3/4 continuation + reasoning trace; byte-exact, CRLF preserved)
ORB_V201C_NSE_REVIEW_KIMI_PART3 (docs/plans/)  - VERBATIM archive of the 3rd Kimi submission (consolidated Tasks 1-4: 18 variants, 50-row decision table, top-10; byte-exact)
ORB_V201_VERIFIED_ANSWER (docs/plans/)  - line-by-line verification of all three v2.01 submissions vs our docs: §1-6 submission 1 (1 wrong/13 missed/11 right); §7 submission 2 (4 corrections/11 misses/13 conflicts); §8 submission 3 (0 contradictions/10 new rules/6 triple-confirmations)
INDICATOR_COVERAGE_V199 (docs/plans/)  - complete safe indicator coverage spec + results (v1.99: 49/94 runtime, registry 86/7/1)
FLOW_REAUDIT (scripts/flow_reaudit.py + docs/runbooks/flow-reaudit.md)  - first check for any flow issue; full D1-D8 on real HSTRY data
| Best think-engine flow (job/why/when reasoning)? | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix B — Think Engine)` (§5.8) |
| What to attach to Gemini/Claude/Kimi/GLM? | §0.5 External AI send pack |

---

## 0. Recommended read / use order

### 0.1 First hour (human or AI)

```text
ORDER  PATH
-----  ----
  1    THIS FILE  (docs/FILE_DOCUMENT_INDEX.md)
  2    docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md  ← plain-English application brain + authority + wiring
  3    docs/plans/FINAL_REQUIRED_FLOW.md          ← your required product spine
  4    docs/plans/PROJECT_GOD_VIEW_FOR_AI.md      ← full skeleton: indicators + engines
  5    docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)   ← short multi-AI plan pack
  6    TRADE_VISION_README.md  § MASTER GUIDE  (or ARCHITECTURE.md § MASTER GUIDE)
  7    docs/IMPLEMENTATION_STATUS.md            ← latest tip + full ship log
  8    docs/SAFETY_INVARIANTS.md                  ← never break
  9    docs/NEXT_BUILD_TARGET.md                  ← what to build next
 10    ARCHITECTURE.md  § OPERATOR MAP            ← screen → API
 11    docs/context.md                            ← domain + invariants
 12    docs/graph.md                              ← structure picture
 13    Only then: §7.4 ownership map + exact code
```

### 0.1b Token-saving read order for new chat (from former CONTEXT_INDEX)

```text
1. TRADE_VISION_README.md (§ AI Handoff)
2. docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md  ← when task touches engine behavior/wiring/authority
3. docs/IMPLEMENTATION_STATUS.md   ← tip at top; one version section if needed
4. docs/NEXT_BUILD_TARGET.md
5. docs/SAFETY_INVARIANTS.md
6. only then open exact source files needed for the requested change
```

### 0.5 External AI send pack (token-conscious)

```text
DEFAULT (zero-context AI that must understand the whole product):
  1) docs/plans/PROJECT_GOD_VIEW_FOR_AI.md     ← god skeleton (indicators, engines, flows)
  2) docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md  ← how specialist brains are meant to behave/connect
  3) docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)  ← what to build (one-touch paper spine)

OPTIONAL ADD:
  4) docs/plans/FINAL_REQUIRED_FLOW.md
  5) docs/SAFETY_INVARIANTS.md

DO NOT SEND FIRST:
  IMPLEMENTATION_STATUS.md (whole)
  TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md (whole)
  full ARCHITECTURE.md / whole repo
```

### 0.2 When implementing a version

```text
 1  docs/NEXT_BUILD_TARGET.md
 2  docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md  (if engine/wiring/authority changes)
 3  docs/plans/FINAL_REQUIRED_FLOW.md  (if paper-guidance related)
 4  Matching plan under docs/plans/ (if subsystem work)
 5  SPEC.md + ARCHITECTURE.md (contracts)
 6  this file §7.4 ownership map → open listed modules
 7  docs/API_ENDPOINT_INDEX.md / FRONTEND_PANEL_MAP.md
 8  Implement + tests (TEST_PLAN.md / TEST_ID_INDEX.md)
 9  Update docs/IMPLEMENTATION_STATUS.md (latest tip block + append version section)
10  Refresh context/graph/MASTER GUIDE / this index if structure changed
11  Refresh APPLICATION_BRAIN_SKELETON_AND_WIRING if engine role, authority, data contract, or decision wiring changed
```

### 0.3 When only running Stock App chart/sim

```text
 1  ../STOCK_APP_README.md  (§ MASTER GUIDE + quick start)
 2  ../STOCK_APP_ARCHITECTURE.md  (operator map + paper sim flow)
 3  ../API.md
 4  server.py / static/*
```

### 0.4 Avoid opening first (too large)

These are important but too large for first-pass context (use §0.6 to pick a slice first):

```text
apps/api/app/main.py
apps/web/src/App.tsx
apps/api/tests/test_api.py  (whole)
docs/IMPLEMENTATION_STATUS.md  (whole — open tip + one version only)
docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md  (slice only)
```

### 0.6 Question → file router (former CONTEXT_INDEX — full table)

> **Purpose:** reduce token usage — answer “Need X → read Y” without grepping all docs.  
> **Last reviewed with merge:** 2026-09-08  
> **Update when:** new key docs appear or ownership moves.

| Need | Read This First | Then Read |
|------|-----------------|-----------|
| What is already built? / latest version tip? | `docs/IMPLEMENTATION_STATUS.md` (tip at top, full log below) | `docs/NEXT_BUILD_TARGET.md` |
| Build-as-planned audit (gaps / doc drift)? | `docs/BUILD_AUDIT.md` | code + graph + FINAL_REQUIRED_FLOW |
| **How does data move Start→End (visual)?** | **`docs/TV_COMPLETE_FLOW_MAP.html`** Tabs 1–2 | `docs/PROJECT_BRAIN.html` |
| **What brains exist / how are they wired / who can overrule whom?** | **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** | `docs/TV_COMPLETE_FLOW_MAP.html` + exact code |
| **Explain every block in plain English?** | **`docs/PROJECT_BRAIN.html`** | `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md` + HTML **Tab 3** |
| **Exact paper code path from Python?** | **`docs/TV_COMPLETE_FLOW_MAP.html` Tab 5** | `paper_guidance_spine.py` + ORB modules |
| **Was the flow map audited vs code?** | **`docs/TV_COMPLETE_FLOW_MAP.html` Tab 5** | audit score 86/100 + fixes applied |
| **Graph work history / which file best?** | **`docs/TV_COMPLETE_FLOW_MAP.html` Tab 5** | this index § Flow map pack |
| What should be built next? | `docs/NEXT_BUILD_TARGET.md` | plans only if needed for that target |
| What is the system? | `docs/context.md` | `ARCHITECTURE.md` |
| 2-min operator map (screen→button→API)? | `ARCHITECTURE.md` § OPERATOR MAP | `../STOCK_APP_ARCHITECTURE.md` § OPERATOR MAP (Stock App) |
| Paper trade full flow (symbol→calc→paper)? | `ARCHITECTURE.md` § PAPER TRADE FULL FLOW | `docs/TV_COMPLETE_FLOW_MAP.html` Tabs 1+5 |
| Will paper flow work / improve how? | `ARCHITECTURE.md` § J. Flow assessment | Stock App paper assessment in `../STOCK_APP_ARCHITECTURE.md` |
| Compact handoff (legacy path) | `TRADE_VISION_README.md § AI / New-Chat Handoff` | `docs/context.md` |
| What are the safety rules? | `docs/SAFETY_INVARIANTS.md` | `docs/context.md` INV-* |
| What files own what? | **this file §7.4** | source files listed there |
| What UI panels exist? | `docs/FRONTEND_PANEL_MAP.md` | `apps/web/src/App.tsx` |
| What API endpoints exist? | `docs/API_ENDPOINT_INDEX.md` | `apps/api/app/main.py` |
| What tests matter? | `docs/TEST_ID_INDEX.md` | `apps/api/tests/test_api.py` |
| What does the graph show? | `docs/graph.md` | `docs/graph/project_graph.json` |
| Root monorepo constraints | `../STOCK_APP_ARCHITECTURE.md` + TV `ARCHITECTURE.md` §6 | `docs/context.md` § monorepo |
| How does indicator intelligence work? | `docs/plans/TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md` | `docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md` |
| How does OpenAlgo fit? | `docs/plans/OPENALGO_PAPER_TO_LIVE_REMAINING_BUILD_PLAN.md` | `docs/SAFETY_INVARIANTS.md` |
| Required final paper-guidance spine? | `docs/plans/FINAL_REQUIRED_FLOW.md` | `ARCHITECTURE.md` § MASTER GUIDE |
| Current Paper Guidance P0 code/contract/tests? | `docs/IMPLEMENTATION_STATUS.md` § v1.87 | `paper_guidance_spine.py` + `test_paper_guidance_spine.py` |
| Full doc/folder index? | **this file** | §0.6 + §7.4 + §12 |
| Token-light brief for external AIs? | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` | `docs/plans/FINAL_REQUIRED_FLOW.md` |
| Full god-view for external AIs? | `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md` | `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md` + `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` |
| ORB strategy/TF/candle-count research? | `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` | `research/` engine + ORR in `self_indc` |
| Best think-engine order? | `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md` | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix B — Think Engine)` |
| Combined multi-AI design + implement charter? | `docs/plans/TRADE_VISION_ARCHITECTURE_DESIGN.md` (§0 = OLD + 3 patches) | PAPER_TRADE_SPINE brief + ORB plan |
| How do Gemini/Grok credentials work? | `docs/runbooks/EXTERNAL_AI_CREDENTIALS_RUNBOOK.md` | `apps/api/app/behavior/ai_credentials_vault.py` |

---

## 1. Document field legend

Each entry below uses:

| Field | Meaning |
|-------|---------|
| **Purpose** | Why the file exists |
| **Function** | What job it performs in the project |
| **Action** | What you *do* with it (read / update / follow) |
| **Requirement** | What rule or need it encodes (if any) |
| **Use when** | Trigger to open it |
| **Authority** | How much to trust it vs code |

---

## 2. Entry files (start here)

### 2.1 `docs/FILE_DOCUMENT_INDEX.md` (this file)

| Field | Detail |
|-------|--------|
| **Purpose** | Master index: Q→file router + ownership map + full doc/folder catalog |
| **Function** | Navigation layer over all other docs **and** high-signal code owners |
| **Action** | Read first; update when new docs/folders/owners/questions are added |
| **Requirement** | Keep paths accurate; link FINAL_REQUIRED_FLOW; no separate CONTEXT_INDEX / FILE_OWNERSHIP files |
| **Use when** | Lost, onboarding, “where is X?”, “who owns Y?” |
| **Authority** | Map only; not runtime |

### 2.2 `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Durable plain-English reference for the application's thinking/calculation/decision skeleton |
| **Function** | Maps specialist brains, inputs/outputs, ORB/AFRE/Jarvis relationships, authority hierarchy, desired final output, and future-evolution rules |
| **Action** | Read before adding/replacing/rewiring a major engine; update when engine ownership, authority, contracts, data path, ORB/AFRE behavior, or final decision wiring changes |
| **Requirement** | Preserve one canonical decision authority, fail-closed missing data, PIT/proof/safety boundaries, no external-AI override, and no parallel hidden decision path |
| **Use when** | Future upgrades/patches, brain evolution, wiring changes, “why are there multiple decision engines?”, ORB/AFRE architecture work |
| **Authority** | Architecture/reference map; implementation code remains source of truth |

### 2.3 `docs/plans/FINAL_REQUIRED_FLOW.md`

| Field | Detail |
|-------|--------|
| **Purpose** | **Your product requirement:** one analysis→label→decision→paper-guidance spine |
| **Function** | Defines present vs final product vs gaps vs phases to build |
| **Action** | Treat as requirement baseline; implement Phase 0→2 before more engines |
| **Requirement** | One `PaperTradeGuidance`; human approve before paper fill; no live v1 |
| **Use when** | Any “paper decision” / organization / missing-flow discussion |
| **Authority** | **Highest for product intent** (target); not yet fully implemented |

### 2.4 `TRADE_VISION_README.md` (trade-vision-app)

| Field | Detail |
|-------|--------|
| **Purpose** | Project intro, mode, handoff list, MASTER GUIDE |
| **Function** | Onboarding + safety boundary summary |
| **Action** | Read MASTER GUIDE; run stack per instructions |
| **Requirement** | research/mock/paper-review; live blocked |
| **Use when** | First clone / “what is this app?” |
| **Authority** | High for mode; version tip may lag pointer by a few lines — trust IMPLEMENTATION_STATUS |

### 2.5 `ARCHITECTURE.md` (trade-vision-app)

| Field | Detail |
|-------|--------|
| **Purpose** | Living architecture, operator map, paper flow, ADRs, MASTER GUIDE |
| **Function** | Screen→API map + system contracts + full monorepo findings in MASTER GUIDE |
| **Action** | Read operator map before coding UI/API; update when routes/panels change |
| **Requirement** | No live routing; reduce-only arbiter; MOCK mode |
| **Use when** | Designing features, explaining flow, AI handoff deep dive |
| **Authority** | High for design; ship completion = IMPLEMENTATION_STATUS |

### 2.6 Root `../STOCK_APP_README.md` and `../STOCK_APP_ARCHITECTURE.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Stock App product + monorepo MASTER GUIDE |
| **Function** | Chart app install, features, wiring, paper sim path |
| **Action** | Use for :8014 Stock App; MASTER GUIDE for two-product map |
| **Requirement** | Educational; paper sim only (not live broker) |
| **Use when** | Chart/backtest/sim/research engine work at repo root |
| **Authority** | High for Stock App wiring |

---

## 3. Core Trade Vision handoff docs (`docs/`)

### 3.1 `docs/IMPLEMENTATION_STATUS.md` (latest tip + full ship log)

| Field | Detail |
|-------|--------|
| **Purpose** | **Merged:** latest completed tip **and** full version-by-version ship log |
| **Function** | Session tip (top) + historical “what shipped in vX” (body) |
| **Action** | Read **Latest completed tip** every session; append a version section after each ship; update tip block to match |
| **Requirement** | Tip must match last shipped version section |
| **Use when** | “What version are we on?” **or** “What did v1.xx implement?” |
| **Authority** | **Highest for version tip + implementation history** |

### 3.2 `docs/NEXT_BUILD_TARGET.md`

| Field | Detail |
|-------|--------|
| **Purpose** | What to build next (candidates / lock) |
| **Function** | Prevent random feature sprawl |
| **Action** | Lock target before coding; prefer FINAL_REQUIRED_FLOW Phase 0+1 |
| **Requirement** | Don’t start version without status/context/graph/tests/safety |
| **Use when** | Planning next PR / session |
| **Authority** | Process gate |

### 3.3 `docs/SAFETY_INVARIANTS.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Non-negotiable safety rules |
| **Function** | Blocks live trade, AI override, future-bar leakage |
| **Action** | Never “temporary disable”; test must prove live blocked |
| **Requirement** | TV: no live orders, no broker creds, WAIT-first language |
| **Use when** | Any decision/execution/OpenAlgo/AI change |
| **Authority** | **Highest for safety** |

### 3.4 `docs/context.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Domain knowledge, INV table, policies, known unknowns |
| **Function** | Fable context layer for AI/engineer |
| **Action** | Read before large refactors; update after invariant changes |
| **Requirement** | Documents monorepo boundary + INV-* |
| **Use when** | Deep domain questions, handoff continuity |
| **Authority** | High for domain |

### 3.5 `TRADE_VISION_README.md` § AI / New-Chat Handoff (former `AI_HANDOFF_CONTEXT.md`)

| Field | Detail |
|-------|--------|
| **Purpose** | Compact new-chat handoff (**merged into README** 2026-07-24) |
| **Function** | Minimum context without whole repo; Appendix A holds v1.63–v1.82 historical notes |
| **Action** | Give new AI **this README section**; keep tip aligned with `IMPLEMENTATION_STATUS` |
| **Requirement** | Lists first-read order + do-not-touch + safety pointers; tip must match v1.94+ ship log |
| **Use when** | New chat / new engineer day-1 |
| **Authority** | High for onboarding; **IMPLEMENTATION_STATUS tip wins** if conflict |

### 3.6 ~~`docs/CONTEXT_INDEX.md`~~ → **merged into this file §0.6**

| Field | Detail |
|-------|--------|
| **Purpose** | Former standalone “Need X → read Y” router |
| **Status** | **Merged 2026-07-24** into **§0.6** of this file; do not recreate |
| **Action** | Update §0.6 rows when new key questions appear |
| **Authority** | Index only (this file) |

### 3.7 ~~`docs/CONTEXT_MAINTENANCE_RUNBOOK.md`~~ → **`TRADE_VISION_README.md` § AI Handoff (context maintenance)**

| Field | Detail |
|-------|--------|
| **Purpose** | Former standalone post-ship doc hygiene checklist |
| **Status** | **Merged 2026-07-24** into README **Fast continuation rule + context maintenance** |
| **Action** | After each ship, follow that README checklist; do not recreate the runbook file |
| **Use when** | Post-release hygiene / preventing stale handoffs |
| **Authority** | Process |

### 3.8 ~~`docs/FILE_OWNERSHIP_MAP.md`~~ → **merged into this file §7.4**

| Field | Detail |
|-------|--------|
| **Purpose** | Former standalone high-signal file → owner/purpose map |
| **Status** | **Merged 2026-07-24** into **§7.4** of this file; do not recreate |
| **Action** | Update §7.4 when major modules added |
| **Requirement** | Not every `.py` listed — high-signal only |
| **Use when** | “Which file owns indicator reliability?” → §7.4 |
| **Authority** | Map; incomplete for tiny modules |

### 3.9 `docs/API_ENDPOINT_INDEX.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Route families summary |
| **Function** | Avoid opening entire `main.py` first |
| **Action** | Find family → then open main.py slice |
| **Requirement** | Keep aligned with real routes |
| **Use when** | API work / integration |
| **Authority** | Index; code wins if conflict |

### 3.10 `docs/FRONTEND_PANEL_MAP.md`

| Field | Detail |
|-------|--------|
| **Purpose** | UI panels / workspaces map |
| **Function** | Locate UI without whole App.tsx |
| **Action** | Map panel → endpoint |
| **Requirement** | Panel safety notes where relevant |
| **Use when** | Frontend / Jarvis card work |
| **Authority** | Index |

### 3.11 `docs/TEST_ID_INDEX.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Named tests / IDs map |
| **Function** | Find regression coverage |
| **Action** | Name tests before implementing (project rule) |
| **Requirement** | Safety-related tests required for decision routes |
| **Use when** | Writing/reviewing tests |
| **Authority** | Index |

### 3.12 `docs/MILESTONE_EASY_EXPLANATION.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Human-friendly milestone summary |
| **Function** | Explain versions without full status log |
| **Action** | Read for storytelling / PM-level view |
| **Requirement** | None |
| **Use when** | Non-deep overview |
| **Authority** | Summary; detail in IMPLEMENTATION_STATUS |

### 3.13 `docs/graph.md` + `docs/graph/project_graph.json` (includes former README_GRAPH at §0)

| Field | Detail |
|-------|--------|
| **Purpose** | System structure graph (human + machine) |
| **Function** | Orientation of modules/authority |
| **Action** | Update graph when major version/integration ships |
| **Requirement** | Reflect actual structure, not pure aspiration |
| **Use when** | Architecture orientation, Knowledge UI |
| **Authority** | Structural map |

### 3.14 `docs/INDICATOR_INTELLIGENCE_CATALOG.md` (v1.96)

| Field | Detail |
|-------|--------|
| **Purpose** | Evidence-backed contract for every indicator available to Trade Vision |
| **Function** | One record per indicator: formula evidence, signal meaning, lag, repaint, family, safe use |
| **Action** | Regenerate via `scripts/build_indicator_intelligence_catalog.py`; never hand-edit JSON |
| **Requirement** | Machine truth lives in `data/indicator-intelligence/indicator_contracts.v1.json`; gates CAT-V196-001..009 |
| **Use when** | Indicator / voting / reliability / panel work; before trusting any indicator output |
| **Authority** | Catalog of record for indicator semantics; vendor copy is code authority |

### 3.15 `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Code-grounded easy-English map of Trade Vision's specialist brains and application skeleton |
| **Function** | Explains data→calculation→context/memory→strategy→failure/derivatives→risk→arbiter→Jarvis flow; records overlapping decision layers and preferred future authority model |
| **Action** | Use as the first architecture reference before future brain upgrades/patches; update only when major roles, authority or wiring change |
| **Requirement** | Keep specialist evidence separate from final authority; preserve fail-closed/PIT/proof/safety semantics |
| **Use when** | Future system evolution, refactor planning, adding an engine, consolidating duplicate decision layers, AFRE/ORB/Jarvis work |
| **Authority** | Architecture understanding/reference; code wins on runtime truth |

---

## 4. Spec / test / TV product root docs

### 4.1 `SPEC.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Requirements / product specification |
| **Function** | Contract-level “what should exist” |
| **Action** | Align features to SPEC; update when requirements change |
| **Requirement** | Research-first, safety-bound product |
| **Use when** | Spec conflicts, new capability design |
| **Authority** | Requirements (with FINAL_REQUIRED_FLOW for paper spine) |

### 4.2 `TEST_PLAN.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Test strategy |
| **Function** | How to verify builds |
| **Action** | Follow for acceptance; add cases for new spine |
| **Requirement** | Live trading must remain blocked in tests |
| **Use when** | Planning verification |
| **Authority** | Process |

### 4.3 Root `../API.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Stock App HTTP API reference |
| **Function** | Document stock/predict/backtest/sim endpoints |
| **Action** | Use with Swagger `:8014/docs` |
| **Requirement** | May lag server.py — verify against live `/docs` |
| **Use when** | Stock App API integration |
| **Authority** | Medium (code/Swagger higher) |

### 4.4 Root `../PWA_MOBILE_UPGRADE.md`

| Field | Detail |
|-------|--------|
| **Purpose** | PWA/mobile upgrade notes for Stock App |
| **Function** | Historical/feature notes for installable web app |
| **Action** | Read when touching service worker / manifest |
| **Use when** | PWA work |
| **Authority** | Feature notes |

### 4.5 Root `../llms.txt`

| Field | Detail |
|-------|--------|
| **Purpose** | Tiny LLM-oriented project blurb |
| **Function** | Quick agent summary |
| **Action** | Optional |
| **Authority** | Low / incomplete vs MASTER GUIDE |

---

## 5. Plans folder (`docs/plans/`) — order of meaning

Read plans in this **meaning order** (not file date):

```text
1  FINAL_REQUIRED_FLOW.md                         ← product spine (your requirement)
2  PROJECT_GOD_VIEW_FOR_AI.md                     ← full inventory for external AIs
3  FINAL_REQUIRED_FLOW.md Appendix A (AI Brief)                  ← short multi-AI build-plan pack
4  ORB_RESEARCH_ENGINE_PLAN.md                    ← ORB TF/bars/combo research lab
4b ORB_CONTEXT_NATIVE_PLAN_V2.md                  ← v2.00 ORB upgrade plan (gap+CPR+PDH/PDL+realism; PROPOSED)
4c ORB_STRATEGY_MEMORANDUM.md                     ← v2.00 rule-level trade spec (entry/stop/target + examples)
4d ORB_V2_JUDGE_FINDINGS.md                       ← adversarial verification of the v2 plan
4e ORB_V201_PRECODE_REVIEW_KIMI.md                ← verbatim archive: submission 1 (pre-code review)
4f ORB_V201_NSE_REVIEW_KIMI.md                    ← verbatim archive: submission 2 (NSE v2.01)
4g ORB_V201B_NSE_REVIEW_KIMI_PART2.md             ← verbatim archive: submission 3 (continuation + trace)
4h ORB_V201C_NSE_REVIEW_KIMI_PART3.md             ← verbatim archive: submission 4 (consolidated deliverable)
4i ORB_V201_VERIFIED_ANSWER.md                    ← verified answers: all four submissions, §1–§9
4j ORB_V2_BUILD_PLAN.md                          ← approved v2 build plan (staged 4→2→1, M1–M6 + verification protocol)
5  FINAL_REQUIRED_FLOW.md Appendix B (Think Engine)            ← question-driven engine order + Flow R/D
6  TRADE_VISION_MAX_CHART_REASONING_...           ← evidence engines (mostly shipped)
7  TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md     ← memory mega-architecture (partial)
8  OPENALGO_PAPER_TO_LIVE_REMAINING_BUILD_PLAN.md  ← execution after paper-review (mostly future)
```

**Count:** 17 plan/pack files under `docs/plans/` (2026-09-03 audit: +ORB_V201_PRECODE_REVIEW_KIMI retro-archive, +ORB_V201C_NSE_REVIEW_KIMI_PART3; 2026-09-02: +ORB_V201_NSE_REVIEW_KIMI, +ORB_V201B_NSE_REVIEW_KIMI_PART2, +ORB_V201_VERIFIED_ANSWER; 2026-08-31: +ORB_CONTEXT_NATIVE_PLAN_V2, +ORB_STRATEGY_MEMORANDUM, +ORB_V2_JUDGE_FINDINGS).

### 5.1 `FINAL_REQUIRED_FLOW.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Required final flow: organized guidance for paper trade |
| **Function** | Present / final / gaps / phases / acceptance |
| **Action** | Build Phase 0→1→2 first |
| **Requirement** | One boss arbiter; approve→sim fill; no live v1 |
| **Use when** | Always for product direction |
| **Authority** | Product requirement |

### 5.2 `TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Chart/regime/structure/risk/lifecycle/arbiter stack |
| **Function** | Design for v1.70–v1.75 (+ heritage → 80/81) |
| **Action** | Use as evidence-layer design; already largely implemented |
| **Requirement** | Evidence-only; no live |
| **Use when** | Touching reasoning engines |
| **Authority** | Design; status for ship = IMPLEMENTATION_STATUS |

### 5.3 `TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Full indicator memory, analogs, Kronos twin mega-spec |
| **Function** | Long-range architecture (huge) |
| **Action** | Implement only slices that plug into FINAL_REQUIRED_FLOW step 3 |
| **Requirement** | PIT, no Kronos override, family caps |
| **Use when** | Memory/analog/feature-store deep work |
| **Authority** | Vision; **not fully done** |

### 5.4 `OPENALGO_PAPER_TO_LIVE_REMAINING_BUILD_PLAN.md`

| Field | Detail |
|-------|--------|
| **Purpose** | Remaining after v1.47: paper fills → live gates |
| **Function** | Milestones 4.1–4.9 |
| **Action** | Only after FINAL_REQUIRED_FLOW Phase 2 (sim) is solid |
| **Requirement** | Paper before live; tiny pilot; bot last |
| **Use when** | OpenAlgo execution path |
| **Authority** | Roadmap; **mostly not implemented** |

### 5.5 `PROJECT_GOD_VIEW_FOR_AI.md`

| Field | Detail |
|-------|--------|
| **Purpose** | **Full god skeleton for zero-context external AIs** |
| **Function** | Monorepo map; Stock App classic/ML/HMM/research; all **71 si_*** + **23 pta_*** groups by purpose; self_indc disk list; ~143 behavior engines by role (PIT, v1.70–75, Jarvis, Kronos, OA); how to use efficiently; present vs missing; safety |
| **Action** | Attach when another AI must understand **what exists** (indicators + thinking engines) before planning |
| **Requirement** | Reuse engines; do not invent parallel indicator zoo; family-cap + lag-aware votes |
| **Use when** | Multi-AI (Gemini/Claude/Kimi/GLM/…) design sessions; onboarding architects |
| **Authority** | Inventory + roles ground truth for planning (not runtime code) |
| **Pairs with** | `APPLICATION_BRAIN_SKELETON_AND_WIRING.md` (how brains are intended to connect) + `FINAL_REQUIRED_FLOW.md Appendix A (AI Brief)` (what to build) + `FINAL_REQUIRED_FLOW.md` (requirement) |

### 5.6 `FINAL_REQUIRED_FLOW.md` **Appendix A** (AI Brief — merged)

| Field | Detail |
|-------|--------|
| **Purpose** | **Token-light multi-AI planning pack** for one-touch paper guidance |
| **Function** | Goal, spine architecture, PaperTradeGuidance contracts, gaps G1–G10, phases P0–P6, engine order, acceptance, anti-patterns |
| **Status** | **Merged 2026-07-24** into `FINAL_REQUIRED_FLOW.md` Appendix A; separate `PAPER_TRADE_SPINE_AI_BRIEF.md` deleted |
| **Action** | Edit Appendix A in FINAL_REQUIRED_FLOW; attach with god-view for zero-context AIs |
| **Requirement** | No live v1; human approve before sim fill; one final_band language |
| **Use when** | Asking external AIs for a **build plan** (not full code dump) |
| **Authority** | Planning brief under product spine |
| **Pairs with** | `PROJECT_GOD_VIEW_FOR_AI.md` when AI has no indicator/engine context |

### 5.7 `ORB_RESEARCH_ENGINE_PLAN.md`

| Field | Detail |
|-------|--------|
| **Purpose** | **ORB research lab requirement:** backtest which ORB strategy × timeframe × orb candle count/window × filter combo is best by **profit** and **repeated success** |
| **Function** | Spec for multi-layer pipeline (Discover→Prove→Playbook→Decide→Paper); `research/orb/*` + validation + guidance evidence; **§0.8 = ORB vs Kronos/Vision/other engines influence map** for AI reference |
| **Action** | Build as Stock App research track (parallel to paper spine); do not auto-live-trade winners; AIs should read **§0** + **§0.8** before placing ORB in TV/Kronos |
| **Requirement** | No lookahead on OR lock; session-correct open; OOS/consistency not only max profit; costs on; ORB does not boss Kronos/arbiter |
| **Use when** | Designing ORB discovery / “what TF and how many OR candles to run” / how ORB affects Vision/Kronos |
| **Authority** | Research product plan + placement/influence authority for ORB; **not fully implemented** as dedicated ORB lab |
| **Present today** | `research/` discovery + `opening_range_reversal` / hybrid (not full ORB combo sweeper; not wired into Kronos/TV) |
| **Pairs with** | `research/engine/*`, `shared/indicators/self_indc.py`, `static/research.html`, paper spine + GOD_VIEW |

### 5.8 `FINAL_REQUIRED_FLOW.md` **Appendix B** (Think Engine — merged)

| Field | Detail |
|-------|--------|
| **Purpose** | **Question-driven best flow** for all think engines before building |
| **Function** | Arranges engines by job/function/output/purpose/requirement; designs Flow R (research) vs Flow D (decide/paper) using why/what/when/how/what-if/who-wins; stress-tests wrong orders |
| **Status** | **Merged 2026-07-24** into `FINAL_REQUIRED_FLOW.md` Appendix B; separate `THINK_ENGINE_BEST_FLOW_REASONING.md` deleted |
| **Action** | Read Appendix B before wiring spine/ORB; use PART E checklist on every PR |
| **Requirement** | Two cadences; single arbiter; no discover-on-click; no auto paper |
| **Use when** | “How should engines be ordered?” / multi-AI architecture design |
| **Authority** | Flow design under product spine; coding lock remains ARCHITECTURE_DESIGN §0 |
| **Pairs with** | APPLICATION_BRAIN_SKELETON_AND_WIRING + FINAL_REQUIRED_FLOW body + ORB plan §0–0.8 + GOD_VIEW |

---

## 6. Runbooks & reports

### 6.1 Runbooks (`docs/runbooks/`)

| File | Purpose | Use when |
|------|---------|----------|
| `EXTERNAL_AI_CREDENTIALS_RUNBOOK.md` | Gemini/Grok vault setup (not broker) | AI credential issues |
| `deployment-backup-restore.md` | Deploy/backup/restore ops | Ops recovery |
| `openalgo-adapter-health.md` | Adapter health checks | OA adapter down |
| `openalgo-transport-backlog.md` | Transport backlog handling | Stuck outbox |
| `openalgo-transport-circuit.md` | Circuit breaker ops | Cascading failures |
| `openalgo-transport-dead-letter.md` | Dead-letter handling | Poison messages |
| `openalgo-transport-slo.md` | Transport SLOs | Reliability targets |

| Field (all runbooks) | Detail |
|----------------------|--------|
| **Function** | Operational procedures |
| **Action** | Follow steps; do not invent live trade enablement |
| **Requirement** | Keep TV non-routing |
| **Authority** | Ops |

### 6.2 Test reports (`docs/test-reports/`)

| File | Purpose |
|------|---------|
| `RELIANCE_*.md` | Research/validation writeups (MTF, 1m, Kronos twin) |

| Field | Detail |
|-------|--------|
| **Function** | Evidence notes for specific symbol research |
| **Action** | Read as experiment results, not product law |
| **Authority** | Research artifacts |

### 6.3 Root `../reports/`

| Path | Purpose |
|------|---------|
| `reports/2026-02-17/`, `2026-02-18/` | Phase design/impl notes (backtrader, HMM, websocket, portfolio…) |
| `reports/indicator_audit/` | Indicator readiness audits (e.g. INFY/AAPL) |

| Field | Detail |
|-------|--------|
| **Function** | Historical design/QA trail for Stock App phases |
| **Action** | Archaeology / proof; prefer FINAL_REQUIRED_FLOW + MASTER GUIDE for current direction |
| **Authority** | Historical |

---

## 7. Important folders (code & data) — use order

### 7.1 Trade Vision apps

| Folder | Purpose | Function | Action / use |
|--------|---------|----------|--------------|
| `apps/api/app/` | FastAPI app package | Routes, models, storage | Primary backend work |
| `apps/api/app/behavior/` | Decision/evidence engines | Jarvis, arbiter, indicators, OA, Kronos bridges | **Most TV brain code** |
| `apps/api/app/orb/` | ORB core/discovery/proof/adaptive controller | ORB research + causal adaptive decision support | Read with APPLICATION_BRAIN_SKELETON_AND_WIRING for authority/wiring |
| `apps/api/tests/` | Backend tests | Regression | Run before claiming ship |
| `apps/web/src/` | React UI | Workspaces/panels | Frontend |
| `apps/kronos-service/` | Isolated Kronos inference | Forecast service | Do not import heavy model into API process |
| `apps/openalgo-adapter/` | OA boundary **simulator** | HMAC adapter | Paper/review transport — not live broker fill product |
| `legacy/stock_app/` | Vendored reference | Migration reference | Do not use as production import path casually |
| `external/kronos/` | Upstream Kronos source | Model source | Isolated |
| `data/` (under TV) | Local DBs/json research data | Persistence artifacts | Don’t commit secrets |

### 7.2 Stock App root folders

| Folder | Purpose | Function | Action / use |
|--------|---------|----------|--------------|
| `server.py` | Monolith API + ML | Stock App backend | Chart/sim/backtest/research routes |
| `static/` | HTML/JS UI pages | Chart, backtest, research, portfolio, compare, realtime | Browser UI |
| `indicators/` + `self_indc/` | Indicator library | Chart overlays / strategies | Pattern work |
| `backtest/` | Backtrader strategies | Historical sim | Strategy runs |
| `validation/` | WF / CPCV | Anti-leakage validation | Rigorous backtests |
| `hmm/` | Regime model | Bull/Sideways/Bear | Regime features |
| `research/` | Strategy discovery engine | Jobs, ML, storage | `/research` product |
| `portfolio/` | Portfolio tools | Analyze/summary | `/portfolio` |
| `alerts/` + `scheduler.py` | Monitor + Discord | Regime/signal alerts | Ops alerts |
| `cache/` | Models / MTF cache | Speed | Don’t treat cache as authority |
| `config/` | WF/CPCV config | Parameters | Validation tuning |
| `shared/` | Shared indicator helpers | Reuse | Library |
| `tests/` | Root pytest | Stock App tests | CI local |
| `reports/` | Phase reports | History | Docs archaeology |

### 7.3 Runtime DBs / artifacts (easy to miss)

| Artifact | Purpose | Note |
|----------|---------|------|
| `sim_trading.db` (root) | Stock App paper sim | Real paper **book** for root product |
| `research.db` (root) | Research engine DB | Discovery jobs |
| TV SQLite / data stores | Behavior history, intents, intakes | Research/audit; not live broker ledger |
| `cache/models/*.pkl` | Cached ML/HMM | Stale risk if market regime shifts |

### 7.4 File ownership map (former FILE_OWNERSHIP_MAP — full tables)

> **Purpose:** help agents open the right files first.  
> **Last reviewed with merge:** 2026-09-08  
> **Rule:** high-signal only — not every tiny module.  
> **Legacy/external:** reference only unless migrated behind safety tests.

#### 7.4.1 Core docs

| File | Owner/Purpose |
|------|----------------|
| `docs/context.md` | domain invariants, policies, known unknowns (Fable context) |
| `docs/graph.md` | human system graph + data-flow Mermaid |
| `docs/graph/project_graph.json` | machine knowledge graph |
| **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** | **plain-English application skeleton, specialist-brain roles, authority hierarchy, ORB/AFRE/Jarvis wiring, desired final output, future evolution/patch rules** |
| `docs/INDICATOR_INTELLIGENCE_CATALOG.md` | v1.96 per-indicator contracts of record (formula evidence, lag, repaint, families); machine truth in `data/indicator-intelligence/` |
| `TRADE_VISION_README.md` § AI Handoff | compact new-chat handoff (merged; keep aligned with IMPLEMENTATION_STATUS tip) |
| **`docs/FILE_DOCUMENT_INDEX.md` (this file)** | full doc/folder index + **§0.6 Q→file router** + **§7.4 ownership** |
| `docs/IMPLEMENTATION_STATUS.md` | latest completed tip + full ship log |
| `docs/NEXT_BUILD_TARGET.md` | next build candidates |
| `docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md` | full indicator/9C future roadmap |
| `docs/plans/TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md` | v1.70-v1.79 chart/indicator reasoning expansion |
| `docs/plans/FINAL_REQUIRED_FLOW.md` | **product requirement spine** + App. A AI Brief + App. B Think Engine |
| `docs/plans/FINAL_REQUIRED_FLOW.md` App. A | token-light multi-AI pack (merged) |
| `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md` | full god skeleton for external AIs |
| `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` | ORB research lab: strategy × TF × orb bars/window |
| `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` | **v2.00 ORB upgrade plan (PROPOSED):** gap bias-lock + CPR wide/narrow + PDH/PDL family + execution realism; milestones M1-M6; §7 v2.1 addendum (policy split by path, playbook migration, staged grid) |
| `docs/plans/ORB_STRATEGY_MEMORANDUM.md` | **v2.1 rule-level trade spec:** rule IDs (GAP/TRAP/CPR/ZONE/EXIT/CTX), exclusive zones Z1-Z5, precedence ladder, entry/stop/target per combo + repaired worked examples 1A/1B/2/3/4 |
| `docs/plans/ORB_V2_JUDGE_FINDINGS.md` | three verification passes: claims tables, errors E1-E3, gaps G1-G5; §6 second pass; §7 third pass (v2.01 review) |
| `docs/plans/ORB_V201_PRECODE_REVIEW_KIMI.md` | **VERBATIM archive** of submission 1 (2026-09-01 pre-code review): B1–B8 blockers, S-A/S-B insights, S1–S10 decisions, P1–P3, V1–V4, replacement Example 3; retro-archived 09-03 |
| `docs/plans/ORB_V201_NSE_REVIEW_KIMI.md` | **VERBATIM archive** of the 2nd external review: NSE Tuesday-expiry regime, 18 ORB variants, ~40 failure scenarios, derivatives overlay, 25-row decision table, top-10 |
| `docs/plans/ORB_V201B_NSE_REVIEW_KIMI_PART2.md` | **VERBATIM archive** of the continuation submission: expiry-verification banner, Task 3 IV/expiry/basis modules, Task 4 decision table + flags; Part B = reasoning trace; both byte-exact (CRLF preserved) |
| `docs/plans/ORB_V201C_NSE_REVIEW_KIMI_PART3.md` | **VERBATIM archive** of the consolidated submission: 18 variants, ~35-row failure taxonomy, full derivatives overlay, 50-row decision table, ranked top 10; byte-exact |
| `docs/plans/ORB_V201_VERIFIED_ANSWER.md` | **verified answers** on all three v2.01 submissions: §1–6 (1 wrong / 13 missed / 11 already-right) + §7 continuation (4 corrections / 11 misses / 13 conflicts) + §8 consolidated (0 contradictions / 10 new rules / 6 triple-confirmations) + adoption maps |
| `docs/plans/FINAL_REQUIRED_FLOW.md` App. B | question-driven engine order; Flow R vs D (merged) |
| `docs/plans/TRADE_VISION_ARCHITECTURE_DESIGN.md` | multi-AI design; **§0 coding lock = OLD + 3 patches** |
| `SPEC.md` | requirements |
| `ARCHITECTURE.md` | architecture contracts + ADR index + version log |
| `TEST_PLAN.md` | test strategy |
| `../STOCK_APP_ARCHITECTURE.md` (repo root) | Stock App wiring + root-arch invariants + chart deep-dives |
| `../STOCK_APP_README.md` (repo root) | Stock App product entry / install |

#### 7.4.2 Backend

| File | Owner/Purpose |
|------|----------------|
| `apps/api/app/main.py` | FastAPI route surface / active engine imports and pipeline wiring |
| `apps/api/app/models.py` | Pydantic contracts |
| `apps/api/app/state.py` | capability manifest and graph path |
| `apps/api/app/storage.py` | persistence helpers |
| `apps/api/app/responses.py` | response/envelope helpers |
| `apps/api/app/behavior/candle_anatomy.py` | candle structure calculations |
| `apps/api/app/behavior/condition_classifier.py` | deterministic behavior/market condition classification |
| `apps/api/app/behavior/context_engines.py` | VWAP/ORB/CPR/PDH/PDL, HTF, gap, index/sector context |
| `apps/api/app/behavior/session_memory.py` | session/day-of-week/Stock-DNA behavior memory |
| `apps/api/app/behavior/hypothesis_engine.py` | continuation vs reversal vs fakeout hypothesis comparison |
| `apps/api/app/behavior/decision_engine.py` | universal-agreement behavior decision and safety gates |
| `apps/api/app/behavior/risk_engine.py` | risk sizing, daily loss, cooldown, portfolio heat |
| `apps/api/app/behavior/execution_event_oi_risk.py` | execution/liquidity/event/OI reality layer |
| `apps/api/app/behavior/final_confluence_arbiter.py` | priority-weighted conflict resolver / reduce-only authority |
| `apps/api/app/behavior/twin_arbiter.py` | Behavior vs Kronos comparison; conflict reduces action |
| `apps/api/app/behavior/jarvis_decision_room.py` | assembles chart/indicator/history/reviewer/safety evidence room |
| `apps/api/app/behavior/jarvis_decision_arbiter.py` | Jarvis hard gates and external-review conflict handling |
| `apps/api/app/behavior/jarvis_decision_fusion.py` | read-only fusion of TV/Gemini/Kronos/OpenAlgo/paper evidence |
| `apps/api/app/behavior/jarvis_master_panel.py` | all-evidence presentation/master panel; older paths preserved |
| `apps/api/app/behavior/jarvis_trading_decision_output.py` | trader-readable final plan/evidence/blocker output |
| `apps/api/app/orb/core.py` | ORB/ORR opening range and signal construction |
| `apps/api/app/orb/discovery.py` | historical ORB combination discovery |
| `apps/api/app/orb/proof.py` | train-only selection + OOS/holdout/walk-forward proof + playbook promotion |
| `apps/api/app/orb/adaptive/controller.py` | bounded causal AFRE scenario/contingency controller |
| `apps/api/app/orb/adaptive/runtime.py` | synchronized event reducer, quarantine, capability merge, paper gating |
| `apps/api/app/orb/adaptive/variants.py` | 18 original ORB variant research assessments |
| `apps/api/app/orb/adaptive/scenario_detection.py` | complete A-G failure scenario detector |
| `apps/api/app/orb/adaptive/derivatives.py` | deterministic Task-3 derivatives calculations/capabilities |
| `apps/api/app/orb/adaptive/risk_context.py` | structured external factual risk/event capabilities |
| `apps/api/app/behavior/indicator_registry.py` | indicator registry and metadata |
| `apps/api/app/behavior/indicator_lag_voting.py` | v1.80 lag-aware voting |
| `apps/api/app/behavior/indicator_reliability_memory.py` | v1.81 reliability rollups |
| `apps/api/app/behavior/indicator_signal_history_ingestion.py` | v1.84 pending ingest |
| `apps/api/app/behavior/paper_guidance_config.py` | v1.87 config-driven P0 thresholds |
| `apps/api/app/behavior/paper_guidance_spine.py` | v1.87 D1 safety gate + D2 strict snapshot/hash |
| `apps/api/app/behavior/shared_snapshot.py` | Kronos/Twin immutable snapshot; strict close-time sibling |
| `apps/api/tests/test_paper_guidance_spine.py` | v1.87 focused safety/determinism/MTF tests |
| `apps/api/app/behavior/indicator_signal_history_completion.py` | v1.85 complete-pending |
| `apps/api/app/behavior/trendforge_bridge.py` | v1.86 signed TrendForge intake |
| `apps/api/app/behavior/real_mtf_pullback.py` | v1.63 closed-candle MTF pullback/opposition classifier |
| `apps/api/app/behavior/release_control.py` | benchmark/release evidence and v1.66 scenario coverage families |
| `apps/api/app/behavior/operational_safety.py` | golden replay fixture contracts and deterministic verification |
| `apps/api/app/behavior/ai_credentials_vault.py` | Gemini/Grok credential slots (not broker) |
| `apps/api/app/behavior/*` | behavior/Jarvis/Kronos/OpenAlgo modules |
| `apps/api/tests/test_api.py` | backend regression suite |
| `apps/api/tests/test_trendforge_bridge.py` | v1.86 TrendForge tests |

#### 7.4.3 Frontend

| File | Owner/Purpose |
|------|----------------|
| `apps/web/src/App.tsx` | main workspace shell and remaining large routing logic |
| `apps/web/src/api/client.ts` | frontend API client |
| `apps/web/src/components/primitives.tsx` | shared UI primitives |
| `apps/web/src/components/aiCredentialsPanel.tsx` | credential vault UI |
| `apps/web/src/components/safetyPanels.tsx` | extracted safety display panels |
| `apps/web/src/components/workspaces/referenceWorkspaces.tsx` | reference workspace components |
| `apps/web/src/components/workspaces/systemWorkspace.tsx` | system workspace |
| `apps/web/src/components/workspaces/replayEvidencePanels.tsx` | replay evidence display panels |

#### 7.4.4 Legacy / isolated services

| File/Folder | Rule |
|-------------|------|
| `legacy/stock_app` | reference only unless explicitly migrated behind safety tests |
| `external/kronos` | isolated external model source |
| `apps/kronos-service` | isolated Kronos service; API must not import heavy model stack directly |

---

## 8. Important details often missed (add these to your mental model)

### 8.1 Product / flow

1. **Two products, one monorepo** — Stock App ≠ Trade Vision authority.  
2. **Many engines ≠ one spine** — organization gap is real; see FINAL_REQUIRED_FLOW and APPLICATION_BRAIN_SKELETON_AND_WIRING.  
3. **PAPER-CANDIDATE ≠ paper fill** — label/review only in TV.  
4. **Stock App paper requires human/API trade POST** — indicators do not auto-trade.  
5. **No one-click** symbol → all calc → paper → result (not built).  
6. **Dual decision language** — BUY/SELL/HOLD vs WAIT/WATCH/PAPER-CANDIDATE.  
7. **Best existing “boss” idea** — TV final confluence arbiter v1.75 — still not a full product spine UX.  
8. **OpenAlgo adapter is a simulator** — not completed paper→live product.  
9. **Live trading is blocked by design** in TV; enabling it is a separate safety program, not a small flag.  
10. **Port confusion** — Stock App often **8014** here; older docs may say 8000.
11. **Multiple decision-like modules are intentionally preserved historical layers** — do not assume every file named `decision`, `arbiter`, `fusion`, or `master` has equal authority; consult `APPLICATION_BRAIN_SKELETON_AND_WIRING.md` before adding another final-decision path.

### 8.2 Data / correctness

12. **yfinance** — fine for research, not exchange co-location quality.  
13. **Closed bars only** for decision features — incomplete HTF must not vote as closed.  
14. **Missing context** (breadth/OI) must be **unavailable**, not invented clean.  
15. **Proxy indicators** may still exist in matrices — not all “validated.”  
16. **Verified trade signal** is **narrow** (e.g. INFY 5m style gates) — not universal.  
17. **Cache is speed, not authority** — stale model risk.  
18. **Same-bar target+stop** → conservative stop-first / ambiguous rules (do not assume win).
19. **AFRE v4 strict large-gap rule is `gap > 1.5 x prior ATR`** — exactly 1.5x is not large; do not silently reintroduce the older 1.4x/1% floor.
20. **Dealer-signed GEX requires real dealer-position sign** — never infer dealer side from OI alone.
21. **UNOBSERVABLE is not SAFE** — missing external facts must remain unavailable/fail-closed.

### 8.3 Docs / process

22. **IMPLEMENTATION_STATUS** is huge — never “read all”; open one version.  
23. **Legacy plans** (chart / memory / OpenAlgo) are layers; **spine** is FINAL_REQUIRED_FLOW (includes AI Brief App. A + Think Engine App. B); **god inventory** is PROJECT_GOD_VIEW_FOR_AI; **brain/wiring reference** is APPLICATION_BRAIN_SKELETON_AND_WIRING.  
24. **MASTER GUIDE** lives *inside* ARCHITECTURE/TRADE_VISION_README bottoms; dedicated packs live under `docs/plans/` plus the new brain/wiring reference under `docs/`.  
25. **Version renames** happened (plan titles vs status titles for some v1.68/69).  
26. **Ship hygiene** — after code: status + version pointer + safety still true + optional graph; update brain/wiring reference only if authority/roles/contracts/wiring changed.  
27. **AI credentials ≠ broker credentials** — vault is Gemini/Grok only.  
28. **Kronos cannot override NO_TRADE** — research prior only.  
29. **TrendForge v1.86** — signed research intake only; does not unlock trading.  
30. **Root research engine** (`research/`) is separate from TV Behavior memory — don’t assume shared state.  
31. **Discord alerts** are optional ops — not the decision spine.  
32. **PWA offline** does not mean offline trading authority.  
33. **Tests may pass while product spine missing** — unit engines ≠ connected flow.  
34. **Next preferred build** — FINAL_REQUIRED_FLOW Phase 0+1 (one guidance endpoint/card), then Phase 2 approve→sim.

### 8.4 Security / ops (often forgotten)

35. No browser session harvesting / hidden login tokens for brokers.  
36. Kill switch must block order-path simulation too.  
37. HMAC secrets for OA/TrendForge are separate; loopback defaults matter.  
38. Rate limits / nonce / timestamp skew on adapter are security features, not noise.  
39. Logs must not store secrets, cookies, full order credentials.

---

## 9. Quick “which file for which action”

| Action you want | Open |
|-----------------|------|
| **Understand application brains / skeleton / authority / future wiring** | **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** |
| Understand required paper flow | `docs/plans/FINAL_REQUIRED_FLOW.md` |
| Full project god skeleton (indicators+engines) | `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md` |
| Short multi-AI one-touch plan pack | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` |
| ORB best TF / candle count / combo research | `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` |
| What to send external AIs | §0.5 External AI send pack |
| See all docs map | **this file** |
| See latest version + full completed log | `docs/IMPLEMENTATION_STATUS.md` (tip at top; one version section for history) |
| Pick next build | `docs/NEXT_BUILD_TARGET.md` |
| Safety check | `docs/SAFETY_INVARIANTS.md` |
| Screen → API | `ARCHITECTURE.md` § OPERATOR MAP |
| Stock App paper sim how | root `STOCK_APP_ARCHITECTURE.md` paper section |
| Find code owner | **this file §7.4** |
| Question → which file? | **this file §0.6** |
| Find API family | `docs/API_ENDPOINT_INDEX.md` |
| Find UI panel | `docs/FRONTEND_PANEL_MAP.md` |
| Chart engine design | `docs/plans/TRADE_VISION_MAX_CHART_REASONING_...` |
| Memory mega design | `docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md` |
| OA paper→live remaining | `docs/plans/OPENALGO_PAPER_TO_LIVE_...` |
| Full findings dump | `ARCHITECTURE.md` / `TRADE_VISION_README.md` § MASTER GUIDE |
| Stock App features/install | root `STOCK_APP_README.md` |
| Stock App API | root `API.md` + `:8014/docs` |

---

## 10. Update rules for this index

Update **this file** when:

```text
- new doc or plan is created
- read order changes
- FINAL_REQUIRED_FLOW phases complete
- major folder ownership changes (§7.4)
- new “Need X → read Y” question (§0.6)
- a “missed detail” becomes a new invariant
- APPLICATION_BRAIN_SKELETON_AND_WIRING is created/moved/renamed or its ownership/use changes
```

Also update `docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md` when a major engine is added/removed, authority moves, a canonical data path changes, ORB/AFRE/Jarvis wiring changes, or a presentation-only module gains decision authority.

Do **not** recreate `CONTEXT_INDEX.md` or `FILE_OWNERSHIP_MAP.md`.  
Do **not** duplicate full IMPLEMENTATION_STATUS here — only point to it.

---

## 11. Bottom line

```text
INDEX (this file)                    → library catalog + §0.6 Q→file + §7.4 ownership
APPLICATION_BRAIN_SKELETON_AND_WIRING → how the application brains behave/connect + who has authority + future patch rules
FINAL_REQUIRED_FLOW                  → what product must become (spine)
PROJECT_GOD_VIEW_FOR_AI              → full indicators + engines skeleton for external AIs
FINAL_REQUIRED_FLOW App. A           → short multi-AI one-touch plan pack (former PAPER_TRADE_SPINE_AI_BRIEF)
FINAL_REQUIRED_FLOW App. B           → think-engine order why/when (former THINK_ENGINE_BEST_FLOW)
ORB_RESEARCH_ENGINE_PLAN             → ORB strategy×TF×bars/window research lab
ORB_CONTEXT_NATIVE_PLAN_V2           → v2.00 ORB upgrade plan (gap+CPR+PDH/PDL+realism; PROPOSED)
ORB_STRATEGY_MEMORANDUM              → v2.00 rule-level trade spec (entry/stop/target + examples)
ORB_V2_JUDGE_FINDINGS                → adversarial verification of the v2 plan
MASTER GUIDE sections                → condensed findings in ARCHITECTURE/TRADE_VISION_README
IMPLEMENTATION_STATUS                → latest tip + full ship log
SAFETY_INVARIANTS                    → what must never break
CODE folders + §7.4                  → where to implement / who owns module
§12 AUDIT                            → full inventory + what was previously skipped

Missing product reality:
  organized single paper-guidance action not fully connected yet.
```

**Path:** `trade-vision-app/docs/FILE_DOCUMENT_INDEX.md`

---

## 12. FULL FILESYSTEM AUDIT (2026-07-22; index delta 2026-09-08)

### 12.1 Audit method

```text
Scanned monorepo for:
  - all *.md recursively (excluding node_modules, .venv, __pycache__, .git, catboost_info, legacy copies inside noise)
  - top-level and TV second-level product folders
  - root operational scripts, configs, static pages, DBs
Compared against prior FILE_DOCUMENT_INDEX content (§2–§7)
Result: first index was high-signal only — many docs/folders were summarized or omitted.
This section closes that gap with explicit inventory.
```

### 12.2 Coverage verdict

| Category | Prior index | After §12 | Notes |
|----------|-------------|-----------|-------|
| TV `docs/*.md` core handoff | Covered | Covered | Complete; +APPLICATION_BRAIN_SKELETON_AND_WIRING indexed 2026-09-08 |
| TV `docs/plans/*` (17) | Covered | Covered | Complete |
| TV `docs/runbooks/*` (7) | Named | Named | Complete |
| TV `docs/test-reports/*` (4) | Wildcard only | **Named fully** | Fixed |
| TV `docs/graph/*` | Covered | Covered | Complete |
| TV root SPEC/TEST/README/ARCH | Covered | Covered | Complete |
| Root README/ARCH/API/PWA/llms | Covered | Covered | Complete |
| Root `reports/**/*.md` (19) | Folder only | **Full file list** | Fixed |
| Kronos external READMEs | Missing | **Listed** | Fixed |
| Kronos-service README + model READMEs | Missing | **Listed** | Fixed |
| `data/secrets/README.md` | Missing | **Listed** | Fixed |
| `packages/`, `plugins/`, root `docs/` | Missing | **Listed** | Fixed |
| Root scripts / bats / requirements / LICENSE | Missing | **Listed** | Fixed |
| TV scripts / package.json / pytest.ini | Missing | **Listed** | Fixed |
| `static/*` pages | Partial | **Full list** | Fixed |
| `research/` subpackages | Folder only | **Subdirs named** | Fixed |
| Behavior module count (~143 py) | Not counted | **Counted** | Fixed |
| Root tests count (~53) | Not counted | **Counted** | Fixed |
| self_indc py count (~48) | “~40+” | **48** | Fixed |
| Noise (.tmp, .codex sessions, pytest cache) | Not declared | **Excluded with reason** | Fixed |
| Every individual `behavior/*.py` name | Not listed | **Not listed by name** (too large) — use §7.4 + glob | Intentional |
| IMPLEMENTATION_STATUS every version section | Not inlined | Point only | Intentional |

**Honest prior miss rate:** high-signal index covered ~40% of project markdown paths by name; ~60% were folder-level or omitted. §12 aims for **100% of product markdown paths named** (noise excluded).

---

### 12.3 Complete markdown inventory (product-relevant)

Paths relative to monorepo root unless marked `(TV)`.

#### A. Root product docs (5)

| Path | Purpose / use |
|------|----------------|
| `STOCK_APP_README.md` | Stock App features, install, MASTER GUIDE |
| `STOCK_APP_ARCHITECTURE.md` | Stock App wiring, operator map, monorepo MASTER GUIDE (**only** root arch file) |
| `API.md` | Stock App REST API reference |
| `PWA_MOBILE_UPGRADE.md` | PWA/mobile upgrade notes |
| `llms.txt` | Tiny LLM blurb (incomplete vs MASTER GUIDE) |

#### B. Trade Vision product root docs (4)

| Path | Purpose / use |
|------|----------------|
| `trade-vision-app/TRADE_VISION_README.md` | TV intro, handoff list, MASTER GUIDE |
| `trade-vision-app/ARCHITECTURE.md` | TV contracts, operator map, deep MASTER GUIDE |
| `trade-vision-app/SPEC.md` | Requirements/spec |
| `trade-vision-app/TEST_PLAN.md` | Test strategy |

#### C. Trade Vision `docs/` core (17 markdown + graph json)

| Path | In prior index? |
|------|-----------------|
| `docs/FILE_DOCUMENT_INDEX.md` | Yes (this file; **also holds** former CONTEXT_INDEX + FILE_OWNERSHIP_MAP) |
| **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** | **NEW 2026-09-08:** code-grounded plain-English application brain/skeleton/authority/wiring reference for future upgrades/patches |
| `docs/context.md` | Yes |
| `TRADE_VISION_README.md A AI / New-Chat Handoff` | Yes |
| `TRADE_VISION_README.md` A context maintenance (former CONTEXT_MAINTENANCE_RUNBOOK) | Yes |
| `docs/IMPLEMENTATION_STATUS.md` | Yes (latest tip + full log; former CURRENT_VERSION_POINTER merged) |
| `docs/NEXT_BUILD_TARGET.md` | Yes |
| `docs/SAFETY_INVARIANTS.md` | Yes |
| `docs/INDICATOR_INTELLIGENCE_CATALOG.md` | **NEW v1.96** (per-indicator contracts; generated by `scripts/build_indicator_intelligence_catalog.py`) |
| `docs/INDICATOR_GROUP_AND_USE_MAP.md` | **NEW v1.96** (19 trading-purpose groups, vote families) |
| `docs/generated/INDICATOR_CATALOG_TABLE.md` | **NEW v1.96** (human table; generated - do not hand-edit) |
| `docs/API_ENDPOINT_INDEX.md` | Yes |
| `docs/FRONTEND_PANEL_MAP.md` | Yes |
| `docs/TEST_ID_INDEX.md` | Yes |
| `docs/MILESTONE_EASY_EXPLANATION.md` | Yes |
| `docs/graph.md` | Yes |
| `docs/graph.md` §0 how-to (former README_GRAPH) | Yes (bundled into graph.md) |
| `docs/graph/project_graph.json` | Yes (not md) |

#### C.1 Fable campaign evidence (v1.87)

| Path | Purpose |
|------|---------|
| `docs/fable/SPEC.md` | approved v1.87 requirements and invariants |
| `docs/fable/CAMP_ARCHITECTURE.md` | P0 D1/D2 design boundary |
| `docs/fable/PLAN.md` | milestone steps and acceptance |
| `docs/fable/CAMPAIGN.md` | production campaign sequence and risks |
| `docs/fable/CONTEXT.md` | compact restart state |
| `docs/fable/DECISIONS.md` | ADR decisions, including spine-before-ORB |
| `docs/fable/TRACEABILITY.md` | requirement-to-code-to-test map |
| `docs/fable/REVIEW.md` | adversarial completion evidence |

#### D. Plans / AI packs (7) — all named

| Path | Status (product) |
|------|------------------|
| `docs/plans/FINAL_REQUIRED_FLOW.md` | Requirement spine |
| `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md` | **External-AI god skeleton** (indicators + engines + flows) |
| `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` | **Token-light multi-AI plan pack** (one-touch paper) |
| `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` | **ORB lab:** TF × orb bars/window × strategy combo research |
| `docs/plans/ORB_TIMING_RESEARCH_V197.md` | **v1.97 build spec:** per-stock ORB clock-window timing research |
| `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` | **NEW 2026-08-31, PROPOSED:** v2.00 ORB upgrade plan (gap+CPR+PDH/PDL+realism; M1-M6) |
| `docs/plans/ORB_STRATEGY_MEMORANDUM.md` | **NEW 2026-08-31:** v2.00 rule-level trade spec (entry/stop/target + worked examples) |
| `docs/plans/ORB_V2_JUDGE_FINDINGS.md` | **NEW 2026-08-31:** adversarial verification of the v2 plan (E1-E3, G1-G5) |
| `docs/plans/ORB_V201_PRECODE_REVIEW_KIMI.md` | **NEW 2026-09-03 (retro):** verbatim archive of submission 1 |
| `docs/plans/ORB_V201_NSE_REVIEW_KIMI.md` | **NEW 2026-09-02:** verbatim archive of the 2nd external review (0 diffs) |
| `docs/plans/ORB_V201B_NSE_REVIEW_KIMI_PART2.md` | **NEW 2026-09-02:** verbatim archive of the continuation submission (byte-exact, CRLF preserved) |
| `docs/plans/ORB_V201C_NSE_REVIEW_KIMI_PART3.md` | **NEW 2026-09-03:** verbatim archive of the consolidated submission (byte-exact) |
| `docs/plans/ORB_V201_VERIFIED_ANSWER.md` | **NEW 2026-09-02:** verified answers — submission 1: 1 wrong / 13 missed / 11 right; submission 2: 4 corrections / 11 misses / 13 conflicts; submission 3: 0 contradictions / 10 new rules / 6 triple-confirmations |
| `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix B — Think Engine)` | **Question-driven best think-engine flow** (job classes + Flow R/D) |
| `docs/plans/TRADE_VISION_ARCHITECTURE_DESIGN.md` | **AI-combined master design**; **§0 = OLD plan + only 3 patches** (D2 snapshot_hash, D6 low_evidence re-check, Week4 prove+promote / bridge v1.1) |
| `docs/plans/TRADE_VISION_MAX_CHART_REASONING_V1_70_TO_V1_79_PLAN.md` | Mostly implemented |
| `docs/plans/TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md` | Partial |
| `docs/plans/OPENALGO_PAPER_TO_LIVE_REMAINING_BUILD_PLAN.md` | Mostly future |

#### E. Runbooks (7) — all named

| Path | Purpose |
|------|---------|
| `docs/runbooks/EXTERNAL_AI_CREDENTIALS_RUNBOOK.md` | Gemini/Grok vault |
| `docs/runbooks/deployment-backup-restore.md` | Deploy/backup/restore |
| `docs/runbooks/openalgo-adapter-health.md` | Adapter health |
| `docs/runbooks/openalgo-transport-backlog.md` | Outbox backlog |
| `docs/runbooks/openalgo-transport-circuit.md` | Circuit breaker |
| `docs/runbooks/openalgo-transport-dead-letter.md` | Dead letter |
| `docs/runbooks/openalgo-transport-slo.md` | Transport SLOs |

#### F. TV test-reports (4) — **was wildcard; now full names**

| Path | Purpose |
|------|---------|
| `docs/test-reports/RELIANCE_MULTITIMEFRAME_RESEARCH.md` | MTF research writeup |
| `docs/test-reports/RELIANCE_NSE_1m_VALIDATION.md` | 1m validation notes |
| `docs/test-reports/RELIANCE_TWIN_KRONOS_BASE_RESEARCH.md` | Twin/Kronos base research |
| `docs/test-reports/RELIANCE_TWIN_REAL_RESEARCH.md` | Twin real research |

#### G. Root `reports/` (19 markdown) — **was folder-only; now full names**

**2026-02-17 (5):**

| Path | Topic |
|------|-------|
| `reports/2026-02-17/backtrader-phase2-frontend.md` | Backtrader FE phase |
| `reports/2026-02-17/backtrader-phase3-fix.md` | Backtrader phase3 fix |
| `reports/2026-02-17/ensemble-comparison-design.md` | Ensemble compare design |
| `reports/2026-02-17/phase2-p3-qa.md` | Phase2 P3 QA |
| `reports/2026-02-17/stock-app-readme.md` | Snapshot readme |

**2026-02-18 (7):**

| Path | Topic |
|------|-------|
| `reports/2026-02-18/phase2-backtrader.md` | Phase2 backtrader |
| `reports/2026-02-18/phase35-integration-test.md` | Phase 3.5 integration |
| `reports/2026-02-18/phase5-hmm-design.md` | HMM design |
| `reports/2026-02-18/phase7-step6-portfolio.md` | Portfolio step |
| `reports/2026-02-18/phase8b-websocket.md` | WebSocket phase |
| `reports/2026-02-18/phase9-github-prep.md` | GitHub prep |
| `reports/2026-02-18/phase9-impl.md` | Phase9 impl |

**indicator_audit (7):**

| Path | Topic |
|------|-------|
| `reports/indicator_audit/AAPL_5m_10_indicator_production_readiness.md` | AAPL readiness |
| `reports/indicator_audit/AAPL_5m_last5_indicators_formula_notes.md` | AAPL formula notes |
| `reports/indicator_audit/AAPL_5m_next5_indicators_formula_notes.md` | AAPL next5 formulas |
| `reports/indicator_audit/INFY_5m_10_indicator_production_readiness.md` | INFY readiness (linked to verified signal) |
| `reports/indicator_audit/INFY_5m_pattern_indicator_audit.md` | INFY pattern audit |
| `reports/indicator_audit/test_pack/INFY_5m_indicator_formula_notes.md` | Test pack formulas |
| `reports/indicator_audit/test_pack/PROMPT_external_ai_indicator_review.md` | External AI review prompt |

Also non-md under audit (CSVs/JSON/etc.) — operational artifacts, not docs.

#### H. Kronos / external / service docs — **previously missing**

| Path | Purpose / use |
|------|----------------|
| `trade-vision-app/apps/kronos-service/KRONOS_SERVICE_README.md` | How to run Kronos service |
| `trade-vision-app/apps/kronos-service/models/Kronos-mini/KRONOS_MINI_README.md` | Model card |
| `trade-vision-app/apps/kronos-service/models/Kronos-base/KRONOS_BASE_README.md` | Model card |
| `trade-vision-app/apps/kronos-service/models/Kronos-Tokenizer-2k/KRONOS_TOKENIZER_2K_README.md` | Tokenizer card |
| `trade-vision-app/apps/kronos-service/models/Kronos-Tokenizer-base/KRONOS_TOKENIZER_BASE_README.md` | Tokenizer card |
| `trade-vision-app/external/kronos/README.md` | Upstream Kronos project |
| `trade-vision-app/external/kronos/finetune_csv/README.md` | Finetune CSV flow |
| `trade-vision-app/external/kronos/finetune_csv/README_CN.md` | Finetune (Chinese) |
| `trade-vision-app/external/kronos/webui/README.md` | Kronos webui |

#### I. Secrets / data docs — **previously missing**

| Path | Purpose / use |
|------|----------------|
| `trade-vision-app/data/secrets/README.md` | How secrets are stored (AI vault paths; not broker) |

#### J. Explicit noise / non-product markdown (exclude from “must read”)

| Path pattern | Why excluded |
|--------------|--------------|
| `.tmp/master_*.md` | Scratch used to expand MASTER GUIDE |
| `.codex/**/*.md` | Local agent session dumps |
| `.pytest_cache/README.md`, `.test_cache/**` | Tooling caches |
| `legacy/**` large trees | Reference copy — not primary docs map |
| `node_modules/**` | Dependencies |
| `catboost_info/**` | Training noise |

---

### 12.4 Complete folder inventory (product)

#### Root monorepo folders

| Folder | Purpose | Prior? | Action |
|--------|---------|--------|--------|
| `alerts/` | Regime/signal alerts, Discord | Yes | Ops signals |
| `backtest/` | Backtrader engine/strategies | Yes | Historical sim |
| `cache/` | Model/MTF/yfinance cache | Yes | Speed only |
| `config/` | WF/CPCV configs | Yes | Validation params |
| `docs/` (root) | **Empty/placeholder** | **Missed** | Prefer TV `docs/` |
| `hmm/` | MarketHMM | Yes | Regime |
| `indicators/` | Chart + brains + `self_indc/` (~48 py) | Yes | Indicators |
| `plugins/` | Local plugin experiments (e.g. gemini-codex-router) | **Missed** | Not product spine |
| `portfolio/` | Portfolio analyze | Yes | `/portfolio` |
| `reports/` | Phase + indicator_audit history | Partial | Archaeology |
| `research/` | Discovery engine package | Partial | See 12.5 |
| `scripts/` | Root helpers (e.g. preview serve) | **Missed** | Dev helpers |
| `shared/` | Shared indicator helpers | Yes | Library |
| `static/` | HTML/JS UI pages | Partial | See 12.6 |
| `tests/` | ~53 `test_*.py` | Yes | Stock App tests |
| `validation/` | Purged WF, CPCV, permutation… | Yes | Anti-leakage |
| `trade-vision-app/` | TV product | Yes | Decision product |
| `__pycache__/` | Bytecode | Noise | Ignore |

#### Trade Vision folders

| Folder | Purpose | Prior? |
|--------|---------|--------|
| `apps/api/` | FastAPI + `app/behavior/` (~143 py modules) | Yes |
| `apps/api/app/orb/` | ORB research/proof + adaptive AFRE stack | **Indexed 2026-09-08** |
| `apps/api/tests/` | Backend tests | Yes |
| `apps/web/` | React/Vite UI | Yes |
| `apps/kronos-service/` | Kronos inference service | Yes |
| `apps/openalgo-adapter/` | OA simulator adapter | Yes |
| `packages/` | Shared packages (monorepo JS/TS helpers) | **Missed** |
| `scripts/` | dev-api/web, research stack, verify, twin research | **Missed** |
| `docs/` | All TV handoff docs | Yes |
| `data/` | Local DB/json/secrets (large) | Partial |
| `external/kronos/` | Upstream Kronos | Partial |
| `legacy/` | Vendored stock-app copy | Yes (rule only) |
| `node_modules/` | FE deps | Noise |

---

### 12.5 `research/` subpackages (Stock App) — **was single line**

| Subfolder | Purpose |
|-----------|---------|
| `research/advanced/` | Monte Carlo, regime, sensitivity, walk-forward helpers |
| `research/data/` | MTF loaders, validators, corporate actions, lag audit |
| `research/engine/` | Agent, backtester, combinator, runner, scorer, risk matrix |
| `research/filters/` | Regime filters |
| `research/jobs/` | Job state |
| `research/ml/` | ML gate/models for research |
| `research/selection/` | Correlation selection |
| `research/signals/` | Signal generators |
| `research/storage/` | DB models for research.db |
| `research/validation/` | Research-side validation |
| `research/api.py` | Wired into root `server.py` as research router |

---

### 12.6 `static/` pages (Stock App UI) — **full list**

| File | Purpose |
|------|---------|
| `static/index.html` | Main chart / sim / indicators |
| `static/index_test.html` | Chart test harness |
| `static/research.html` | Strategy discovery UI |
| `static/backtest.html` | Backtest UI |
| `static/portfolio.html` | Portfolio UI |
| `static/compare.html` | Compare UI |
| `static/realtime.html` | WebSocket realtime dashboard |
| `static/manifest.json` | PWA manifest |
| `static/service-worker.js` | Offline cache SW |
| `static/icon-192.png`, `icon-512.png` | PWA icons |

---

### 12.7 Root operational files (scripts/config) — **previously missing**

| File | Purpose / action |
|------|------------------|
| `server.py` | Stock App FastAPI monolith — main process |
| `scheduler.py` | MonitorScheduler (regime alerts) |
| `walk_forward.py` | WF helper at root |
| `requirements.txt` | Python deps for Stock App |
| `LICENSE` | MIT license |
| `start_server.bat` / `start-server.bat` | Start server :8014 |
| `restart.bat` / `restart_gpu_server.bat` | Restart helpers |
| `check_server.py` | Health probe helper |
| `generate_icons.py` | PWA icon generation |
| `print_folds.py` | Debug WF folds |
| `_check_vbt.py` | VectorBT check |
| `test_*.py` (root) | Ad-hoc e2e/sim/walk-forward tests outside `tests/` |
| `sim_trading.db` | Paper sim ledger |
| `research.db` | Research engine DB |
| `server*.log` / `*.err.log` | Runtime logs (do not treat as docs) |
| `.gitignore` | Ignore rules |

#### TV operational files

| File / path | Purpose |
|-------------|---------|
| `trade-vision-app/package.json` | Workspace npm scripts |
| `trade-vision-app/pytest.ini` | Pytest config |
| `trade-vision-app/apps/api/requirements.txt` | API deps |
| `trade-vision-app/apps/web/package.json` | Web app deps |
| `trade-vision-app/scripts/dev-api.ps1` | Start API |
| `trade-vision-app/scripts/dev-web.ps1` | Start web |
| `trade-vision-app/scripts/start-research-stack.ps1` | Start research stack |
| `trade-vision-app/scripts/stop-research-stack.ps1` | Stop stack |
| `trade-vision-app/scripts/verify-local-research-stack.ps1` | Verify stack |
| `trade-vision-app/scripts/verify_research_stack.py` | Verify stack (py) |
| `trade-vision-app/scripts/validate_historical_ohlcv.py` | OHLCV validation |
| `trade-vision-app/scripts/run_reliance_twin_research.py` | Twin research runner |
| `trade-vision-app/scripts/build_multitimeframe_research_report.py` | MTF report builder |
| `trade-vision-app/scripts/serve_preview.py` / `serve_tradevision_preview.js` | Preview servers |

---

### 12.8 Scale counts (for honesty)

| Item | Count (approx, audit day) |
|------|---------------------------|
| Product-relevant `.md` files (noise excluded) | ~70+ |
| TV `docs/` markdown files | **17 core** + plans + runbooks + test-reports (updated 2026-09-08 for brain/wiring reference) |
| Root `reports/**/*.md` | **19** |
| `behavior/*.py` modules | **~143** |
| `indicators/self_indc/*.py` | **~48** |
| Root `tests/test_*.py` | **~53** |
| TV API tests | primary `test_api.py` + focused modules |

**Not indexed by individual filename:** every behavior module, every self_indc file, every pytest — use:

```text
docs/FILE_DOCUMENT_INDEX.md §7.4  (high-signal modules)
docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md  (brain/authority/wiring map)
apps/api/app/behavior/*.py  (glob)
apps/api/app/orb/*.py + apps/api/app/orb/adaptive/*.py
indicators/self_indc/*.py   (glob)
tests/ + apps/api/tests/    (glob)
docs/IMPLEMENTATION_STATUS.md (version → files when shipped)
```

---

### 12.9 What was wrong / incomplete in the first index

| Miss type | Examples |
|-----------|----------|
| Folder summarization | `reports/` without 19 filenames |
| Wildcard only | `RELIANCE_*.md` without 4 real names |
| Entire doc trees omitted | Kronos external READMEs, kronos-service README, data/secrets README |
| Ops surface omitted | bat/ps1 scripts, package.json, requirements, LICENSE |
| Empty root `docs/` not noted | Confusion risk vs TV docs |
| `plugins/`, `packages/`, `scripts/` omitted | Secondary but real |
| `research/` substructure omitted | Engine/data/ml/signals/… |
| `static/` incomplete | Only “pages” not listed |
| Counts vague | “~40+ indicators” vs 48; no behavior count |
| No explicit noise policy | .tmp / .codex / caches looked “missing” when correctly ignored |

---

### 12.10 Still intentionally NOT inlined (and why)

| Item | Why not listed name-by-name |
|------|-----------------------------|
| All 143 `behavior/*.py` | Index would be unreadable; ownership map + status ship notes + APPLICATION_BRAIN_SKELETON_AND_WIRING for roles |
| All adaptive ORB functions | Use §7.4 high-signal owners + APPLICATION_BRAIN_SKELETON_AND_WIRING + exact code |
| All 48 self_indc modules | Same; indicator registry is runtime authority in TV |
| All test function IDs | `TEST_ID_INDEX.md` + pytest collection |
| All API routes | `API_ENDPOINT_INDEX.md` + OpenAPI `/docs` |
| All IMPLEMENTATION_STATUS versions | File is 300KB+; open by version |
| `data/**` thousands of json | Runtime research data, not documentation |
| `node_modules/**` | Dependencies |

If you need a **generated** full `behavior` filename dump later, produce it by script into an appendix — do not hand-maintain 143 rows here unless necessary.

---

### 12.11 Audit checklist (re-run anytime)

```text
[ ] All TV docs/*.md appear in §12.3 C
[ ] APPLICATION_BRAIN_SKELETON_AND_WIRING is present and indexed when engine/wiring authority reference is needed
[ ] All docs/plans/* appear in §12.3 D
[ ] All runbooks appear in §12.3 E
[ ] All test-reports appear in §12.3 F
[ ] All reports/**/*.md appear in §12.3 G
[ ] Kronos/service/external READMEs appear in §12.3 H
[ ] Root product md appear in §12.3 A
[ ] TV product root md appear in §12.3 B
[ ] Product folders appear in §12.4
[ ] Noise exclusions declared in §12.3 J
[ ] FINAL_REQUIRED_FLOW still top requirement in §0
[ ] MASTER GUIDE pointers still valid in ARCHITECTURE/TRADE_VISION_README
[ ] If a major brain/arbiter/data path changed, APPLICATION_BRAIN_SKELETON_AND_WIRING was refreshed
```

Re-run command sketch:

```powershell
Get-ChildItem -Recurse -Filter *.md |
  Where-Object { $_.FullName -notmatch 'node_modules|\.venv|__pycache__|\.git|catboost|legacy|node_modules' }
```

---

### 12.12 Link back

| Need after audit | Open |
|------------------|------|
| **Application brain / authority / wiring** | **`docs/APPLICATION_BRAIN_SKELETON_AND_WIRING.md`** |
| Product spine | `docs/plans/FINAL_REQUIRED_FLOW.md` |
| God-view for external AIs | `docs/plans/PROJECT_GOD_VIEW_FOR_AI.md` |
| Multi-AI short plan pack | `docs/plans/FINAL_REQUIRED_FLOW.md (Appendix A — AI Brief)` |
| External AI send order | §0.5 |
| Read order | §0 of this file |
| Per-doc purpose tables | §2–§6 |
| Full inventory | **§12 this audit** |
| Code ownership | `docs/FILE_DOCUMENT_INDEX.md` §7.4 |
| What shipped | `docs/IMPLEMENTATION_STATUS.md` |

**Audit conclusion:** First index was useful but incomplete. §12 names essentially all product documentation paths and product folders; code modules remain intentionally summarized by folder/count + ownership map. The 2026-09-08 update adds the application-brain/skeleton/wiring reference so future architecture work has a durable, code-grounded mental model before modifying the system.
