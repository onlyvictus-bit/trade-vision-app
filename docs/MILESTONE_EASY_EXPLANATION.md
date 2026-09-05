# Trade Vision Easy Explanation

Last verified: 2026-07-24

## Current Status

```text
latest_completed_version = v1.94 - ORB Paper Lifecycle Feedback
latest_functional_version = v1.94
latest_full_backend_regression = v1.94, 2026-07-24, 715 passed
latest_focused_backend_verification = v1.94 32 passed; v1.92-v1.94 54 passed
latest_ui_verification = v1.94 typecheck/build + RELIANCE browser click-through passed
current_mode = research / mock / paper-review only
live_trading = blocked
```

v1.87-v1.94 create the safe ORB paper-guidance flow:

1. D1 checks that the data and system are safe.
2. If D1 fails, the answer is WAIT and no snapshot is created.
3. If D1 passes, D2 freezes only fully closed candles.
4. D2 creates a fingerprint (`snapshot_hash`) of those exact candles.
5. The output explains what ran and what was skipped.
6. ORB proposes the main setup and D6 decides whether it remains WAIT/WATCH or
   can become an eligible paper candidate.
7. A local simulated record requires an eligible stored ticket and explicit
   human approval.
8. An explicit replay action may simulate a local fill and outcome from future
   closed candles; it never claims a broker fill.
9. Completed, integrity-valid outcomes build a separate ORB reliability report.
10. Feedback can reduce/quarantine trust but cannot approve or route a trade.

This matters because every future engine must analyze the same frozen candles.
It prevents one engine from seeing a developing candle while another sees a
closed candle, and it makes the result reproducible later.

Current downloaded RELIANCE result is `WATCH / NO_PLAYBOOK`: MTF is aligned,
but no proof-backed playbook exists and evidence is `0/30`, so record and
lifecycle buttons are correctly disabled.

## What Trade Vision Does In Simple English

Trade Vision is a research cockpit for trading decisions. It does not blindly say buy or sell. It gathers chart, candle, indicator, replay, historical memory, safety, and optional external-AI evidence, then explains whether the operator should:

```text
WAIT
WATCH
PAPER-CANDIDATE
NO TRADE
FAKEOUT WARNING
AVOID CHOP
```

It does not place live orders.

## Main Parts

| Part | Input Needed | How It Processes | What It Gives | How It Helps Trading |
|---|---|---|---|---|
| System Mode | none | Locks app to safe mode | mock/paper-review status | Prevents fake/live confusion |
| Kill Switch | operator action | blocks order-path surfaces | armed/triggered state | Emergency safety boundary |
| Time Provider | backend clock | uses backend-owned time | consistent timestamps | Replay and PIT safety |
| Data Quality | candles/OHLCV | checks gaps, bad candles, invalid values | data-quality result | Avoids false signals from bad data |
| Point-in-Time Guard | candles/features | blocks future leakage | safe/blocked evidence | Prevents backtest cheating |
| Feature Registry | indicator/feature metadata | versions feature definitions | reproducible features | Explains which calculations were used |
| Indicator Registry | indicator metadata | tracks purpose and delay metadata | indicator feature map | Foundation for all-indicator intelligence |
| Indicator Intelligence | every indicator contract | classifies purpose, failure modes, reliability, lag | trusted indicator reasoning | Prevents blind indicator stacking |
| Lag-Aware Voting | `confirmation_delay_bars` | downweights late indicators | delay-adjusted vote | Stops MACD/MA late confirmation from over-promoting a setup |
| Full Timeframe Contract | `1m, 3m, 5m, 15m, 30m, 1H, 4H, daily, weekly` | recalculates closed-bar context per timeframe | nine-timeframe MTF evidence | Prevents missing 30m/4H context from weakening decisions |
| 9C DNA | last 9 closed candles | builds candle/indicator/context vector | current setup fingerprint | Finds similar historical situations |
| Pattern Memory | historical setups | compares winners/failures | analog evidence | Shows what happened before |
| Session Memory | time of day/week | learns stock-specific behavior windows | session edge/warning | Avoids lunch chop/opening fakeout traps |
| Replay | seed/session | deterministic playback | repeatable evidence | Debugs logic safely |
| Replay Evidence | snapshots/archive/features | explains reproducibility | evidence cards | Shows why replay result can be audited |
| Research Chart | candle data | chart/indicator display | visual trading screen | Lets user inspect candles, indicators, entry/SL/target |
| Jarvis Room | combined evidence | assembles decision packet | explanation and blockers | One place to read decision reasoning |
| Gemini/Grok Review | verified packet only | external AI reviews evidence | side-by-side text response | Adds review without giving control |
| Kronos/Twin | candle forecast prior | compares forecast with behavior engine | agreement/conflict | Forecast is one vote, not boss |
| OpenAlgo Handoff | safe paper intent | verifies dry-run/paper boundary | preview/export checks | Future executor boundary without live authority |
| Safety Invariants | all decision evidence | applies hard gates | WAIT/block when unsafe | Capital protection before confidence |
| Release-readiness Evidence | final audit/safety scan/manifest | summarizes release proof into one packet | ready/blocked evidence state | Lets operator verify release evidence without hunting across routes |

## Current Meaning

Trade Vision currently gives a strong research/paper-review foundation:

- system safety status
- replay evidence
- Jarvis decision room
- chart/research surfaces
- behavior intelligence endpoints
- indicator cache and 9C route families
- Gemini/Grok review surfaces
- Kronos/Twin surfaces
- OpenAlgo-safe handoff checks
- context files for future AI/chat continuation

## What It Does Not Do

It does not:

- trade live
- create live broker credentials
- route live orders
- let external AI override risk
- let Kronos override no-trade
- use browser cookies/session capture
- trust missing indicators as zero
- trust lagging indicators as fresh confirmation

## How A New AI Should Continue

Start here:

```text
TRADE_VISION_README.md § AI / New-Chat Handoff
docs\FILE_DOCUMENT_INDEX.md §0.6
docs\IMPLEMENTATION_STATUS.md
docs\NEXT_BUILD_TARGET.md
docs\SAFETY_INVARIANTS.md
```

Then open source files only as needed.

## Next Useful Build Direction

Recent completed builds:

```text
v1.63 - Real MTF Pullback Engine
v1.64 - Indicator Result Cache Completion
v1.65 - Indicator Cache Frontend Controls
v1.66 - Golden Fixture Regression Pack
v1.67 - TV-PROD-RED-001 Final Red-Team Gate
v1.68 - Performance and Latency Budget Hardening
v1.69 - Release-readiness Evidence Refresh
v1.70 - Chart Reasoning + Volatility Regime
v1.71 - Market Regime + Breadth + RS + Bayesian
v1.72 - Market Structure + Liquidity Engine
v1.73 - Execution + Event + OI Risk Guard
v1.74 - Post-Entry Lifecycle Manager
v1.75 - Final Confluence Conflict Arbiter
v1.80 - Indicator Intelligence Contract + Ontology + Lag-Aware Voting
v1.81 - Per-Indicator Reliability Memory + Outcome Labeling Bridge
v1.82 - Full Timeframe Contract Expansion + Indicator Reliability UI Drilldown
```

Easy meaning:

```text
Trade Vision now has separate reports for closed-candle chart/volatility context, market/breadth/relative-strength context, market-structure/liquidity context, execution/event/OI risk context, post-entry lifecycle context, final conflict resolution, indicator ontology, indicator reliability, and full nine-timeframe support. The newest v1.82 packet makes 30m and 4H first-class backend timeframes and exposes reliability drilldown fields for trading review.
```

What it gives:

```text
WAIT / WATCH / AVOID
pullback state
higher-timeframe direction
lower-timeframe pullback timeframes
opposition timeframes
simple trader summary
research-only safety gates
indicator cache hit/miss state
cache artifact identity
safe cache cleanup controls
16 golden replay scenarios
expanded scenario coverage families
TV-PROD-RED-001 final release gate
short-lived final-audit cache
faster repeated Jarvis/release audit reads
release-readiness evidence state
final-audit/safety-scan/manifest alignment
blocking release gate list
wick/body rejection index
candle acceleration
EMA tangled-state
Hurst/fractal noise
ATR/HV/BB-width percentile
volatility regime
VCP contraction and volume dry-up
market context status
trend and breadth state
relative strength score and position
Bayesian posterior confidence
stock-specific edge
cooldown after repeated failures
Volume Profile POC/VAH/VAL/HVN/LVN
TPO value area and single prints
VSA effort/result state
liquidity sweep direction
order-block and fair-value-gap zones
BOS/CHoCH state
Wyckoff spring/UTAD/LPS context
fill probability
spread/slippage/impact risk
liquidity grade
single-wick entry risk
gap-through-entry risk
event risk score
expected-move cap
gamma wall and max-pain context
post-entry trade state
breakeven/current stop
simulated partial exit
trailing stop
thesis weakening reason
invalidation trigger
add-on block
trap score and stop-hunt score
```

The practical next build is:

```text
v1.73 - Execution + Event + OI Risk Guard
```

The important future indicator roadmap is:

```text
v1.76 - Full Indicator Intelligence Ontology (requirement heritage; implemented by v1.80)
v1.77 - Indicator Reliability Memory (requirement heritage; implemented by v1.81)
v1.78 - Sequential Indicator Causality Engine (preserve existing event_sequence_mining.py wiring)
v1.79 - Indicator Conflict and Redundancy Arbiter (preserve existing redundancy/confluence wiring)
v1.80 - Indicator Intelligence Contract + Ontology + Lag-Aware Voting
v1.81 - Per-Indicator Reliability Memory + Outcome Labeling Bridge
v1.82 - Full Timeframe Contract Expansion + Indicator Reliability UI Drilldown
```

Easy meaning:

```text
v1.80 teaches Trade Vision what each indicator is for, when it is late, and when it can lie.
v1.81 checks history to learn whether each indicator actually works for this stock, timeframe, session, and regime.
v1.82 makes 30m and 4H part of the same backend contract as the other timeframes and exposes reliability details for UI drilldown.
```

The most important missing implementation rule preserved in the plan:

```text
confirmation_delay_bars must be used as vote weight.
Late indicators can explain, but cannot create false confidence.
```

Current implemented update:

```text
v1.82 is now implemented at backend level and full-regression verified.
It expands timeframe support and exposes reliability drilldown data, but persistent real indicator-label storage and dedicated React card verification are still future work.
```
