import pandas as pd

from shared.indicators.self_indc import compute_all, opening_range_reversal


def test_opening_range_reversal_red_entry_contract():
    idx = pd.date_range("2026-05-01 09:30", periods=48, freq="5min")
    rows = []
    for ts in idx:
        if ts.time() < pd.Timestamp("2026-05-01 10:00").time():
            rows.append([100.0, 101.0, 99.0, 100.0, 1000])
        elif ts.time() == pd.Timestamp("2026-05-01 10:05").time():
            # Touch OR low, then rally to midpoint TP on the same bar.
            rows.append([99.5, 100.1, 98.9, 99.8, 1500])
        else:
            rows.append([100.0, 100.3, 99.7, 100.0, 1000])

    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"], index=idx)

    out = opening_range_reversal(df)

    assert "signals" in out
    assert "long" in out and "short" in out and "exit" in out
    assert len(out["or_high"]) == len(df)
    assert len(out["or_low"]) == len(df)
    assert len(out["tp"]) == len(df)
    assert len(out["sl"]) == len(df)
    assert any(e["name"] == "ORR Long" and e["direction"] == "bull" for e in out["signals"])
    assert any(e["name"].startswith("ORR Exit") for e in out["signals"])
    assert out["trades"] and out["trades"][0]["exit_reason"] in {"tp", "sl", "eod"}

    all_ind = compute_all(df)
    assert "si_opening_range_rev" in all_ind
    assert "signals" in all_ind["si_opening_range_rev"]
