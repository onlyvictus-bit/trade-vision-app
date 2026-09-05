# Trade Vision / Monorepo — Build Audit

> **Purpose:** Track whether the project was **built as planned**, with test cases tied to authority docs.  
> **Audit date:** 2026-07-24  
> **Auditor method:** Plan (FINAL / NEXT / plans) vs Claims (IMPLEMENTATION_STATUS) vs Proof (code/tests/API client) vs Docs (ARCH / graph / maps) vs Safety.  
> **Tip claimed:** v1.94 (ORB Paper Lifecycle Feedback) · Full backend 715 passed (cited in status).  
> **Do not treat this file as product requirement** — requirement remains `plans/FINAL_REQUIRED_FLOW.md`.

---

## 0. How to read results

| Result | Meaning |
|--------|---------|
| **PASS** | Planned + claimed + proved in code (and docs OK) |
| **PARTIAL** | Built enough to use, but incomplete vs full plan acceptance |
| **MISS** | Planned / required, not found in code |
| **WRONG** | Built differently than plan/contract (behavior or values) |
| **DOC_DRIFT** | Code exists (or file renamed) but graph/ARCH/status/map still wrong or stale |
| **SAFE** | Safety invariant holds |
| **N/A** | Not required for current tip / out of scope |

**Score rule for a version claim:**  
`CLAIMED` in IMPLEMENTATION_STATUS → must have module/route/tests or mark **PARTIAL/MISS**.

---

## 1. Authority files used for this audit

| # | File | Role in audit |
|---|------|----------------|
| A1 | `docs/plans/FINAL_REQUIRED_FLOW.md` | Product acceptance (spine) |
| A2 | `docs/NEXT_BUILD_TARGET.md` | What is “done” tip + what is next |
| A3 | `docs/IMPLEMENTATION_STATUS.md` | Version claims (tip + log) |
| A4 | `ARCHITECTURE.md` | Contracts, operator map, production boundary |
| A5 | `docs/SAFETY_INVARIANTS.md` | Hard safety law |
| A6 | `docs/graph.md` + `docs/graph/project_graph.json` | Structural map |
| A7 | `docs/FILE_DOCUMENT_INDEX.md` | Doc/code navigation map |
| A8 | `TRADE_VISION_README.md` | Entry + handoff claims |
| A9 | `docs/API_ENDPOINT_INDEX.md` / `FRONTEND_PANEL_MAP.md` | Surface maps |
| A10 | `SPEC.md` / `TEST_PLAN.md` | Requirements & test strategy |
| A11 | Code: `apps/api`, `apps/web`, root `server.py` | Proof |

---

## 2. Audit test cases (by source file)

### 2.1 From `FINAL_REQUIRED_FLOW.md` (product spine)

| ID | Test case | Expected | Evidence method | Result | Finding |
|----|-----------|----------|-----------------|--------|---------|
| F-01 | One paper-guidance run API exists | Route present | `main.py` / client `paperGuidanceRun` | **PASS** | `POST /api/v1/paper-guidance/run` + client.ts |
| F-02 | PaperGuidance spine module exists | Module on disk | path check | **PASS** | `paper_guidance_spine.py`, `paper_guidance_config.py` |
| F-03 | D6 arbiter exists as sole final band boss (design) | Module + role | code + ARCH | **PASS** | `final_confluence_arbiter.py`; ORB maps to arbiter decisions |
| F-04 | ORB proposes setup, not final authority | ORB guidance uses arbiter band | `orb_guidance.py` | **PASS** | Maps PAPER-CANDIDATE → `ENTER_PAPER`; arbiter remains judge |
| F-05 | Human-approved simulated paper record | Record API + ledger | routes + module | **PASS** | `record-simulated`, `simulated_paper_ledger.py` |
| F-06 | Lifecycle observe / outcomes / reliability | Endpoints + modules | code | **PASS** | `orb_paper_lifecycle.py`, `orb_paper_feedback.py`, observe routes |
| F-07 | No live broker from TV spine | Flags blocked | SAFETY + code flags | **SAFE/PASS** | Status + graph + invariants: live blocked |
| F-08 | TV does not auto-write Stock App `sim_trading.db` | No sim_trading wiring | search `apps/api` | **PASS** (by design) | No `sim_trading` hits under TV API; Stock App sim separate |
| F-09 | One primary UI “Run paper guidance” + one final vocabulary | Primary UX complete | web App.tsx / panels | **PARTIAL** | **API client** has full paper-guidance family; **App.tsx** still heavy multi-panel soup — not a single clean primary card-only path |
| F-10 | One `PaperTradeGuidance` product object every run | Typed guidance object | models + spine | **PARTIAL** | Guidance objects exist; dual language still coexists (`PAPER-CANDIDATE` + `ENTER_PAPER`) |
| F-11 | ENTER_PAPER offers approve paper trade | Approve only when eligible | ledger + gates | **PARTIAL** | Record path exists; browser tip often **WATCH / NO_PLAYBOOK** so approve disabled (correct fail-closed, but product “ready playbook” scarce) |
| F-12 | Approve → paper record + result | TV local ledger (v1.93+) or optional Stock App bridge | design + code | **PARTIAL** (docs fixed 2026-07-24) | TV local ledger shipped; Stock App `sim_trading` bridge still optional/not wired (by design) |
| F-13 | Low evidence cannot high-confidence ENTER_PAPER | Caps / NO_PLAYBOOK | status UI + gates | **PASS** | Reliability 0/30 / NO_PLAYBOOK keeps WATCH; lag voting blocks promote |
| F-14 | Documented engine order matches code | Order documented + implemented | FINAL + spine/ORB | **PARTIAL** | Campaign D1–D7 implemented in pieces; single linear “one ordered list in one function” still product-organized around ORB+arbiter, not full FINAL Phase-1 table as sole path |
| F-15 | ORB research lab `research/orb/*` | Package exists | filesystem | **MISS** | `research/orb/` **not present**; discovery lives under `apps/api/app/orb/` offline path instead |
| F-16 | FINAL acceptance checklist checkboxes updated | Reflect reality | FINAL §8 | **PASS** (fixed 2026-07-24) | Honest `[x]`/`[~]`/`[ ]` + Phase 2 three-paper meanings |
| F-17 | One-touch symbol→guidance→approve→result complete | Full acceptance | END-TO-END | **PARTIAL** | Spine APIs + local paper exist; product acceptance not fully closed (playbooks/evidence/30 outcomes) |

### 2.2 From `NEXT_BUILD_TARGET.md` + `IMPLEMENTATION_STATUS.md`

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| S-01 | Tip version = v1.94 | Tip matches | **PASS** | IMPLEMENTATION_STATUS tip |
| S-02 | v1.94 purpose bullets match modules | lifecycle + atomic store | **PASS** | `orb_paper_lifecycle`, `atomic_json_store`, feedback modules present |
| S-03 | Cited tests exist as claim | 715 backend cited | **PASS** (claim) | Not re-run in this audit session; treat as **claimed-pass** until re-pytest |
| S-04 | No approved next version | NEXT says none | **PASS** | v1.95 proposed only |
| S-05 | v1.95 not implemented as “done” | No false tip | **PASS** | Tip remains v1.94 |
| S-06 | Frontend refresh / fast-lane issue noted | Operational gap tracked | **PARTIAL** | Described in NEXT; not fixed (expected until approved milestone) |

### 2.3 From `ARCHITECTURE.md` production boundary

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| R-01 | Production boundary documents D1→D7 paper path | Section present | **PASS** | Current Production Boundary v1.94 |
| R-02 | Three paper meanings documented | A/B/C kinds | **PASS** | TV label / local ledger / Stock App sim |
| R-03 | Monorepo Stock App map present | A-SA / G-SA | **PASS** | Absorbed Stock App operator + sim maps |
| R-04 | Stock App :8014 + sim routes exist | server.py | **PASS** | `/api/sim/accounts` present; `sim_trading.db` present |

### 2.4 From `SAFETY_INVARIANTS.md`

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| Z-01 | No live broker orders | blocked | **SAFE/PASS** | Graph + docs + design |
| Z-02 | No broker credential creation by TV | blocked | **SAFE/PASS** | Vault is AI-only (Gemini/Grok) |
| Z-03 | External AI cannot override risk | display-only | **SAFE/PASS** | Documented + review paths |
| Z-04 | Kronos research only | non-authoritative | **SAFE/PASS** | Isolated service + arbiter reduce-only |
| Z-05 | No future-bar leakage in decision features | closed candles | **PASS** (design+tests claimed) | D2 closed-candle snapshot; re-verify with focused tests if needed |
| Z-06 | Forbidden outputs LIVE BUY/SELL not product finals | not primary | **PASS** | TV bands WAIT/WATCH/PAPER-CANDIDATE/ENTER_PAPER |

### 2.5 From `graph.md` / `project_graph.json`

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| G-01 | JSON tip v1.94 | matches STATUS | **PASS** | `latest_completed_version: v1.94` |
| G-02 | live_trading_blocked true in summary | true | **PASS** | summary flags OK |
| G-03 | ORB paper lifecycle nodes present | v193/v194 nodes | **PASS** | orb-paper-ledger-v193, lifecycle-v194 |
| G-04 | Paper guidance spine node present | yes | **PASS** | paper-guidance-spine-v187 |
| G-05 | Graph nodes match **current** doc set | no deleted-doc nodes | **PASS** (fixed 2026-07-24) | Ghosts removed from `project_graph.json` |
| G-06 | Graph includes FILE_DOCUMENT_INDEX | node for main map | **PASS** (fixed 2026-07-24) | Nodes: `file-document-index`, `final-required-flow`, `build-audit` |
| G-07 | graph.md §0 how-to present | merged README_GRAPH | **PASS** | §0 exists |

### 2.6 From `FILE_DOCUMENT_INDEX.md` / README / maps

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| M-01 | No live links to deleted docs | 0 live paths | **PASS** (as of last full scan) | Former/merged wording only |
| M-02 | Handoff points to TRADE_VISION_README | yes | **PASS** | AI Handoff section |
| M-03 | Maintenance checklist in README | yes | **PASS** | Fast continuation + context maintenance |
| M-04 | API_ENDPOINT_INDEX lists paper-guidance family | yes | **PARTIAL** | Index may lag; **code/client are proof** — re-sync index if family missing |
| M-05 | FRONTEND_PANEL_MAP lists ORB/paper guidance UI | panel map accurate | **PARTIAL** | Verify panel map vs App; client APIs exist, panel map may lag |

### 2.7 From plans still separate

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| P-01 | ORB lab `research/orb/*` per ORB plan | folder + sweeper | **MISS** | Not built under root `research/orb/`; API `apps/api/app/orb/*` covers product ORB campaign instead |
| P-02 | OpenAlgo paper→live remaining plan | mostly future | **N/A / MISS by design** | Live path correctly not product-default |
| P-03 | Full indicator memory mega-plan DoD | full DoD | **PARTIAL** | v1.80–85 pieces shipped; mega-plan not fully done |
| P-04 | Max chart reasoning v1.70–75 | engines present | **PASS** | Modules present for 70–75 stack |
| P-05 | ARCHITECTURE_DESIGN §0 implement lock | D-order + 3 patches | **PARTIAL** | Implemented in campaign form; not every “ideal” think-flow alternate |

### 2.8 Stock App (root) quick cases

| ID | Test case | Expected | Result | Finding |
|----|-----------|----------|--------|---------|
| SA-01 | server.py runs chart API surface | exists | **PASS** | Monolith present |
| SA-02 | sim paper book API | `/api/sim/*` | **PASS** | accounts/trade routes |
| SA-03 | TV auto-fill Stock App sim | must **not** without design | **PASS** | Not wired (correct for current safety) |

---

## 3. Summary scorecard

| Area | PASS | PARTIAL | MISS | DOC_DRIFT | SAFE |
|------|-----:|--------:|-----:|----------:|-----:|
| FINAL spine | 7 | 6 | 2 | 1 | 1 |
| Status / Next | 5 | 1 | 0 | 0 | 0 |
| Architecture | 4 | 0 | 0 | 0 | 0 |
| Safety | 0 | 0 | 0 | 0 | 6 |
| Graph / maps | 4 | 2 | 0 | 2 | 0 |
| Other plans | 1 | 2 | 1 | 0 | 0 |
| Stock App | 3 | 0 | 0 | 0 | 0 |

**Overall:** Campaign **v1.88–v1.94 is substantially built** (modules/routes/client).  
**Product acceptance** from FINAL checklist is **not fully closed** (checkboxes still empty; playbook/evidence/UI unity gaps).  
**Docs/graph lag** on deleted/merged files.

---

## 4. Priority findings (action list)

### P0 — Fix doc/graph truth (cheap, high confusion)

| # | Issue | Fix | Status (2026-07-24) |
|---|--------|-----|---------------------|
| D1 | Graph still nodes deleted docs (handoff, context-index, version-pointer, maintenance runbook) | Refresh `project_graph.json` + `graph.md` | **FIXED** — ghosts removed |
| D2 | Graph missing FILE_DOCUMENT_INDEX node | Add node + edges from knowledge/readme | **FIXED** — + `final-required-flow`, `build-audit` |
| D3 | FINAL §8 acceptance still all `[ ]` | Update to `[x]` / `[~]` with evidence | **FIXED** — honest checklist |
| D4 | FINAL Phase-2 text still “sim_trading.db first” as only paper book | Clarify TV local ledger vs Stock App sim | **FIXED** — Phase 2 three meanings |

### P1 — Product gaps vs plan

| # | Issue | Fix |
|---|--------|-----|
| B1 | `research/orb/*` lab path missing | Either implement under root research **or** update ORB plan + FINAL to say product ORB lives in `apps/api/app/orb/*` |
| B2 | Primary UI still multi-panel soup | Dedicated Jarvis ORB / paper-guidance primary card (reduce competing finals) |
| B3 | Dual decision language | Normalize product language (`ENTER_PAPER` vs `PAPER-CANDIDATE`) in primary UI + docs |
| B4 | 30 completed outcomes / promoted playbooks scarce | Offline proof campaign (NEXT v1.95 direction) — not claimed done |

### P2 — Optional / later

| # | Issue | Fix |
|---|--------|-----|
| C1 | OpenAlgo live | Stay blocked until separate plan |
| C2 | Full indicator memory mega-plan | Slice only if needed for spine |
| C3 | Re-run full pytest to reconfirm 715 | Fresh evidence for audit S-03 |

---

## 5. Built but not fully reflected in docs/graph (DOC_DRIFT detail)

| Built (code) | Missing / wrong in docs |
|--------------|-------------------------|
| Paper-guidance client API family | May be incomplete in API_ENDPOINT_INDEX / FRONTEND_PANEL_MAP |
| Merged docs (handoff, indexes, maintenance) | **Fixed 2026-07-24** — graph ghosts removed |
| FILE_DOCUMENT_INDEX as master map | **Fixed 2026-07-24** — first-class graph node |
| TV local paper ledger | **Fixed 2026-07-24** — FINAL §8 + Phase 2 three meanings |
| ORB offline under `apps/api/app/orb` | FINAL/ORB plan still emphasize root `research/orb/*` lab (still open) |

---

## 6. Re-audit commands (repeatable)

```text
# Modules
dir trade-vision-app\apps\api\app\behavior\paper*.py
dir trade-vision-app\apps\api\app\orb

# Routes / client
findstr /i "paper-guidance" trade-vision-app\apps\api\app\main.py
findstr /i "paperGuidance" trade-vision-app\apps\web\src\api\client.ts

# Graph tip
findstr latest_completed_version trade-vision-app\docs\graph\project_graph.json

# Status tip
findstr latest_completed_version trade-vision-app\docs\IMPLEMENTATION_STATUS.md

# Tests (authoritative re-proof)
cd trade-vision-app
python -m pytest apps/api/tests -q
```

---

## 7. Audit log

| Date | Action |
|------|--------|
| 2026-07-24 | Initial scratch audit; BUILD_AUDIT.md created; cases filled from code/docs snapshot |
| 2026-07-24 | Multi-brain §9: Codex best prompt + Grok A–H re-proof + Antigravity (Claude quota → Gemini Pro) second brain; consensus table |
| 2026-07-24 | **DOCS FIRST fix (no Antigravity):** graph ghosts removed; FILE_DOCUMENT_INDEX + FINAL + BUILD_AUDIT nodes; FINAL §8 honesty + Phase 2 three paper meanings |

---

## 8. Bottom line

```text
BUILT (strong): v1.88–v1.94 ORB/paper spine backend + client APIs + safety blocks.
PARTIAL: one primary UX language/card; playbook evidence density.
MISS: root research/orb lab path as written in older plan text.
DOC_DRIFT (fixed 2026-07-24): graph ghosts + FILE_DOCUMENT_INDEX node + FINAL §8 honesty.
SAFE: live trading remains blocked.

Next: dual-band UI decision · ORB plan path decision · primary card · optional pytest re-run.
```

**File path:** `trade-vision-app/docs/BUILD_AUDIT.md`

---

## 9. Multi-brain audit append (2026-07-24)

> Protocol: **Codex first** (best prompt + method) → Grok executes → append → **Antigravity/Claude** same research → append.  
> Session: Codex CLI `0.145.0` model `gpt-5.6-sol` session `019f94a2-1d64-7643-91ec-485197b42c52`.

### 9.1 Codex SUPER BRAIN — BEST_PROMPT (verbatim)

```text
You are a read-only senior monorepo auditor. Audit:

D:\Projects\trading-platforms\stock-app

Objective: verify requirement/plan vs implementation vs documentation for Trade Vision + Stock App at the claimed v1.94 “ORB Paper Lifecycle Feedback And Atomic Store Hardening” tip. Do not implement, edit, install, migrate, delete, commit, or call any broker/external AI.

Read authority sources in this exact order:

1. trade-vision-app/docs/plans/FINAL_REQUIRED_FLOW.md — product requirement authority
2. trade-vision-app/docs/IMPLEMENTATION_STATUS.md — read “Latest completed tip” first, then only v1.88–v1.94 sections
3. trade-vision-app/docs/NEXT_BUILD_TARGET.md
4. trade-vision-app/ARCHITECTURE.md — current production boundary and v1.94 sections
5. trade-vision-app/docs/SAFETY_INVARIANTS.md
6. trade-vision-app/docs/FILE_DOCUMENT_INDEX.md
7. trade-vision-app/docs/graph.md and docs/graph/project_graph.json
8. trade-vision-app/docs/BUILD_AUDIT.md — prior audit evidence, never unquestioned authority

Evidence rule: every conclusion must cite:
`relative/path:line | symbol/heading/key | “short exact quote”`.
A filename alone, test count, generated bundle, comment, or documentation claim is insufficient proof of runtime wiring. Trace contracts → producers → API routes → clients/UI → persistence → tests. When evidence conflicts, requirement authority outranks implementation claims; code/runtime outranks descriptive status claims about what exists.

Score every finding with exactly one:
- PASS | PARTIAL | MISS | WRONG | DOC_DRIFT | SAFE

Audit these slices first:

A. Paper-guidance spine: D1–D7, immutable snapshot, ORB proposal, D6 sole final-band authority, Jarvis ticket, explicit human approval, local lifecycle feedback.
B. ORB v1.89–v1.94 lifecycle: discover → prove/promote → guide → approve simulated record → observe outcome → completed-only reliability → atomic storage/monitoring.
C. Vocabulary: ENTER_PAPER versus PAPER-CANDIDATE; distinguish internal mapping from competing primary product outputs.
D. Planned research/orb/* versus implemented apps/api/app/orb/*: determine missing product, renamed location, or stale plan—do not assume equivalence.
E. Compare graph.md/project_graph.json nodes against FILE_DOCUMENT_INDEX and filesystem.
F. FINAL_REQUIRED_FLOW acceptance checklist honesty.
G. Stock App isolation: server.py /api/sim/* / sim_trading.db separate from TV local ledger.
H. Live broker safety: blocked credentials, routing, OpenAlgo live, auto-approval.

Required output: executive verdict; slice matrix A–H; top five mismatches; safety proof; next-fix order labeled DOCS FIRST | CODE FIRST | DECISION REQUIRED; BUILD_AUDIT append candidate; evidence gaps.
```

### 9.2 Codex METHOD + HYPOTHESES (condensed)

**Method (9 steps):** authority chain → tip claims v1.88–94 → requirement-to-symbol matrix → trace model→API→UI→store → dual-product search (ORB/bands/sim/OpenAlgo) → filesystem vs graph/index → re-score FINAL checklist → rank mismatches with docs/code order → no edits/brokers.

**Codex hypotheses (pre-execution):**

1. Backend lifecycle real; one-touch UX still PARTIAL.
2. ENTER_PAPER ↔ PAPER-CANDIDATE is internal mapping but user-facing drift.
3. `research/orb/*` absent; `apps/api/app/orb/*` is campaign ORB not full lab.
4. FINAL still implies Stock App `sim_trading` fill; v1.93+ uses isolated TV ledger.
5. Live blocked in docs/flags; must prove route reachability not just booleans.

**Anti-patterns Codex flagged:** counting files/tests as done; recursive trust of BUILD_AUDIT; merging both paper ledgers; treating ORB as final boss; labeling every gap DOC_DRIFT.

### 9.3 Grok execution of Codex prompt — slice matrix A–H (fresh evidence 2026-07-24)

| Slice | Score | Evidence (path \| symbol \| quote/fact) | Gap / impact |
|-------|-------|------------------------------------------|--------------|
| **A** Paper-guidance spine | **PASS** (API) / **PARTIAL** (product UX) | `apps/api/app/main.py:5688` `paper_guidance_run` → `POST /api/v1/paper-guidance/run`; modules `paper_guidance_spine.py`, `final_confluence_arbiter.py`, `simulated_paper_ledger.py` | API spine wired; primary one-card UI still multi-panel |
| **B** ORB v1.94 lifecycle | **PASS** (modules+routes) | Routes: `record-simulated`, `paper-records/observe`, `paper-outcomes`, `orb-reliability/{playbook_id}`, `storage-monitor` in `main.py:5728–5853`; modules `orb_paper_lifecycle.py`, `orb_paper_feedback.py`, `atomic_json_store.py` | Tip claim matches code shape; 715 pytest **not re-run** this session (claimed-pass) |
| **C** Dual vocabulary | **PARTIAL** / **DOC_DRIFT** | `orb_guidance.py:159-160` maps arbiter `PAPER-CANDIDATE` → product band `ENTER_PAPER`; models still expose both `PaperGuidanceBand` (`ENTER_PAPER`) and arbiter `PAPER-CANDIDATE` | Two product languages coexist; operator confusion risk |
| **D** research/orb vs app/orb | **MISS** (plan path) / **PASS** (product ORB package) | `research/orb` **False** on disk; `apps/api/app/orb` has `core.py`, `discovery.py`, `proof.py`; FINAL §9b still says `research/orb/*` lab | Plan text stale vs campaign implementation location |
| **E** Graph vs FILE_DOCUMENT_INDEX | **DOC_DRIFT** | `project_graph.json` nodes still: `ai-handoff-context`, `context-index`, `current-version-pointer`, `context-maintenance-runbook`; files deleted (Test-Path False); `FILE_DOCUMENT_INDEX.md` exists (True) but **no** graph node id | Agents following graph hit ghosts |
| **F** FINAL checklist honesty | **DOC_DRIFT** | `FINAL_REQUIRED_FLOW.md:494-505` all eleven items still `[ ]` unchecked despite partial/PASS builds | Overstates “undone”; under-credits v1.88–94 |
| **G** Stock App isolation | **PASS** / **SAFE** design | No `sim_trading` hits under TV `apps/api`; root `server.py:6511+` has `/api/sim/*`; `sim_trading.db` at monorepo root True; ARCHITECTURE three paper meanings | FINAL line “Approve creates sim fill” still ambiguous vs TV local ledger |
| **H** Live broker blocked | **SAFE** | `state.py:30-36` `SYSTEM_MODE` `allows_live_orders=False`, `allows_broker_credentials=False`; `main.py` capability payloads `live_trading_blocked: True`; SAFETY_INVARIANTS + graph summary flag true | Boolean + mode wiring present; no live place-order path found in this pass |

**Executive verdict (Codex method):** Campaign **v1.88–v1.94 is substantially built** at API/module level. Product **acceptance** (FINAL §8) and **docs/graph truth** lag. Confidence: **high** on modules/routes/safety flags; **medium** on full UI one-touch and pytest 715 without re-run.

### 9.4 Top 5 mismatches (product risk rank)

| Rank | Issue | Score | Fix label |
|-----:|-------|-------|-----------|
| 1 | FINAL §8 all `[ ]` while spine routes exist | DOC_DRIFT | **DOCS FIRST** — honest `[x]`/`[~]` with evidence pointers |
| 2 | Dual ENTER_PAPER / PAPER-CANDIDATE as primary language | PARTIAL | **DECISION REQUIRED** then **CODE FIRST** (UI + primary contract) or doc-normalize mapping |
| 3 | Graph ghost nodes for deleted docs; missing FILE_DOCUMENT_INDEX | DOC_DRIFT | **DOCS FIRST** — refresh `project_graph.json` + graph.md |
| 4 | FINAL “Approve creates sim fill” vs TV local ledger not Stock App | DOC_DRIFT / PARTIAL | **DOCS FIRST** clarify three paper meanings; optional later bridge = new plan |
| 5 | `research/orb/*` plan vs `apps/api/app/orb/*` product | MISS/DOC_DRIFT | **DECISION REQUIRED** — implement lab **or** rewrite FINAL/ORB plan placement |

### 9.5 Next-fix order (Codex labels)

1. **DOCS FIRST** — Graph refresh (remove ghosts; add FILE_DOCUMENT_INDEX + TRADE_VISION_README edges).  
2. **DOCS FIRST** — FINAL §8 checklist honesty + Phase-2 sim wording.  
3. **DECISION REQUIRED** — Primary band vocabulary (keep mapping but single UI label).  
4. **DECISION REQUIRED** — ORB lab path ownership (`research/orb` vs API package).  
5. **CODE FIRST** (only after decision) — Primary Jarvis paper-guidance card / reduce competing finals.  
6. **CODE FIRST** (optional) — Re-run `python -m pytest apps/api/tests -q` to refresh S-03 evidence.

### 9.6 Codex success criteria check

| Criterion | Met? |
|-----------|------|
| A–H scored with path/symbol evidence | **Yes** |
| Top 5 ranked | **Yes** |
| FINAL checklist independently noted | **Yes** (all still `[ ]`) |
| Graph/index drift enumerated | **Yes** |
| Ledgers separated | **Yes** |
| Live block traced to SYSTEM_MODE + flags | **Yes** |
| Fix order docs/code labeled | **Yes** |

### 9.7 Antigravity SUPER BRAIN (Claude + Gemini path)

#### 9.7.1 Claude Sonnet attempt

| Attempt | Model | Result |
|---------|-------|--------|
| 1 | default (print) | Partial start only — explored workspace then exited empty (no structured matrix) |
| 2 | `claude-sonnet-4-6` | **BLOCKED** — `Individual quota reached. Resets in ~167h` |
| 3 | `gemini-3.1-pro-high` via **same Antigravity CLI** | **SUCCESS** — full BEST_PROMPT + matrix + TOP_5 + append body |

> User intent: Antigravity → Claude. Claude quota forced Antigravity **Gemini Pro High** as the second brain for this session. Re-run Claude when quota resets:  
> `agy --dangerously-skip-permissions --model claude-sonnet-4-6 --add-dir D:\Projects\trading-platforms\stock-app --mode plan --print-timeout 12m -p "<audit prompt>"`

#### 9.7.2 Antigravity BEST_PROMPT (Gemini 3.1 Pro High)

```text
Evaluate the repository status for Stock App & Trade Vision v1.94 ORB Paper Lifecycle under D:\Projects\trading-platforms\stock-app. Perform a strict, read-only verification across code, schemas, API endpoints, graphs, and documentation.

Categorize every audited slice into exactly one score: PASS, PARTIAL, MISS, WRONG, DOC_DRIFT, or SAFE. Every finding MUST include verifiable empirical evidence formatted as [relative_path:line_number] + symbol_name + "exact quote or code snippet".

Audit Focus:
1. API & Spine Routing: paper-guidance routes in trade-vision-app/apps/api/app/main.py
2. ORB Paper Lifecycle & Storage: orb_paper_lifecycle.py, orb_paper_feedback.py, atomic_json_store
3. Band Vocabulary: PAPER-CANDIDATE → ENTER_PAPER in orb_guidance.py
4. Directory Structure: research/orb absent vs apps/api/app/orb present
5. Graph Synchronization: project_graph.json vs FILE_DOCUMENT_INDEX.md
6. Plan Checklists: FINAL_REQUIRED_FLOW.md §8
7. Isolation: sim_trading absent under apps/api vs server.py /api/sim
8. Live Trading Block: SYSTEM_MODE.allows_live_orders=False + live_trading_blocked
```

#### 9.7.3 Antigravity slice matrix (fresh tool pass)

| Slice | Score | Evidence (path:line / symbol) | Finding |
|-------|-------|-------------------------------|---------|
| **A** Paper guidance routes | **PASS** | `main.py:5688` `paper_guidance_run`; also 5714 tickets, 5728 record-simulated, 5775 observe, 5825 reliability | All paper-guidance family routes present |
| **B** ORB lifecycle + atomic store | **PASS** | `orb_paper_lifecycle.py:30` `evaluate_simulated_paper_lifecycle`; `orb_paper_feedback.py:38` `build_orb_paper_reliability` | Lifecycle + reliability + atomic store path verified |
| **C** Band mapping | **PARTIAL** | `orb_guidance.py:158` maps arbiter `PAPER-CANDIDATE` → `ENTER_PAPER` | Dual vocab still in models/schemas |
| **D** ORB placement | **PASS*** | `research/orb` not found; `apps/api/app/orb/core.py` present | *Score differs from Codex/Grok “MISS on plan path” — Antigravity scores product location PASS; plan text still DOC_DRIFT |
| **E** Graph vs FS | **DOC_DRIFT** | `project_graph.json:61-63` ghost nodes; `FILE_DOCUMENT_INDEX.md` exists without graph node | Stale graph after doc merge |
| **F** FINAL §8 checklist | **DOC_DRIFT** | `FINAL_REQUIRED_FLOW.md:493-505` all `[ ]` | Checklist honesty lag |
| **G** sim isolation | **PASS** | No `sim_trading` under TV `apps/api`; `server.py:6511` `/api/sim/accounts` | Ledgers separated |
| **H** Live block | **SAFE** | `state.py:34` `allows_live_orders=False`; live_trading_blocked guards | Fail-closed |

#### 9.7.4 Antigravity TOP_5 mismatches

1. Graph ghost nodes (`ai-handoff-context`, `context-index`, `current-version-pointer`) after merge into FILE_DOCUMENT_INDEX.  
2. FINAL §8 still all unchecked despite v1.87–v1.94 implementation.  
3. Dual band terminology (`ENTER_PAPER` / `PAPER-CANDIDATE`) across guidance + models.  
4. Path-reference ambiguity (`apps/api/...` vs monorepo `trade-vision-app/apps/api/...`).  
5. Missing `FILE_DOCUMENT_INDEX` node in `project_graph.json`.

#### 9.7.5 Antigravity next-fix order

1. **DOCS FIRST** — Refresh `project_graph.json` + `graph.md` (remove ghosts; add FILE_DOCUMENT_INDEX).  
2. **DOCS FIRST** — Honest FINAL §8 `[x]` / `[~]` with evidence.  
3. **DECISION → CODE** — Normalize primary vocabulary ENTER_PAPER vs PAPER-CANDIDATE.  
4. **DOCS FIRST** — Standardize monorepo-relative paths in docs.

#### 9.7.6 Antigravity CLAUDE_FINDINGS_APPEND body (paste-ready summary)

```text
[AUDIT VERIFICATION SUMMARY - v1.94 ORB PAPER LIFECYCLE]
Date: 2026-07-24 · Brain: Antigravity (Claude quota → gemini-3.1-pro-high)
Monorepo Root: D:\Projects\trading-platforms\stock-app

1. Spine & Endpoints: VERIFIED — paper-guidance routes main.py:5688-5850
2. ORB Lifecycle & Persistence: VERIFIED — lifecycle + reliability + atomic_json_store
3. Architecture Placement: VERIFIED product path apps/api/app/orb; research/orb absent
4. Safety: SAFE — allows_live_orders=False; live_trading_blocked
5. Isolation: VERIFIED — sim_trading not in TV API; Stock App /api/sim only
6. Doc/Graph: DOC_DRIFT — ghost graph nodes; FINAL §8 all [ ]; dual band language
```

### 9.8 Multi-brain consensus (Codex + Grok + Antigravity)

| Topic | Codex hyp. | Grok evidence | Antigravity | Consensus |
|-------|------------|---------------|-------------|-----------|
| Backend spine v1.88–94 | Real | PASS routes/modules | PASS | **Built** |
| Primary one-touch UX | PARTIAL | PARTIAL | (not deep UI) | **PARTIAL** |
| Dual band language | Drift | PARTIAL | PARTIAL | **Fix needed** |
| research/orb | Missing lab | MISS plan path | PASS product path | **DECISION: lab vs rewrite plan** |
| Graph ghosts | Likely | DOC_DRIFT proven | DOC_DRIFT | **DOCS FIRST** |
| FINAL checklist | Stale | All `[ ]` | DOC_DRIFT | **DOCS FIRST** |
| sim isolation | Separate | PASS | PASS | **OK by design** |
| Live blocked | Prove flags | SAFE SYSTEM_MODE | SAFE | **SAFE** |

**Agreed next work (no code this session):**  
1) Graph refresh · 2) FINAL §8 honesty · 3) Band language decision · 4) ORB plan path decision · 5) optional pytest re-run.

### 9.9 Audit log addendum

| Date | Action |
|------|--------|
| 2026-07-24 | Codex best-prompt design (session 019f94a2…) + Grok re-audit slices A–H; multi-brain §9.1–9.6 appended |
| 2026-07-24 | Antigravity: Claude Sonnet quota blocked; Gemini 3.1 Pro High completed second-brain audit; §9.7–9.8 consensus appended |
| 2026-07-24 | **§10 Frontend line-check** (read-only): client + App.tsx ORB/paper path; no Antigravity; no UI edits |

---

## 10. Frontend code audit (line-check — findings only)

> **Scope:** `apps/web/src/**` paper/ORB + shell design vs claimed maps.  
> **Mode:** read-only — **no redesign** until you name files to edit.  
> **Date:** 2026-07-24  

### 10.1 Files that exist (frontend package)

| File | Role | In map? | OK? |
|------|------|---------|-----|
| `apps/web/src/main.tsx` | React mount | yes | **PASS** — thin, correct |
| `apps/web/src/App.tsx` (~5.8k lines) | Almost all UI + Jarvis + ORB panel | yes | **PARTIAL** — works but mega-file soup |
| `apps/web/src/api/client.ts` | HTTP client | yes | **PASS** routes; **PARTIAL** typing |
| `apps/web/src/api/schemas.ts` | Zod for many APIs | yes | **MISS** for paper-guidance types (no PaperTrade schemas) |
| `apps/web/src/components/primitives.tsx` | Panel/Metric/Status | yes | **PASS** |
| `apps/web/src/components/aiCredentialsPanel.tsx` | AI vault | yes | **PASS** (side path) |
| `apps/web/src/components/safetyPanels.tsx` | Safety display | yes | **PASS** (side path) |
| `apps/web/src/components/workspaces/*` | system / replay / reference | yes | **PASS** present |
| `apps/web/src/styles.css` | styles | yes | **PASS** (ORB classes used) |

**Not a separate file:** “ORB Paper Guidance panel” lives **inside** `App.tsx` (`JarvisDecisionRoom`), not its own component file.

### 10.2 API client vs backend (paper-guidance family)

| Client method | Route | Used in App.tsx? | Design score |
|---------------|-------|------------------|--------------|
| `paperGuidanceRun` | `POST .../run` | **Yes** (`runOrbGuidance`) | **PASS** wired |
| `paperGuidanceRecordSimulated` | `POST .../record-simulated` | **Yes** | **PASS** + confirm + fixed approval phrase |
| `paperGuidanceObserveSimulated` | `POST .../paper-records/observe` | **Yes** | **PASS** lifecycle |
| `paperGuidancePaperRecords` | `GET .../paper-records` | **Yes** (load + refresh) | **PASS** |
| `paperGuidancePaperOutcomes` | `GET .../paper-outcomes` | **Yes** | **PASS** |
| `paperGuidanceOrbReliability` | `GET .../orb-reliability/{id}` | **Yes** | **PASS** |
| `paperGuidanceStorageMonitor` | `GET .../storage-monitor` | **Yes** | **PASS** |
| `paperGuidanceOrbTickets` | `GET .../orb-tickets` | **No (0 uses)** | **PARTIAL** — client exists, **UI never calls** |

**Typing:** all paper methods use `z.object({}).passthrough()` — loose; score **PARTIAL**.

### 10.3 ORB Paper Guidance UI (App.tsx — coded path)

| Piece | Where | Exists? | Correct design? |
|-------|-------|---------|-----------------|
| State hooks (TF, direction, busy, records, lifecycle, reliability, store) | ~1728–1742 | Yes | **PASS** for v1.92–1.94 |
| Load records/outcomes/monitor | ~1867–1889 | Yes | **PASS** |
| Load reliability when playbook_id | ~1890–1913 | Yes | **PASS** |
| `buildOrbGuidancePayload` closed-candle MTF | ~1558–1611 | Yes | **PASS** |
| `buildOrbLifecycleSeries` post-decision bars | ~1622–1646 | Yes | **PASS** |
| `runOrbGuidance` → import + run | ~1915–1937 | Yes | **PARTIAL** — **hardcoded RELIANCE** import |
| `recordOrbPaperTrade` confirm + phrase | ~1939–1967 | Yes | **PASS** human gate |
| `evaluateOrbPaperLifecycle` observe | ~1968–2021 | Yes | **PARTIAL** — gate quirk below |
| Panel “ORB Paper Guidance” | ~2135–2359 | Yes | **PASS** real panel |
| Buttons Analyze / Record / Evaluate | ~2183–2219 | Yes | **PASS** + test ids |
| Band, entry/stop/target, blockers, ledger | ~2223–2358 | Yes | **PASS** for ORB ticket |
| Safety “LOCAL SIMULATION ONLY” | ~2220 | Yes | **SAFE** |
| Primary button label | “Analyze RELIANCE ORB” | Yes | **PARTIAL** — not generic “Run paper guidance” |

### 10.4 Design problems (product spine vs UI)

| ID | Result | What is wrong | Evidence |
|----|--------|---------------|----------|
| FE-01 | **PARTIAL** | **Two competing “finals” on same Trade tab** | Brief/Cockpit use `finalAction` (~1841, 2108, 2361). ORB uses `final_band` (~2140, 2226). |
| FE-02 | **PARTIAL** | Not one primary product action | Many trade-tab panels still show Final Action; ORB is one of many. |
| FE-03 | **PARTIAL** | Dual band language in product surface | ORB band vs older Jarvis `final_action` strings. |
| FE-04 | **PARTIAL** | Evaluate gated on `can_record_paper` | ~2205–2207 should mainly need **existing paper_record**, not can_record. |
| FE-05 | **PARTIAL** | Symbol hardcode | `behaviorImportLocalReliancePreview` (~1921) vs room `rawChartSymbol`. |
| FE-06 | **MISS (UI)** | `paperGuidanceOrbTickets` unused | Client only. |
| FE-07 | **MISS (types)** | No Zod PaperTradeGuidance | schemas.ts silent on paper family. |
| FE-08 | **PASS** | Panel order matches map | Brief then ORB (~2108 → ~2135). |
| FE-09 | **PARTIAL** | Monolith App.tsx | ~154 Panel titles; ORB not extracted. |
| FE-10 | **SAFE** | No live order UI on ORB path | Confirm copy + disabled gates. |

### 10.5 Easy English summary

```text
WHAT EXISTS AND WORKS
- Paper guidance API calls are in client.ts; almost all are used in App.tsx.
- Jarvis has a real "ORB Paper Guidance" panel:
  Analyze → show band/entry/stop → Record simulated paper → Evaluate replay.
- Safety text: local only, no broker.
- Blockers, ledger, reliability, store health show after run.

WHAT IS NOT CLEAN PRODUCT DESIGN YET
- Many "final" answers on the same screen (old Jarvis + ORB).
- Analyze path is RELIANCE lab, not a general one-touch product.
- Paper response types are not strongly typed in schemas.ts.
- Client method paperGuidanceOrbTickets is unused.
- Evaluate button is gated a bit oddly (can_record_paper).
- Huge App.tsx (~5800 lines, ~150 panels).

VERDICT
Frontend paper/ORB path is REAL and mostly wired to the backend.
It is NOT yet the clean "one primary paper guidance card" product.
No UI files edited — findings only. You pick what to change next.
```

### 10.6 Suggested edit targets (only when you say so)

| Priority | File | Why |
|----------|------|-----|
| 1 | `App.tsx` (ORB panel only first) | Dual-final display; evaluate gate; symbol hardcode |
| 2 | Optional extract | `components/workspaces/orbPaperGuidancePanel.tsx` |
| 3 | `api/schemas.ts` + client | Real PaperTradeGuidance types |
| 4 | Use or remove | `paperGuidanceOrbTickets` |

---

## 11. FINAL_REQUIRED_FLOW vs code flow (verify)

> **Plan file:** `docs/plans/FINAL_REQUIRED_FLOW.md`  
> **Date:** 2026-07-24 · **Read-only verify** · no product redesign  

### 11.1 Required flow steps (§5.1) vs code

| # | FINAL step | Code path | Follows? |
|---|------------|-----------|----------|
| 1 | INPUT symbol + TF | `PaperGuidanceRequest` + UI builds payload (`buildOrbGuidancePayload`) | **YES** (UI lab often forces RELIANCE 1m download) |
| 2 | SNAPSHOT closed bars + hash | `run_paper_guidance_p0` → D1 safety + `freeze_d2_closed_candle_snapshot` | **YES** |
| 3 | ANALYSIS engines = evidence | P1: chart, candle condition, levels, indicators, MTF | **MOSTLY** — not exact FINAL list (see 11.2) |
| 4 | LABELING / MEMORY | `_build_persisted_memory_evidence` | **YES** (when data exists) |
| 5 | RISK / SAFETY gates | D1 mode/kill/PIT/quality; D4 structure + exec/liquidity | **YES** |
| 6 | ONE ARBITER boss | `build_final_confluence_arbiter_report` (P1 once; ORB path **re-runs** arbiter) | **YES** boss role · **NOTE** arbiter runs twice when ORB on |
| 7 | PaperTradeGuidance one object | `PaperTradeGuidance` model returned by `POST /run` | **YES** API |
| 8 | next_action DO_NOTHING / OFFER_PAPER | set in `orb_guidance` from `can_record_paper` | **YES** on ORB path |
| 9 | Human APPROVE | `POST /record-simulated` + `approval_text=RECORD_SIMULATED_PAPER_TRADE` + confirm UI | **YES** |
| 10 | PAPER FILL | **TV local** `simulated_paper_ledger` (not Stock App `sim_trading.db`) | **YES** to updated Phase 2B · **NO** to old diagram “sim_trading.db v1” line |
| 11 | PaperTradeResult / outcome | `POST .../observe` + outcomes + reliability | **YES** v1.94 lifecycle |
| 12 | live blocked | `SYSTEM_MODE.allows_live_orders=False` | **YES** |

### 11.2 Live call chain (what actually runs)

```text
UI: Analyze RELIANCE ORB
  → GET local RELIANCE 1m preview
  → POST /api/v1/paper-guidance/run
       main.paper_guidance_run
         → run_paper_guidance_with_orb
              → run_paper_guidance_p1
                   → run_paper_guidance_p0   (D1 + D2 snapshot)
                   → CHART_REASONING
                   → CANDLE_CONDITION
                   → LEVEL_CONTEXT
                   → indicator snapshot evidence
                   → MTF_CONFIRMATION
                   → persisted memory evidence
                   → MARKET_STRUCTURE_LIQUIDITY
                   → EXECUTION_EVENT_OI_RISK
                   → FINAL_CONFLUENCE_ARBITER  (1st; P1 maps PAPER-CANDIDATE→WATCH)
              → if include_orb_playbook:
                   load active playbook → build_orb_candidate (ORB proposes only)
                   → FINAL_CONFLUENCE_ARBITER  (2nd; entry_plan_authority_present)
                   → map PAPER-CANDIDATE → ENTER_PAPER
                   → save OrbGuidanceTicket
                   → return PaperTradeGuidance + orb_ticket fields

UI: Record Simulated Paper (if can_record_paper)
  → confirm dialog
  → POST /record-simulated
       → load ticket, require ENTER_PAPER + hash match + phrase
       → TV local ledger only (no broker, no sim_trading.db)

UI: Evaluate Replay Result
  → POST /paper-records/observe
       → lifecycle outcome + reliability refresh
```

### 11.3 FINAL suggested engine order vs P1 code

| FINAL suggested order | In P1/ORB code? |
|-----------------------|-----------------|
| snapshot + PIT/data quality | **YES** D1/D2/P0 |
| chart reasoning v1.70 | **YES** |
| market regime feedback v1.71 | **PARTIAL** — score derived from chart; no full v1.71 engine receipt |
| structure liquidity v1.72 | **YES** |
| exec/event/oi risk v1.73 | **YES** |
| indicator lag vote + reliability | **PARTIAL** — memory/indicators present; `indicator_signal_score` often **0.0** hardcoded into arbiter request |
| final arbiter v1.75 | **YES** |
| package PaperTradeGuidance | **YES** |
| ORB as setup authority | **YES** only in `run_paper_guidance_with_orb` (after P1) |
| Kronos | **SKIPPED** by design (cannot boost) |

### 11.4 Non-negotiables (§1.3) vs code

| Constraint | Code | Score |
|------------|------|-------|
| No live broker in spine | ledger audit “no order”; SYSTEM_MODE | **PASS** |
| No hidden auto live routing | no place-order in paper path | **PASS** |
| Human approve before paper | confirm + literal approval_text | **PASS** |
| No future-bar leakage | PIT + closed snapshot + ORB hash check | **PASS** (by design) |
| Low evidence caps ENTER_PAPER | low_evidence_flag + blockers + arbiter | **PASS** |
| External AI cannot override | not in paper run path as authority | **PASS** |
| Kronos research only | skipped / cannot boost | **PASS** |

### 11.5 Where code does **NOT** fully follow FINAL product success (§1.4)

| Success metric | Reality | Score |
|----------------|---------|-------|
| Single action (one API + one UI) | One API **yes**; UI is ORB-specific + many competing finals | **PARTIAL** |
| Single decision language | ENTER_PAPER product + PAPER-CANDIDATE arbiter + Jarvis `final_action` | **NO** |
| Single boss in UX | Arbiter boss in **API**; UI still shows room Final Action cards | **PARTIAL** |
| Traceability engines_run | receipts on guidance object | **YES** API |
| Optional paper after approve | TV local **yes**; Stock App bridge **no** | **PARTIAL** (matches Phase 2B) |
| No silent competing finals | Many Jarvis panels still show finals | **NO** (UI) |

### 11.6 Easy English verdict

```text
DOES THE CODE FOLLOW THE FINAL FLOW?

BACKEND SPINE: YES in spirit and mostly in steps.
  symbol/TF → closed snapshot → evidence engines → arbiter → PaperTradeGuidance
  → human approve → local paper record → observe result
  live trading stays off.

BACKEND vs EXACT ENGINE LIST: PARTIAL.
  Order is D1–D6 style, not a perfect 1:1 copy of the “suggested first engine order”.
  Regime v1.71 and lag-vote are weaker than the plan drawing.

UI PRODUCT FLOW: PARTIAL / NO for “one place one final”.
  ORB panel follows approve → record → evaluate.
  Rest of Jarvis still shows other “final” answers.

OLD DIAGRAM “sim_trading.db v1”: NO longer the TV path.
  Code uses TV local ledger (matches updated Phase 2 text, not old ASCII box).

OVERALL: Campaign path follows FINAL spine enough to be the real product path.
            Full FINAL “definition of done” is still open (UI unity + language + evidence density).
```

