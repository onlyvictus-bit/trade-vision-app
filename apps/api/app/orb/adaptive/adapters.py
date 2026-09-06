"""Explicit bridges to existing Trade Vision candle contracts and finer bars.

No new network loader, no fabricated availability, no 5m -> 3m interpolation.
The caller verifies source timestamp convention and adjustment lineage first.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Mapping
from .contracts import Bar, MINUTE, clock_ns, day_of


def from_candle_series(series, *, availability_ns: Mapping[int, int], source_id: str,
                       price_basis: str, verified_native_minutes: int) -> tuple[Bar, ...]:
    timeframe = {"1m":1,"3m":3,"5m":5}.get(series.timeframe)
    if timeframe is None or timeframe != verified_native_minutes:
        raise ValueError("REQUIRES_VERIFIED_NATIVE_1M_3M_OR_5M_SOURCE")
    bars = []
    for raw in series.bars:
        if raw.symbol.upper() != series.symbol.upper() or raw.timeframe != series.timeframe:
            raise ValueError("LEGACY_CANDLE_IDENTITY_MISMATCH")
        if raw.volume is None:
            raise ValueError("MISSING_VOLUME_CANNOT_BECOME_SYNTHETIC_ZERO")
        if raw.timestamp_ns not in availability_ns:
            raise ValueError("EXPLICIT_BAR_AVAILABILITY_REQUIRED")
        bars.append(Bar(symbol=series.symbol.upper(),minutes=timeframe,open_ns=raw.timestamp_ns,
                        close_ns=raw.timestamp_ns+timeframe*MINUTE,
                        available_ns=availability_ns[raw.timestamp_ns],open=raw.open,high=raw.high,
                        low=raw.low,close=raw.close,volume=raw.volume,source_id=source_id,price_basis=price_basis))
    return tuple(bars)


def aggregate_verified_finer(bars: tuple[Bar, ...], target_minutes: int) -> tuple[Bar, ...]:
    if not bars or target_minutes not in (3,5):
        raise ValueError("NONEMPTY_FINER_SERIES_AND_3M_OR_5M_TARGET_REQUIRED")
    source = bars[0].minutes
    if source > target_minutes or target_minutes % source:
        raise ValueError("CANNOT_RECONSTRUCT_FINER_OR_NON_NESTING_BARS")
    identity={(b.symbol,b.minutes,b.source_id,b.price_basis,b.revision) for b in bars}
    if len(identity)!=1 or bars[0].revision!=0:
        raise ValueError("MIXED_OR_REVISED_AGGREGATION_SOURCE")
    if [b.open_ns for b in bars] != sorted({b.open_ns for b in bars}):
        raise ValueError("AGGREGATION_REQUIRES_CHRONOLOGICAL_UNIQUE_INPUT")
    groups=defaultdict(list)
    for b in bars:
        anchor=clock_ns(day_of(b.open_ns),555)
        if not anchor<=b.open_ns<clock_ns(day_of(b.open_ns),930):
            raise ValueError("FINER_BAR_OUTSIDE_SESSION")
        start=anchor+((b.open_ns-anchor)//(target_minutes*MINUTE))*target_minutes*MINUTE
        groups[start].append(b)
    output=[]
    for start,group in sorted(groups.items()):
        expected=list(range(start,start+target_minutes*MINUTE,source*MINUTE))
        if [b.open_ns for b in group]!=expected:
            raise ValueError("INCOMPLETE_AGGREGATION_INTERVAL_NO_SYNTHETIC_FILL")
        output.append(Bar(symbol=group[0].symbol,minutes=target_minutes,open_ns=start,
                          close_ns=start+target_minutes*MINUTE,available_ns=max(b.available_ns for b in group),
                          open=group[0].open,high=max(b.high for b in group),low=min(b.low for b in group),
                          close=group[-1].close,volume=sum(b.volume for b in group),
                          source_id=f"derived-{target_minutes}m:{group[0].source_id}"[:160],price_basis=group[0].price_basis))
    return tuple(output)



def repository_gate_hash() -> str:
    """Hash exact reused data-gate source AND effective frozen thresholds."""
    import hashlib
    from pathlib import Path
    from dataclasses import asdict
    from ...behavior.paper_guidance_config import load_paper_guidance_config
    from .contracts import digest
    root=Path(__file__).resolve().parents[2]
    paths=("models.py","behavior/paper_guidance_spine.py","behavior/data_quality.py",
           "behavior/point_in_time_guard.py","behavior/paper_guidance_config.py")
    return digest({"files":{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in paths},
                   "settings":asdict(load_paper_guidance_config())})


class RepositoryDataGuard:
    """The SAME host D1 price/data checks run in research and observation.

    Runtime mode/kill checks remain independent service permissions. Research
    must not let today's kill switch alter yesterday's historical price labels.
    No post-proof price veto is bolted onto the guidance path.
    """
    def __init__(self, expected_hash: str):
        from ...behavior.paper_guidance_config import load_paper_guidance_config
        self.settings=load_paper_guidance_config()
        self.source_hash=repository_gate_hash()
        if self.source_hash!=expected_hash:
            raise ValueError("HOST_D1_SOURCE_OR_THRESHOLDS_CHANGED_REPROVE_POLICY")

    def is_current(self) -> bool:
        try: return repository_gate_hash()==self.source_hash
        except (OSError,ValueError): return False

    def __call__(self,snapshot) -> bool:
        try:
            from ... import models
            from ...behavior.paper_guidance_spine import run_paper_guidance_p0
            if not self.is_current() or not snapshot.bars: return False
            timeframe=f"{snapshot.bars[0].minutes}m"
            series=models.CandleSeries(symbol=snapshot.prior.symbol,timeframe=timeframe,bars=[
                models.CandleBar(symbol=b.symbol,timeframe=timeframe,timestamp_ns=b.open_ns,
                                open=b.open,high=b.high,low=b.low,close=b.close,volume=b.volume,
                                source="user_csv",sequence_number=i+1)
                for i,b in enumerate(snapshot.bars)])
            request=models.PaperGuidanceRequest(symbol=series.symbol,timeframe=timeframe,series=series,
                                               decision_time_ns=snapshot.as_of_ns,direction="neutral",
                                               include_orb_playbook=False,include_kronos=False)
            mode=models.SystemMode(mode=models.SystemModeValue.MOCK,display_label="AFRE research data validation",
                                   immutable=True,allows_live_orders=False,allows_broker_credentials=False,
                                   watermark_text="RESEARCH DATA VALIDATION - NO ORDERS")
            kill=models.KillSwitchState(state="armed",reason=None,source=None,actor_id=None,
                                       triggered_at=None,blocks_order_paths=False)
            result=run_paper_guidance_p0(request,mode=mode,kill_switch=kill,config=self.settings)
            return bool(result.safety_gate.passed)
        except Exception:
            return False
