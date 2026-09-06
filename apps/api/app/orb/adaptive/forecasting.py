"""Separated structural labels, chronological frequency models and evaluation.

Only two structural events have implemented labelers here. Trade-outcome,
wait-value and institutional-cause probabilities are never substituted for
these targets. No fitted/validated real-data artifact ships with this release.
"""
from __future__ import annotations
from collections import defaultdict
from math import log, sqrt
from statistics import mean
from typing import Literal

from .contracts import (Bar, Candidate, Forecast, Frozen, MarketSnapshot, MINUTE,
                        digest, evolve)


class Label(Frozen):
    forecast_id: str
    episode_id: str
    session_date: str
    symbol: str
    event: str
    horizon_minutes: int
    issued_ns: int
    matured_ns: int
    event_observed_ns: int | None = None
    status: Literal["KNOWN", "CENSORED"]
    outcome: Literal[0, 1] | None
    context_key: str
    rules_hash: str
    source_origin: Literal["REAL_ATTESTED", "SYNTHETIC"]


def context_key(features: dict) -> str:
    return ":".join((str(features.get("gap_direction", "UNKNOWN")),
                     "EXTENDED" if features.get("extension_or", 0) > .5 else "NEAR",
                     "RECLAIM" if features.get("failure_count", 0) else "INITIAL",
                     "CLOCK_"+str(int(features.get("elapsed_minutes",0))//15)))


def label_structural(forecast: Forecast, snapshot: MarketSnapshot, future: tuple[Bar, ...],
                     features: dict, *, rules_hash: str, source_origin: str) -> Label:
    """Outcome-only interface. Never called by Controller.evaluate().

    Known label requires the entire horizon, even for early positive events;
    incomplete records are not converted to zero or silently dropped.
    """
    if forecast.snapshot_hash != snapshot.snapshot_hash:
        raise ValueError("FORECAST_SNAPSHOT_IDENTITY_MISMATCH")
    if forecast.event not in {"RETURN_INSIDE_OR", "PDC_TOUCH"}:
        raise ValueError("NO_STRUCTURAL_LABELER_FOR_THIS_ACTION_DEPENDENT_TARGET")
    if not snapshot.bars:
        raise ValueError("MISSING_ISSUE_PREFIX")
    step = snapshot.bars[-1].minutes * MINUTE
    start = snapshot.bars[-1].close_ns
    end = forecast.effective_end_ns
    bars = [b for b in future if start <= b.open_ns < end]
    known = (len(bars) == forecast.horizon_bars and
             [b.open_ns for b in bars] == list(range(start, end, step)) and
             all(b.symbol == forecast.symbol and b.price_basis == snapshot.prior.price_basis and
                 b.minutes == snapshot.bars[-1].minutes and b.revision == 0 for b in bars))
    event_at = None
    if known:
        for b in bars:
            if forecast.event == "RETURN_INSIDE_OR":
                hit = b.close <= features["or_high"] if features["gap_direction"] == "LONG" else b.close >= features["or_low"]
            else:
                hit = b.low <= snapshot.prior.close if features["gap_direction"] == "LONG" else b.high >= snapshot.prior.close
            if hit:
                # Interval close is observation time, not invented touch time.
                event_at = b.available_ns
                break
    # Do not call an event first detected at issue time a prediction.
    if event_at is not None and event_at <= forecast.issued_ns:
        raise ValueError("DETECTION_IS_NOT_A_POSITIVE_LEAD_TIME_FORECAST")
    return Label(forecast_id=forecast.forecast_id, episode_id=forecast.episode_id,
                 session_date=forecast.session_date, symbol=forecast.symbol,
                 event=forecast.event, horizon_minutes=forecast.horizon_minutes,
                 issued_ns=forecast.issued_ns, matured_ns=max([end, *[b.available_ns for b in bars]]),
                 event_observed_ns=event_at, status="KNOWN" if known else "CENSORED",
                 outcome=int(event_at is not None) if known else None,
                 context_key=context_key(features), rules_hash=rules_hash, source_origin=source_origin)


def unique_date_cells(rows: tuple[Label, ...]) -> tuple[Label, ...]:
    # Earliest issued episode per date and conditional cell. Simultaneous
    # symbols are not claimed as extra independent dates. Population is this
    # deterministic sampling rule, not every intraday alert on every symbol.
    seen = set()
    out = []
    for row in sorted(rows, key=lambda x: (x.issued_ns, x.symbol, x.forecast_id)):
        key = (row.session_date, row.event, row.horizon_minutes, row.context_key)
        if key not in seen:
            seen.add(key)
            out.append(row)
    return tuple(out)


def probability_metrics(pairs: tuple[tuple[float, int], ...]) -> dict:
    if not pairs:
        return {"count": 0, "brier": None, "log_loss": None, "ece": None, "bins": []}
    buckets = defaultdict(list)
    for p, y in pairs:
        if not 0 <= p <= 1 or y not in (0,1):
            raise ValueError("INVALID_PROBABILITY_OR_LABEL")
        buckets[min(4, int(p*5))].append((p, y))
    bins = [{"bin": b, "count": len(v), "predicted": mean(x[0] for x in v),
             "observed": mean(x[1] for x in v)} for b, v in sorted(buckets.items())]
    return {"count": len(pairs), "brier": mean((p-y)**2 for p,y in pairs),
            "log_loss": -mean(y*log(max(1e-12,p)) + (1-y)*log(max(1e-12,1-p)) for p,y in pairs),
            "ece": sum(b["count"]*abs(b["predicted"]-b["observed"]) for b in bins)/len(pairs), "bins": bins}


class FrequencyCell(Frozen):
    key: str
    probability: float
    interval: tuple[float, float]
    unique_dates: int


class FrequencyModel(Frozen):
    symbols: tuple[str, ...]
    pipeline_code_hash: str
    version: Literal["frequency-baseline-1"] = "frequency-baseline-1"
    rules_hash: str
    event: str
    horizon_minutes: int
    trained_through_ns: int
    calibration_through_ns: int
    validated_through_ns: int
    train_dates: tuple[str, ...]
    calibration_dates: tuple[str, ...]
    test_dates: tuple[str, ...]
    cells: tuple[FrequencyCell, ...]
    baseline_probability: float
    calibration_metrics: dict
    test_metrics: dict
    source_origin: Literal["REAL_ATTESTED", "SYNTHETIC"]
    status: Literal["SUPPORTED_BY_DECLARED_TESTS", "UNSUPPORTED"]
    min_unique_dates: int
    model_hash: str


def _cell_key(row: Label) -> str:
    return row.context_key


def fit_frequency_model(train: tuple[Label, ...], calibration: tuple[Label, ...],
                        test: tuple[Label, ...], *, min_unique_dates: int = 20) -> FrequencyModel:
    """Fit earlier-only cells; calibration and test do NOT alter estimates.

    Calibration is a held-later reliability assessment, not a claim that a
    chosen binning method universally calibrates probabilities. Counts and
    class support are explicit acceptance choices requiring research review.
    """
    if min_unique_dates < 2 or not train or not calibration or not test:
        raise ValueError("THREE_NONEMPTY_CHRONOLOGICAL_SEGMENTS_REQUIRED")
    all_rows = train + calibration + test
    identities = {(r.rules_hash, r.event, r.horizon_minutes) for r in all_rows}
    if len(identities) != 1:
        raise ValueError("MIXED_EVENT_HORIZON_OR_POLICY_LABELS")
    if any(r.matured_ns <= r.issued_ns or r.status != "KNOWN" or r.outcome is None for r in all_rows):
        raise ValueError("CENSORED_OR_NON_CAUSAL_LABELS_CANNOT_TRAIN_MODEL")
    if not max(r.session_date for r in train) < min(r.session_date for r in calibration) <= max(r.session_date for r in calibration) < min(r.session_date for r in test):
        raise ValueError("DATE_GROUPS_OVERLAP_OR_ARE_NOT_CHRONOLOGICAL")
    if max(r.matured_ns for r in train) >= min(r.issued_ns for r in calibration) or max(r.matured_ns for r in calibration) >= min(r.issued_ns for r in test):
        raise ValueError("LABEL_HORIZON_CROSSES_FOLD_BOUNDARY")
    train, calibration, test = map(unique_date_cells, (train, calibration, test))
    grouped = defaultdict(list)
    for row in train:
        grouped[_cell_key(row)].append(row.outcome)
    # Smoothing to a data-derived baseline; no arbitrary 50% missing prior.
    baseline = mean(r.outcome for r in train)
    cells = []
    for key, outcomes in sorted(grouped.items()):
        n = len(outcomes)
        phat = mean(outcomes)
        z = 1.959963984540054
        denom = 1 + z*z/n
        center = (phat + z*z/(2*n))/denom
        half = z*sqrt(phat*(1-phat)/n + z*z/(4*n*n))/denom
        cells.append(FrequencyCell(key=key, probability=(sum(outcomes)+5*baseline)/(n+5),
                                   interval=(max(0.,center-half), min(1.,center+half)), unique_dates=n))
    lookup = {c.key:c for c in cells}
    def metrics(rows):
        pairs = tuple((lookup[r.context_key].probability, r.outcome) for r in rows
                      if r.context_key in lookup and lookup[r.context_key].unique_dates >= min_unique_dates)
        result = probability_metrics(pairs)
        result["unsupported_count"] = len(rows)-len(pairs)
        result["baseline_brier"] = mean((baseline-r.outcome)**2 for r in rows)
        return result
    cm, tm = metrics(calibration), metrics(test)
    real = all(r.source_origin == "REAL_ATTESTED" for r in all_rows)
    supported = (real and len({r.session_date for r in calibration}) >= min_unique_dates and
                 len({r.session_date for r in test}) >= min_unique_dates and
                 {r.outcome for r in train} == {0,1} and {r.outcome for r in test} == {0,1} and
                 cm["unsupported_count"] == 0 and tm["unsupported_count"] == 0 and
                 cm["ece"] is not None and cm["ece"] <= .15 and tm["ece"] <= .15 and
                 tm["brier"] <= tm["baseline_brier"] + 1e-12)
    rules, event, horizon = next(iter(identities))
    from .governance import code_fingerprint
    supported_symbols = tuple(sorted(sym for sym in {r.symbol for r in train} if
        len({r.session_date for r in train if r.symbol == sym}) >= min_unique_dates and
        len({r.session_date for r in test if r.symbol == sym}) >= min_unique_dates))
    payload = dict(symbols=supported_symbols, pipeline_code_hash=code_fingerprint(), rules_hash=rules, event=event, horizon_minutes=horizon,
                   trained_through_ns=max(r.matured_ns for r in train),
                   calibration_through_ns=max(r.matured_ns for r in calibration),
                   validated_through_ns=max(r.matured_ns for r in test),
                   train_dates=tuple(sorted({r.session_date for r in train})),
                   calibration_dates=tuple(sorted({r.session_date for r in calibration})),
                   test_dates=tuple(sorted({r.session_date for r in test})),
                   cells=tuple(c.model_dump(mode="json") for c in cells),
                   baseline_probability=baseline, calibration_metrics=cm, test_metrics=tm,
                   source_origin="REAL_ATTESTED" if real else "SYNTHETIC",
                   status="SUPPORTED_BY_DECLARED_TESTS" if supported else "UNSUPPORTED",
                   min_unique_dates=min_unique_dates)
    return FrequencyModel(**payload, model_hash=digest(payload))


class FrequencyForecaster:
    def __init__(self, model: FrequencyModel, rules_hash: str):
        data = model.model_dump(mode="json", exclude={"model_hash", "version"})
        if digest(data) != model.model_hash or model.rules_hash != rules_hash:
            raise ValueError("MODEL_INTEGRITY_OR_RULE_BINDING_FAILED")
        from .governance import code_fingerprint
        if model.pipeline_code_hash != code_fingerprint():
            raise ValueError("FORECAST_PIPELINE_CHANGED_REVALIDATE_MODEL")
        self.model, self.model_hash = model, model.model_hash

    def estimate(self, forecast: Forecast, features: dict) -> Forecast:
        m = self.model
        if m.status != "SUPPORTED_BY_DECLARED_TESTS" or m.validated_through_ns >= forecast.issued_ns or forecast.symbol not in m.symbols:
            return evolve(forecast, reason="MODEL_UNSUPPORTED_OR_NOT_AVAILABLE_BEFORE_FORECAST")
        if forecast.event != m.event or forecast.horizon_minutes != m.horizon_minutes:
            return forecast
        cell = next((c for c in m.cells if c.key == context_key(features)), None)
        if not cell or cell.unique_dates < m.min_unique_dates:
            return evolve(forecast, reason="OUT_OF_SUPPORT_CONDITIONAL_CELL")
        return evolve(forecast, forecast_status="ESTIMATED", probability=cell.probability,
                      interval=cell.interval, support_unique_dates=cell.unique_dates,
                      model_hash=m.model_hash, reason="FROZEN_CONDITIONAL_FREQUENCY_WITH_HELD_LATER_DIAGNOSTICS")


def score_forecasts(forecasts: tuple[Forecast, ...], labels: tuple[Label, ...], *, known_at_ns: int) -> dict:
    labels_by_id = {l.forecast_id: l for l in labels}
    if len(labels_by_id) != len(labels):
        raise ValueError("DUPLICATE_LABEL_IDS")
    seen, pairs, leads = set(), [], []
    skipped = {"unestimated":0, "unmatured_or_censored":0, "duplicate_episode":0}
    for f in sorted(forecasts, key=lambda x:(x.issued_ns,x.forecast_id)):
        label = labels_by_id.get(f.forecast_id)
        if not label or label.matured_ns > known_at_ns or label.status != "KNOWN":
            skipped["unmatured_or_censored"] += 1
            continue
        if label.event != f.event or label.horizon_minutes != f.horizon_minutes or label.issued_ns != f.issued_ns or label.symbol != f.symbol or label.session_date != f.session_date or label.episode_id != f.episode_id:
            raise ValueError("FORECAST_LABEL_CONTRACT_MISMATCH")
        key = (f.symbol, f.session_date, f.episode_id, f.event, f.horizon_minutes)
        if key in seen:
            skipped["duplicate_episode"] += 1
            continue
        seen.add(key)
        if label.event_observed_ns is not None:
            if label.event_observed_ns <= f.issued_ns:
                raise ValueError("POST_EVENT_DETECTION_CANNOT_SCORE_AS_PREDICTION")
            leads.append((label.event_observed_ns-f.issued_ns)/1_000_000_000)
        if f.probability is None:
            skipped["unestimated"] += 1
            continue
        pairs.append((f.probability,label.outcome))
    return {**probability_metrics(tuple(pairs)), "lead_seconds": leads, "skipped": skipped,
            "note":"Lead time is to event observation at bar availability, not unknown intrabar touch time."}
