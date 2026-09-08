# M3.1 AGI-Reasoning Audit — Source Reference

**Date:** 2026-09-08  
**Branch:** `m3-1-semantic-hardening-audit`

This file preserves the provenance of the user-supplied reference text used to drive the M3.1.1 semantic-hardening work.

## Source attachment

- Original uploaded filename: `After re-verifying the actual M3.1.txt`
- SHA-256: `824acd661a02cb77f463483bd6ac4cd66dadd2940b6003e1d377a9727c98c8ef`
- Source size: 23,701 bytes
- Source lines: 1,429

## Canonical repository interpretation

The repository-ready analysis derived from that reference is preserved in:

- `docs/M3_1_SEMANTIC_INTELLIGENCE_REVERIFY_AND_HARDENING_PLAN_2026-09-08.md`
- initial audit commit: `45031c250693bf91c1fa1c3a80acbd36a933430d`

The source reference and the canonical plan establish these non-negotiable design principles:

1. M3.1 remains a locked causal/provenance baseline; semantic upgrades run in shadow mode first.
2. Raw facts are calculated once from the approved D2 closed-candle snapshot.
3. Every downstream claim must distinguish `OBSERVED`, `DERIVED`, `INFERRED`, `HYPOTHESIS`, and calibrated `PREDICTIVE` evidence.
4. Missing/unknown/unavailable evidence must never be silently converted to neutral numeric evidence.
5. Heuristic scores are not probabilities unless backed by PIT-safe calibration and out-of-sample validation.
6. OHLCV-derived market-structure concepts are explicitly labeled as proxies/candidates when intent cannot be observed directly.
7. Correlated indicators must not inflate independent confluence.
8. Competing hypotheses, contradiction tracking, expected observations, falsification, OOD detection, and abstention are the target reasoning pattern.
9. D6 remains the sole final-band authority.
10. No execution authority is introduced.

## Implementation sequence

```text
D2 CLOSED-CANDLE SNAPSHOT
        |
        v
MARKET PRIMITIVE KERNEL v2
        |
        +--> MORPHOLOGY FACTS
        +--> LEVEL GRAPH FACTS
        +--> VOL/STATE FACTS
        +--> STRUCTURE PROXIES
        +--> INDICATOR DAG FACTS
        |
        v
EPISTEMIC EVIDENCE GRAPH
        |
        +--> M3.2 CONTEXT
        +--> M3.3 MEMORY / CALIBRATION
        |
        v
HYPOTHESIS + FALSIFICATION ENGINE
        |
        v
SCENARIO / UNCERTAINTY / ABSTENTION
        |
        v
D6 ONLY
```

This file is a provenance pointer, not a replacement for the detailed hardening plan.