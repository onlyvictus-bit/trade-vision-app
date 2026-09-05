# Remaining Python recheck (all `apps/api/app` modules)

> **Date:** 2026-07-25  
> **Goal:** Recheck **remaining** `.py` files beyond the paper-spine deep dive.  
> **Companion:** `TV_COMPLETE_FLOW_MAP.html` **Tab 5** (exact /run chain — former VERIFIED md merged).  
> **Method:** Full disk inventory + `main.py` import graph + sample entry functions + call-count for key builders.

---

## 1. Inventory totals

| Location | `.py` count |
|----------|------------:|
| `apps/api/app` total (no `__pycache__`) | **174** |
| `behavior/` | **150** (149 modules + `__init__`) |
| `orb/` | **4** |
| App root (`main`, `models`, `state`, …) | **9** |
| `vendor/` | **11** |

| Link to `main.py` | Count |
|-------------------|------:|
| `from .behavior.<module>` imports | **144** |
| On disk, **not** direct main import | **5** (see §2) |

---

## 2. Not imported by `main.py` (but still used)

| Module | How it connects |
|--------|-----------------|
| `paper_guidance_spine` | Called only by `orb_guidance.run_paper_guidance_with_orb` |
| `paper_guidance_config` | Used by spine / orb / ledger config loaders |
| `real_indicator_adapter` | Used by spine `_snapshot_indicator_evidence` |
| `jarvis_decision_arbiter` | Used by `jarvis_decision_room` |
| `nine_candle_reasoning_arbiter` | Used inside nine-candle stack |

These are **not orphans** — they are **second-layer** modules.

---

## 3. Category map (all 149 behavior modules)

### A — PAPER_SPINE (16) — product path /run → record → observe

**On path (code-verified):**

| File | Role on paper path |
|------|--------------------|
| `paper_guidance_spine` | P0 + P1 engines + arbiter #1 |
| `paper_guidance_config` | thresholds, store paths |
| `orb_guidance` | wrap + ORB + arbiter #2 + ticket |
| `final_confluence_arbiter` | band boss |
| `data_quality` | quality gate |
| `point_in_time_guard` | no future bars |
| `chart_reasoning_volatility` | CHART_REASONING |
| `condition_classifier` | CANDLE_CONDITION |
| `context_engines` | LEVEL_CONTEXT + HTF confirm |
| `real_indicator_adapter` | SNAPSHOT_INDICATOR_RUNTIME |
| `market_structure_liquidity` | STRUCTURE_LIQUIDITY |
| `execution_event_oi_risk` | EXECUTION_EVENT_OI_RISK |
| `simulated_paper_ledger` | record-simulated |
| `orb_paper_lifecycle` | observe |
| `orb_paper_feedback` | reliability + storage monitor |
| `atomic_json_store` | ticket/paper/outcome files |

**Also required (not in behavior):** `orb/core.py`, `orb/proof.py` (`list_orb_playbooks`), `state.py`, `storage.py` (history rows), `main.py` routes, `models.py`.

---

### B — JARVIS_UI (44) — assembly / panels / gates for Decision Room

Examples (all `jarvis_*`):

- `jarvis_decision_room` — **room hub** (builds state for UI)
- `jarvis_decision_arbiter` — room-side arbiter helper (not paper spine arbiter)
- `jarvis_master_panel`, `jarvis_decision_fusion`, `jarvis_trading_decision_output` — competing “final” **display**
- `jarvis_evidence_assembly` / `jarvis_evidence_cache` — bundles OpenAlgo/paper-safety widgets
- OpenAlgo-related jarvis: `jarvis_openalgo_handoff_gate`, `jarvis_paper_execution_loop`, …
- AI-related jarvis: `jarvis_gemini_*`, comparison/diff/ledger helpers
- Memory/display: candle cause-effect, indicator combination, …

**Flow impact:** These run on **Jarvis / behavior routes**, not inside `POST /paper-guidance/run`.  
UI can show their “Final Action” **next to** ORB paper card → product confusion (known).

---

### C — EXTERNAL_AI (5)

| File | Role |
|------|------|
| `gemini_provider` | Gemini status/review |
| `grok_provider` | Grok review |
| `grok_gateway_provider` | Local gateway |
| `ai_credentials_vault` | AI keys only |
| `external_ai_reliability` | reliability of reviews |

**main.py uses:** yes (multiple routes).  
**paper /run:** **NO** — spine sets `external_ai_score=0.0`.

---

### D — KRONOS / TWIN / TRENDFORGE (5)

| File | Role |
|------|------|
| `kronos_proxy` | forecast/status/backtest helpers |
| `shared_snapshot` | Kronos shared snapshot helper |
| `twin_arbiter` | twin comparison |
| `full_twin_analysis` | full twin report |
| `trendforge_bridge` | signed research intake |

**main.py uses:** Kronos/twin builders heavily (separate route families).  
**paper /run:** Kronos **skipped** (warning only). Twin/TrendForge **not** on /run.

---

### E — OPENALGO / EXEC BOUNDARY (10)

| File | Role |
|------|------|
| `openalgo_transport` | enqueue/deliver/worker |
| `openalgo_adapter_harness` | adapter dry-run status |
| `openalgo_report_importer` | report summary |
| `executor_handoff_audit` | handoff envelope |
| `paper_executor_permission` | permission matrix |
| `execution_intent_paper_safety` | paper intent safety |
| `execution_simulator` | behavior execution sim |
| `paper_reality_check` | room paper reality widget |
| `transport_resilience` | transport resilience |
| `transport_security` | transport security |

**paper /run:** **NO**.  
**After TV Record Simulated Paper:** **not auto-chained**.  
Live routing blocked by design/safety.

---

### F — INDICATOR / 9C / MTF PANELS (18)

Includes: `indicator_registry`, `indicator_lag_voting`, `indicator_reliability_memory`, signal history ingest/complete, result cache, runtime bridge/coverage, promotion gates, observations, expansion, `nine_candle_*`, `real_mtf_pullback`, replay indicator matrix/validation.

| Note | Detail |
|------|--------|
| `indicator_lag_voting` | Has **main routes** (`build_indicator_lag_voting` used in main) |
| Same module | **Not** imported by `paper_guidance_spine` |
| Paper path indicators | Only via `real_indicator_adapter` snapshot runtime |
| 9C | Large hybrid stack; Behavior/Jarvis panels |

---

### G — RELEASE / OPS SAFETY (8)

`deployment_recovery`, `final_release_audit`, `operational_safety`, `red_team_final_gate`, `release_control`, `release_readiness_evidence`, `runtime_readiness`, `safety_hardening`

**paper /run:** not the spine. Supports ops/readiness APIs.

---

### H — RESEARCH / ANALYSIS (other) (~43)

Examples: `market_regime_feedback`, `regime_gate`, `decision_engine`, `risk_engine`, `post_entry_lifecycle`, `walk_forward_validation`, `analog_research`, `hypothesis_engine`, pattern/session/level memory, feature store, chart_replay, data_adapter, frontend_panels, corporate action, cross-market, …

| Critical recheck | Result |
|------------------|--------|
| `market_regime_feedback` | **Has routes in main** (`build_market_regime_feedback` used) |
| Same | **Not** called from paper spine |
| Spine “regime score” | Derived from **chart** helper `_market_regime_score`, not this module |

---

## 4. `orb/` package (4 files)

| File | On Analyze/run? | Role |
|------|-----------------|------|
| `core.py` | **YES** (`build_orb_candidate`) | OR setup on snapshot |
| `proof.py` | **partial** (`list_orb_playbooks` on run; `run_orb_proof` / `promote_*` offline) | playbooks |
| `discovery.py` | **NO on Analyze** | offline discovery jobs (separate APIs) |
| `__init__.py` | exports | package |

---

## 5. App root modules (9)

| File | Role |
|------|------|
| `main.py` | all HTTP routes |
| `models.py` | schemas / envelopes |
| `state.py` | SYSTEM_MODE, kill switch, paths |
| `storage.py` | DB/history helpers (memory rows) |
| `order_guard.py` | order safety |
| `security.py` | security helpers |
| `responses.py` | envelopes |
| `observability.py` | logs/metrics |
| `__init__.py` | package |

---

## 6. `vendor/` (11)

Third-party / vendored code supporting services — **not** product flow steps. Do not treat as engines in the process diagram.

---

## 7. Does remaining code change the process flow?

| Question | Answer |
|----------|--------|
| Is stock→…→end paper order still correct? | **YES** |
| Are there extra engines silently inside /run? | **NO** (confirmed hardcodes + import graph) |
| Are remaining modules dead? | **NO** — most exposed via **other** main routes |
| Should flow map list all 149 as sequential steps? | **NO** — that would be false |
| Should intersection map list them as side hubs? | **YES** (by family: Jarvis, AI, Kronos/Twin, OpenAlgo, Indicator/9C, Research) |

### Extra builders that exist as **parallel APIs** (not paper steps)

```text
build_market_regime_feedback  → own behavior routes
build_indicator_lag_voting    → own behavior routes
build_kronos_*                → kronos routes
build_twin_* / full_twin      → twin routes
build_jarvis_decision_room    → jarvis routes
build_nine_candle_*           → behavior/9C routes
build_real_mtf_pullback       → behavior routes
```

---

## 8. Correct multi-lane picture

```text
LANE A — PRODUCT PAPER (single process Start→End)
  UI Analyze → /paper-guidance/run → spine engines → arbiter → ORB → ticket
  → optional record → observe → END
  Modules: §3A + orb/core + orb/proof(list) + state/storage/main

LANE B — JARVIS ROOM (parallel)
  /jarvis* + decision_room assembles display from many widgets
  May show Kronos/AI/OpenAlgo/9C/other finals
  Does NOT replace LANE A boss (final_confluence_arbiter on paper path)

LANE C — RESEARCH APIs (parallel)
  Kronos, Twin, TrendForge, regime feedback, lag vote, walk-forward, analogs, …

LANE D — BOUNDARY (parallel, blocked from live)
  OpenAlgo transport/handoff preview
  Stock App (outside this package) sim/ML

LANE E — OPS / RELEASE
  readiness, red-team, deployment, hardening
```

---

## 9. Flow map correction checklist

| Item | Status after recheck |
|------|----------------------|
| Paper step order | Valid |
| Exact engine_ids on /run | Valid in VERIFIED doc |
| Hardcoded scores | Valid |
| Ticket 900s fresh | Valid |
| Remaining py are “missing steps” | **False** — they are other lanes |
| market_regime_feedback unused in repo | **False** — used by main routes, not paper spine |
| indicator_lag_voting unused in repo | **False** — used by main + reliability helpers, not paper spine |

---

## 10. Files produced

| File | Content |
|------|---------|
| `docs/TV_COMPLETE_FLOW_MAP.html` Tab 5 | Deep paper path (merged; former VERIFIED md removed) |
| `docs/REMAINING_PY_INVENTORY.md` | This file — remaining modules by lane |
| `docs/TV_COMPLETE_FLOW_MAP.html` Tabs 1–4 | Visual process + intersections + block details |
| `docs/PROJECT_BRAIN.html` | Short plain-English cards |

---

## 11. Honest statement

- **Rechecked remaining modules** by inventory + import graph + main builder usage + entry-point sampling.  
- **Did not** re-read every line of every research/Jarvis file (hundreds of KB each, e.g. `nine_candle_hybrid`).  
- **Did confirm** they are almost all wired to **main routes**, but **not** into the paper `/run` sequential chain.  
- Product Start→End flow does **not** need 149 sequential boxes — that would misrepresent the code.
