import pandas as pd

from shared.indicators.self_indc import LiquidityEntrySettings, LiquidityEntryZones, compute_all, liquidity_entry


def _base_frame(n=80, base=100.0):
    idx = pd.date_range("2026-05-01 09:15", periods=n, freq="5min")
    rows = [[base, base + 0.4, base - 0.4, base + 0.1, 1000] for _ in range(n)]
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx)


def test_liquidity_entry_bullish_sweep_structural_rr():
    df = _base_frame()
    # Confirmed pivot low at bar 20 is stored at bar 25.
    df.iloc[20] = [100.0, 100.3, 98.0, 100.1, 1200]
    df.iloc[30] = [100.0, 100.5, 97.0, 100.2, 1500]
    df.iloc[31] = [100.2, 102.0, 100.0, 101.5, 1500]
    settings = LiquidityEntrySettings(
        use_local_ema_filter=False,
        min_sweep_distance_pips=1,
        min_candle_range_pips=1,
        require_midline_break=False,
        signal_cooldown_bars=0,
    )

    result = LiquidityEntryZones(settings, asset_type="stock", min_tick=0.01).run(df)

    assert result["sweep_detected"].iloc[30]
    assert result["sweep_type"].iloc[30] == "bull"
    assert result["buy_signal"].iloc[31]
    entry = result["trade_entry"].iloc[31]
    sl = result["trade_sl"].iloc[31]
    tp = result["trade_tp"].iloc[31]
    assert round(sl, 4) == 97.0
    assert round(tp, 4) == round(entry + (entry - sl) * 2.0, 4)


def test_liquidity_entry_bearish_sweep_structural_rr():
    df = _base_frame()
    # Confirmed pivot high at bar 20 is stored at bar 25.
    df.iloc[20] = [100.0, 102.0, 99.7, 100.1, 1200]
    df.iloc[30] = [100.0, 103.0, 99.5, 99.8, 1500]
    df.iloc[31] = [99.8, 100.0, 98.0, 98.5, 1500]
    settings = LiquidityEntrySettings(
        use_local_ema_filter=False,
        min_sweep_distance_pips=1,
        min_candle_range_pips=1,
        require_midline_break=False,
        signal_cooldown_bars=0,
    )

    result = LiquidityEntryZones(settings, asset_type="stock", min_tick=0.01).run(df)

    assert result["sweep_detected"].iloc[30]
    assert result["sweep_type"].iloc[30] == "bear"
    assert result["sell_signal"].iloc[31]
    entry = result["trade_entry"].iloc[31]
    sl = result["trade_sl"].iloc[31]
    tp = result["trade_tp"].iloc[31]
    assert round(sl, 4) == 103.0
    assert round(tp, 4) == round(entry - (sl - entry) * 2.0, 4)


def test_liquidity_entry_contract_and_compute_all():
    df = _base_frame()
    out = liquidity_entry(df)

    assert set(out) == {"signals", "sweeps", "levels", "trade_lines", "quality"}
    assert set(out["trade_lines"]) == {"entry", "sl", "tp"}
    assert len(out["trade_lines"]["entry"]) == len(df)
    assert len(out["quality"]) == len(df)
    assert out["signals"] == []

    all_ind = compute_all(df)
    assert "si_liquidity_entry" in all_ind
    assert set(all_ind["si_liquidity_entry"]) == {"signals", "sweeps", "levels", "trade_lines", "quality"}
