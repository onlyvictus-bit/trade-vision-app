# Trade Vision Safety Invariants

Last reviewed: 2026-07-21

Companion: `docs/context.md` (INV-* table). TrendForge intakes must also prove research-only safety envelopes (v1.86).

These rules are non-negotiable.

## Execution Authority

```text
Trade Vision does not place live broker orders.
Trade Vision does not create broker credentials.
Trade Vision does not enable hidden order routing.
OpenAlgo is an external future execution system, not Trade Vision execution authority.
```

## Decision Authority

```text
Trade Vision Behavior Engine = memory/risk/no-trade authority.
Kronos = research forecast prior/scenario generator only.
Gemini/Grok = external review/display only.
OpenAlgo report = imported evidence/reality check only.
No external AI can override risk, no-trade, kill switch, stale evidence, or low evidence.
```

## Data And Evidence

```text
No future candle data may enter decision-time features.
Incomplete higher-timeframe candles cannot be used as closed evidence.
Missing indicator values must be masked, not treated as zero.
Cached indicator results are speed artifacts, not authority.
Evidence must be hash-bound when exported or reviewed externally.
```

## Indicator Intelligence

```text
Every trusted indicator needs an Indicator Intelligence Contract.
Correlated indicators count as one evidence group.
confirmation_delay_bars must reduce late indicator voting power.
Lagging indicators may explain but cannot alone promote WAIT to WATCH or WATCH to PAPER-CANDIDATE.
Future-pivot indicators remain explanation-only until causally confirmed.
```

## Safety Outputs

Allowed high-level outputs:

```text
WAIT
WATCH
PAPER-CANDIDATE
NO TRADE
FAKEOUT WARNING
AVOID CHOP
```

Forbidden outputs:

```text
LIVE BUY
LIVE SELL
AUTO EXECUTE
ROUTE ORDER
IGNORE RISK
IGNORE LOW EVIDENCE
```

## Test Requirement

Every new route or panel that touches decision evidence must prove:

```text
live_trading_blocked = true
order_routing_enabled = false
trade_allowed = false unless explicitly research/paper flag only
no_future_leakage = true where applicable
```

