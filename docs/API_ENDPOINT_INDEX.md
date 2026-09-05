# API Endpoint Index

Last reviewed: 2026-07-24

Purpose: summarize the route families before opening `apps/api/app/main.py`.  
Scale: **409** `@app` route decorators, **405** unique path strings, largest family `v1/behavior`.

## Core System

```text
GET  /health
GET  /ready
GET  /api/time
GET  /api/auth/me
GET  /api/system/mode
GET  /api/system/features
GET  /api/system/killswitch
POST /api/system/killswitch/trigger
POST /api/system/killswitch/reset
GET  /api/system/pipeline
GET  /api/storage/status
```

## Paper Guidance And ORB

```text
POST /api/v1/paper-guidance/run
GET  /api/v1/paper-guidance/orb-tickets
POST /api/v1/paper-guidance/record-simulated
GET  /api/v1/paper-guidance/paper-records
POST /api/v1/paper-guidance/paper-records/observe
GET  /api/v1/paper-guidance/paper-outcomes
GET  /api/v1/paper-guidance/orb-reliability/{playbook_id}
GET  /api/v1/paper-guidance/storage-monitor
```

The simulated-record route requires an eligible server-stored ORB ticket, exact
snapshot hash, and explicit approval text. These routes expose no broker or live
execution path. Lifecycle observation is an explicit replay/downloaded-data
action; it never claims an automatic or broker fill. Reliability counts only
completed, integrity-valid outcomes and cannot promote a playbook.

## Observability / Audit / Layout

```text
GET  /api/observability/status
GET  /api/observability/requests
GET  /api/audit/events
GET  /api/audit/integrity
GET  /api/layout/{workspace_id}
PUT  /api/layout/{workspace_id}
```

## Cockpit-ish system state (mock envelopes)

```text
GET  /api/decision/current
GET  /api/portfolio/state
GET  /api/risk/state
GET  /api/market/dna
GET  /api/microstructure/state
```

## Replay / Data / Features

```text
GET  /api/replay/session
POST /api/replay/start
POST /api/replay/seek
POST /api/replay/play
POST /api/replay/pause
POST /api/replay/step
GET  /api/replay/archive
POST /api/data/ingest/mock
GET  /api/data/snapshots
GET  /api/data/quality
GET  /api/features/registry
```

## Execution simulation / order-path guard (not live broker)

```text
GET  /api/execution/simulation
GET  /api/execution/order-path/status
POST /api/execution/order-path/simulate
GET  /api/simulation/integrity
```

Safety: simulation and order-path probes remain non-live; `live_order_routing_enabled=false` on pipeline.

## Deployment / recovery (research stack ops)

```text
GET  /api/v1/deployment/configuration
GET  /api/v1/deployment/readiness
GET  /api/v1/deployment/smoke
POST /api/v1/deployment/database/backup
POST /api/v1/deployment/database/restore-drill
```

See runbook: `docs/runbooks/deployment-backup-restore.md`.

## Jarvis Decision Room

Route family:

```text
/api/v1/jarvis/*
```

Important groups:

```text
decision-room
production-blockers
preflight-evidence
gemini
grok
ai-review
external-ai
openalgo
indicator-combination-memory
candle-cause-effect-memory
decision-evidence/export
```

## Behavior Intelligence

Route family:

```text
/api/v1/behavior/*
```

Recent MTF route additions:

```text
GET  /api/v1/behavior/timeframes/pullback/current
POST /api/v1/behavior/timeframes/pullback
```

Recent market-structure route additions:

```text
GET  /api/v1/behavior/market-structure/liquidity/current
POST /api/v1/behavior/market-structure/liquidity/analyze
GET  /api/v1/behavior/execution-event-oi/risk/current
POST /api/v1/behavior/execution-event-oi/risk/analyze
GET  /api/v1/behavior/post-entry/lifecycle/current
POST /api/v1/behavior/post-entry/lifecycle/analyze
GET  /api/v1/behavior/final-confluence/arbiter/current
POST /api/v1/behavior/final-confluence/arbiter/analyze
GET  /api/v1/behavior/indicators/{indicator_id}/ontology
POST /api/v1/behavior/indicators/lag-vote
POST /api/v1/behavior/indicators/reliability/label-signal
GET  /api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}
GET  /api/v1/behavior/indicators/intelligence-summary/{symbol}
```

v1.80 indicator-intelligence routes:

```text
GET /api/v1/behavior/indicators/{indicator_id}/ontology
  -> returns one registry entry with purpose/category/lag/failure/conflict metadata

POST /api/v1/behavior/indicators/lag-vote
  -> applies lag_weight = 1 / (1 + confirmation_delay_bars)
  -> keeps lagging/stale indicators from promoting WATCH to PAPER-CANDIDATE

GET /api/v1/behavior/indicators/intelligence-summary/{symbol}
  -> compact symbol-level summary of ontology coverage and sample lag-aware votes
```

v1.81 indicator-reliability routes:

```text
POST /api/v1/behavior/indicators/reliability/label-signal
  -> labels one indicator signal against a completed 3/5/9/12/20-candle horizon
  -> pending horizons are not counted
  -> same-bar target/stop collision uses conservative stop-first unless lower-timeframe proof exists

GET /api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}
  -> returns per-stock/per-regime/per-session reliability rollup
  -> Bayesian-shrinks low evidence toward neutral
  -> returns reciprocal-signal warning and reliability quarantine state
```

Safety rule:

```text
These routes are research-only. They cannot create orders, route OpenAlgo intent, override no-trade gates, or grant probability authority.
```

v1.82 timeframe/reliability-drilldown routes:

```text
GET  /api/v1/behavior/features/seven-timeframe/current
POST /api/v1/behavior/features/seven-timeframe
GET  /api/v1/behavior/timeframes/conflict/current
POST /api/v1/behavior/timeframes/conflict
GET  /api/v1/behavior/patterns/by-timeframe
POST /api/v1/behavior/patterns/by-timeframe/analyze
GET  /api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}
GET  /api/v1/behavior/frontend/panel-map
```

The legacy `seven-timeframe` route name is retained for compatibility, but the v1.82 runtime contract emits:

```text
1m, 3m, 5m, 15m, 30m, 1H, 4H, daily, weekly
```

Safety rule:

```text
30m and 4H are closed-candle, point-in-time-safe research timeframes only. They cannot enable probability authority, order routing, broker credentials, or live trading.
```

v1.83 persistent indicator signal history routes:

```text
POST /api/v1/behavior/indicators/reliability/save-history
GET  /api/v1/behavior/indicators/{indicator_id}/signal-history/{symbol}
GET  /api/v1/behavior/indicators/{indicator_id}/reliability-drilldown/{symbol}
```

Safety rule:

```text
Stored indicator signal history is evidence only. Pending labels are stored for audit but excluded from reliability counts. Reliability can reduce confidence, but cannot approve trades, probability authority, OpenAlgo routing, broker routing, or live trading.
```

Indicator cache routes:

```text
POST   /api/v1/behavior/indicator-cache/save/{symbol}
GET    /api/v1/behavior/indicator-cache/status/{symbol}
GET    /api/v1/behavior/indicator-cache/results/{symbol}
DELETE /api/v1/behavior/indicator-cache/{cache_id}
```

v1.65 frontend wiring:

```text
Jarvis Evidence & Data Lab exposes Reload Status, Save Indicator Results, Force Recompute, Clear First Failed/Row, and per-row Clear Row against this route family.
These controls are cache/audit controls only and cannot enable probability authority or order routing.
```

Important groups:

```text
data
guards
timeframes
timeframes/pullback
features
candles
conditions
context
session
stock DNA and memory
pattern memory
outcomes
decision
risk
execution
validation
safety
memory quarantine
golden fixtures
9c-dna
indicator-cache
redundancy
combination-similarity
analog-research
event-sequences
confluence
design-similarity
calendar/event-regime
cross-market
corporate-abnormal
tradeability
```

## Kronos / Twin Machine

```text
GET  /api/v1/kronos/status
GET  /api/v1/kronos/models
POST /api/v1/kronos/validate-input
POST /api/v1/kronos/forecast
POST /api/v1/kronos/backtest
GET  /api/v1/twin/current
POST /api/v1/twin/analyze
GET  /api/v1/twin/reliability
```

## OpenAlgo-Safe Future Handoff (~40 routes)

Route family:

```text
/api/v1/openalgo/*
```

Major subgroups (not live broker authority):

```text
# Intent preview / export / verify
POST /api/v1/openalgo/preview-intent
POST /api/v1/openalgo/export-intent
POST /api/v1/openalgo/verify-intent
GET  /api/v1/openalgo/verify-intent/current
GET  /api/v1/openalgo/intents/pending
GET  /api/v1/openalgo/intents/{intent_id}
POST /api/v1/openalgo/intents/{intent_id}/cancel

# Executor dry-run / golden / conformance
GET  /api/v1/openalgo/executor/spec
GET  /api/v1/openalgo/executor/dry-run/current
POST /api/v1/openalgo/executor/dry-run/export
POST /api/v1/openalgo/executor/dry-run/verify
GET  /api/v1/openalgo/executor/golden-fixtures
GET  /api/v1/openalgo/executor/golden-fixtures/verify
GET  /api/v1/openalgo/executor/golden-fixtures/{fixture_id}
GET  /api/v1/openalgo/executor/golden-fixtures/{fixture_id}/verify
GET  /api/v1/openalgo/executor/conformance/current
POST /api/v1/openalgo/executor/conformance/evaluate

# Transport outbox / worker
GET  /api/v1/openalgo/transport/status
GET  /api/v1/openalgo/transport/outbox
GET  /api/v1/openalgo/transport/outbox/{delivery_id}
POST /api/v1/openalgo/transport/enqueue
POST /api/v1/openalgo/transport/outbox/{delivery_id}/deliver
POST /api/v1/openalgo/transport/outbox/{delivery_id}/retry
POST /api/v1/openalgo/transport/outbox/{delivery_id}/cancel
POST /api/v1/openalgo/transport/worker/run
GET  /api/v1/openalgo/transport/traces

# Resilience / security / reports / adapter harness
GET  /api/v1/openalgo/resilience/current
GET  /api/v1/openalgo/resilience/health-history
GET  /api/v1/openalgo/resilience/incidents
POST /api/v1/openalgo/resilience/health-sample
POST /api/v1/openalgo/resilience/fault-harness
POST /api/v1/openalgo/resilience/incidents/{incident_id}/acknowledge
GET  /api/v1/openalgo/security/posture
GET  /api/v1/openalgo/security/threat-report
GET  /api/v1/openalgo/security/trace-integrity
POST /api/v1/openalgo/report/import
GET  /api/v1/openalgo/report/imports
GET  /api/v1/openalgo/report/current/{symbol}
GET  /api/v1/openalgo/report/reality-check/current/{symbol}
GET  /api/v1/openalgo/adapter-harness/status
```

Rule:

```text
Preview/export/verify/transport routes are paper/dry-run/research safety surfaces.
They must not become direct live execution authority inside Trade Vision.
```

## TrendForge Integration (v1.86)

```text
POST /api/v1/integrations/trendforge/pull-latest
GET  /api/v1/integrations/trendforge/intakes
```

Rules:

```text
Default source is loopback-only.
Packet must verify HMAC and research-only safety envelope.
Cannot create broker orders or enable live routing.
```

Implementation: `apps/api/app/behavior/trendforge_bridge.py`.

## Knowledge Graph

```text
GET /api/knowledge/graph
```

Reads:

```text
docs/graph/project_graph.json
```

Human twin: `docs/graph.md`.

## v1.66 Golden Fixture Note

```text
GET /api/v1/behavior/replay/golden-fixtures
GET /api/v1/behavior/replay/golden-fixtures/{fixture_id}/verify
GET /api/v1/behavior/benchmark/scenario-coverage/current
```

Golden **fixtures** seeded in API (`_ensure_golden_replay_fixtures`): **16**

```text
6 legacy: golden_opening_drive … golden_expiry_pin
10 9C/chart-risk: golden_9c_clean_breakout … golden_9c_ood_unknown
   (includes golden_9c_fake_breakout)
```

Scenario **coverage families** (`REQUIRED_SCENARIO_FAMILIES`): **15** names  
(there is no separate family token `fake_breakout`; see `docs/graph.md` reconciliation note).

Scenario coverage version:

```text
behavior-scenario-coverage.v1.66
```

## v1.68 Final Audit Performance Note

```text
GET /api/v1/behavior/red-team/tv-prod-red-001
GET /api/v1/release/final-audit
GET /api/v1/release/readiness-evidence
POST /api/v1/release/candidate/export
```

The final release audit now includes blocking gate:

```text
tv_prod_red_001
```

Final audit version:

```text
tradevision-final-release-audit.v1.68
```

Performance rule:

```text
GET /api/v1/release/final-audit uses the v1.68 final-audit builder.
Repeated calls can reuse a short-lived identity-aware audit cache.
The cache cannot hide monkeypatched or changed TV-PROD-RED-001 failure evidence because dependency identities are part of the cache key.
```

## v1.69 Release-readiness Evidence Note

```text
GET /api/v1/release/readiness-evidence
GET /api/v1/release/readiness-evidence?force_refresh=true
```

The release-readiness evidence route summarizes:

```text
final audit version/status
static safety scan version/status
release manifest ID/hash/artifact count
blocking gate IDs
required missing artifacts
final-audit cache TTL
source endpoint list
```

Safety rule:

```text
The route is read-only evidence. It cannot approve live trading, create orders, export to OpenAlgo, or bypass final-audit gates.
```

## v1.70 Chart Reasoning + Volatility Regime Note

```text
POST /api/v1/behavior/chart/reasoning/analyze
GET  /api/v1/behavior/chart/reasoning/current
```

The chart-reasoning route computes:

```text
wick/body rejection index
candle acceleration
candle mass index
micro-trend slope
EMA distance and tangled-state
hidden divergence flags
oscillator exhaustion state
Hurst exponent
fractal dimension and fractal noise
ATR percentile using prior closed data
historical volatility percentile
Bollinger-width percentile
volatility regime
VCP contraction and volume dry-up
```

Safety rule:

```text
The route is closed-candle, read-only evidence. It cannot approve probability authority, paper execution, OpenAlgo export, order routing, or live trading.
```

## v1.71 Market Regime + Breadth + RS + Bayesian Note

```text
POST /api/v1/behavior/market-regime/feedback
GET  /api/v1/behavior/market-regime/feedback/current
```

The market-regime feedback route computes:

```text
market_context_status
trend_state
breadth_state
relative_strength_score
relative_strength_position
rolling_correlation_to_index
leading_lagging_state
Bayesian posterior confidence
stock_specific_edge
recent_failure_penalty
dynamic_confirmation_requirement
cooldown_active
confidence_cap
```

Safety rule:

```text
The route is read-only evidence. Missing market context caps confidence at WATCH, weak breadth or repeated failures cap confidence at WAIT, and the route cannot approve probability authority, paper execution, OpenAlgo export, order routing, or live trading.
```

## v1.84 Current Indicator Signal History Ingestion

```text
POST /api/v1/behavior/indicators/reliability/ingest-current
```

The route ingests current closed-candle 9C indicator signals into `indicator_signal_history` as pending records. It records symbol, timeframe, indicator id, signal direction, signal time, decision time, session phase, regime id, source snapshot id/hash, feature manifest version, registry version, signal value, and signal strength.

Safety rule:

```text
Current ingestion never fabricates future-horizon outcomes. Saved rows are pending-only, counted_record_count remains 0, and the route cannot approve probability authority, paper execution, OpenAlgo export, order routing, or live trading.
```

## v1.85 Pending Indicator Outcome Completion

```text
POST /api/v1/behavior/indicators/reliability/complete-pending
```

The route scans pending indicator history rows for one indicator/stock/timeframe, applies only explicitly supplied future bars, and upserts completed labels under the same history ids when the stored horizon is complete.

Safety rule:

```text
The route does not fetch or infer future candles. Incomplete supplied horizons remain pending. Same-bar target/stop collisions use conservative stop-first labeling. Completion cannot approve probability authority, paper execution, OpenAlgo export, order routing, or live trading.
```

## v1.87 Paper Guidance Spine P0

```text
POST /api/v1/paper-guidance/run
```

Request: `PaperGuidanceRequest` with explicit symbol, timeframe, `CandleSeries`,
optional decision time, evidence count, and optional research-engine requests.

Response: `ApiEnvelope[PaperTradeGuidance]`.

Pipeline:

```text
D1 safety gate -> D2 closed-candle freeze/hash -> WAIT/WATCH guidance
```

Safety:

```text
D1 failure => no snapshot and no snapshot_hash
P0 cannot return ENTER_PAPER
no entry ticket
no paper fill
no broker credentials/order
no OpenAlgo routing
no live trading
```

## v1.89-v1.97 ORB Research + Timing

```text
POST /api/v1/orb/build                      (v1.89 candidate builder)
POST /api/v1/orb/discover                   (v1.90 async combination sweep)
GET  /api/v1/orb/discover/{job_id}          (v1.90 job poll)
POST /api/v1/orb/prove                      (v1.91 walk-forward proof)
POST /api/v1/orb/playbooks/promote          (v1.91 playbook promotion)
GET  /api/v1/orb/playbooks                  (v1.91 playbook list)
POST /api/v1/orb/timing-research            (v1.97 per-stock clock-window timing batch; symbols explicit or trendforge_latest)
GET  /api/v1/orb/timing-research/jobs/{job_id}
GET  /api/v1/orb/timing-research/runs
GET  /api/v1/orb/timing-research/runs/{run_id}
GET  /api/v1/orb/timing-research/runs/{run_id}/export.csv
```

The v1.97 timing-research batch backtests the requested clock windows
(default 09:15-09:20 / 09:15-09:30 / 09:15-09:35 / 09:15-09:40) per stock on
HSTRY history via the untouched v1.90 discovery engine, persists runs to
`orb_timing_runs`/`orb_timing_rows`, and writes JSON/CSV/MD exports under
`data/orb_research/`.

Safety rule:

```text
All ORB timing research is research-only: research_only=true, trade_allowed=false,
order_routing_enabled=false, live_trading_blocked=true on every job, result, and export.
Playbook promotion (trading-adjacent) remains a separate explicit action.
No broker credentials, orders, or OpenAlgo routing exist on these surfaces.
```
