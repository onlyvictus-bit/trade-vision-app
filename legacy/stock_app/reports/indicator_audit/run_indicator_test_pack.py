from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reports.indicator_audit.run_10_indicator_readiness import add_indicators, load_infy_5m
from shared.indicators.pta import aroon_lines, cdl_patterns, fisher_line, hma_line, mfi_line
from shared.indicators.pta_signal_markers import compute_all as pta_marker_payload
from shared.indicators.self_indc import cdl_patterns_adv, mp_value_area_markers, trend_signals_markers

OUT_DIR = ROOT / "reports" / "indicator_audit" / "test_pack"
SAMPLE_BARS = 300
CONTEXT_BARS = 12000


REQUESTED = [
    "Doji", "HMA", "Skew Reversal", "ZScore", "TTM Trend", "Aroon", "ADX",
    "Williams %R", "CCI", "RSI", "MACD", "Short Run Bear", "Long Run Bull",
    "Drawdown Recovery", "Trend Signal", "EBSW Cycle", "TS Signal", "AMAT Bull",
    "HLC3 MA", "Aroon Signal", "Vortex Signal", "CMF Signal", "MFI Signal",
    "Long Return Momentum", "TSI Signal", "KDJ Signal", "Fisher Signal",
    "RSX Signal", "Market Profile VA",
]


FORMULAS = {
    "Doji": "Candle body <= 10% of high-low range. Neutral marker. Use as warning/filter only.",
    "HMA": "Hull Moving Average length 20 from pandas-ta-classic: WMA(2*WMA(close,n/2)-WMA(close,n),sqrt(n)). Overlay line.",
    "Skew Reversal": "Rolling return skew period 30 crosses below -0.5. Contrarian bullish marker.",
    "ZScore": "z=(close-rolling_mean_50)/rolling_std_50. Bull if crosses below -2. Bear if crosses above +2.",
    "TTM Trend": "pandas-ta-classic TTM Trend length 6. Marker when trend state flips bullish.",
    "Aroon": "Aroon Up/Down length 25 from pandas-ta-classic. Subpanel lines.",
    "ADX": "Wilder ADX14 with +DI/-DI. Subpanel. Trend strength, not standalone entry.",
    "Williams %R": "%R14=-100*(HH14-close)/(HH14-LL14). Bull crosses up -80. Bear crosses down -20.",
    "CCI": "CCI20=(typical_price-SMA20)/(0.015*mean_abs_dev20). Bull crosses up -100. Bear crosses down +100.",
    "RSI": "Wilder RSI14. Bull crosses up 30. Bear crosses down 70. Filter/warning only.",
    "MACD": "EMA12-EMA26, signal EMA9, histogram. Bull/bear cross markers.",
    "Short Run Bear": "EMA21<EMA55, close<EMA21, both EMA slopes down 8 bars, spread>0.15*ATR14, sustained 5 bars, first confirmed bar only.",
    "Long Run Bull": "EMA21>EMA55, close>EMA21, both EMA slopes up 8 bars, spread>0.15*ATR14, sustained 5 bars, first confirmed bar only.",
    "Drawdown Recovery": "Rolling 50-bar drawdown recovers after deep pullback. Bullish bounce filter.",
    "Trend Signal": "UAlgo trend signal wrapper from self-indc. Markers sanitized and cooldown applied.",
    "EBSW Cycle": "Even Better Sine Wave from pandas-ta-classic. Bull/bear when cycle crosses zero.",
    "TS Signal": "Trend Signal TP/SL wrapper from self-indc. Marker only; exact TP/SL requires strategy validation.",
    "AMAT Bull": "Adaptive Moving Average Trend from pandas-ta-classic. Bull/bear trend-state flips.",
    "HLC3 MA": "HLC3=(high+low+close)/3. Fast SMA10 crosses slow SMA30.",
    "Aroon Signal": "Aroon Up crosses above/down crosses above, length 25.",
    "Vortex Signal": "Vortex VI+/VI- length 14 cross.",
    "CMF Signal": "Chaikin Money Flow length 20 crosses zero.",
    "MFI Signal": "MFI14 crosses up 30/down 70.",
    "Long Return Momentum": "Rolling mean log return period 10 crosses threshold 0.",
    "TSI Signal": "True Strength Index fast13 slow25 signal13 cross.",
    "KDJ Signal": "KDJ stochastic-derived K/D cross length 9.",
    "Fisher Signal": "Fisher Transform length 9 line/signal cross.",
    "RSX Signal": "RSX threshold/cross wrapper from pandas-ta-classic. Momentum marker.",
        "Market Profile VA": "Previous-session Market Profile Value Area. VAH/VAL/POC from prior session volume profile, 24 bins, 70% value area. Bull when close crosses above prior VAH; bear when close crosses below prior VAL.",
}


def _round(v, nd=6):
    if pd.isna(v):
        return None
    try:
        return round(float(v), nd)
    except Exception:
        return v


def _events(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("signals"), list):
        return [x for x in payload["signals"] if isinstance(x, dict)]
    return []


def _event_map(payloads: dict) -> dict[str, list[dict]]:
    out = {}
    for key, value in payloads.items():
        out[key] = _events(value)
    return out


def _pta():
    try:
        import pandas_ta_classic as pta
        return pta
    except Exception:
        return None


def _first_col(df: pd.DataFrame, contains: str | None = None, fallback: int = 0) -> pd.Series | None:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if contains:
        for col in df.columns:
            if contains.lower() in str(col).lower():
                return df[col]
    return df.iloc[:, fallback] if len(df.columns) > fallback else None


def _market_profile_levels(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["mp_val"] = np.nan
    out["mp_vah"] = np.nan
    out["mp_poc"] = np.nan
    if not isinstance(df.index, pd.DatetimeIndex):
        return out
    high_s = df["high"].astype(float)
    low_s = df["low"].astype(float)
    volume_s = df["volume"].astype(float).clip(lower=0)
    bin_count = 24
    value_area_pct = 0.68
    sessions = list(df.groupby(df.index.date, sort=True).groups.items())

    def _profile(pos):
        low = float(low_s.iloc[pos].min())
        high = float(high_s.iloc[pos].max())
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            return None
        bins = np.linspace(low, high, bin_count + 1)
        step = float((high - low) / bin_count)
        volume_by_bin = np.zeros(bin_count, dtype=float)
        for row_pos in pos:
            bar_high = float(high_s.iloc[row_pos])
            bar_low = float(low_s.iloc[row_pos])
            bar_volume = float(volume_s.iloc[row_pos])
            if not np.isfinite(bar_high) or not np.isfinite(bar_low) or bar_volume <= 0:
                continue
            candle_size = max(bar_high - bar_low, step)
            for level in range(bin_count):
                price_low = bins[level]
                price_high = bins[level + 1]
                overlap = max(0.0, min(bar_high, price_high) - max(bar_low, price_low))
                if overlap > 0:
                    volume_by_bin[level] += bar_volume * (overlap / candle_size)
        total_volume = float(volume_by_bin.sum())
        if total_volume <= 0:
            return None
        poc_bin = int(np.argmax(volume_by_bin))
        selected = {poc_bin}
        selected_volume = float(volume_by_bin[poc_bin])
        left = poc_bin - 1
        right = poc_bin + 1
        while selected_volume < total_volume * value_area_pct and (left >= 0 or right < bin_count):
            left_volume = volume_by_bin[left] if left >= 0 else -1
            right_volume = volume_by_bin[right] if right < bin_count else -1
            if right_volume >= left_volume:
                selected.add(right)
                selected_volume += float(max(right_volume, 0))
                right += 1
            else:
                selected.add(left)
                selected_volume += float(max(left_volume, 0))
                left -= 1
        return bins, selected, poc_bin

    for session_i in range(1, len(sessions)):
        prev_idx = df.index.get_indexer(list(sessions[session_i - 1][1]))
        curr_idx = df.index.get_indexer(list(sessions[session_i][1]))
        prev_idx = prev_idx[prev_idx >= 0]
        curr_idx = curr_idx[curr_idx >= 0]
        if len(prev_idx) < 10:
            continue
        prof = _profile(prev_idx)
        if prof is None:
            continue
        bins, selected, poc_bin = prof
        out.iloc[curr_idx, out.columns.get_loc("mp_val")] = float(bins[min(selected)])
        out.iloc[curr_idx, out.columns.get_loc("mp_vah")] = float(bins[max(selected) + 1])
        out.iloc[curr_idx, out.columns.get_loc("mp_poc")] = float((bins[poc_bin] + bins[poc_bin + 1]) / 2)
    out["mp_cross_bull"] = (df["close"].shift(1) <= out["mp_vah"]) & (df["close"] > out["mp_vah"])
    out["mp_cross_bear"] = (df["close"].shift(1) >= out["mp_val"]) & (df["close"] < out["mp_val"])
    out["VAH"] = out["mp_vah"]
    out["VAL"] = out["mp_val"]
    out["POC"] = out["mp_poc"]
    out["profile_bin_count"] = 24
    out["value_area_pct"] = value_area_pct
    return out


def build_debug_columns(df: pd.DataFrame, df_title: pd.DataFrame, calc: pd.DataFrame) -> pd.DataFrame:
    pta = _pta()
    d = pd.DataFrame(index=df.index)
    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
    body = (c - df["open"]).abs()
    rng = (h - l).replace(0, np.nan)
    d["is_session_open_bar"] = df.index.to_series().dt.date.ne(df.index.to_series().dt.date.shift(1))
    d["doji_body"] = body
    d["doji_range"] = rng
    d["doji_body_range_ratio"] = body / rng
    d["doji_bool_exact"] = d["doji_body_range_ratio"] <= 0.10
    d["log_return"] = np.log(c / c.shift(1))
    d["pct_return"] = c.pct_change()
    d["skew_30"] = d["pct_return"].rolling(30, min_periods=10).skew()
    d["prev_skew_30"] = d["skew_30"].shift(1)
    d["skew_cross_below_minus_0_5"] = (d["skew_30"] < -0.5) & (d["prev_skew_30"] >= -0.5)
    d["mean_50"] = c.rolling(50, min_periods=25).mean()
    d["std_50"] = c.rolling(50, min_periods=25).std()
    d["zscore_50"] = (c - d["mean_50"]) / d["std_50"].replace(0, np.nan)
    d["prev_zscore_50"] = d["zscore_50"].shift(1)
    d["zscore_bull_cross"] = (d["zscore_50"] < -2) & (d["prev_zscore_50"] >= -2)
    d["zscore_bear_cross"] = (d["zscore_50"] > 2) & (d["prev_zscore_50"] <= 2)
    d["ema12"] = c.ewm(span=12, adjust=False).mean()
    d["ema26"] = c.ewm(span=26, adjust=False).mean()
    d["prev_macd"] = calc["macd"].shift(1)
    d["prev_macd_signal_line"] = calc["macd_signal_line"].shift(1)
    delta = c.diff()
    d["rsi_gain"] = delta.clip(lower=0)
    d["rsi_loss"] = -delta.clip(upper=0)
    d["rsi_avg_gain_wilder_14"] = d["rsi_gain"].ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    d["rsi_avg_loss_wilder_14"] = d["rsi_loss"].ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    d["typical_price"] = (h + l + c) / 3
    d["cci_sma20"] = d["typical_price"].rolling(20, min_periods=20).mean()
    d["cci_mad20"] = (d["typical_price"] - d["cci_sma20"]).abs().rolling(20, min_periods=20).mean()
    d["hh14"] = h.rolling(14, min_periods=14).max()
    d["ll14"] = l.rolling(14, min_periods=14).min()
    d["prev_williams_r_14"] = calc["williams_r_14"].shift(1)
    d["rsi_bull_cross_30"] = (calc["rsi_14"] > 30) & (calc["rsi_14"].shift(1) <= 30)
    d["rsi_bear_cross_70"] = (calc["rsi_14"] < 70) & (calc["rsi_14"].shift(1) >= 70)
    d["bars_since_high_25"] = h.rolling(25, min_periods=25).apply(lambda x: 24 - int(np.argmax(x)), raw=True)
    d["bars_since_low_25"] = l.rolling(25, min_periods=25).apply(lambda x: 24 - int(np.argmin(x)), raw=True)
    d["aroon_bull_cross_exact"] = (calc["aroon_up_25"] > calc["aroon_down_25"]) & (calc["aroon_up_25"].shift(1) <= calc["aroon_down_25"].shift(1))
    d["aroon_bear_cross_exact"] = (calc["aroon_down_25"] > calc["aroon_up_25"]) & (calc["aroon_down_25"].shift(1) <= calc["aroon_up_25"].shift(1))
    d["ema21"] = calc["ema_fast_21"]
    d["ema55"] = calc["ema_slow_55"]
    d["ema21_slope_8"] = calc["ema_fast_21"] - calc["ema_fast_21"].shift(8)
    d["ema55_slope_8"] = calc["ema_slow_55"] - calc["ema_slow_55"].shift(8)
    d["atr14"] = calc["atr_14_sma"]
    prev_close = c.shift(1)
    d["tr"] = pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    up_move = h.diff()
    down_move = -l.diff()
    d["plus_dm"] = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    d["minus_dm"] = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    d["tr_wilder_14"] = d["tr"].ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    d["plus_dm_wilder_14"] = pd.Series(d["plus_dm"], index=df.index).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    d["minus_dm_wilder_14"] = pd.Series(d["minus_dm"], index=df.index).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    d["dx"] = 100 * (calc["plus_di_14"] - calc["minus_di_14"]).abs() / (calc["plus_di_14"] + calc["minus_di_14"]).replace(0, np.nan)
    d["spread_atr_ratio"] = (calc["ema_fast_21"] - calc["ema_slow_55"]).abs() / calc["atr_14_sma"].replace(0, np.nan)
    long_state = (calc["ema_fast_21"] > calc["ema_slow_55"]) & (c > calc["ema_fast_21"]) & (d["ema21_slope_8"] > 0) & (d["ema55_slope_8"] > 0) & (d["spread_atr_ratio"] > 0.15)
    short_state = (calc["ema_fast_21"] < calc["ema_slow_55"]) & (c < calc["ema_fast_21"]) & (d["ema21_slope_8"] < 0) & (d["ema55_slope_8"] < 0) & (d["spread_atr_ratio"] > 0.15)
    d["long_state"] = long_state
    d["short_state"] = short_state
    d["long_sustain_count"] = long_state.rolling(5, min_periods=1).sum()
    d["short_sustain_count"] = short_state.rolling(5, min_periods=1).sum()
    d["first_confirmed_bull"] = calc["long_run_bull"]
    d["first_confirmed_bear"] = calc["short_run_bear"]
    d["rolling_peak_50"] = c.rolling(50, min_periods=10).max()
    d["deep_pullback_threshold"] = -0.01
    d["recovery_threshold"] = -0.005
    d["drawdown_recovery_bool"] = calc["drawdown_recovery"]
    d["hlc3"] = d["typical_price"]
    d["hlc3_fast_sma10"] = d["hlc3"].rolling(10, min_periods=1).mean()
    d["hlc3_slow_sma30"] = d["hlc3"].rolling(30, min_periods=1).mean()
    d["prev_hlc3_fast_sma10"] = d["hlc3_fast_sma10"].shift(1)
    d["prev_hlc3_slow_sma30"] = d["hlc3_slow_sma30"].shift(1)
    d["hlc3_bull_cross"] = (d["hlc3_fast_sma10"] > d["hlc3_slow_sma30"]) & (d["prev_hlc3_fast_sma10"] <= d["prev_hlc3_slow_sma30"])
    d["hlc3_bear_cross"] = (d["hlc3_fast_sma10"] < d["hlc3_slow_sma30"]) & (d["prev_hlc3_fast_sma10"] >= d["prev_hlc3_slow_sma30"])
    try:
        wma10 = pta.wma(df_title["Close"], length=10) if pta is not None else None
        wma20 = pta.wma(df_title["Close"], length=20) if pta is not None else None
        raw_hma = 2 * wma10 - wma20 if wma10 is not None and wma20 is not None else None
        d["wma_close_10"] = wma10.reindex(df.index) if wma10 is not None else np.nan
        d["wma_close_20"] = wma20.reindex(df.index) if wma20 is not None else np.nan
        d["raw_hma"] = raw_hma.reindex(df.index) if raw_hma is not None else np.nan
        d["wma_raw_sqrt20"] = pta.wma(raw_hma, length=int(np.sqrt(20))).reindex(df.index) if pta is not None and raw_hma is not None else np.nan
    except Exception:
        pass
    d["rolling_mean_log_return_10"] = d["log_return"].rolling(10, min_periods=3).mean()
    d["prev_rolling_mean_log_return_10"] = d["rolling_mean_log_return_10"].shift(1)
    d["log_return_bull_cross"] = (d["rolling_mean_log_return_10"] > 0) & (d["prev_rolling_mean_log_return_10"] <= 0)
    d["log_return_bear_cross"] = (d["rolling_mean_log_return_10"] < 0) & (d["prev_rolling_mean_log_return_10"] >= 0)
    if pta is not None:
        for prefix, result in {
            "ttm": pta.ttm_trend(df_title["High"], df_title["Low"], df_title["Close"], length=6),
            "ebsw": pta.ebsw(df_title["Close"], length=40, bars=15),
            "vortex": pta.vortex(df_title["High"], df_title["Low"], df_title["Close"], length=14),
            "cmf": pta.cmf(df_title["High"], df_title["Low"], df_title["Close"], df_title["Volume"], length=20),
            "tsi": pta.tsi(df_title["Close"], fast=13, slow=25, signal=13),
            "kdj": pta.kdj(df_title["High"], df_title["Low"], df_title["Close"], length=9),
            "rsx": pta.rsx(df_title["Close"], length=14),
        }.items():
            try:
                if prefix == "ttm":
                    s = _first_col(result) if isinstance(result, pd.DataFrame) else result
                    d["ttm_state"] = s.reindex(df.index)
                    d["prev_ttm_state"] = d["ttm_state"].shift(1)
                    d["ttm_flip_bull"] = (d["ttm_state"] > 0) & (d["prev_ttm_state"] <= 0)
                elif prefix == "ebsw":
                    s = _first_col(result) if isinstance(result, pd.DataFrame) else result
                    d["ebsw_cycle"] = s.reindex(df.index)
                    d["prev_ebsw_cycle"] = d["ebsw_cycle"].shift(1)
                    d["ebsw_cross_above_zero"] = (d["ebsw_cycle"] > 0) & (d["prev_ebsw_cycle"] <= 0)
                    d["ebsw_cross_below_zero"] = (d["ebsw_cycle"] < 0) & (d["prev_ebsw_cycle"] >= 0)
                elif prefix == "vortex":
                    d["vi_plus_14"] = result.iloc[:, 0].reindex(df.index)
                    d["vi_minus_14"] = result.iloc[:, 1].reindex(df.index)
                    d["prev_vi_plus_14"] = d["vi_plus_14"].shift(1)
                    d["prev_vi_minus_14"] = d["vi_minus_14"].shift(1)
                    d["vortex_bull_cross"] = (d["vi_plus_14"] > d["vi_minus_14"]) & (d["prev_vi_plus_14"] <= d["prev_vi_minus_14"])
                    d["vortex_bear_cross"] = (d["vi_minus_14"] > d["vi_plus_14"]) & (d["prev_vi_minus_14"] <= d["prev_vi_plus_14"])
                elif prefix == "cmf":
                    d["cmf_20"] = result.reindex(df.index)
                    d["prev_cmf_20"] = d["cmf_20"].shift(1)
                    d["cmf_cross_above_zero"] = (d["cmf_20"] > 0) & (d["prev_cmf_20"] <= 0)
                    d["cmf_cross_below_zero"] = (d["cmf_20"] < 0) & (d["prev_cmf_20"] >= 0)
                elif prefix == "tsi":
                    d["tsi"] = result.iloc[:, 0].reindex(df.index)
                    d["tsi_signal_line"] = result.iloc[:, 1].reindex(df.index)
                    d["prev_tsi"] = d["tsi"].shift(1)
                    d["prev_tsi_signal_line"] = d["tsi_signal_line"].shift(1)
                    d["tsi_bull_cross"] = (d["tsi"] > d["tsi_signal_line"]) & (d["prev_tsi"] <= d["prev_tsi_signal_line"])
                    d["tsi_bear_cross"] = (d["tsi"] < d["tsi_signal_line"]) & (d["prev_tsi"] >= d["prev_tsi_signal_line"])
                elif prefix == "kdj":
                    d["kdj_k"] = result.iloc[:, 0].reindex(df.index)
                    d["kdj_d"] = result.iloc[:, 1].reindex(df.index)
                    d["kdj_j"] = result.iloc[:, 2].reindex(df.index) if len(result.columns) > 2 else np.nan
                    d["prev_kdj_k"] = d["kdj_k"].shift(1)
                    d["prev_kdj_d"] = d["kdj_d"].shift(1)
                    d["kdj_bull_cross"] = (d["kdj_k"] > d["kdj_d"]) & (d["prev_kdj_k"] <= d["prev_kdj_d"])
                    d["kdj_bear_cross"] = (d["kdj_k"] < d["kdj_d"]) & (d["prev_kdj_k"] >= d["prev_kdj_d"])
                elif prefix == "rsx":
                    d["rsx"] = result.reindex(df.index)
                    d["prev_rsx"] = d["rsx"].shift(1)
                    d["rsx_bull_cross_50"] = (d["rsx"] > 50) & (d["prev_rsx"] <= 50)
                    d["rsx_bear_cross_50"] = (d["rsx"] < 50) & (d["prev_rsx"] >= 50)
            except Exception:
                pass
        try:
            amat = pta.amat(df_title["Close"], fast=8, slow=21)
            if isinstance(amat, pd.DataFrame):
                d["amat_state_1"] = amat.iloc[:, 0].reindex(df.index)
                d["amat_state_2"] = amat.iloc[:, 1].reindex(df.index) if len(amat.columns) > 1 else np.nan
                d["prev_amat_state_1"] = d["amat_state_1"].shift(1)
                d["prev_amat_state_2"] = d["amat_state_2"].shift(1)
                d["amat_bull_flip"] = (d["amat_state_1"] > 0) & (d["prev_amat_state_1"] <= 0)
                d["amat_bear_flip"] = (d["amat_state_2"] > 0) & (d["prev_amat_state_2"] <= 0)
        except Exception:
            pass
    d["prev_mfi_14"] = calc["mfi_14"].shift(1)
    d["mfi_bull_cross_30"] = (calc["mfi_14"] > 30) & (d["prev_mfi_14"] <= 30)
    d["mfi_bear_cross_70"] = (calc["mfi_14"] < 70) & (d["prev_mfi_14"] >= 70)
    fish = fisher_line(df_title, 9)
    d["fisher_debug"] = pd.Series(fish.get("fisher", []), index=df.index)
    d["fisher_signal_debug"] = pd.Series(fish.get("signal", []), index=df.index)
    d["prev_fisher"] = d["fisher_debug"].shift(1)
    d["prev_fisher_signal"] = d["fisher_signal_debug"].shift(1)
    d["fisher_bull_cross"] = (d["fisher_debug"] > d["fisher_signal_debug"]) & (d["prev_fisher"] <= d["prev_fisher_signal"])
    d["fisher_bear_cross"] = (d["fisher_debug"] < d["fisher_signal_debug"]) & (d["prev_fisher"] >= d["prev_fisher_signal"])
    return pd.concat([d, _market_profile_levels(df)], axis=1)


def _has_event(events: list[dict], t: str, name_contains: str | None = None) -> str:
    hits = []
    for e in events:
        if e.get("time") != t:
            continue
        if name_contains and name_contains.lower() not in str(e.get("name", "")).lower():
            continue
        hits.append(f"{e.get('name')}:{e.get('direction')}")
    return "|".join(hits)


def _signal_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v)


def _add_marker_audit(row: dict, prefix: str, signal_col: str, bull_col: str | None = None, bear_col: str | None = None) -> None:
    marker = bool(_signal_text(row.get(signal_col)))
    bull = bool(row.get(bull_col, False)) if bull_col else False
    bear = bool(row.get(bear_col, False)) if bear_col else False
    expected = bull or bear
    if expected and not marker and row.get("is_session_open_bar"):
        reason = "EXPECTED_BLOCKED_SESSION_OPEN"
    elif expected and not marker:
        reason = "MISSING_MARKER"
    elif marker and not expected:
        reason = "EXTRA_MARKER"
    elif marker and expected:
        reason = "OK"
    else:
        reason = "NO_SIGNAL"
    row[f"{prefix}_marker_present"] = marker
    row[f"{prefix}_expected_cross"] = expected
    row[f"{prefix}_bull_expected"] = bull
    row[f"{prefix}_bear_expected"] = bear
    row[f"{prefix}_block_reason"] = reason


def build_pack() -> dict:
    df = load_infy_5m().tail(CONTEXT_BARS)
    df_title = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    calc = add_indicators(df.copy())
    pta_payload = pta_marker_payload(df_title)
    self_payload = {
        "si_cdl": cdl_patterns_adv(df_title),
        "si_trend_sig": trend_signals_markers(df_title),
        "si_mp_va": mp_value_area_markers(df_title),
    }
    pta_events = _event_map(pta_payload)
    self_events = _event_map(self_payload)

    # Overlay/subpanel values used by chart.
    hma = hma_line(df_title, 20)
    aroon = aroon_lines(df_title, 25)
    if aroon.get("up") and aroon.get("down"):
        calc["aroon_up_25"] = pd.Series(aroon["up"], index=calc.index)
        calc["aroon_down_25"] = pd.Series(aroon["down"], index=calc.index)
    fisher = fisher_line(df_title, 9)
    mfi = mfi_line(df_title, 14)
    cdl = cdl_patterns(df_title)
    debug = build_debug_columns(df, df_title, calc)

    sample = calc.tail(SAMPLE_BARS).copy()
    rows = []
    for i, (ts, r) in enumerate(sample.iterrows()):
        pos = len(calc) - len(sample) + i
        t = ts.strftime("%Y-%m-%d %H:%M")
        row = {
            "time": t,
            "open": _round(r["open"], 4),
            "high": _round(r["high"], 4),
            "low": _round(r["low"], 4),
            "close": _round(r["close"], 4),
            "volume": int(r["volume"]),
            "doji_signal": _has_event(self_events.get("si_cdl", []), t, "Doji") or _has_event(cdl, t, "Doji"),
            "hma_20": hma[pos] if pos < len(hma) else None,
            "skew_reversal_signal": _has_event(pta_events.get("pta_skew", []), t),
            "zscore_signal": _has_event(pta_events.get("pta_zscore", []), t),
            "ttm_trend_signal": _has_event(pta_events.get("pta_ttm", []), t),
            "aroon_up_25": _round(r.get("aroon_up_25"), 4),
            "aroon_down_25": _round(r.get("aroon_down_25"), 4),
            "aroon_chart_up": aroon.get("up", [None])[pos] if pos < len(aroon.get("up", [])) else None,
            "aroon_chart_down": aroon.get("down", [None])[pos] if pos < len(aroon.get("down", [])) else None,
            "adx_14": _round(r.get("adx_14"), 4),
            "plus_di_14": _round(r.get("plus_di_14"), 4),
            "minus_di_14": _round(r.get("minus_di_14"), 4),
            "williams_r_14": _round(r.get("williams_r_14"), 4),
            "willr_bull": bool(r.get("willr_bull", False)),
            "willr_bear": bool(r.get("willr_bear", False)),
            "cci_20": _round(r.get("cci_20"), 4),
            "cci_bull": bool(r.get("cci_bull", False)),
            "cci_bear": bool(r.get("cci_bear", False)),
            "rsi_14": _round(r.get("rsi_14"), 4),
            "macd": _round(r.get("macd"), 6),
            "macd_signal_line": _round(r.get("macd_signal_line"), 6),
            "macd_hist": _round(r.get("macd_hist"), 6),
            "macd_bull": bool(r.get("macd_bull", False)),
            "macd_bear": bool(r.get("macd_bear", False)),
            "short_run_bear": bool(r.get("short_run_bear", False)),
            "long_run_bull": bool(r.get("long_run_bull", False)),
            "drawdown_pct": _round(r.get("drawdown_pct"), 6),
            "drawdown_recovery": bool(r.get("drawdown_recovery", False)),
            "trend_signal": _has_event(self_events.get("si_trend_sig", []), t),
            "ebsw_cycle_signal": _has_event(pta_events.get("pta_ebsw", []), t),
            "ts_signal": _has_event(self_events.get("si_trend_sig", []), t),
            "amat_signal": _has_event(pta_events.get("pta_amat", []), t),
            "hlc3_ma_signal": _has_event(pta_events.get("pta_hlc3", []), t),
            "aroon_signal": _has_event(pta_events.get("pta_aroon_sig", []), t),
            "vortex_signal": _has_event(pta_events.get("pta_vortex", []), t),
            "cmf_signal": _has_event(pta_events.get("pta_cmf", []), t),
            "mfi_14": _round(r.get("mfi_14"), 4),
            "mfi_chart": mfi[pos] if pos < len(mfi) else None,
            "mfi_signal": _has_event(pta_events.get("pta_mfi_sig", []), t),
            "long_return_momentum_signal": _has_event(pta_events.get("pta_log_ret", []), t),
            "tsi_signal": _has_event(pta_events.get("pta_tsi", []), t),
            "kdj_signal": _has_event(pta_events.get("pta_kdj", []), t),
            "fisher": fisher.get("fisher", [None])[pos] if pos < len(fisher.get("fisher", [])) else None,
            "fisher_signal_line": fisher.get("signal", [None])[pos] if pos < len(fisher.get("signal", [])) else None,
            "fisher_signal": _has_event(pta_events.get("pta_fisher_sig", []), t),
            "rsx_signal": _has_event(pta_events.get("pta_rsx", []), t),
            "market_profile_va_signal": _has_event(self_events.get("si_mp_va", []), t),
        }
        for col in debug.columns:
            val = debug[col].iloc[pos] if pos < len(debug) else None
            row[col] = bool(val) if isinstance(val, (bool, np.bool_)) else _round(val, 6)
        _add_marker_audit(row, "doji", "doji_signal", "doji_bool_exact")
        _add_marker_audit(row, "skew", "skew_reversal_signal", "skew_cross_below_minus_0_5")
        _add_marker_audit(row, "zscore", "zscore_signal", "zscore_bull_cross", "zscore_bear_cross")
        _add_marker_audit(row, "ttm", "ttm_trend_signal", "ttm_flip_bull")
        _add_marker_audit(row, "aroon", "aroon_signal", "aroon_bull_cross_exact", "aroon_bear_cross_exact")
        _add_marker_audit(row, "mfi", "mfi_signal", "mfi_bull_cross_30", "mfi_bear_cross_70")
        _add_marker_audit(row, "vortex", "vortex_signal", "vortex_bull_cross", "vortex_bear_cross")
        _add_marker_audit(row, "cmf", "cmf_signal", "cmf_cross_above_zero", "cmf_cross_below_zero")
        _add_marker_audit(row, "long_return", "long_return_momentum_signal", "log_return_bull_cross", "log_return_bear_cross")
        _add_marker_audit(row, "tsi", "tsi_signal", "tsi_bull_cross", "tsi_bear_cross")
        _add_marker_audit(row, "kdj", "kdj_signal", "kdj_bull_cross", "kdj_bear_cross")
        _add_marker_audit(row, "fisher", "fisher_signal", "fisher_bull_cross", "fisher_bear_cross")
        _add_marker_audit(row, "rsx", "rsx_signal", "rsx_bull_cross_50", "rsx_bear_cross_50")
        _add_marker_audit(row, "hlc3", "hlc3_ma_signal", "hlc3_bull_cross", "hlc3_bear_cross")
        _add_marker_audit(row, "ebsw", "ebsw_cycle_signal", "ebsw_cross_above_zero", "ebsw_cross_below_zero")
        _add_marker_audit(row, "amat", "amat_signal", "amat_bull_flip", "amat_bear_flip")
        _add_marker_audit(row, "market_profile_va", "market_profile_va_signal", "mp_cross_bull", "mp_cross_bear")
        rows.append(row)

    audit_rows = []
    for name in REQUESTED:
        signal_cols = [c for c in rows[0].keys() if name.lower().split()[0] in c.lower()]
        if name == "Williams %R":
            signal_cols = ["willr_bull", "willr_bear"]
        elif name == "RSI":
            signal_cols = ["rsi_14"]
        elif name == "MACD":
            signal_cols = ["macd_bull", "macd_bear"]
        count = 0
        for row in rows:
            for c in signal_cols:
                v = row.get(c)
                if v not in (False, "", None, 0):
                    count += 1
        key = name.lower().replace(" %r", "").replace("%", "").replace(" ", "_").replace("/", "_").replace("&", "and")
        prefix_map = {
            "doji": "doji", "skew_reversal": "skew", "zscore": "zscore", "ttm_trend": "ttm",
            "aroon_signal": "aroon", "vortex_signal": "vortex", "cmf_signal": "cmf",
            "mfi_signal": "mfi", "long_return_momentum": "long_return", "tsi_signal": "tsi",
            "kdj_signal": "kdj", "fisher_signal": "fisher", "rsx_signal": "rsx",
            "market_profile_va": "market_profile_va", "hlc3_ma": "hlc3", "ebsw_cycle": "ebsw",
            "amat_bull": "amat",
        }.get(key)
        block_counts = {}
        if prefix_map and rows:
            reason_col = f"{prefix_map}_block_reason"
            block_counts = pd.Series([row.get(reason_col, "") for row in rows]).value_counts().to_dict()
        audit_rows.append({
            "indicator": name,
            "formula": FORMULAS.get(name, ""),
            "sample_signal_or_value_count": count,
            "block_reason_counts": json.dumps(block_counts, sort_keys=True),
            "chart_source": "backend API payload; no frontend recalculation",
            "test_status": "NEEDS_REVIEW_BY_EXTERNAL_AI",
        })

    return {
        "symbol": "INFY",
        "tf": "5m_from_1m",
        "source": r"C:\Users\sakth\Downloads\HSTRY\INFY_NSE_1m.csv",
        "context_rows": len(df),
        "sample_rows": len(rows),
        "range": [str(df.index[0]), str(df.index[-1])],
        "rows": rows,
        "audit": audit_rows,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pack = build_pack()
    sample_csv = OUT_DIR / "INFY_5m_indicator_test_sample.csv"
    audit_csv = OUT_DIR / "INFY_5m_indicator_formula_signal_audit.csv"
    notes_md = OUT_DIR / "INFY_5m_indicator_formula_notes.md"
    prompt_md = OUT_DIR / "PROMPT_external_ai_indicator_review.md"
    json_file = OUT_DIR / "INFY_5m_indicator_test_pack.json"

    pd.DataFrame(pack["rows"]).to_csv(sample_csv, index=False)
    pd.DataFrame(pack["audit"]).to_csv(audit_csv, index=False)
    json_file.write_text(json.dumps(pack, indent=2, default=str), encoding="utf-8")

    notes = [
        "# Indicator Formula Notes",
        "",
        f"Symbol: {pack['symbol']}",
        f"TF: {pack['tf']}",
        f"Source: `{pack['source']}`",
        f"Range: {pack['range'][0]} to {pack['range'][1]}",
        "",
    ]
    for item in pack["audit"]:
        notes.append(f"## {item['indicator']}")
        notes.append(item["formula"])
        notes.append("Chart rule: backend calculates value/signal, frontend only displays it.")
        notes.append("Live safety rule: first candle of each session is blocked from marker output to avoid gap/open false signals.")
        notes.append("")
    notes_md.write_text("\n".join(notes), encoding="utf-8")

    prompt = f"""Review these indicator calculations like a strict trading-system auditor.

Goal:
Check formula correctness, signal correctness, no lookahead, no repeated false signal, no buy+sell same candle, and whether chart output should match backend output.

Data source:
{pack['source']}

Timeframe:
INFY 1m resampled to 5m.

Files I will paste/upload:
1. Formula notes: {notes_md.name}
2. Sample calculated rows: {sample_csv.name}
3. Audit summary: {audit_csv.name}

Indicators to review:
{", ".join(REQUESTED)}

For each indicator return this exact format:

Indicator:
Formula correct: YES/NO/UNCLEAR
Signal timing correct: YES/NO/UNCLEAR
Lookahead risk: YES/NO/UNCLEAR
Chart display should be: overlay/subpanel/marker/level/filter
TradingView match expected: YES/NO/PARTIAL/NO_STANDARD_EQUIVALENT
Problem found:
Fix needed:
Trader use: entry/filter/warning only
Final status: READY / FIX / DO NOT USE

Rules:
- Do not assume. Use only formula notes and sample rows.
- First candle of each session is intentionally blocked from chart marker output. If a debug cross is true on 09:15 but marker is blank, mark it as EXPECTED_BLOCKED, not a formula bug.
- If sample rows are not enough, say exactly what extra rows/columns are needed.
- Standard indicators must match common formula unless notes say custom.
- Custom indicators must be judged by source formula and signal behavior.
"""
    prompt_md.write_text(prompt, encoding="utf-8")
    print(json.dumps({
        "sample_csv": str(sample_csv.resolve()),
        "audit_csv": str(audit_csv.resolve()),
        "notes_md": str(notes_md.resolve()),
        "prompt_md": str(prompt_md.resolve()),
        "json": str(json_file.resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
