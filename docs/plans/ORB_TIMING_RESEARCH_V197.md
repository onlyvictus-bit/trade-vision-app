# ORB Timing Research v1.97 — Approved Build Spec

> **Status:** Approved 2026-08-25 (user locked: v1.97 · 5m sweep + 1m top-20 · full panel · daily TrendForge watchlist)
> **Parent plan:** `ORB_RESEARCH_ENGINE_PLAN.md` — this builds its remaining slice (§3.4 "Best clock window" report + §4 "Multi-symbol leaderboard")
> **Question answered:** per stock, which opening-range end wins intraday — **09:20, 09:30, 09:35, or 09:40?**
> **Safety:** research-only. Every response carries `research_only=true, trade_allowed=false, live_trading_blocked=true`. Playbook promotion is a separate future approval.

## 1. Locked decisions

| Decision | Value |
|---|---|
| Version | v1.97 (v1.96 = Indicator Catalog; v1.95 reserved/proposed) |
| Sweep timeframe | 5m on all requested symbols; 1m refinement on top-20 by composite |
| Clock windows (default) | (09:15→09:20), (09:15→09:30), (09:15→09:35), (09:15→09:40) — editable per run |
| Strategy families | orb_breakout, orr_reversal, hybrid_orb (honest comparison) |
| Grids | reward_risk [1,2,3] × volume_confirmation [False,True] → 4 windows × 3 families × 3 RR × 2 vol = **72 combos/symbol** |
| Symbol source | `explicit` (user list) or `trendforge_latest` (READY/PRIORITY_RADAR from latest accepted intake) |
| Universe data | `C:\Users\sakth\Downloads\HSTRY\{SYMBOL}_NSE_{tf}.csv` — ~90 NSE symbols, 2015→ present, format `date,time,open,high,low,close,volume,oi` (IST wall time) — **format pre-verified on RELIANCE / M_M / BAJAJ-AUTO** |
| UI | Research-tab "ORB Timing Lab" panel |

## 2. Architecture (additive only — v1.90 engine untouched)

```text
HSTRY CSV → hstry_csv.load_hstry_series(symbol, tf, start_date)   [NEW]
          → CandleSeries (epoch ns UTC, session 09:15–15:30, closed bars)
          → orb.discovery.run_orb_discovery(request)               [EXISTING v1.90 — no math changes]
                clock_windows=4, families=3, RR×vol grids, costs, no-lookahead OR lock
          → timing_research per-window extraction                  [NEW]
          → aggregate_leaderboard (per-stock best netR / best consistency / composite;
                                   universe verdict incl. NO_SIGNIFICANT_DIFFERENCE)
          → checkpoint after each symbol (resumable)               [NEW]
          → storage tables + data/orb_research/ exports            [NEW, M2]
          → API routes + Research panel                            [NEW, M3]
          → real daily run                                         [M4, needs user's stock list]
```

## 3. New files

| File | Content |
|---|---|
| `apps/api/app/orb/hstry_csv.py` | `load_hstry_series(symbol, timeframe="5m", start_date=None, base_dir=None)`; tf alias map (`03m`→`3m`, `1h`→`1H`, `4h`→`4H`); IST wall time → UTC epoch ns; raises `HstryCsvNotFound` |
| `apps/api/app/orb/timing_research.py` | Request/job models, `submit/run/get` job trio (pattern: `discovery.py:32-71`), `run_timing_research()`, `aggregate_leaderboard()`, checkpoint/resume |
| `apps/api/tests/test_orb_timing_v197.py` | Gates ORB-T197-001..010 |
| `data/orb_research/` | `{run_id}.json`, `leaderboard.csv` (byte-stable), `summary.md` per-stock cards |
| models.py additions | `OrbTimingResearchRequest`, `OrbTimingWindowRow`, `OrbTimingLeaderboardEntry`, `OrbTimingResearchResult` |
| storage.py additions | `orb_timing_runs`, `orb_timing_rows` tables + save/list functions |
| main.py routes | `POST /api/v1/orb/timing-research` (submit), `GET .../jobs/{id}`, `GET .../runs`, `GET .../runs/{id}/export.csv` |
| web | `client.ts` API fns + App.tsx Research-tab panel |

## 4. Speed & efficiency

- 5m default: ~2,700 sessions × 72 combos/symbol ≈ 30–90 s/symbol; watchlist (10–20) ≈ 6–30 min sequential
- `start_date` bound (default last 3 years) to cut dead history
- Checkpoint after each symbol → crash-resume, no recompute
- Optional bounded `max_workers` (default 1)
- 1m refinement only for top-20 composite symbols

## 5. Test gates

| Gate | Proves |
|---|---|
| ORB-T197-001 | loader tz round-trip: CSV wall time → correct epoch ns |
| ORB-T197-002 | session filter 09:15–15:30 + tf alias mapping + missing-file error |
| ORB-T197-003 | aggregator matches hand-computed fixture (winner, consistency, no-diff state) |
| ORB-T197-004 | checkpoint resume skips completed symbols |
| ORB-T197-005 | persistence round-trip (save run + rows → list → identical) |
| ORB-T197-006 | export CSV byte-stable across two generations |
| ORB-T197-007 | no_future_leakage propagated on every row; research-only flags on result |
| ORB-T197-008 | minimum_trades guard → window marked insufficient, never fabricated |
| ORB-T197-009 | API routes: submit→poll→result envelope; research-only flags |
| ORB-T197-010 | FRONTEND_PANEL_MAP + API_ENDPOINT_INDEX entries exist |

## 6. Milestones & doc-sync protocol

M0 this spec → M1 loader+engine (gates 001-004) → M2 persistence+exports (005-007) → M3 API+panel (008-010) → M4 real run on user's daily list → M5 analysis + judge.

After EVERY milestone: `IMPLEMENTATION_STATUS.md` tip, `TEST_ID_INDEX.md`, and at campaign close: `API_ENDPOINT_INDEX.md`, `FRONTEND_PANEL_MAP.md`, `FILE_DOCUMENT_INDEX.md`, `ARCHITECTURE.md` version section, `docs/graph/project_graph.json` (zero dangling), `NEXT_BUILD_TARGET.md` refresh.
