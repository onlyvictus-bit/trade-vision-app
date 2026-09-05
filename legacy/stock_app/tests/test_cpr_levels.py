import pandas as pd

from shared.indicators.self_indc import cpr_levels


def test_cpr_levels_match_tradingview_daily_formula():
    idx = pd.to_datetime([
        "2026-05-01 09:30",
        "2026-05-01 15:30",
        "2026-05-04 09:30",
        "2026-05-04 10:00",
    ])
    df = pd.DataFrame({
        "Open": [145.0, 146.0, 146.0, 147.0],
        "High": [149.9, 148.0, 150.0, 151.0],
        "Low": [143.0, 144.0, 145.0, 146.0],
        "Close": [146.0, 144.2, 148.0, 149.0],
        "Volume": [1000, 1000, 1000, 1000],
    }, index=idx)

    out = cpr_levels(df)
    series = out["series"]

    assert series["p"][2] == 145.70
    assert series["bc"][2] == 146.45
    assert series["tc"][2] == 144.95
    assert series["prev_day_high"][2] == 149.90
    assert series["prev_day_low"][2] == 143.00
    assert series["r1"][2] == 148.40
    assert series["r2"][2] == 152.60
    assert series["r3"][2] == 155.30
    assert series["r4"][2] == 159.50
    assert series["s1"][2] == 141.50
    assert series["s2"][2] == 138.80
    assert series["s3"][2] == 134.60
    assert series["s4"][2] == 131.90
    assert series["p"][2] == series["p"][3]
