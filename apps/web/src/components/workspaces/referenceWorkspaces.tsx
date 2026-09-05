import { useMemo } from "react";
import { Card, Metric, Panel } from "../primitives";

export function Knowledge({ data }: { data: any }) {
  const summary = data.graph?.data.summary ?? {};
  const domains = summary.domain_counts ?? {};
  return (
    <div className="workspace">
      <Panel title="Knowledge Graph" span="wide" badge={`${data.graph?.data.nodes.length ?? 0} nodes`}>
        <div className="feature-grid">
          {Object.entries(domains).map(([name, count]) => <Card key={name} title={name} value={String(count)} note="files" />)}
        </div>
      </Panel>
      <Panel title="Graph Source">
        <p>{data.graph?.data.root}</p>
        <p>Generated: {data.graph?.data.generated_at}</p>
      </Panel>
    </div>
  );
}

export function Implementation({ data }: { data: any }) {
  const capabilities = data.features?.data.capabilities ?? [];
  const byStatus = useMemo(() => {
    return capabilities.reduce((acc: Record<string, number>, item: any) => {
      acc[item.status] = (acc[item.status] ?? 0) + 1;
      return acc;
    }, {});
  }, [capabilities]);
  return (
    <div className="workspace">
      <Panel title="Capability Manifest" span="wide" badge="source of truth">
        <div className="dna-grid">
          {Object.entries(byStatus).map(([status, count]) => <Metric key={status} label={status} value={String(count)} />)}
        </div>
        <div className="capability-table">
          {capabilities.map((cap: any) => <div key={cap.name}><b>{cap.name}</b><span>{cap.status}</span><small>{cap.ui_module}</small></div>)}
        </div>
      </Panel>
    </div>
  );
}
