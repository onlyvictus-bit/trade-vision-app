# Trade Vision — Context (Domain, Environment, Constraints)

> **Purpose:** Domain knowledge, invariants vs policies, environmental bounds, and files that must stay in sync.  
> **Audience:** New engineer / AI handoff (read before `main.py` or `App.tsx`).  
> **Last verified against code:** 2026-07-24  
> **Latest completed version:** **v1.94** - ORB Paper Lifecycle Feedback  
> **Working path:** `D:\Projects\trading-platforms\stock-app\trade-vision-app`

---

## v1.94 Current Context

- Entry route: `POST /api/v1/paper-guidance/run`.
- D1 fails closed before snapshot/hash creation.
- D2 uses candle close time and produces a deterministic SHA-256 snapshot.
- P0 returns only WAIT/WATCH and has no entry, fill, routing, broker, or live
  authority.
- Older Kronos/Twin shared snapshots now exclude incomplete candles.
- Verification: 20 focused tests and 598 full backend tests passed on
  2026-07-23.
- The approved v1.88-v1.94 Paper Guidance + ORB paper campaign is complete.

Known hardening work:

- daily/weekly close semantics still use fixed durations rather than an
  exchange-calendar session model;
- the local RELIANCE CSV and some vendored indicator paths remain dev-only
  hardcoded paths;
- Jarvis now exposes ORB guidance, explicit paper-intent recording, explicit
  replay lifecycle evaluation, completed-only reliability, and storage health.

## 0. Diff vs previous context layer (2026-07-01 handoff)

| Change | Before | After |
|--------|--------|-------|
| Latest version | v1.85 | **+ v1.86 TrendForge** |
| Graph latest | v1.85 only | **+ trendforge node / edges** |
| Indicator intelligence type | treated as roadmap in places | **completed through v1.85** |
| Root monorepo | under-documented | **+ explicit adjacency in graph/context** |
| Safety file review date | 2026-06-30 | still valid content; review pointer here |

Related files that **must** stay consistent with this document:

| File | Role | Update when |
|------|------|-------------|
| `docs/IMPLEMENTATION_STATUS.md` | One-screen version | Every completed version |
| `docs/NEXT_BUILD_TARGET.md` | Next work | After each version |
| `TRADE_VISION_README.md § AI / New-Chat Handoff` | Compact handoff | Major version / safety / roadmap |
| `docs/SAFETY_INVARIANTS.md` | Non-negotiable rules | Any authority change |
| `docs/graph/project_graph.json` | Machine graph | Ownership/API/panel/roadmap |
| `docs/graph.md` | Human graph | Same as JSON |
| `ARCHITECTURE.md` | Design contracts | Component / ADR change |
| `docs/IMPLEMENTATION_STATUS.md` | Ship log | Every version |
| `docs/API_ENDPOINT_INDEX.md` | Route families | New route family |
| `docs/FRONTEND_PANEL_MAP.md` | UI surfaces | New panel/control |
| `docs/FILE_DOCUMENT_INDEX.md §7.4` | Open-this-first map | New owner files |
| `SPEC.md` / `TEST_PLAN.md` | Requirements / tests | Scope change |

---

## 1. Product intent (immutable product shape)

Trade Vision is a **research-first trading intelligence** system. It answers:

```text
What is happening now?
Has this stock done this before?
What happened after that?
Which evidence agrees or conflicts?
Where is the trade wrong?
Should the operator WAIT, WATCH, or mark a PAPER-CANDIDATE?
```

It is **not** an autonomous live trading bot.

**Code validation**

- `apps/api/app/state.py`: `SYSTEM_MODE` → `MOCK`, `allows_live_orders=False`, `allows_broker_credentials=False`, `immutable=True`
- Boot audit: `"Trade Vision API booted in MOCK mode. Live order routing disabled."`

**Expiration:** Revisit only with an explicit product ADR that flips system mode off MOCK and a full red-team + legal review. Until then, any PR enabling live routing is a defect.

---

## 2. Invariant domain rules (falsifiable)

These are **not** business preferences. Violation is a release blocker.

| ID | Invariant | Validation (code / test) | Consequence of violation |
|----|-----------|--------------------------|---------------------------|
| INV-1 | Live trading blocked | Reports set `live_trading_blocked=true`; tests in `apps/api/tests/` for decision/openalgo/trendforge | Live capital risk; release audit fail |
| INV-2 | Order routing disabled inside TV | `order_routing_enabled=false` on packages/gates | Accidental broker path |
| INV-3 | No broker credentials stored in TV | Safety invariants + credential vault is for **Gemini/Grok only** (`ai_credentials_vault.py`) | Credential exfil / broker session |
| INV-4 | No future candle leakage into decision-time features | PIT guards (`point_in_time_guard.py`), closed aggregates | Lookahead bias; invalid research |
| INV-5 | Incomplete HTF bars ≠ closed evidence | MTF builders / pullback engine | False confluence |
| INV-6 | Missing indicator values masked, not zero | Indicator runtime / cache integrity | Silent false signals |
| INV-7 | Indicator cache is speed artifact, not authority | Cache reports `used_for_probability=false` | Fake confidence |
| INV-8 | External AI cannot override risk / no-trade / kill switch | Jarvis review schema + safety tests | Unsafe promotion |
| INV-9 | Kronos is research forecast prior only | Twin arbiter wiring; safety invariants | Model-driven live risk |
| INV-10 | OpenAlgo is external boundary, not TV execution authority | openalgo handoff gates; adapter isolation | Premature live coupling |
| INV-11 | TrendForge packets must prove research-only safety envelope | `trendforge_bridge._verify_safety` | Execution-enabled intake |
| INV-12 | TrendForge default source is loopback only | `LOCAL_HOSTS` + remote URL reject tests | Untrusted remote intake |
| INV-13 | Lagging indicators cannot alone promote WAIT→WATCH or WATCH→PAPER-CANDIDATE | `confirmation_delay_bars` + lag voting | Late MACD false confidence |
| INV-14 | Pending signal-history rows do not count for reliability | v1.84/v1.85 modules | Inflated sample counts |
| INV-15 | Same-bar target/stop → stop-first unless LTF proof | Outcome labeler | Optimistic labels |
| INV-16 | TV-PROD-RED-001 failure blocks production research release candidate | `red_team_final_gate.py` | Shipping manipulated-wick blind spot |
| INV-17 | Final-audit cache TTL 2.0s; red-team failure must not be hidden by cache | `FINAL_AUDIT_CACHE_TTL_SECONDS = 2.0` | Stale pass on failed gate |
| INV-18 | Knowledge graph is orientation, not implementation SoT | `docs/graph.md` §0 + body, `state.KNOWLEDGE_GRAPH_PATH` | Implementing from stale graph |

**Allowed decision vocabulary (outputs)**

```text
WAIT | WATCH | PAPER-CANDIDATE | NO TRADE | FAKEOUT WARNING | AVOID CHOP
```

**Forbidden outputs**

```text
LIVE BUY | LIVE SELL | AUTO EXECUTE | ROUTE ORDER | IGNORE RISK | IGNORE LOW EVIDENCE
```

Source: `docs/SAFETY_INVARIANTS.md`.

---

## 3. Mutable business policies (may change with ADR)

| Policy | Current value | Code / doc | Revisit when |
|--------|---------------|------------|--------------|
| System mode label | Practice Mode - No Real Money | `state.SYSTEM_MODE` | Live product launch ADR |
| Default research symbol examples | RELIANCE-centric fixtures/tests | tests + panel map examples | Multi-market expansion |
| Timeframe contract | `1m,3m,5m,15m,30m,1H,4H,daily,weekly` (legacy route name `seven-timeframe`) | v1.82 runtime | New TF added |
| Indicator registry size | Locked ~94 indicator intelligence contract set (heritage plans cite 94) | `indicator_registry.py` | Registry lock change |
| Final audit cache | 2.0 seconds | `final_release_audit.py` | Latency SLO redesign |
| Golden replay fixtures | **16** seeded fixtures (6 legacy + 10 `golden_9c_*`) in `main.py` | v1.66 | New failure regime needed |
| Scenario coverage families | **15** names in `REQUIRED_SCENARIO_FAMILIES` | `release_control.py` | When adding a fixture that needs its own family token (e.g. `fake_breakout`) |
| TrendForge max packet age default | API `max_age_seconds` default 120 on pull route | `main.py` trendforge route | Ops wants longer/shorter |
| Reliability horizons | 3/5/9/12/20 candles (label path) | reliability label-signal | New horizon research |
| Complete-pending bar source | **Caller-supplied only** | v1.85 design | Local candle DB promotion |

---

## 4. Environment & topology

| Component | Path | Role |
|-----------|------|------|
| API | `apps/api` | FastAPI; 409 route decorators / 405 unique paths; owns decision contracts |
| Web | `apps/web` | React workspaces (Jarvis, Research, Behavior, System, Replay) |
| Kronos service | `apps/kronos-service` | Isolated forecast process; API must not import heavy model stack |
| OpenAlgo adapter | `apps/openalgo-adapter` | Isolated boundary simulator / dry-run plane |
| Contracts package | `packages/contracts` | Shared contract package (if consumed) |
| Design vault / graph | `docs/graph/project_graph.json` | Overridable via `TRADEVISION_DESIGN_VAULT` |
| Legacy chart app | monorepo `../server.py`, `../static`, `../indicators` | Reference; optional `legacy/stock_app` copy |
| Root research engine | monorepo `../research` (`/api/research`) | Separate strategy discovery; not TV authority |

**Mode defaults**

- Time provider: virtual/mock sequence (`TIME_STATE` in `state.py`)
- Kill switch: loaded from storage; default `armed` with `blocks_order_paths=False` until triggered (order paths still gated by mode)

---

## 5. Performance / scale boundaries (only measured claims)

| Metric | Bound | Source |
|--------|-------|--------|
| Final audit uncached (local) | ~7242 ms | IMPLEMENTATION_STATUS / AI_HANDOFF v1.68 |
| Final audit cached | ~0.33–0.40 ms | same |
| Final audit cache TTL | **2.0 s** | `FINAL_AUDIT_CACHE_TTL_SECONDS` |
| Full backend regression (v1.93, 2026-07-24) | **683 passed**, 0 failed | `python -m pytest apps/api/tests -q` |
| Focused Paper Guidance + ORB v1.88-v1.93 | **85 passed** | campaign modules |
| Full backend regression (v1.94, 2026-07-24) | **715 passed**, 0 failed | `python -m pytest apps/api/tests -q` |
| Focused ORB lifecycle v1.94 | **32 passed** | `test_orb_feedback_hardening_v194.py` |
| Focused ORB UI/ledger/lifecycle v1.92-v1.94 | **54 passed** | three campaign modules |
| Focused v1.85 subset | **37 passed**, 510 deselected | IMPLEMENTATION_STATUS |
| TrendForge focused tests | **6 passed** (plus 6 OpenAlgo adapter) | IMPLEMENTATION_STATUS v1.86 |
| Concurrent users / 10k scale | **[GAP: requires load-test report]** | Not in repo |
| Multi-tenant isolation | **[GAP: requires tenancy ADR]** | Single-operator research assumption |
| Market-data fan-in (symbols) | **[GAP: requires capacity model]** | Snapshot/import oriented |

Do **not** document “scalable” or “fast” without one of the rows above.

---

## 6. Domain objects (contracts first)

| Object | Meaning | Authority |
|--------|---------|-----------|
| Point-in-time snapshot | OHLCV + metadata at decision time | Data truth for research |
| Behavior report | Typed evidence envelope | May reduce confidence |
| Indicator intelligence contract | Ontology: purpose, lag, failure, conflict | Required for trusted indicators |
| Signal history row | Pending or completed label | Research reliability only |
| Twin analysis | Behavior safety + Kronos prior | Safety wins |
| External AI review | Schema-bound display critique | Display only |
| TrendForge intake | Signed scanner evidence | Research; safety envelope mandatory |
| OpenAlgo package | Paper/dry-run handoff package | Boundary; no live authority |
| Release readiness evidence | Audit summary | Blocks release candidate when gates fail |

---

## 7. Known unknowns

| ID | Unknown | Why it matters | What unblocks |
|----|---------|----------------|---------------|
| KU-1 | Production multi-user concurrency limit | Capacity planning | Load test + ADR |
| KU-2 | When MOCK mode may become non-immutable | Live trading roadmap | Explicit product + legal ADR |
| KU-3 | Auto-promotion path from reliability → probability authority | Currently blocked; plans discuss future | Bayesian sample gates + ADR; tests must prove no routing |
| KU-4 | v1.78 sequential causality “complete” definition | Plan heritage vs partial `event_sequence_mining.py` | Scope freeze in plan + version entry |
| KU-5 | v1.79 conflict arbiter vs v1.75 final confluence overlap | Naming confusion | Architecture note + single authority diagram |
| KU-6 | Indicator reliability still may use fixture labels when history empty | v1.86 status note | More real history ingestion + completion |
| KU-7 | Remote TrendForge allowlist (if ever) | Security boundary | Explicit host policy ADR + HMAC rotation |
| KU-8 | ~~Full regression after v1.94~~ | **Resolved 2026-07-24: 715 passed** | Re-run after next approved milestone |
| KU-9 | Global frontend evidence refresh can delay dev API health under one worker | Open | Lazy-load by active workspace/subtab before deployment SLO sign-off |
| KU-10 | Daily/weekly close uses fixed duration, not exchange calendar | v1.87 P0 | Calendar-aware close policy before live-derived data |
| KU-11 | Dev-only RELIANCE/vendor paths are hardcoded | static audit 2026-07-23 | Config manifests before deployment packaging |
| KU-12 | Root research engine coupling to TV | Separate products in monorepo | Integration ADR if unified UI desired |
| KU-13 | Whether `fake_breakout` should become its own scenario **family** (fixture already exists) | Family count 15 vs fixture count 16 | Product decision + release_control update |

---

## 8. Do-not-touch without approval

```text
Do not enable live broker order routing.
Do not store browser sessions, cookies, or hidden login tokens for brokers.
Do not let Gemini, Grok, Kronos, OpenAlgo, or TrendForge override no-trade/risk gates.
Do not delete legacy stock-app references.
Do not delete mock/replay paths when adding real paths.
Do not remove existing plan content while merging; append or clearly supersede.
Do not treat docs/graph as implementation source of truth.
```

---

## 9. First-read order (token-saving)

```text
1. docs/context.md                    (this file)
2. docs/IMPLEMENTATION_STATUS.md
3. docs/NEXT_BUILD_TARGET.md
4. docs/SAFETY_INVARIANTS.md
5. ARCHITECTURE.md                    (contracts + ADR index)
6. docs/graph.md                      (structure)
7. Only then: exact source file for the task
```

Avoid opening first: `apps/api/app/main.py`, `apps/web/src/App.tsx`, full `IMPLEMENTATION_STATUS.md` (use indexes).

---

## 10. Traceability map (claim → artifact)

| Claim | Artifact |
|-------|----------|
| Latest version v1.94 | `IMPLEMENTATION_STATUS.md`; Paper Guidance/ORB modules; 32 focused + 715 full tests |
| ORB guidance, simulated ledger, lifecycle, feedback | `orb_guidance.py`; `simulated_paper_ledger.py`; `orb_paper_lifecycle.py`; `orb_paper_feedback.py`; Jarvis ORB panel |
| MOCK immutable | `state.py` SYSTEM_MODE |
| Knowledge graph path | `state.KNOWLEDGE_GRAPH_PATH` |
| Safety vocabulary | `SAFETY_INVARIANTS.md` |
| Indicator history pipeline | v1.83–v1.85 modules + routes in `main.py` |
| Red-team gate | `red_team_final_gate.py` |
| Root chart app separate | monorepo `server.py` + root `STOCK_APP_ARCHITECTURE.md` |

### Expiration

Refresh this file when INV-* set changes, a new external integration ships, or measured performance bounds change.
