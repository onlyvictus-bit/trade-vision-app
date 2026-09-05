from pathlib import Path

import numpy as np
import pandas as pd

from research.engine.runner import run_discovery
from research.ml.feature_select import remove_correlated_features
from research.ml.features import build_feature_matrix
from research.ml.labeler import label_tp_before_sl


def _df(rows: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01 09:15", periods=rows, freq="1min")
    close = pd.Series(np.linspace(100, 110, rows) + np.sin(np.arange(rows) / 5), index=idx)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.002,
            "low": close * 0.998,
            "close": close,
            "volume": 1000 + np.arange(rows),
        },
        index=idx,
    )


def test_feature_matrix_lags_current_bar():
    df = _df(120)
    features = build_feature_matrix(df)
    spike_idx = df.index[80]
    df_spike = df.copy()
    df_spike.loc[spike_idx, "close"] = 9999
    features_spike = build_feature_matrix(df_spike)
    assert features.loc[spike_idx].equals(features_spike.loc[spike_idx])


def test_labeler_tp_before_sl_outputs_binary_labels():
    df = _df(180)
    entries = pd.Series(False, index=df.index)
    entries.iloc[20:120:10] = True
    labels, pnl = label_tp_before_sl(df, entries, sl_pct=0.003, tp_pct=0.003, max_hold_bars=30)
    assert len(labels) > 0
    assert set(labels.unique()).issubset({0, 1})
    assert labels.index.equals(pnl.index)


def test_feature_correlation_prunes_duplicate_columns():
    idx = pd.RangeIndex(50)
    df = pd.DataFrame({"a": np.arange(50), "b": np.arange(50) * 2, "c": np.random.default_rng(1).normal(size=50)}, index=idx)
    pruned, dropped = remove_correlated_features(df, threshold=0.85)
    assert "b" in dropped
    assert "b" not in pruned.columns


def test_infy_ml_gate_smoke_if_file_exists():
    src = Path(r"C:\Users\sakth\Downloads\HSTRY\INFY_NSE_1m.csv")
    if not src.exists():
        return
    results = run_discovery(
        symbol="INFY",
        start_date="2015-02-02",
        end_date="2015-02-06",
        interval="1m",
        extra_intervals=["5m", "15m"],
        categories=["trend"],
        max_signals=1,
        min_trades=1,
        min_validation_trades=1,
        min_holdout_trades=1,
        min_wf_trades=1,
        min_validation_score=0,
        min_holdout_score=0,
        min_wf_score=0,
        max_mc_p_value=1,
        fdr_q=1,
        mc_runs=10,
        sweep_params=True,
        max_param_combos=1,
        use_processes=False,
        sl_mode="fixed",
        fixed_sl_grid=[0.005],
        fixed_tp_grid=[0.01],
        data_path=str(src),
        use_ml_gate=True,
        ml_use_gpu=False,
        ml_min_train_labels=10,
        ml_max_hold_bars=30,
        ml_threshold_quantile=0.5,
        enforce_validation_gates=True,
    )
    assert isinstance(results, list)
