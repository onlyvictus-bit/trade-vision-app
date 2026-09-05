from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TRADE_VISION_SCRIPT = ROOT / "scripts" / "build_multitimeframe_research_report.py"
TRADE_VISION_JSON = ROOT / "data" / "validation" / "RELIANCE_multitimeframe_research.json"
TRADE_VISION_MARKDOWN = ROOT / "docs" / "test-reports" / "RELIANCE_MULTITIMEFRAME_RESEARCH.md"
SERVICE_ROOT = ROOT / "apps" / "kronos-service"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Trade Vision and real Kronos side by side on identical RELIANCE candles.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--symbol", default="RELIANCE")
    parser.add_argument("--lookback", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--kronos-model", choices=["Kronos-mini", "Kronos-base"], default="Kronos-mini")
    args = parser.parse_args()
    model_slug = args.kronos_model.lower().replace("-", "_")
    output_json = ROOT / "data" / "validation" / f"RELIANCE_twin_{model_slug}_research.json"
    output_markdown = ROOT / "docs" / "test-reports" / f"RELIANCE_TWIN_{model_slug.upper()}_RESEARCH.md"

    _refresh_trade_vision(args.csv_path, args.symbol)
    trade_vision = json.loads(TRADE_VISION_JSON.read_text(encoding="utf-8"))
    tv_module = _load_module("tradevision_multitimeframe", TRADE_VISION_SCRIPT)
    kronos_module = _load_module("tradevision_kronos_service", SERVICE_ROOT / "main.py", add_path=SERVICE_ROOT)
    minute = tv_module.load_source(args.csv_path)
    comparisons: dict[str, dict[str, object]] = {}

    for index, (timeframe, config) in enumerate(tv_module.TIMEFRAMES.items()):
        raw_frame = tv_module.aggregate(minute, timeframe, config["rule"])
        source_frame = raw_frame.tail(args.lookback)
        service_timeframe = {"daily": "1D", "weekly": "1W"}.get(timeframe, timeframe)
        bars = [
            kronos_module.CandleBar(
                symbol=args.symbol.upper(),
                timeframe=service_timeframe,
                timestamp_ns=int(timestamp.tz_convert("UTC").value),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                source="historical",
                sequence_number=sequence,
            )
            for sequence, (timestamp, row) in enumerate(source_frame.iterrows(), start=1)
        ]
        snapshot_id = f"{args.symbol.lower()}-{trade_vision['source_last_timestamp']}-{timeframe}-{len(bars)}"
        series = kronos_module.CandleSeries(
            symbol=args.symbol.upper(),
            timeframe=service_timeframe,
            bars=bars,
            snapshot_id=snapshot_id,
            schema_version="candles.tradevision.point_in_time.v1",
        )
        request = kronos_module.KronosForecastRequest(
            symbol=args.symbol.upper(),
            timeframe=service_timeframe,
            seed=args.seed + index,
            lookback_candles=len(bars),
            forecast_horizon_bars=int(config["horizon"]),
            decision_time_ns=bars[-1].timestamp_ns,
            series=series,
            replay_snapshot_id=snapshot_id,
            model_name=args.kronos_model,
        )
        kronos = kronos_module._real_forecast(request)
        behavior = trade_vision["timeframes"][timeframe]
        twin = _compare(behavior, kronos)
        comparisons[timeframe] = {
            "input": {
                "snapshot_id": snapshot_id,
                "candle_count": len(bars),
                "last_timestamp": source_frame.index[-1].isoformat(),
                "input_snapshot_hash": kronos["input_snapshot_hash"],
                "same_point_in_time_source": source_frame.index[-1].isoformat() == behavior["as_of"],
            },
            "trade_vision": {
                "recommendation": behavior["recommendation"],
                "raw_action": behavior["raw_action"],
                "analysis_direction": behavior["analysis_direction"],
                "directional_score": behavior["directional_score"],
                "patterns": behavior["patterns"],
                "analog_summary": behavior["analog_summary"],
                "plan": behavior["plan"],
            },
            "kronos": {
                "model_name": kronos["model_name"],
                "model_version": kronos["model_version"],
                "tokenizer_name": kronos["tokenizer_name"],
                "direction": kronos["forecast_path"]["trend_direction"],
                "expected_return_pct": kronos["forecast_path"]["expected_return_pct"],
                "expected_move_atr": kronos["forecast_path"]["expected_move_atr"],
                "continuation_probability": kronos["forecast_path"]["continuation_probability"],
                "reversal_probability": kronos["forecast_path"]["reversal_probability"],
                "range_probability": kronos["forecast_path"]["range_probability"],
                "forecast_confidence": kronos["forecast_confidence"],
                "forecast_path": kronos["forecast_path"]["candles"],
                "sanity_check": kronos["sanity_check"],
                "output_hash": kronos["output_hash"],
                "notes": kronos["notes"],
            },
            "twin": twin,
        }

    output = {
        "version": "tradevision-kronos-twin-real.v0.48",
        "symbol": args.symbol.upper(),
        "point_in_time": trade_vision["source_last_timestamp"],
        "source_file": str(args.csv_path.resolve()),
        "engines": {
            "trade_vision": "Compact candle/indicator/history behavior analyzer",
            "kronos": f"Real NeoQuasar/{args.kronos_model} with its official paired tokenizer",
            "twin": "Conflict-reducing research arbiter; never order authority",
        },
        "timeframes": comparisons,
        "overall": _overall(comparisons),
        "safety": {
            "research_only": True,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "warning": "Source ends 2026-03-20. This is historical validation, not a current market recommendation.",
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(_markdown(output), encoding="utf-8")
    print(json.dumps({"json": str(output_json), "markdown": str(output_markdown), "overall": output["overall"]}, indent=2))
    return 0


def _refresh_trade_vision(csv_path: Path, symbol: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(TRADE_VISION_SCRIPT),
            str(csv_path),
            "--symbol",
            symbol,
            "--output",
            str(TRADE_VISION_JSON),
            "--markdown",
            str(TRADE_VISION_MARKDOWN),
        ],
        cwd=ROOT,
        check=True,
    )


def _load_module(name: str, path: Path, *, add_path: Path | None = None):
    if add_path is not None and str(add_path) not in sys.path:
        sys.path.insert(0, str(add_path))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _compare(behavior: dict[str, object], kronos: dict[str, object]) -> dict[str, object]:
    recommendation = str(behavior["recommendation"])
    behavior_direction = str(behavior["analysis_direction"])
    kronos_direction = str(kronos["forecast_path"]["trend_direction"])
    sanity = bool(kronos["sanity_check"]["passed"])
    if not sanity:
        state, action, reason = "KRONOS_BLOCKED", "WAIT", "Kronos failed sanity checks."
    elif recommendation == "WAIT":
        aligned = behavior_direction == kronos_direction
        state = "LATENT_AGREEMENT_BUT_BEHAVIOR_WAIT" if aligned else "SOFT_CONFLICT"
        action = "WAIT"
        reason = "Trade Vision did not pass its evidence gates; Kronos cannot promote it."
    elif recommendation == kronos_direction:
        state, action, reason = f"AGREE_{kronos_direction}", "RESEARCH_CANDIDATE", "Both engines align, subject to risk and replay validation."
    else:
        state, action, reason = "HARD_CONFLICT", "WAIT", "Trade Vision and Kronos disagree on direction."
    return {
        "agreement_state": state,
        "arbiter_action": action,
        "reason": reason,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _overall(comparisons: dict[str, dict[str, object]]) -> dict[str, object]:
    actions = {timeframe: value["twin"]["arbiter_action"] for timeframe, value in comparisons.items()}
    kronos_directions = {timeframe: value["kronos"]["direction"] for timeframe, value in comparisons.items()}
    trade_vision = {timeframe: value["trade_vision"]["recommendation"] for timeframe, value in comparisons.items()}
    return {
        "result": "NO_TRADE" if any(action == "WAIT" for action in actions.values()) else "RESEARCH_CANDIDATE",
        "trade_vision_actions": trade_vision,
        "kronos_directions": kronos_directions,
        "twin_actions": actions,
        "reason": "Any unresolved timeframe conflict or Trade Vision WAIT keeps the overall decision at NO_TRADE.",
    }


def _markdown(output: dict[str, object]) -> str:
    lines = [
        "# RELIANCE Trade Vision + Real Kronos Twin Report",
        "",
        f"**Point-in-time:** {output['point_in_time']}",
        "",
        "> Historical research using data ending March 20, 2026. It is not a current recommendation.",
        "",
        "| TF | Trade Vision | Raw Bias | Present Patterns | Kronos | Expected Return | Twin | Entry / SL / T1 |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    for timeframe, comparison in output["timeframes"].items():
        tv = comparison["trade_vision"]
        kronos = comparison["kronos"]
        twin = comparison["twin"]
        plan = tv["plan"]
        patterns = ", ".join(tv["patterns"][:3])
        levels = f"{plan['entry_low']:.2f}-{plan['entry_high']:.2f} / {plan['stop_loss']:.2f} / {plan['target_1r']:.2f}"
        lines.append(
            f"| {timeframe} | **{tv['recommendation']}** | {tv['analysis_direction']} | {patterns} | "
            f"**{kronos['direction']}** | {kronos['expected_return_pct']:.2f}% | **{twin['arbiter_action']}** | {levels} |"
        )
    lines.extend(["", "## Engine Evidence", ""])
    for timeframe, comparison in output["timeframes"].items():
        kronos = comparison["kronos"]
        lines.extend(
            [
                f"### {timeframe}",
                f"- Same snapshot: `{comparison['input']['same_point_in_time_source']}`",
                f"- Trade Vision analog evidence: `{comparison['trade_vision']['analog_summary']['match_count']}` matches",
                f"- Kronos: `{kronos['model_name']}` / `{kronos['model_version']}`",
                f"- Kronos direction: **{kronos['direction']}**, expected move `{kronos['expected_move_atr']}` ATR",
                f"- Twin: **{comparison['twin']['agreement_state']}** - {comparison['twin']['reason']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Overall",
            "",
            f"**{output['overall']['result']}**",
            "",
            output["overall"]["reason"],
            "",
            "Trade permission and order routing remain disabled.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
