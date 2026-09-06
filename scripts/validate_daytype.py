"""Validate the day-type condition engine on real HSTRY sessions.

For each session: opening scenario (prev-day data only) -> prediction, then
ex-post outcome label from the completed day -> confusion matrix + hit rates.
Writes delete/daytype_validation.json + .md
"""

import json
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

import pandas as pd

from app.orb import context as C
from app.orb.hstry_csv import load_hstry_series

SYMBOLS = ["RELIANCE", "BEL", "TCS", "INFY", "HDFCBANK"]
START = "2024-01-01"


def main() -> None:
    matrix: Counter = Counter()
    directional_hits = directional_total = 0
    coverage = Counter()
    for symbol in SYMBOLS:
        series = load_hstry_series(symbol, "5m", start_date=START)
        frame = pd.DataFrame(
            [{"open": b.open, "high": b.high, "low": b.low, "close": b.close,
              "volume": b.volume or 0.0} for b in series.bars],
            index=pd.to_datetime([b.timestamp_ns for b in series.bars]),
        )
        frame.index = frame.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
        daily = C.daily_from_intraday(frame)
        dates = sorted({ts.strftime("%Y-%m-%d") for ts in frame.index})
        opens = {}
        daybars = {}
        for d in dates:
            bars = frame[frame.index.strftime("%Y-%m-%d") == d]
            if len(bars):
                opens[d] = float(bars.iloc[0]["open"])
                daybars[d] = bars
        for rec in C.classify_history(symbol, daily, opens):
            day = daybars.get(rec["session_date"])
            if day is None or len(day) < 10:
                continue
            window = daily.loc[: rec["session_date"]].iloc[-16:-1]
            atr = C.atr_wilder(window["high"], window["low"], window["close"], 14)
            outcome = C.label_day_outcome(
                day_high=float(day["high"].max()), day_low=float(day["low"].min()),
                day_close=float(day["close"].iloc[-1]), atr14=atr)
            pred = C.predict_day_type(rec)
            matrix[(pred["prediction"], outcome)] += 1
            coverage[pred["prediction"]] += 1
            if pred["prediction"] in ("TREND_DAY", "RANGE_DAY") and pred["direction"] != "either":
                directional_total += 1
                day_dir = "up" if float(day["close"].iloc[-1]) >= float(day["open"].iloc[0]) else "down"
                if pred["direction"] == day_dir and outcome == ("TREND_DAY" if pred["prediction"] == "TREND_DAY" else outcome):
                    directional_hits += 1
        print(f"  {symbol} done")

    total = sum(matrix.values())
    trend_hit = matrix[("TREND_DAY", "TREND_DAY")] / max(1, sum(v for k, v in matrix.items() if k[0] == "TREND_DAY"))
    range_hit = matrix[("RANGE_DAY", "RANGE_DAY")] / max(1, sum(v for k, v in matrix.items() if k[0] == "RANGE_DAY"))
    out = {
        "generated_at": datetime.now().isoformat(), "symbols": SYMBOLS,
        "confusion": {f"{p}->{a}": n for (p, a), n in sorted(matrix.items())},
        "trend_precision": round(trend_hit, 3), "range_precision": round(range_hit, 3),
        "directional_hit_rate": round(directional_hits / max(1, directional_total), 3),
        "coverage": dict(coverage), "total_sessions": total,
    }
    base = r"D:\Projects\trading-platforms\stock-app\trade-vision-app\delete\daytype_validation"
    with open(base + ".json", "w") as f:
        json.dump(out, f, indent=1)
    lines = ["# Day-type validation (prediction vs completed-session outcome)", "",
             f"sessions={total} coverage={dict(coverage)}", "",
             "## Confusion (predicted -> actual)"]
    for k in sorted(out["confusion"]):
        lines.append(f"- {k}: {out['confusion'][k]}")
    lines += ["",
              f"TREND precision (predicted TREND that trended): {out['trend_precision']}",
              f"RANGE precision (predicted RANGE that ranged): {out['range_precision']}",
              f"Directional hit rate: {out['directional_hit_rate']}"]
    with open(base + ".md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("saved to delete/daytype_validation.json + .md")


if __name__ == "__main__":
    main()
