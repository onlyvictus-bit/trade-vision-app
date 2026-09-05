"""
research.engine.runner — Discovery orchestrator
=================================================
Fetches data → pre-computes signals → generates combos → backtests
each across R:R ratios → scores → stores top results.

Key capabilities
----------------
* ``sweep_params=False``  — uses each signal's default params (fast, ~4700 combos)
* ``sweep_params=True``   — Cartesian-product of each signal's param_grid, capped
                            at ``max_param_combos`` per signal combo (for grid search)
* ProcessPoolExecutor for CPU-bound VectorBT on large combo sets
  (falls back to ThreadPoolExecutor if pickling fails on Windows)
"""
from __future__ import annotations

import itertools
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from research.signals import registry
from research.engine.combinator import generate_combos
from research.engine.backtester import BacktestResult, run_vectorbt_backtest, run_vectorbt_backtest_batch
from research.engine.risk_matrix import build_risk_pairs, parse_rr_ratios
from research.engine.scorer import compute_composite_score, rank_metric_value
from research.data.local_loader import load_ohlcv_file
from research.data.mtf_loader import fetch_mtf_data, align_mtf_data
from research.data.validator import validate_ohlcv
from research.data.corporate_actions import detect_possible_splits
from research.validation.gates import rankable_only
from research.validation.oos_split import split_train_validation_holdout
from research.validation.fdr import benjamini_hochberg
from research.validation.cost_stress import cost_scenarios
from research.validation.slippage_model import atr_slippage_pct
from research.advanced.monte_carlo import monte_carlo_trades
from research.advanced.sensitivity import neighbor_params, sensitivity_flag
from research.advanced.regime import adx_regime
from research.ml.features import build_feature_matrix
from research.ml.gate import MLGate
from research.ml.labeler import label_tp_before_sl
from research.ml.selector import train_and_select
from research.filters import RegimeFilter, build_filter_masks, DEFAULT_FILTER_CONFIG


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_ohlcv(symbol: str, start: str, end: str, interval: str = "1d", data_path: str | None = None) -> pd.DataFrame:
    if data_path:
        return load_ohlcv_file(data_path, start=start, end=end)
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)
    if df.empty:
        raise ValueError(f"No data for {symbol} ({start}→{end}, {interval})")
    df.columns = [c.lower() for c in df.columns]
    return df


# ── Param-grid expansion ──────────────────────────────────────────────────────

def _expand_signal_params(signal_name: str) -> List[Dict[str, Any]]:
    """
    Return a list of param dicts for ``signal_name`` by expanding its param_grid.
    If the signal has no param_grid, returns the default params as a single item.
    """
    sig = registry.get(signal_name)
    if not sig or not sig.param_grid:
        return [sig.params if sig else {}]

    keys = list(sig.param_grid.keys())
    values = [sig.param_grid[k] for k in keys]
    base = dict(sig.params)  # defaults as fallback values

    combos = []
    for vals in itertools.product(*values):
        p = dict(base)
        p.update(dict(zip(keys, vals)))
        combos.append(p)
    return combos or [base]


def _iter_param_combos(
    combo_names: Tuple[str, ...],
    max_param_combos: int = 50,
) -> List[Dict[str, Dict[str, Any]]]:
    """
    For a tuple of signal names return a list of {signal_name: params} dicts
    representing all param combinations (Cartesian product), capped at
    ``max_param_combos`` to prevent combinatorial explosion.
    """
    per_signal_params = [_expand_signal_params(name) for name in combo_names]
    all_combos = list(itertools.product(*per_signal_params))

    if len(all_combos) > max_param_combos:
        # Uniform stride sampling to stay within cap
        step = max(1, len(all_combos) // max_param_combos)
        all_combos = all_combos[::step][:max_param_combos]

    return [
        {name: combo_names[i] and params_list[i]
         for i, (name, params_list) in enumerate(zip(combo_names, combo))}
        for combo in all_combos
    ]


def _build_param_variants(
    combo_names: Tuple[str, ...],
    sweep_params: bool,
    max_param_combos: int,
) -> List[Dict[str, Dict[str, Any]]]:
    """Return list of {signal_name: params} dicts to test for this combo."""
    if not sweep_params:
        # Just default params — one variant
        return [{name: registry.get(name).params for name in combo_names}]

    per_signal = [_expand_signal_params(name) for name in combo_names]
    all_combos = list(itertools.product(*per_signal))
    if len(all_combos) > max_param_combos:
        step = max(1, len(all_combos) // max_param_combos)
        all_combos = all_combos[::step][:max_param_combos]

    return [
        {combo_names[i]: pset for i, pset in enumerate(combo)}
        for combo in all_combos
    ]


def _slice_context(context_dfs: Dict[str, pd.DataFrame] | None, index: pd.Index) -> Dict[str, pd.DataFrame] | None:
    if not context_dfs:
        return None
    return {tf: df.reindex(index) for tf, df in context_dfs.items()}


def _compute_entries_for_candidate(
    df: pd.DataFrame,
    combo_names: Tuple[str, ...],
    signal_params: Dict[str, Dict[str, Any]],
    context_dfs: Dict[str, pd.DataFrame] | None = None,
) -> pd.Series:
    idx = df.index
    arrays = []
    for name in combo_names:
        sig = registry.get(name)
        computed = sig(df, overrides=signal_params.get(name, {}), context_dfs=context_dfs)
        arrays.append(computed.reindex(idx, fill_value=False).to_numpy(dtype=bool, copy=False))
    if not arrays:
        return pd.Series(False, index=idx)
    return pd.Series(np.logical_and.reduce(arrays), index=idx)


def _equity_returns(result: BacktestResult) -> List[float]:
    vals = np.asarray(result.equity_curve, dtype=float)
    if vals.size < 2:
        return []
    return np.diff(vals).tolist()


def _walk_forward_gate(
    candidate: Dict[str, Any],
    df: pd.DataFrame,
    context_dfs: Dict[str, pd.DataFrame] | None,
    interval: str,
    commission: float,
    slippage: float,
    capital: float,
    min_trades: int,
    min_score: float,
    n_splits: int = 3,
) -> Tuple[bool, List[Dict[str, Any]]]:
    n = len(df)
    if n < n_splits * 20:
        return True, [{"skipped": "insufficient_validation_bars"}]

    combo = tuple(candidate["entry_signals"])
    params = candidate["signal_params"]
    sl_pct = float(candidate["sl_pct"])
    tp_pct = float(candidate["tp_pct"])
    direction = candidate["direction"]

    # Pre-build all fold segments so threads only do compute (no shared state)
    segments = []
    for part in np.array_split(np.arange(n), n_splits):
        seg = df.iloc[part]
        seg_ctx = _slice_context(context_dfs, seg.index)
        segments.append((seg, seg_ctx))

    def _run_fold(seg_tuple):
        seg, seg_ctx = seg_tuple
        entries = _compute_entries_for_candidate(seg, combo, params, seg_ctx)
        result = run_vectorbt_backtest(
            seg, entries, pd.Series(False, index=seg.index),
            sl_pct=sl_pct, tp_pct=tp_pct,
            commission=commission, slippage=slippage,
            initial_capital=capital, direction=direction, interval=interval,
        )
        score = compute_composite_score(result)
        return {"trades": result.trades, "score": score, "sharpe": result.sharpe}

    # Run all folds in parallel — each is independent (different df slice)
    with ThreadPoolExecutor(max_workers=n_splits) as pool:
        reports = list(pool.map(_run_fold, segments))

    # Evaluate pass/fail in fold order (preserves determinism)
    for rep in reports:
        if rep["trades"] < min_trades or rep["score"] < min_score:
            return False, reports
    return True, reports


def _regime_breakdown(df: pd.DataFrame, entries: pd.Series) -> Dict[str, Any]:
    regimes = adx_regime(df).reindex(df.index).fillna("range")
    entry_regimes = regimes[entries.reindex(df.index, fill_value=False).astype(bool)]
    counts = entry_regimes.value_counts().to_dict()
    total = max(int(sum(counts.values())), 1)
    weights = {k: round(v / total, 4) for k, v in counts.items()}
    best = max(weights, key=weights.get) if weights else "unknown"
    return {"entry_counts": counts, "entry_weights": weights, "best_regime": best}


def _validate_candidate(
    candidate: Dict[str, Any],
    validation_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    validation_context: Dict[str, pd.DataFrame] | None,
    holdout_context: Dict[str, pd.DataFrame] | None,
    interval: str,
    commission: float,
    slippage: float,
    capital: float,
    min_validation_trades: int,
    min_holdout_trades: int,
    min_validation_score: float,
    min_holdout_score: float,
    mc_runs: int,
    max_mc_p_value: float,
    max_sensitivity_drop: float,
    min_wf_score: float,
    min_wf_trades: int,
    ml_gate: MLGate | None = None,
) -> Dict[str, Any]:
    out = dict(candidate)
    out["passed"] = False
    out["rejected_by"] = None
    out["gate_details"] = {}

    combo = tuple(candidate["entry_signals"])
    params = candidate["signal_params"]
    sl_pct = float(candidate["sl_pct"])
    tp_pct = float(candidate["tp_pct"])
    direction = candidate["direction"]

    # Local entry cache: same (df_id, combo, params) reused for val + sensitivity loop
    _entry_cache: Dict[tuple, pd.Series] = {}

    def _cached_entries(df_: pd.DataFrame, ctx_) -> pd.Series:
        try:
            key = (id(df_), combo, hash(str(params)))
        except Exception:
            key = None
        if key is not None and key in _entry_cache:
            return _entry_cache[key]
        result = _compute_entries_for_candidate(df_, combo, params, ctx_)
        if key is not None:
            _entry_cache[key] = result
        return result

    try:
        val_entries = _cached_entries(validation_df, validation_context)
        if ml_gate is not None:
            val_entries = ml_gate.filter(val_entries, validation_df, validation_context, risk=(sl_pct, tp_pct))
        val_result = run_vectorbt_backtest(
            validation_df,
            val_entries,
            pd.Series(False, index=validation_df.index),
            sl_pct=sl_pct,
            tp_pct=tp_pct,
            commission=commission,
            slippage=slippage,
            initial_capital=capital,
            direction=direction,
            interval=interval,
        )
        val_score = compute_composite_score(val_result)
        out["gate_details"]["OOS_VALIDATION"] = {
            "trades": val_result.trades,
            "score": val_score,
            "sharpe": val_result.sharpe,
        }
        if val_result.trades < min_validation_trades or val_score < min_validation_score:
            out["rejected_by"] = "OOS_VALIDATION"
            return out

        wf_ok, wf_reports = _walk_forward_gate(
            candidate,
            validation_df,
            validation_context,
            interval,
            commission,
            slippage,
            capital,
            min_wf_trades,
            min_wf_score,
        )
        out["gate_details"]["WALK_FORWARD"] = wf_reports
        if not wf_ok:
            out["rejected_by"] = "WALK_FORWARD"
            return out

        hold_entries = _compute_entries_for_candidate(holdout_df, combo, params, holdout_context)
        if ml_gate is not None:
            hold_entries = ml_gate.filter(hold_entries, holdout_df, holdout_context, risk=(sl_pct, tp_pct))
        hold_result = run_vectorbt_backtest(
            holdout_df,
            hold_entries,
            pd.Series(False, index=holdout_df.index),
            sl_pct=sl_pct,
            tp_pct=tp_pct,
            commission=commission,
            slippage=slippage,
            initial_capital=capital,
            direction=direction,
            interval=interval,
        )
        hold_score = compute_composite_score(hold_result)
        out["gate_details"]["FINAL_HOLDOUT"] = {
            "trades": hold_result.trades,
            "score": hold_score,
            "sharpe": hold_result.sharpe,
        }
        if hold_result.trades < min_holdout_trades or hold_score < min_holdout_score:
            out["rejected_by"] = "FINAL_HOLDOUT"
            return out

        out["gate_details"]["REGIME"] = _regime_breakdown(validation_df, val_entries)
        if ml_gate is not None:
            out["gate_details"]["ML_GATE"] = dict(ml_gate.last_report)

        mc = monte_carlo_trades(_equity_returns(val_result), runs=mc_runs)
        out["gate_details"]["MONTE_CARLO"] = mc
        if mc["p_value"] > max_mc_p_value:
            out["rejected_by"] = "MONTE_CARLO"
            return out

        # Build all neighbor variants first, then run in parallel
        neighbor_tasks = []  # entries per neighbor
        for sig_name in combo:
            sig = registry.get(sig_name)
            for n_params in neighbor_params(params.get(sig_name, {}), sig.param_grid)[:2]:
                n_all_params = dict(params)
                n_all_params[sig_name] = n_params
                # Use cache when n_all_params == params (no-op neighbor), else compute fresh
                if n_all_params == params:
                    n_entries = _cached_entries(validation_df, validation_context)
                else:
                    n_entries = _compute_entries_for_candidate(validation_df, combo, n_all_params, validation_context)
                neighbor_tasks.append(n_entries)

        def _run_neighbor(n_entries):
            return run_vectorbt_backtest(
                validation_df, n_entries,
                pd.Series(False, index=validation_df.index),
                sl_pct=sl_pct, tp_pct=tp_pct,
                commission=commission, slippage=slippage,
                initial_capital=capital, direction=direction, interval=interval,
            )

        neighbor_scores = []
        if neighbor_tasks:
            with ThreadPoolExecutor(max_workers=len(neighbor_tasks)) as pool:
                n_results = list(pool.map(_run_neighbor, neighbor_tasks))
            for n_result in n_results:
                if n_result.trades >= min_validation_trades:
                    neighbor_scores.append(compute_composite_score(n_result))
        s_flag = sensitivity_flag(val_score, neighbor_scores, max_drop=max_sensitivity_drop)
        out["gate_details"]["SENSITIVITY"] = {
            "flag": s_flag,
            "neighbor_scores": neighbor_scores,
        }
        if s_flag == "overfit_risk":
            out["rejected_by"] = "SENSITIVITY"
            return out

        # Run all cost stress scenarios in parallel — same entries, same df, different fees
        scenarios = list(cost_scenarios(commission, slippage, (2.0, 5.0)))

        def _run_stress(args):
            c, s, label = args
            r = run_vectorbt_backtest(
                validation_df, val_entries,
                pd.Series(False, index=validation_df.index),
                sl_pct=sl_pct, tp_pct=tp_pct,
                commission=c, slippage=s,
                initial_capital=capital, direction=direction, interval=interval,
            )
            return label, r

        stress = []
        with ThreadPoolExecutor(max_workers=len(scenarios)) as pool:
            stress_results = list(pool.map(_run_stress, scenarios))
        for label, stress_result in stress_results:
            stress_score = compute_composite_score(stress_result)
            stress.append({"label": label, "score": stress_score, "sharpe": stress_result.sharpe})
            if label == "2x" and stress_score < min_validation_score:
                out["rejected_by"] = "COST_STRESS"
                out["gate_details"]["COST_STRESS"] = stress
                return out
        out["gate_details"]["COST_STRESS"] = stress
    except Exception as exc:
        out["rejected_by"] = "VALIDATION_ERROR"
        out["gate_details"]["VALIDATION_ERROR"] = f"{type(exc).__name__}: {exc}"
        return out

    out["passed"] = True
    return out


def _apply_fdr_gate(candidates: List[Dict[str, Any]], fdr_q: float) -> List[Dict[str, Any]]:
    passed = [c for c in candidates if c.get("passed", True) is True]
    if not passed:
        return candidates
    p_values = [float(c.get("gate_details", {}).get("MONTE_CARLO", {}).get("p_value", 1.0)) for c in passed]
    keep = benjamini_hochberg(p_values, q=fdr_q)
    keep_by_id = {id(c): ok for c, ok in zip(passed, keep)}
    out = []
    for c in candidates:
        if c.get("passed", True) is True and not keep_by_id.get(id(c), False):
            rejected = dict(c)
            rejected["passed"] = False
            rejected["rejected_by"] = "FDR"
            rejected.setdefault("gate_details", {})["FDR"] = {"q": fdr_q}
            out.append(rejected)
        else:
            out.append(c)
    return out


def _apply_strategy_correlation_filter(
    candidates: List[Dict[str, Any]],
    df: pd.DataFrame,
    context_dfs: Dict[str, pd.DataFrame] | None,
    max_corr: float,
) -> List[Dict[str, Any]]:
    """Greedy de-correlation filter.

    Improvement over the original O(N²) pairwise loop:
    - All entry Series are computed first, then correlated in one vectorized
      DataFrame.corr() call instead of incremental pd.Series.corr() calls.
    - Complexity is still O(N²) in the worst case but avoids Python-level
      looping over pairs and profits from NumPy's BLAS-backed dot product.
    """
    if not candidates:
        return []

    # --- Step 1: compute all entry vectors at once ---
    entry_list: List[pd.Series] = []
    for c in candidates:
        try:
            e = _compute_entries_for_candidate(
                df, tuple(c["entry_signals"]), c["signal_params"], context_dfs
            ).astype(float)
        except Exception:
            e = pd.Series(0.0, index=df.index)
        entry_list.append(e)

    # --- Step 2: build correlation matrix in one shot ---
    entry_matrix = pd.concat(entry_list, axis=1)
    entry_matrix.columns = range(len(candidates))
    corr_matrix = entry_matrix.corr().abs()          # single vectorized call

    # --- Step 3: greedy selection (same logic as before, now using matrix) ---
    selected: List[Dict[str, Any]] = []
    selected_idx: List[int] = []

    for i, candidate in enumerate(candidates):
        keep = True
        for j in selected_idx:
            corr_val = corr_matrix.iloc[i, j]
            if pd.notna(corr_val) and corr_val > max_corr:
                keep = False
                break
        if keep:
            candidate.setdefault("gate_details", {})["CORRELATION"] = {"passed": True, "max_corr": max_corr}
            selected.append(candidate)
            selected_idx.append(i)
        else:
            candidate["passed"] = False
            candidate["rejected_by"] = "CORRELATION"
            candidate.setdefault("gate_details", {})["CORRELATION"] = {"passed": False, "max_corr": max_corr}

    return selected


def _apply_ml_gate_to_survivors(
    candidates: List[Dict[str, Any]],
    df: pd.DataFrame,
    context_dfs: Dict[str, pd.DataFrame] | None,
    ml_gate: MLGate,
    direction: str,
    commission: float,
    slippage: float,
    capital: float,
    interval: str,
    min_trades: int,
    primary_metric: str,
    top_n: int,
) -> List[Dict[str, Any]]:
    raw_sorted = sorted(candidates, key=lambda x: x.get("_rank_score", x["composite_score"]), reverse=True)[:top_n]
    filtered_results: List[Dict[str, Any]] = []
    exits = pd.Series(False, index=df.index)

    for item in raw_sorted:
        combo = tuple(item["entry_signals"])
        params = item["signal_params"]
        sl_pct = float(item["sl_pct"])
        tp_pct = float(item["tp_pct"])
        entries = _compute_entries_for_candidate(df, combo, params, context_dfs)
        entries = ml_gate.filter(entries, df, context_dfs, risk=(sl_pct, tp_pct))
        if entries.sum() < min_trades:
            continue
        bt_result = run_vectorbt_backtest(
            df=df,
            entries=entries,
            exits=exits,
            sl_pct=sl_pct,
            tp_pct=tp_pct,
            commission=commission,
            slippage=slippage,
            initial_capital=capital,
            direction=direction,
            interval=interval,
        )
        if bt_result.trades < min_trades:
            continue
        composite = compute_composite_score(bt_result)
        score = composite if primary_metric in ("composite", "composite_score") else rank_metric_value(bt_result, primary_metric)
        updated = dict(item)
        updated["result"] = bt_result
        updated["composite_score"] = composite
        updated["_rank_score"] = score
        updated.setdefault("gate_details", {})["ML_GATE_TRAIN"] = dict(ml_gate.last_report)
        filtered_results.append(updated)

    return filtered_results


# ── Core backtest worker ──────────────────────────────────────────────────────

def _backtest_one_combo(
    combo_names: Tuple[str, ...],
    signal_cache: Dict[str, pd.Series],
    df: pd.DataFrame,
    risk_pairs: List[Tuple[float, float, str]],
    direction: str,
    commission: float,
    slippage: float,
    capital: float,
    min_trades: int,
    interval: str = "1d",
    sweep_params: bool = False,
    max_param_combos: int = 50,
    primary_metric: str = "composite",
    context_dfs: Dict[str, pd.DataFrame] | None = None,
    ml_gate: MLGate | None = None,
    regime_filter: RegimeFilter | None = None,
) -> List[Dict[str, Any]]:
    """
    Run backtests for one signal combo across all R:R ratios and (optionally)
    param-grid combinations. Returns list of result dicts.
    """
    # AND all entry signals using numpy reduce (faster than iterative pandas &)
    _cache_arrays = [
        signal_cache.get(name, pd.Series(False, index=df.index))
        .reindex(df.index, fill_value=False).to_numpy(dtype=bool, copy=False)
        for name in combo_names
    ]
    entries_base = pd.Series(
        np.logical_and.reduce(_cache_arrays) if _cache_arrays else np.zeros(len(df.index), dtype=bool),
        index=df.index,
    )

    # Layer 2: apply regime filter (zscore, entropy, trend-state masks)
    if regime_filter is not None:
        entries_base = regime_filter.apply(entries_base, direction=direction)

    if entries_base.sum() < min_trades:
        return []

    exits = pd.Series(False, index=df.index)

    # Build param variants to test
    param_variants = _build_param_variants(combo_names, sweep_params, max_param_combos)

    results = []
    for signal_params in param_variants:
        # When sweep_params=True and params differ from defaults, recompute signals
        if sweep_params:
            _sweep_arrays = []
            for name in combo_names:
                sig = registry.get(name)
                if sig:
                    try:
                        computed = sig(df, overrides=signal_params[name], context_dfs=context_dfs)
                        _sweep_arrays.append(computed.reindex(df.index, fill_value=False).to_numpy(dtype=bool, copy=False))
                    except Exception:
                        _sweep_arrays.append(signal_cache.get(name, pd.Series(False, index=df.index)).reindex(df.index, fill_value=False).to_numpy(dtype=bool, copy=False))
                else:
                    _sweep_arrays.append(signal_cache.get(name, pd.Series(False, index=df.index)).reindex(df.index, fill_value=False).to_numpy(dtype=bool, copy=False))
            entries = pd.Series(np.logical_and.reduce(_sweep_arrays) if _sweep_arrays else np.zeros(len(df.index), dtype=bool), index=df.index)

            if entries.sum() < min_trades:
                continue
        else:
            entries = entries_base

        # --- Batch all risk pairs into a single Portfolio.from_signals() call ---
        # Collect (entries_for_bt, sl, tp, risk_label, ml_report) per active risk pair
        batch_entries: List[pd.Series] = []
        batch_sl: List[float] = []
        batch_tp: List[float] = []
        batch_meta: List[Tuple] = []  # (sl_pct, tp_pct, risk_label, ml_report)

        for sl_pct, tp_pct, risk_label in risk_pairs:
            entries_for_bt = entries
            ml_report: Dict[str, Any] | None = None
            if ml_gate is not None:
                entries_for_bt = ml_gate.filter(entries, df, context_dfs, risk=(sl_pct, tp_pct))
                ml_report = dict(ml_gate.last_report)
                if entries_for_bt.sum() < min_trades:
                    continue
            batch_entries.append(entries_for_bt)
            batch_sl.append(sl_pct)
            batch_tp.append(tp_pct)
            batch_meta.append((sl_pct, tp_pct, risk_label, ml_report))

        if not batch_entries:
            continue

        # Run all risk variants in one VectorBT call
        bt_results = run_vectorbt_backtest_batch(
            df=df,
            entries_list=batch_entries,
            sl_stops=batch_sl,
            tp_stops=batch_tp,
            commission=commission,
            slippage=slippage,
            initial_capital=capital,
            direction=direction,
            interval=interval,
        )

        for bt_result, (sl_pct, tp_pct, risk_label, ml_report) in zip(bt_results, batch_meta):
            if bt_result.trades < min_trades:
                continue

            composite = compute_composite_score(bt_result)
            score = composite if primary_metric in ("composite", "composite_score") else rank_metric_value(bt_result, primary_metric)

            item = {
                "entry_signals": list(combo_names),
                "exit_signal": None,
                "direction": direction,
                "rr_ratio": risk_label,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "signal_params": signal_params,
                "result": bt_result,
                "composite_score": composite,
                "_rank_score": score,
            }
            if ml_report is not None:
                item.setdefault("gate_details", {})["ML_GATE_TRAIN"] = ml_report
            results.append(item)

    return results


# ── Main entry point ──────────────────────────────────────────────────────────

def run_discovery(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    extra_intervals: List[str] | None = None,
    direction: str = "long",
    max_signals: int = 3,
    categories: List[str] | None = None,
    exclude_categories: List[str] | None = None,
    rr_ratios: List[str] | None = None,
    data_path: str | None = None,
    commission: float = 0.001,
    slippage: float = 0.0005,
    slippage_model: str = "flat",
    max_strategy_corr: float = 0.70,
    capital: float = 100_000,
    min_trades: int = 30,
    max_workers: int = 4,
    sweep_params: bool = True,
    max_param_combos: int = 50,
    use_processes: bool = True,
    sl_mode: str = "fixed",
    fixed_sl_grid: List[float] | None = None,
    fixed_tp_grid: List[float] | None = None,
    atr_period: int = 14,
    atr_mult: float = 1.5,
    primary_metric: str = "composite",
    enforce_validation_gates: bool = True,
    min_validation_score: float = 1.0,
    min_holdout_score: float = 1.0,
    min_validation_trades: int | None = None,
    min_holdout_trades: int | None = None,
    mc_runs: int = 200,
    max_mc_p_value: float = 0.05,
    fdr_q: float = 0.05,
    max_sensitivity_drop: float = 0.25,
    min_wf_score: float = 1.0,
    min_wf_trades: int | None = None,
    enforce_data_integrity: bool = True,
    fail_on_corporate_actions: bool = False,
    use_ml_gate: bool = False,
    ml_use_gpu: bool = True,
    ml_threshold_quantile: float = 0.90,
    ml_max_hold_bars: int = 120,
    ml_max_features: int = 20,
    ml_min_train_labels: int = 30,
    ml_top_n: int = 200,
    ml_fallback_to_raw: bool = False,
    include_rejected: bool = False,
    filter_config: Dict[str, Any] | None = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    _ohlcv_job_id: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Main discovery entry point.

    Parameters
    ----------
    extra_intervals : List[str]
        Additional timeframes to fetch and align (MTF context).
    sweep_params : bool
    ...
    Returns
    -------
    List of result dicts sorted by composite_score descending (top 200).
    """
    # 1. Fetch and align MTF data
    if progress_callback:
        progress_callback(0, 0, "Downloading & aligning MTF data...")
    
    tfs = [interval]
    if extra_intervals:
        tfs.extend(extra_intervals)
        tfs = list(set(tfs)) # unique

    df_map = fetch_mtf_data(symbol, tfs, start_date, end_date, data_path=data_path)
    aligned_map = align_mtf_data(df_map, interval)
    
    df = aligned_map[interval]
    context_dfs = {tf: d for tf, d in aligned_map.items() if tf != interval}

    if len(df) < 60:
        raise ValueError(f"Insufficient data: only {len(df)} bars (need ≥60)")

    if enforce_data_integrity:
        report = validate_ohlcv(df, expected_freq="1min" if interval in ("1m", "1min") else None)
        if not report.ok:
            raise ValueError(f"Data integrity failed: {report.errors}")
        ca_report = detect_possible_splits(df)
        if fail_on_corporate_actions and ca_report.warnings:
            raise ValueError(f"Corporate action warnings: {ca_report.warnings}")

    if enforce_validation_gates:
        split = split_train_validation_holdout(df)
        train_df, validation_df, holdout_df = split.train, split.validation, split.holdout
        train_context = _slice_context(context_dfs, train_df.index)
        validation_context = _slice_context(context_dfs, validation_df.index)
        holdout_context = _slice_context(context_dfs, holdout_df.index)
    else:
        train_df, validation_df, holdout_df = df, df, df
        train_context = validation_context = holdout_context = context_dfs

    if (slippage_model or "flat").lower() == "atr":
        train_slip = atr_slippage_pct(train_df).replace([np.inf, -np.inf], np.nan).dropna()
        if not train_slip.empty:
            slippage = max(float(slippage), float(train_slip.median()))

    # 2. Pre-compute all signals once (KEY optimisation)
    # Clear per-signal caches from any prior run first (frees memory, avoids stale id(df) hits)
    registry.clear_all_caches()
    if progress_callback:
        progress_callback(0, 0, "Computing signals (MTF-aware)...")
    signal_cache = registry.compute_all(train_df, context_dfs=train_context)

    # 2b. Build regime filter layer (pre-computes zscore/entropy/trend masks once)
    _filter_cfg = filter_config if filter_config else None
    _regime_filter: RegimeFilter | None = None
    if _filter_cfg and any(
        _filter_cfg.get(k, False) for k in ("use_zscore", "use_entropy", "use_trend_state")
    ):
        try:
            _regime_filter = build_filter_masks(train_df, config=_filter_cfg)
            if progress_callback:
                summary = _regime_filter.summary()
                progress_callback(0, 0, f"Regime filters active: {list(summary.keys())}")
        except Exception as _fe:
            if progress_callback:
                progress_callback(0, 0, f"Regime filter build failed (disabled): {_fe}")

    # 3. Generate signal combos
    if progress_callback:
        progress_callback(0, 0, "Generating combinations...")
    combos = generate_combos(
        registry,
        max_signals=max_signals,
        direction=direction,
        categories=categories,
        exclude_categories=exclude_categories,
    )
    if not combos:
        raise ValueError("No valid signal combinations for the given filters")

    # 3b. Pre-filter combos: remove any that use dead (< min_trades triggers)
    # or hyper-dense (> 30% of bars) signals — they produce no useful backtests
    _max_density = 0.30 * len(train_df)
    _eligible_signals = {
        name for name, s in signal_cache.items()
        if min_trades <= int(s.sum()) <= _max_density
    }
    _before = len(combos)
    combos = [c for c in combos if all(name in _eligible_signals for name in c)]
    if not combos:
        raise ValueError("All combos filtered out by dead/dense signal check — try lowering min_trades")
    _filtered = _before - len(combos)
    if _filtered > 0 and progress_callback:
        progress_callback(0, 0, f"Pre-filtered {_filtered} combos with dead/dense signals ({len(combos)} remain)")

    # 4. Parse R:R ratios
    rr_str_list = rr_ratios or ["1:1", "1:1.5", "1:2", "1:2.5", "1:3"]
    rr_float_list = parse_rr_ratios(rr_str_list)

    total = len(combos)
    if progress_callback:
        progress_callback(0, total, f"Testing {total} combos × {len(rr_float_list)} R:R ratios" +
                          (f" × param grid" if sweep_params else "") + "...")

    # 5. Risk matrix
    risk_pairs = build_risk_pairs(
        train_df,
        mode=sl_mode,
        rr_ratios=rr_float_list,
        rr_labels=rr_str_list,
        fixed_sl_grid=fixed_sl_grid,
        fixed_tp_grid=fixed_tp_grid,
        atr_period=atr_period,
        atr_mult=atr_mult,
    )

    ml_gate: MLGate | None = None
    if use_ml_gate:
        if progress_callback:
            progress_callback(0, total, "Training ML entry gate...")
        try:
            train_union_entries = pd.Series(False, index=train_df.index)
            for sig_series in signal_cache.values():
                train_union_entries = train_union_entries | sig_series.reindex(train_df.index, fill_value=False).fillna(False).astype(bool)
            if train_union_entries.sum() >= ml_min_train_labels:
                label_sl, label_tp, _ = risk_pairs[0]
                labels, pnl = label_tp_before_sl(
                    train_df,
                    train_union_entries,
                    sl_pct=label_sl,
                    tp_pct=label_tp,
                    direction=direction,
                    max_hold_bars=ml_max_hold_bars,
                )
                if len(labels) >= ml_min_train_labels:
                    features = build_feature_matrix(train_df, context_dfs=train_context, risk=(label_sl, label_tp)).reindex(labels.index)
                    selected = train_and_select(
                        features,
                        labels,
                        pnl=pnl,
                        use_gpu=ml_use_gpu,
                        max_features=ml_max_features,
                        threshold_quantile=ml_threshold_quantile,
                    )
                    if selected is not None:
                        ml_gate = MLGate(selected, min_trades=min_trades, fallback_to_raw=ml_fallback_to_raw)
        except Exception as exc:
            if progress_callback:
                progress_callback(0, total, f"ML gate disabled: {type(exc).__name__}")
    if ml_gate is not None:
        use_processes = False

    # 6. Run backtests
    all_results: List[Dict[str, Any]] = []
    tested = 0

    _worker_kwargs = dict(
        signal_cache=signal_cache,
        df=train_df,
        risk_pairs=risk_pairs,
        direction=direction,
        commission=commission,
        slippage=slippage,
        capital=capital,
        min_trades=min_trades,
        interval=interval,
        sweep_params=sweep_params,
        max_param_combos=max_param_combos,
        primary_metric=primary_metric,
        context_dfs=train_context,
        regime_filter=_regime_filter,
    )

    if total <= 50:
        # Sequential only for very small sets (avoids thread-spawn overhead)
        for combo in combos:
            try:
                res = _backtest_one_combo(combo, **_worker_kwargs)
                all_results.extend(res)
            except Exception:
                pass
            tested += 1
            if progress_callback and tested % 20 == 0:
                progress_callback(tested, total, f"Tested {tested}/{total}")
    else:
        # Parallel for larger sets
        ExecutorClass = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        try:
            with ExecutorClass(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(_backtest_one_combo, combo, **_worker_kwargs): combo
                    for combo in combos
                }
                for future in as_completed(futures):
                    tested += 1
                    try:
                        res = future.result()
                        all_results.extend(res)
                    except Exception:
                        pass
                    if progress_callback and tested % 50 == 0:
                        progress_callback(tested, total, f"Tested {tested}/{total}")
        except Exception as exc:
            # Fall back to ThreadPoolExecutor (e.g. pickling error on Windows with Process)
            if use_processes:
                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    futures = {
                        pool.submit(_backtest_one_combo, combo, **_worker_kwargs): combo
                        for combo in combos
                    }
                    for future in as_completed(futures):
                        tested += 1
                        try:
                            res = future.result()
                            all_results.extend(res)
                        except Exception:
                            pass
                        if progress_callback and tested % 50 == 0:
                            progress_callback(tested, total, f"Tested {tested}/{total}")
            else:
                raise

    if ml_gate is not None:
        if progress_callback:
            progress_callback(total, total, f"Applying ML gate to top {min(ml_top_n, len(all_results))} raw survivors...")
        # Pre-compute feature matrix once for all survivors (avoids per-candidate recomputation)
        ml_gate.prime_feature_cache(train_df, context_dfs=train_context, risk=risk_pairs[0][:2] if risk_pairs else None)
        all_results = _apply_ml_gate_to_survivors(
            all_results,
            df=train_df,
            context_dfs=train_context,
            ml_gate=ml_gate,
            direction=direction,
            commission=commission,
            slippage=slippage,
            capital=capital,
            interval=interval,
            min_trades=min_trades,
            primary_metric=primary_metric,
            top_n=ml_top_n,
        )

    if progress_callback:
        progress_callback(total, total, "Applying validation gates...")

    # Validate only top-N by composite_score — skip low-scorers early
    if enforce_validation_gates and len(all_results) > 500:
        all_results.sort(key=lambda x: x.get("composite_score", -1e9), reverse=True)
        all_results = all_results[:500]

    if enforce_validation_gates:
        min_val_trades = min_validation_trades if min_validation_trades is not None else max(1, min_trades // 5)
        min_hold_trades = min_holdout_trades if min_holdout_trades is not None else max(1, min_trades // 10)
        min_wf_trades_eff = min_wf_trades if min_wf_trades is not None else max(1, min_trades // 10)

        _val_kwargs = dict(
            validation_df=validation_df,
            holdout_df=holdout_df,
            validation_context=validation_context,
            holdout_context=holdout_context,
            interval=interval,
            commission=commission,
            slippage=slippage,
            capital=capital,
            min_validation_trades=min_val_trades,
            min_holdout_trades=min_hold_trades,
            min_validation_score=min_validation_score,
            min_holdout_score=min_holdout_score,
            mc_runs=mc_runs,
            max_mc_p_value=max_mc_p_value,
            max_sensitivity_drop=max_sensitivity_drop,
            min_wf_score=min_wf_score,
            min_wf_trades=min_wf_trades_eff,
            ml_gate=ml_gate,
        )

        def _validate_one(item):
            return _validate_candidate(item, **_val_kwargs)

        # Parallel validation — candidates are independent so ThreadPool is safe.
        # VectorBT releases the GIL for most of its C work, giving real concurrency.
        _n_val_workers = min(8, max(1, len(all_results)))
        if _n_val_workers > 1:
            with ThreadPoolExecutor(max_workers=_n_val_workers) as _pool:
                all_results = list(_pool.map(_validate_one, all_results))
        else:
            all_results = [_validate_one(item) for item in all_results]

        all_results = _apply_fdr_gate(all_results, fdr_q=fdr_q)

    if progress_callback:
        progress_callback(total, total, "Ranking results...")

    # 7. Fail-closed final list.
    # Passed candidates are ranked first. If nothing passes, return the best
    # rejected candidates too so the UI can show why the search failed.
    report_results = rankable_only(all_results)
    report_results.sort(key=lambda x: x.get("_rank_score", x["composite_score"]), reverse=True)
    if max_strategy_corr < 1 and len(report_results) > 1:
        report_results = _apply_strategy_correlation_filter(report_results, train_df, train_context, max_strategy_corr)

    if not report_results and include_rejected:
        report_results = sorted(
            all_results,
            key=lambda x: x.get("_rank_score", x.get("composite_score", -1e9)),
            reverse=True,
        )

    for item in report_results:
        item.pop("_rank_score", None)

    if _ohlcv_job_id and train_df is not None and not train_df.empty:
        try:
            import json as _json
            import pandas as _pd
            from research.storage.db import store_ohlcv as _store_ohlcv
            bars = train_df.reset_index()
            # Cap to 2000 bars for efficient chart rendering; downsample evenly if larger
            if len(bars) > 2000:
                step = len(bars) // 2000 + 1
                bars = bars.iloc[::step]
            col_map = {c: c.lower() for c in bars.columns}
            bars = bars.rename(columns=col_map)
            ts_col = next((c for c in bars.columns if "date" in c or "time" in c or "index" in c.lower()), bars.columns[0])
            ohlcv = []
            for _, row in bars.iterrows():
                t = row[ts_col]
                try:
                    t = int(_pd.Timestamp(t).timestamp())
                except Exception:
                    t = int(t)
                ohlcv.append({
                    "time": t,
                    "open": round(float(row.get("open", 0)), 4),
                    "high": round(float(row.get("high", 0)), 4),
                    "low": round(float(row.get("low", 0)), 4),
                    "close": round(float(row.get("close", 0)), 4),
                    "volume": int(row.get("volume", 0)),
                })
            _store_ohlcv(_ohlcv_job_id, _json.dumps(ohlcv))
        except Exception as _e:
            import logging as _logging
            _logging.getLogger(__name__).debug("OHLCV storage skipped for job %s: %s", _ohlcv_job_id, _e)

    return report_results[:200]
