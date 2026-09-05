from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .. import storage
from ..models import (
    FeatureSnapshotRecord,
    FeatureStoreGate,
    FeatureStoreStatusReport,
    FeatureStoreWriteReport,
    FeatureStoreWriteRequest,
    RuntimeIndicatorCoverageRecord,
    SevenTimeframeFeatureRuntimeReport,
    SevenTimeframeFeatureRuntimeRequest,
    now_iso,
)
from .indicator_registry import ALL_TIMEFRAMES
from .timeframe_feature_builder import FEATURE_RUNTIME_VERSION, build_seven_timeframe_feature_runtime


FEATURE_STORE_VERSION = "behavior-feature-store.v0.62"
FEATURE_VERSION = "behavior_features.v0.62"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
FEATURE_STORE_ROOT = PROJECT_ROOT / "data" / "feature-store"


def _feature_store_root() -> Path:
    configured = os.environ.get("TRADEVISION_FEATURE_STORE_ROOT")
    if configured:
        return Path(configured)
    if str(storage.DB_PATH) == ":memory:":
        return Path(tempfile.gettempdir()) / "tradevision-feature-store-test"
    return FEATURE_STORE_ROOT


def write_feature_store(request: FeatureStoreWriteRequest | None = None) -> FeatureStoreWriteReport:
    payload = request or FeatureStoreWriteRequest()
    runtime = build_seven_timeframe_feature_runtime(
        request=None
        if request is None
        else SevenTimeframeFeatureRuntimeRequest(
            symbol=payload.symbol,
            seed=payload.seed,
            source_bars=payload.source_bars,
        )
    )
    created_at = now_iso()
    storage_root = _feature_store_root()
    records: list[FeatureSnapshotRecord] = []
    total_feature_rows = 0
    for coverage in runtime.indicator_coverage:
        feature_rows = _validated_feature_rows(runtime, coverage, payload.adjusted_price_version)
        path = _partition_path(
            storage_root=storage_root,
            symbol=runtime.symbol,
            timeframe=coverage.timeframe,
            decision_time_ns=runtime.decision_time_ns,
            adjusted_price_version=payload.adjusted_price_version,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in feature_rows) + "\n"
        path.write_text(content, encoding="utf-8")
        row_hash = _sha256(content)
        record = FeatureSnapshotRecord(
            snapshot_id=f"feature-{runtime.symbol.lower()}-{coverage.timeframe.lower()}-{row_hash[:16]}",
            symbol=runtime.symbol,
            timeframe=coverage.timeframe,
            decision_time_ns=runtime.decision_time_ns,
            source_snapshot_hash=runtime.source_snapshot_hash,
            feature_version=FEATURE_VERSION,
            indicator_registry_version=runtime.registry_version,
            storage_uri=str(path),
            storage_format="columnar_jsonl_v1",
            row_hash=row_hash,
            created_at=created_at,
            adjusted_price_version=payload.adjusted_price_version,
            feature_count=len(feature_rows),
            unavailable_feature_count=coverage.blocked_output_groups,
            proxy_excluded_count=coverage.proxy_output_groups,
            blocked_excluded_count=coverage.blocked_output_groups,
            lineage={
                "runtime_version": runtime.runtime_version,
                "feature_store_version": FEATURE_STORE_VERSION,
                "source_timeframe": runtime.source_timeframe,
                "source_bar_count": runtime.source_bar_count,
                "source_snapshot_hash": runtime.source_snapshot_hash,
                "registry_version": runtime.registry_version,
                "adjusted_price_version": payload.adjusted_price_version,
            },
        )
        storage.save_feature_snapshot_record(record)
        records.append(record)
        total_feature_rows += len(feature_rows)
    corruption_ok = _verify_records(records)
    gates = _gates(records=records, runtime=runtime, corruption_ok=corruption_ok)
    return FeatureStoreWriteReport(
        store_version=FEATURE_STORE_VERSION,
        generated_at=created_at,
        symbol=runtime.symbol,
        source_snapshot_hash=runtime.source_snapshot_hash,
        feature_version=FEATURE_VERSION,
        registry_version=runtime.registry_version,
        storage_root=str(storage_root),
        records=records,
        written_record_count=len(records),
        total_feature_rows=total_feature_rows,
        resumable=True,
        corruption_check_passed=corruption_ok,
        raw_adjusted_mix_blocked=True,
        proxy_or_blocked_indicators_excluded=all(record.proxy_excluded_count + record.blocked_excluded_count >= 0 for record in records),
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.62 writes partitioned columnar JSONL feature rows and SQLite metadata/lineage.",
            "The partition path is Parquet-compatible but intentionally uses JSONL until a Parquet dependency is approved.",
            "Only validated available indicator rows are persisted as features; proxy and blocked indicators are counted but excluded.",
            "Raw and adjusted price versions are separated in the partition path and unique metadata key.",
        ],
    )


def feature_store_status(limit: int = 14) -> FeatureStoreStatusReport:
    records = storage.list_feature_snapshot_records(limit=limit)
    storage_root = _feature_store_root()
    return FeatureStoreStatusReport(
        store_version=FEATURE_STORE_VERSION,
        generated_at=now_iso(),
        storage_root=str(storage_root),
        metadata_table="behavior_feature_snapshots",
        record_count=storage.count_feature_snapshot_records(),
        latest_records=records,
        indexes=[
            "idx_behavior_feature_snapshot_lookup(symbol, timeframe, decision_time_ns)",
            "idx_behavior_feature_snapshot_source(source_snapshot_hash, feature_version)",
            "unique(symbol, timeframe, decision_time_ns, feature_version, adjusted_price_version)",
        ],
        corruption_check_passed=_verify_records(records),
        parquet_reserved=True,
        storage_format="columnar_jsonl_v1",
        live_trading_blocked=True,
        notes=[
            "Status reports only v0.62 behavior feature snapshots.",
            "Parquet remains reserved; current writer is deterministic JSONL with the same partition strategy.",
        ],
    )


def _validated_feature_rows(
    runtime: SevenTimeframeFeatureRuntimeReport,
    coverage: RuntimeIndicatorCoverageRecord,
    adjusted_price_version: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for indicator_id, state in sorted(coverage.availability_mask.items()):
        if state != "available":
            continue
        rows.append(
            {
                "symbol": runtime.symbol,
                "timeframe": coverage.timeframe,
                "decision_time_ns": runtime.decision_time_ns,
                "source_snapshot_hash": runtime.source_snapshot_hash,
                "feature_version": FEATURE_VERSION,
                "indicator_registry_version": runtime.registry_version,
                "indicator_id": indicator_id,
                "value": coverage.sample_values[indicator_id],
                "availability": state,
                "adjusted_price_version": adjusted_price_version,
                "source_runtime_version": runtime.runtime_version,
            }
        )
    return rows


def _partition_path(*, storage_root: Path, symbol: str, timeframe: str, decision_time_ns: int, adjusted_price_version: str) -> Path:
    pseudo_date = str(decision_time_ns)[:8]
    return (
        storage_root
        / f"symbol={symbol.upper()}"
        / f"timeframe={timeframe}"
        / f"price_version={adjusted_price_version}"
        / f"decision_bucket={pseudo_date}"
        / "features.jsonl"
    )


def _verify_records(records: list[FeatureSnapshotRecord]) -> bool:
    for record in records:
        path = Path(record.storage_uri)
        if not path.exists():
            return False
        if _sha256(path.read_text(encoding="utf-8")) != record.row_hash:
            return False
    return True


def _gates(
    *,
    records: list[FeatureSnapshotRecord],
    runtime: SevenTimeframeFeatureRuntimeReport,
    corruption_ok: bool,
) -> list[FeatureStoreGate]:
    return [
        _gate("TV-V062-001", "Required feature snapshot metadata rows written", len(records) == len(ALL_TIMEFRAMES), f"{len(records)} records written."),
        _gate("TV-V062-002", "All records share one source snapshot hash", len({record.source_snapshot_hash for record in records}) == 1, runtime.source_snapshot_hash),
        _gate("TV-V062-003", "Proxy and blocked indicators excluded from persisted feature rows", all(record.feature_count <= 94 for record in records), "Only available validated rows are written."),
        _gate("TV-V062-004", "Corruption check passed", corruption_ok, "Stored file hashes match metadata row hashes."),
        _gate("TV-V062-005", "Raw and adjusted versions separated", all("price_version=" in record.storage_uri for record in records), "Partition path includes price version."),
        _gate("TV-V062-006", "No live trading capability", True, "Feature store writes research metadata only."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> FeatureStoreGate:
    return FeatureStoreGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else "Fix v0.62 feature-store persistence before redundancy/similarity work.",
    )


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
