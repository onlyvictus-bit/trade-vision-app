import pandas as pd

from shared.indicators.self_indc import compute_all, hyb_opening_range_reversal


def test_hyb_opening_range_reversal_filters_and_contract():
    idx = pd.date_range("2026-05-01 09:30", periods=60, freq="5min")
    rows = []
    for ts in idx:
        if ts.time() < pd.Timestamp("2026-05-01 10:00").time():
            rows.append([100.0, 101.0, 99.0, 100.0, 1000])
        elif ts.time() == pd.Timestamp("2026-05-01 10:05").time():
            # Touch OR low with high volume and pass permissive filters.
            rows.append([100.5, 101.0, 98.9, 100.8, 3000])
        elif ts.time() == pd.Timestamp("2026-05-01 10:10").time():
            rows.append([100.8, 101.2, 100.0, 101.0, 2500])
        else:
            rows.append([100.2, 100.8, 99.8, 100.4, 1200])

    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"], index=idx)

    out = hyb_opening_range_reversal(
        df,
        volume_mult=0.5,
        atr_min_mult=0.1,
        use_vwap_filter=False,
        use_rsi_filter=False,
    )

    assert "signals" in out
    assert "rejected" in out
    assert "quality" in out
    assert len(out["long"]) == len(df)
    assert len(out["short"]) == len(df)
    assert len(out["exit"]) == len(df)
    assert len(out["or_high"]) == len(df)
    assert len(out["or_low"]) == len(df)
    assert any(e["name"] == "Hyb ORR Long" and e["direction"] == "bull" and "quality" in e for e in out["signals"])
    assert out["trades"] and "quality_score" in out["trades"][0]
    assert "volume" in out["trades"][0]["filters"]

    all_ind = compute_all(df)
    assert "si_hyb_opening_range_rev" in all_ind
    assert "signals" in all_ind["si_hyb_opening_range_rev"]
