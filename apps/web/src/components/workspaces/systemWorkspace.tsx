import { AiCredentialsPanel } from "../aiCredentialsPanel";
import { Metric, Panel } from "../primitives";

export function System({ data, mode }: { data: any; mode: string }) {
  return (
    <div className="workspace">
      <AiCredentialsPanel status={data.aiCredentialStatus?.data} />
      <Panel title="System Pipeline" span="wide" badge={mode}>
        {data.pipeline?.data.steps.map((step: any) => <div className="list-row" key={step.name}><b>{step.name}</b><span>{step.status}</span><small>{step.message}</small></div>)}
      </Panel>
      <Panel title="Persistent Storage" badge={data.storage?.data.status ?? "pending"}>
        <Metric label="Audit Events" value={String(data.storage?.data.audit_events ?? 0)} />
        <Metric label="Replay Sessions" value={String(data.storage?.data.replay_sessions ?? 0)} />
        <Metric label="Replay Events" value={String(data.storage?.data.replay_events ?? 0)} />
        <Metric label="Capability Snapshots" value={String(data.storage?.data.capability_snapshots ?? 0)} />
        <Metric label="PIT Snapshots" value={String(data.storage?.data.point_in_time_snapshots ?? 0)} />
        <Metric label="Feature Versions" value={String(data.storage?.data.feature_versions ?? 0)} />
        <Metric label="Workspace Layouts" value={String(data.storage?.data.workspace_layouts ?? 0)} />
        <Metric label="Request Logs" value={String(data.storage?.data.request_logs ?? 0)} />
        <Metric label="Behavior Runs" value={String(data.storage?.data.behavior_analysis_results ?? 0)} />
        <Metric label="Behavior Memory" value={String(data.storage?.data.behavior_memory_records ?? 0)} />
        <Metric label="Behavior Benchmarks" value={String(data.storage?.data.behavior_benchmark_runs ?? 0)} />
        <Metric label="Safety Reports" value={String(data.storage?.data.behavior_safety_reports ?? 0)} />
        <Metric label="Memory Quarantines" value={String(data.storage?.data.memory_quarantines ?? 0)} />
        <Metric label="Golden Fixtures" value={String(data.storage?.data.golden_replay_fixtures ?? 0)} />
        <Metric label="Benchmark Reports" value={String(data.storage?.data.behavior_benchmark_reports ?? 0)} />
        <Metric label="Release Checklists" value={String(data.storage?.data.release_checklists ?? 0)} />
        <Metric label="Release Approvals" value={String(data.storage?.data.release_approvals ?? 0)} />
        <Metric label="Evidence Bundles" value={String(data.storage?.data.release_evidence_bundles ?? 0)} />
        <Metric label="Evidence Artifacts" value={String(data.storage?.data.release_evidence_artifacts ?? 0)} />
        <Metric label="Scenario Coverage" value={String(data.storage?.data.behavior_scenario_coverage_reports ?? 0)} />
        <p>{data.storage?.data.db_path}</p>
      </Panel>
      <Panel title="Operational Observability" badge={data.observability?.data.log_format ?? "json"}>
        <Metric label="Requests" value={String(data.observability?.data.request_count ?? 0)} />
        <Metric label="Errors" value={String(data.observability?.data.error_count ?? 0)} />
        <Metric label="P95 Latency" value={`${data.observability?.data.p95_latency_ms ?? 0} ms`} />
        <Metric label="Required Fields" value={String(data.observability?.data.required_fields?.length ?? 0)} />
      </Panel>
      <Panel title="Workspace Layout" badge={`v${data.layout?.data.version ?? 1}`}>
        <Metric label="Workspace" value={data.layout?.data.workspace_id ?? "pending"} />
        <Metric label="Panels" value={String(data.layout?.data.panels?.length ?? 0)} />
        <Metric label="Updated" value={data.layout?.data.updated_at ?? "pending"} />
      </Panel>
      <Panel title="Audit Integrity" badge={data.auditIntegrity?.data.chain_valid ? "valid" : "check"}>
        <Metric label="Events" value={String(data.auditIntegrity?.data.event_count ?? 0)} />
        <Metric label="Hashed" value={String(data.auditIntegrity?.data.hashed_event_count ?? 0)} />
        <Metric label="Head Hash" value={data.auditIntegrity?.data.head_hash?.slice(0, 16) ?? "pending"} />
        <Metric label="Algorithm" value={data.auditIntegrity?.data.algorithm ?? "pending"} />
      </Panel>
      <Panel title="Audit Events" span="wide">
        {data.audit?.data.map((event: any) => <div className="list-row" key={event.event_id}><b>{event.level}</b><span>{event.message}</span><small>{event.timestamp}</small></div>)}
      </Panel>
    </div>
  );
}
