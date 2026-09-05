# Frontend Panel Map

Last reviewed: 2026-07-24

Purpose: locate UI surfaces without reading the whole frontend.  
**2-minute operator map (screen → button → API + brain):** `ARCHITECTURE.md` § **OPERATOR MAP**.

## Main Frontend Shell

```text
apps/web/src/App.tsx
```

Responsibilities still present:

- workspace routing
- backend data loading
- replay control handlers
- Jarvis/research/behavior workspace composition
- chart/replay UI integration

## Extracted Components

| Component File | Surface |
|---|---|
| `apps/web/src/components/primitives.tsx` | shared metric/panel/status primitives |
| `apps/web/src/components/aiCredentialsPanel.tsx` | Gemini/Grok credential vault panel |
| `apps/web/src/components/safetyPanels.tsx` | safety display panels |
| `apps/web/src/components/workspaces/referenceWorkspaces.tsx` | reference workspaces |
| `apps/web/src/components/workspaces/systemWorkspace.tsx` | System workspace |
| `apps/web/src/components/workspaces/replayEvidencePanels.tsx` | Replay evidence display panels |

## High-Value User-Facing Areas

| Area | Purpose |
|---|---|
| Jarvis Decision Room | combined evidence, external AI review, OpenAlgo-safe intent preview, blocker display |
| Research | chart/replay/indicator analysis workbench |
| Behavior | behavior intelligence, 9C, analogs, memory, safety reports |
| Replay | deterministic replay controls and evidence cards |
| System | credential status, system health, storage/status panels |

## Recent Behavior Panel Additions

| Panel | Source Contract | Endpoint |
|---|---|---|
| Real MTF Pullback v1.63 | `RealMtfPullbackReport` | `/api/v1/behavior/timeframes/pullback/current` |
| Indicator Result Cache v1.65 | cache status/results/delete envelopes | `/api/v1/behavior/indicator-cache/*` |
| Full-Timeframe Feature Runtime v1.82 | `SevenTimeframeFeatureRuntimeReport` | `/api/v1/behavior/features/seven-timeframe/current` |
| Indicator Reliability Drilldown v1.82 | `IndicatorReliabilityReport` | `/api/v1/behavior/indicators/si_macd_ta/reliability/RELIANCE` |
| Persistent Indicator Signal History v1.83 | `IndicatorSignalHistorySummary` | `/api/v1/behavior/indicators/si_macd_ta/signal-history/RELIANCE` |
| Indicator Reliability Drilldown v1.83 | drilldown envelope with reliability/history | `/api/v1/behavior/indicators/si_macd_ta/reliability-drilldown/RELIANCE` |
| ORB Paper Guidance v1.92 | `PaperTradeGuidance` + `OrbGuidanceTicket` | `POST /api/v1/paper-guidance/run` |
| Simulated ORB Paper Ledger v1.93 | `SimulatedPaperTradeRecord[]` | `/api/v1/paper-guidance/paper-records` |
| ORB Paper Lifecycle v1.94 | `SimulatedPaperLifecycleOutcome[]` | `/api/v1/paper-guidance/paper-records/observe`, `/paper-outcomes` |
| ORB Reliability + Store Health v1.94 | `OrbPaperReliabilityReport`, `PaperGuidanceStorageMonitor` | `/orb-reliability/{playbook_id}`, `/storage-monitor` |
| ORB Timing Lab v1.97 (Research tab) | `OrbTimingResearchJob` + `OrbTimingResearchResult` leaderboard | `POST /api/v1/orb/timing-research`, `GET .../jobs/{id}`, `GET .../runs/{id}/export.csv` |

v1.82 note:

```text
The legacy seven-timeframe route/panel ID remains for compatibility, but the backend payload now includes:
1m, 3m, 5m, 15m, 30m, 1H, 4H, daily, weekly
```

v1.83 note:

```text
Trade Decision Room now has `Indicator Reliability Drilldown v1.83`. It shows history source, persisted rows, counted samples, lag weight, reliability multiplier, fixture fallback, and latest stored labels. It is display-only and cannot approve trades.
```

v1.84 note:

```text
The v1.83 reliability card now includes an `Ingest Current Signals` action. It calls POST /api/v1/behavior/indicators/reliability/ingest-current, stores current closed-candle indicator signals as pending history rows, refreshes the card, and does not count those rows toward reliability until a later completed outcome label exists.
```

v1.85 note:

```text
Backend panel map now includes `Indicator Pending Outcome Completion v1.85`. This is a contract/API surface for completing pending indicator rows from explicitly supplied future bars. It is not exposed as a casual trader button because completion requires a verified future-bar payload.
```

v1.92-v1.93 note:

```text
Trade Decision Room places `ORB Paper Guidance` directly after the Trader
Decision Brief. It loads downloaded RELIANCE 1m data, derives only complete
NSE-session 5m/15m/1H candles, and shows ORB levels, entry/stop/target, MTF,
proof, liquidity, and blockers. `Record Simulated Paper` remains disabled until
the exact server ticket is eligible and requires explicit human confirmation.
```

v1.94 note:

```text
The same ORB panel now reserves an explicit +3/+6/+12 closed-candle replay
horizon. After an eligible paper record exists, `Evaluate Replay Result`
calculates a deterministic local simulated outcome with costs, MFE/MAE, and
conservative stop-first ambiguity. The panel also shows completed-only ORB
reliability and atomic-store integrity. No control routes an order.
```

v1.86 note (TrendForge — **no dedicated trader UI panel**):

```text
Signed TrendForge research intake is an API/integration surface only:
  POST /api/v1/integrations/trendforge/pull-latest
  GET  /api/v1/integrations/trendforge/intakes
There is no casual frontend "pull TrendForge" trade button and no order-routing control.
Intakes are research/audit evidence; live trading remains blocked.
```

## Recent Jarvis Evidence Controls

| Control | Purpose | Safety Rule |
|---|---|---|
| Reload Status | refresh cache status/results after an operation | read-only |
| Save Indicator Results | persist current reference indicator artifacts | cannot enable probability/trading |
| Force Recompute | rebuild artifacts for the same symbol/timeframe identity | cannot bypass manifest/hash checks |
| Clear First Failed / Row | bounded cleanup of one cache row | no broad clear-all action |
| Clear Row | explicit per-row delete | cache cleanup only |

## UI Rule

New trading-decision features should not become essay-only panels. They should show:

```text
chart/evidence
pattern state
indicator alignment
entry / stop / target / invalidation
WAIT/WATCH/PAPER-CANDIDATE state
blocking reason
confidence and evidence quality
```

## v1.87 Paper Guidance UI Status

v1.87 P0 is backend-only. It adds no new panel and removes no existing panel.
The typed endpoint is ready for the planned v1.89 primary Jarvis card after
v1.88 connects D3a-D6 decision evidence.

Future card rule:

```text
one primary band
snapshot identity/hash
reason for / against
blockers and low-evidence cap
entry/stop/target only when a later approved stage can produce them
drill-down for engine evidence
never expose an execution control from the P0 contract
```
