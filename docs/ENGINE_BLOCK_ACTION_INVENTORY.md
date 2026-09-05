# Engine / Block / Action Inventory

> **Purpose:** Count and name research engines, think engines, analysis blocks, gates, arbiters, and product actions present in the monorepo.  
> **Date:** 2026-07-25  
> **Scope:** Trade Vision (`trade-vision-app`) primary; Stock App ML noted separately.  
> **Not product law:** Product requirement remains `docs/plans/FINAL_REQUIRED_FLOW.md`.  
> **Related:** `docs/BUILD_AUDIT.md`, `docs/FRONTEND_PANEL_MAP.md`, `ARCHITECTURE.md`

---

## Headline counts

| Layer | Count (approx) | What it means |
|--------|----------------:|---------------|
| Behavior modules (`apps/api/app/behavior/*.py`) | **~149** | Separate “brains” / services |
| HTTP route decorators in TV API (`main.py`) | **~395** | Many APIs (not 395 different products) |
| Behavior API family alone | **~215** | Most engines exposed as APIs |
| Jarvis-related modules | **~44** | Decision room / AI / gates / panels |
| UI `<Panel>` cards in `App.tsx` | **~154** | Visible “blocks” on screen |
| Paper-guidance product routes | **8** | Real paper spine actions |
| Arbiters (named) | **~4** | Only **1** is product band boss |
| Live trading mode | **blocked** | `SYSTEM_MODE.allows_live_orders=False` |

They are **not all equal**. Most are **research/evidence**. Few are **product actions**. One is **final boss**.

---

## 1) By role

| Role | Meaning | Count feel | Examples |
|------|---------|------------|----------|
| **Research engines** | Offline / forecast / discovery; not boss | ~15–25 named | Kronos, Twin, TrendForge, ORB discovery/proof, analogs, walk-forward |
| **Think / reason engines** | Interpret structure, memory, regime | ~25–40 | Chart reasoning, 9C, regime, hypothesis, pattern memory, lag vote |
| **Analyse blocks** | Measure TA/levels/MTF/OI/liquidity | ~30–50 | MTF, liquidity, OI risk, candles, levels, indicators |
| **Gates / blocks (safety)** | Can only reduce / stop | ~15–25 | PIT, data quality, liquidity C, kill switch, production blockers |
| **Arbiters (bosses)** | Merge to a decision band | ~4 (1 product boss) | **Final confluence arbiter** (product), Jarvis/9C/twin arbiters |
| **Product actions** | User/API changes paper state | ~5–8 | Run guidance, record paper, observe, list records… |
| **Display / assembly** | Package for UI (not new alpha) | ~40+ Jarvis | Master panel, fusion, Gemini room, comparison |

---

## 2) Named examples — present?

| Name | Present? | Where / what | Role |
|------|----------|--------------|------|
| **Kronos** | Yes | `behavior/kronos_proxy.py` + ~10 kronos routes | Research prior only |
| **ORB** | Yes | `orb/core.py`, `discovery.py`, `proof.py` + `orb_guidance` + lifecycle | Setup proposer + paper path |
| **Paper trade** | Yes | spine + simulated ledger + 8 routes | Product action path |
| **ML** | Yes (Stock App) | root `server.py` ML/ensemble/HMM etc. | Separate product; not TV spine boss |
| **Vision (Trade Vision app)** | Yes | whole `trade-vision-app` | Platform name; not one engine |
| **OI** | Yes | `execution_event_oi_risk.py` | Risk/evidence (often proxy if no OI data) |
| **MTF** | Yes | `real_mtf_pullback`, `multi_timeframe_conflict`, MTF in spine | Evidence / gate |
| **Liquidity** | Yes | `market_structure_liquidity.py` | Structure + liquidity grade gate |
| **Gemini / Grok** | Yes | providers + Jarvis AI panels | Review only, not boss |
| **OpenAlgo** | Yes | transport + handoff gates | Boundary / dry-run, not live fill |
| **Twin** | Yes | `twin_arbiter`, `full_twin_analysis` | Research / dual view |
| **9C / DNA** | Yes | `nine_candle_*` | Think / memory |
| **Indicators** | Yes | ~15 indicator modules | Analyse + memory |
| **Regime** | Yes | `market_regime_feedback`, `regime_gate` | Think / gate |
| **Arbiter** | Yes | `final_confluence_arbiter` | **Product boss** |

---

## 3) Named families (catalog)

### A. Research engines (~12–18 families)

| Family | Modules / surface |
|--------|-------------------|
| Kronos | `kronos_proxy` + routes |
| Twin | `twin_arbiter`, `full_twin_analysis` |
| TrendForge | `trendforge_bridge` + integrations routes |
| ORB lab | `orb/discovery`, `orb/proof`, `orb/core` |
| Analogs | `analog_research` |
| Walk-forward | `walk_forward_validation` |
| Event sequence mining | `event_sequence_mining` |
| Hypothesis | `hypothesis_engine` |
| Feature store / redundancy | `feature_store`, `feature_redundancy` |
| Chart replay research | `chart_replay`, replay matrices |
| Stock App research/ML | root `server.py` (RF, boosters, HMM, backtest, …) |

### B. Think / reason engines (~20+ families)

| Family | Examples |
|--------|----------|
| Chart reasoning v1.70 | `chart_reasoning_volatility` |
| Regime feedback v1.71 | `market_regime_feedback` |
| Structure/liquidity v1.72 | `market_structure_liquidity` |
| Exec/event/OI v1.73 | `execution_event_oi_risk` |
| Post-entry v1.74 | `post_entry_lifecycle` |
| 9-candle hybrid | `nine_candle_hybrid` + history/calibration |
| Pattern / session memory | `pattern_memory`, `session_memory` |
| Combination / cause-effect | Jarvis memory modules |
| Lag voting | `indicator_lag_voting` |
| False agreement / confluence helpers | `false_agreement_confluence` |
| Decision engine (behavior) | `decision_engine` (legacy path, not only FINAL spine) |

### C. Analyse blocks

| Block | Examples |
|-------|----------|
| Candles | `candle_anatomy`, condition classifier |
| Levels | band distance, confluence, proximity, VWAP/OR/CPR context |
| MTF | real MTF pullback, multi-TF conflict, timeframe features |
| Indicators | registry, runtime, cache, reliability, signal history |
| Cross-market | `cross_market_influence` |
| Corporate action | abnormal market memory |
| Data quality | `data_quality`, adapters |

### D. Blocks / gates (can stop ENTER_PAPER)

| Gate | Examples |
|------|----------|
| System mode / kill switch | `state.py` SYSTEM_MODE |
| PIT / no future bars | `point_in_time_guard` |
| Data quality blocks trade | `data_quality` |
| Liquidity grade C | via exec/structure + arbiter |
| Low evidence cap | paper spine + reliability min samples |
| Production blockers | `jarvis_production_blockers` |
| OpenAlgo auto-delivery blocked | openalgo handoff gate |
| Paper record eligibility | `can_record_paper`, approval phrase |

### E. Arbiters (decision bosses)

| Arbiter | Product role |
|---------|----------------|
| **`final_confluence_arbiter`** | **Yes — FINAL sole band boss** |
| `jarvis_decision_arbiter` | Room packaging / older path |
| `nine_candle_reasoning_arbiter` | 9C only |
| `twin_arbiter` | Twin research |

### F. Product actions (paper spine)

| Action | API / UI |
|--------|----------|
| Run paper guidance | `POST /api/v1/paper-guidance/run` + Analyze button |
| List tickets | `GET /api/v1/paper-guidance/orb-tickets` (client exists; UI rarely used) |
| Record simulated paper | `POST /api/v1/paper-guidance/record-simulated` + confirm |
| List paper records | `GET /api/v1/paper-guidance/paper-records` |
| Observe lifecycle | `POST /api/v1/paper-guidance/paper-records/observe` |
| List outcomes | `GET /api/v1/paper-guidance/paper-outcomes` |
| Reliability | `GET /api/v1/paper-guidance/orb-reliability/{id}` |
| Store monitor | `GET /api/v1/paper-guidance/storage-monitor` |

**Not product actions:** Gemini review, Kronos forecast, most Behavior panels (read/display).

---

## 4) Keyword hits in `behavior/` filenames (snapshot)

Rough module counts by keyword in filename (one module can match one keyword bucket):

| Keyword | ~Modules | Sample files |
|---------|----------:|--------------|
| jarvis | 44 | decision room, fusion, AI panels, OpenAlgo gates |
| indicator | 15 | registry, lag vote, reliability, cache, history |
| paper | 11 | spine, ledger, lifecycle, paper-ready audits |
| openalgo | 6 | transport, handoff, bridge |
| candle / nine_candle | 6 | hybrid, history, anatomy |
| memory | 8 | pattern, session, reliability, combination |
| gemini | 4 | provider + Jarvis Gemini rooms |
| replay | 4 | chart replay, indicator matrices |
| execution | 4 | OI risk, sim, paper loop |
| arbiter | 4 | final confluence, jarvis, 9C, twin |
| orb (behavior) | 3 | guidance, lifecycle, feedback |
| regime | 3 | feedback, calendar, gate |
| timeframe / mtf | 5 | real_mtf, multi_tf, features |
| kronos | 1 | kronos_proxy |
| trendforge | 1 | trendforge_bridge |
| twin | 2 | twin_arbiter, full_twin |
| grok | 2 | grok_provider, grok_gateway |

ORB package also has: `apps/api/app/orb/core.py`, `discovery.py`, `proof.py`, `__init__.py`.

---

## 5) API route family sizes (TV `main.py` prefixes)

| Family prefix | ~Route count |
|---------------|-------------:|
| behavior | 215 |
| jarvis | 62 |
| openalgo | 40 |
| twin | 10 |
| kronos | 10 |
| ai | 7 |
| replay | 7 |
| system | 6 |
| release / deployment | ~10 |
| paper-guidance (product) | 8 |
| other (auth, knowledge, sim, …) | remainder of ~395 |

---

## 6) Easy English summary

```text
~149 behavior engine/service modules
~395 TV API route decorators
~154 UI panels in App.tsx
~44 Jarvis assembly/AI/gate modules
~15 indicator family modules
~8 paper-guidance product endpoints
~4 arbiters (1 product boss: final confluence)
live trading: blocked

Stock App separately: ML / BUY-SELL / sim book in server.py
```

The project is a **big toolbox**:

- **Lots of research & analysis boxes** (Kronos, ORB, MTF, OI, liquidity, 9C, indicators, AI review…).
- **Many UI cards** (~154) that *show* those boxes.
- **Only a short paper path** is the real product action:  
  **run guidance → (maybe) approve paper → observe result**.
- **One final boss** for paper band: **final confluence arbiter**.  
  ORB proposes; Kronos/AI/ML must not override risk.

---

## 7) Paper product path (spine-only file list)

```text
DOCS
  docs/plans/FINAL_REQUIRED_FLOW.md
  docs/IMPLEMENTATION_STATUS.md
  docs/SAFETY_INVARIANTS.md

API
  apps/api/app/main.py
  apps/api/app/models.py
  apps/api/app/state.py
  apps/api/app/behavior/paper_guidance_spine.py
  apps/api/app/behavior/orb_guidance.py
  apps/api/app/behavior/final_confluence_arbiter.py
  apps/api/app/behavior/simulated_paper_ledger.py
  apps/api/app/behavior/orb_paper_lifecycle.py
  apps/api/app/behavior/orb_paper_feedback.py
  apps/api/app/behavior/atomic_json_store.py
  apps/api/app/orb/core.py
  apps/api/app/orb/discovery.py
  apps/api/app/orb/proof.py

UI
  apps/web/src/api/client.ts
  apps/web/src/App.tsx   (ORB Paper Guidance panel)
```

---

## 8) Maintenance

- Recount after large module adds: behavior `*.py` count, `main.py` route prefixes, `App.tsx` Panel count.
- Do not treat this file as permission to call every engine a product final.
- Authority for “what the product must be” stays `FINAL_REQUIRED_FLOW.md`.
