# ORB opening-sequence source-of-truth map

Verified planning/reference base: `29e9e126401a512c13743871206c2ee6b22772b3`.
Source change: `ORB_BUILD_CHANGE.txt` at `8ba2de96c875b02defe8f3645acbf82584f830b8`, blob `cde19d0859cc84a87f4672a58e218cea84401b61`.
BUILD-4 full-plan source: plan branch `9ca03ef6a988e0c16a6d8260c169ba144894f87b`, blob `43cae9fa59fe9375271f34a2f7398507430f76c6` before reconciliation.

## Canonical owners to reuse

| Fact/capability | Observed owner | B4 opening-sequence use | Duplicate to avoid |
|---|---|---|---|
| closed causal candles | D2 / Decision Spine closed-candle snapshot + `snapshot_feature_kernel.py` | consume exact closed-prefix identity/hash | new raw candle authority or future-inclusive resampling |
| candidate identity/provenance | `apps/api/app/orb/candidate_intake.py` | bind candidate/source/selection identity | ticker-only or reconstructed identity without provenance |
| venue/session/contract/calendar/price rules | `apps/api/app/orb/market_identity/**` | bind exact session, contract, calendar and price basis | hard-coded NSE/commodity clocks, weekday expiry guesses |
| prior completed session | `apps/api/app/orb/prior_session/**` | consume PDH/PDL/session-close/settlement typed references | calendar-day resampling; close-for-settlement substitution |
| candle anatomy / mean-range normalization | `apps/api/app/behavior/candle_anatomy.py` + `decision_spine/snapshot_feature_kernel.py` | consume canonical anatomy; preserve basis/version | renaming historical `range_atr` to Wilder ATR |
| canonical price/level/context facts | M3.1/M3.2 Decision Spine modules | compose receipts and event tuples | new level/VWAP/ATR/CPR source-of-truth inside B4 view |
| memory/analogues | M3.3 `canonical_memory_*`, `canonical_analog_memory.py`, `canonical_pattern_memory.py`, `canonical_nine_candle_memory.py`, `m3_3_memory_wiring.py` | canonical first historical retrieval; zero-authority receipts | direct STUMPY/DTW-first replacement or mock memory |
| final band authority | `decision_spine/authority_registry.py` | no final authority; evidence only | B4 final band, BUY/SELL, execution authority |

## Existing useful implementation evidence, not new canonical ownership

- `apps/api/app/orb/context.py` contains legacy/compatibility gap, CPR, Wilder ATR and session classification calculations. BUILD-3 now explicitly owns raw prior-session facts and says derived ATR/CPR/patterns stay with canonical owners. B4 must not clone this path.
- `apps/api/app/orb/core.py` already distinguishes locked opening range and post-range bars and carries deterministic source/session hashes. It is a protected legacy runtime surface for feature-OFF parity, not the owner of the new sequence view.
- `apps/api/app/orb/timing_research.py`, `discovery.py`, and `proof.py` provide existing timing/discovery/proof infrastructure and deterministic research receipts. BUILD-5/B8 should reuse/extend these seams rather than move timing/value proof into B4.
- `apps/api/app/orb/adaptive/**` provides strong examples of causal prefix validation, research-only outputs, deterministic replay, chronological holdout proof and bounded scenario evidence. It also contains fixed feature-minute/range choices, Wilder-ATR-normalized features and research thresholds, so those remain evidence/reference or later-stage research rather than B4 canonical truth.
- `adaptive/source_scenarios.json` explicitly marks scenario rules `PROPOSED_UNVERIFIED` and default probabilities null; they are not canonical thresholds/probabilities.

## Legacy surfaces to quarantine, not delete in this documentation campaign

1. Direct recalculation in `orb/context.py` when a newer canonical owner exists.
2. `adaptive/features.py` / variants thresholds and 3m/5m feature-policy choices as B5/B7/B8 research inputs, not B4 constants.
3. Older strategy-memo execution commands (broker/margin/flatten) as historical/out-of-scope for ORB authority.
4. Old context-native fail-open semantics as superseded by explicit missingness/fail-closed authority rules.
5. Any legacy `trap_probability` or heuristic confidence number as non-calibrated historical output, not a BUILD-12 probability.

## Future seam needed

`apps/api/app/orb/context_intelligence/opening_sequence.py` is the candidate B4-F seam. It should compose immutable canonical inputs into `OrbOpeningSequenceViewV1`, emit deterministic event tuples plus exact formation/OR-lock identity, and carry `authority=NONE`, `may_execute=false`, `may_set_final_band=false`.

No runtime file is created or modified by this reconciliation campaign.