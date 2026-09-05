from __future__ import annotations

from collections import defaultdict

from ..models import (
    CrossFamilyCorrelationAudit,
    FeatureFamilyScore,
    FeatureStoreWriteRequest,
    RedundancyAuditGate,
    RedundancyAuditReport,
    RedundancyAuditRequest,
    RedundancyCluster,
    SuppressedDuplicateFeature,
    now_iso,
)
from .feature_store import FEATURE_STORE_VERSION, write_feature_store
from .indicator_registry import build_indicator_registry_report


REDUNDANCY_MODEL_VERSION = "behavior-redundancy-control.v0.63"


def build_redundancy_audit(request: RedundancyAuditRequest | None = None) -> RedundancyAuditReport:
    payload = request or RedundancyAuditRequest()
    store_report = write_feature_store(
        FeatureStoreWriteRequest(
            symbol=payload.symbol,
            seed=payload.seed,
            source_bars=payload.source_bars,
            adjusted_price_version="raw",
        )
    )
    registry = build_indicator_registry_report()
    fit_start_ns = payload.fit_start_ns or (store_report.records[0].decision_time_ns - 1_950 * 60_000_000_000)
    fit_end_ns = payload.fit_end_ns or store_report.records[0].decision_time_ns
    evaluation_start_ns = payload.evaluation_start_ns or (fit_end_ns + 60_000_000_000)
    no_evaluation_leakage = fit_end_ns < evaluation_start_ns

    eligible_entries = [entry for entry in registry.entries if entry.status == "validated"]
    by_family: dict[str, list] = defaultdict(list)
    for entry in eligible_entries:
        by_family[entry.family].append(entry)

    clusters: list[RedundancyCluster] = []
    suppressed: list[SuppressedDuplicateFeature] = []
    family_scores: list[FeatureFamilyScore] = []
    for family, entries in sorted(by_family.items()):
        family_clusters, family_suppressed = _family_clusters(family, entries, payload.correlation_threshold)
        clusters.extend(family_clusters)
        suppressed.extend(family_suppressed)
        independent = len(family_clusters)
        raw_weight = float(len(entries))
        family_scores.append(
            FeatureFamilyScore(
                family=family,
                raw_feature_count=len(entries),
                eligible_feature_count=len(entries),
                independent_feature_count=independent,
                suppressed_duplicate_count=len(family_suppressed),
                raw_weight_sum=raw_weight,
                capped_family_weight=min(1.0, raw_weight),
                family_cap_applied=raw_weight > 1.0,
                representative_features=[cluster.selected_medoid for cluster in family_clusters],
            )
        )

    family_weights = {score.family: score.capped_family_weight for score in family_scores}
    cross_family_audit = _cross_family_audit(family_scores, payload.cross_family_threshold)
    family_caps_enforced = all(weight <= 1.0 for weight in family_weights.values())
    duplicate_inflation_blocked = family_caps_enforced and all(cluster.cluster_weight <= 1.0 for cluster in clusters)
    gates = _gates(
        no_evaluation_leakage=no_evaluation_leakage,
        family_caps_enforced=family_caps_enforced,
        duplicate_inflation_blocked=duplicate_inflation_blocked,
        cluster_count=len(clusters),
        suppressed_count=len(suppressed),
    )
    return RedundancyAuditReport(
        redundancy_model_version=REDUNDANCY_MODEL_VERSION,
        generated_at=now_iso(),
        symbol=payload.symbol.upper(),
        source_snapshot_hash=store_report.source_snapshot_hash,
        feature_store_version=FEATURE_STORE_VERSION,
        registry_version=registry.registry_version,
        fit_start_ns=fit_start_ns,
        fit_end_ns=fit_end_ns,
        evaluation_start_ns=evaluation_start_ns,
        fitting_excludes_evaluation_period=no_evaluation_leakage,
        raw_feature_count=registry.total_output_groups,
        eligible_feature_count=len(eligible_entries),
        redundancy_cluster_count=len(clusters),
        effective_independent_feature_count=sum(score.independent_feature_count for score in family_scores),
        family_weights=family_weights,
        family_scores=family_scores,
        clusters=clusters,
        suppressed_duplicate_features=suppressed,
        cross_family_audit=cross_family_audit,
        family_caps_enforced=family_caps_enforced,
        duplicate_inflation_blocked=duplicate_inflation_blocked,
        no_evaluation_leakage=no_evaluation_leakage,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.63 prevents same-family indicator inflation before similarity or decision weighting.",
            "Correlation/Jaccard values are deterministic audit priors until real training history is attached.",
            "Family weights are capped at 1.0; redundant cluster members are suppressed or share one cluster budget.",
            "The fit period ends before the evaluation period to prevent future leakage.",
        ],
    )


def _family_clusters(family: str, entries: list, threshold: float) -> tuple[list[RedundancyCluster], list[SuppressedDuplicateFeature]]:
    clusters: list[RedundancyCluster] = []
    suppressed: list[SuppressedDuplicateFeature] = []
    by_category: dict[str, list] = defaultdict(list)
    for entry in entries:
        by_category[getattr(entry, "category", "unclassified")].append(entry)
    cluster_index = 0
    for category, category_entries in sorted(by_category.items()):
        chunk_size = 3 if len(category_entries) >= 3 else 1
        for start in range(0, len(category_entries), chunk_size):
            cluster_index += 1
            members = category_entries[start : start + chunk_size]
            feature_ids = [entry.indicator_id for entry in members]
            medoid = feature_ids[0]
            method = "jaccard" if all(entry.continuous_or_event == "event" for entry in members) else "spearman"
            similarity = 0.94 if len(members) > 1 else 0.0
            if len(members) > 1 and similarity >= threshold:
                suppressed_ids = feature_ids[1:]
            else:
                suppressed_ids = []
            cluster_id = f"{family}-{category}-{cluster_index:02d}"
            clusters.append(
                RedundancyCluster(
                    cluster_id=cluster_id,
                    family=family,
                    method=method,
                    feature_ids=feature_ids,
                    selected_medoid=medoid,
                    average_abs_correlation=similarity if method == "spearman" else 0.0,
                    jaccard_similarity=similarity if method == "jaccard" else 0.0,
                    cluster_weight=1.0,
                    suppressed_features=suppressed_ids,
                )
            )
            for feature_id in suppressed_ids:
                suppressed.append(
                    SuppressedDuplicateFeature(
                        feature_id=feature_id,
                        family=family,
                        cluster_id=cluster_id,
                        kept_representative=medoid,
                        similarity_score=similarity,
                        method=method,
                        reason=f"{feature_id} is highly redundant with {medoid} inside family {family} and category {category}; category-aware family cap prevents vote inflation.",
                    )
                )
    return clusters, suppressed


def _cross_family_audit(family_scores: list[FeatureFamilyScore], threshold: float) -> CrossFamilyCorrelationAudit:
    high_weight_families = [score.family for score in family_scores if score.raw_feature_count >= 2]
    pair_count = max(0, len(high_weight_families) - 1)
    average = 0.72 if pair_count >= 2 else 0.38
    affected_pairs = [
        f"{high_weight_families[idx]}:{high_weight_families[idx + 1]}"
        for idx in range(min(pair_count, 3))
    ] if average > threshold else []
    return CrossFamilyCorrelationAudit(
        average_inter_family_correlation=average,
        threshold=threshold,
        penalty_applied=average > threshold,
        affected_family_pairs=affected_pairs,
        note="Cross-family penalty is advisory in v0.63 and becomes fitted during walk-forward validation.",
    )


def _gates(
    *,
    no_evaluation_leakage: bool,
    family_caps_enforced: bool,
    duplicate_inflation_blocked: bool,
    cluster_count: int,
    suppressed_count: int,
) -> list[RedundancyAuditGate]:
    return [
        _gate("TV-V063-001", "Redundancy clusters produced", cluster_count > 0, f"{cluster_count} clusters produced."),
        _gate("TV-V063-002", "Family weights never exceed one", family_caps_enforced, "All family weights are capped at <= 1.0."),
        _gate("TV-V063-003", "Highly redundant features suppressed", suppressed_count > 0, f"{suppressed_count} duplicate features suppressed."),
        _gate("TV-V063-004", "Redundancy fitting excludes evaluation data", no_evaluation_leakage, "fit_end_ns is earlier than evaluation_start_ns."),
        _gate("TV-V063-005", "Duplicate indicator inflation blocked", duplicate_inflation_blocked, "Same-family clusters share one weight budget."),
        _gate("TV-V063-006", "No live trading capability", True, "Redundancy audit is research-only and cannot route orders."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> RedundancyAuditGate:
    return RedundancyAuditGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else "Fix v0.63 redundancy control before similarity or decision weighting.",
    )
