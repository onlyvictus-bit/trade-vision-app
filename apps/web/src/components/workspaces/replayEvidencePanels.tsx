import { Metric, Panel, pct } from "../primitives";
import { IntegrityPanel } from "../safetyPanels";

export function ReplayEvidencePanels({ data }: { data: any }) {
  return (
    <>
      <Panel title="Replay Evidence Guide" span="wide" badge="simple view">
        <div className="capability-table compact">
          <div>
            <b>What this tab shows</b>
            <span>Replay proof</span>
            <small>This tab proves that a saved market sequence can be replayed the same way again.</small>
          </div>
          <div>
            <b>What it does not show</b>
            <span>No real trade history</span>
            <small>It does not prove that a real trade was placed. It shows safe replay and simulation evidence only.</small>
          </div>
          <div>
            <b>Where the chart is</b>
            <span>Research tab</span>
            <small>The candle chart, indicator overlays, and selected-candle evidence are in the Research chart replay workbench.</small>
          </div>
          <div>
            <b>Why it matters</b>
            <span>Debug safely</span>
            <small>Use this to check which data, features, and simulated execution assumptions were used before trusting a result.</small>
          </div>
        </div>
      </Panel>
      <Panel title="Execution Simulation">
        <div className="list-row single">
          <span>This is a practice fill model. It estimates slippage, partial fill chance, and adverse selection without sending anything to an execution system.</span>
        </div>
        <Metric label="Slippage" value={`${data.execution?.data.slippage_pct ?? 0}%`} />
        <Metric label="Partial Fill" value={pct(data.execution?.data.partial_fill_probability)} />
        <Metric label="Adverse Selection" value={data.execution?.data.adverse_selection_risk ?? "pending"} />
      </Panel>
      <Panel title="Replay Archive" badge={`${data.replayArchive?.data.length ?? 0} sessions`}>
        <div className="list-row single">
          <span>These are repeatable test sessions. Same scenario and seed should recreate the same event path.</span>
        </div>
        {data.replayArchive?.data.slice(0, 6).map((item: any) => (
          <div className="list-row" key={item.session_id}>
            <b>{item.scenario_id}</b>
            <span>seed {item.seed}</span>
            <small>{item.event_count} events</small>
          </div>
        ))}
      </Panel>
      <Panel title="Point-in-Time Snapshots" badge="immutable">
        <div className="list-row single">
          <span>These snapshots are the exact data packets used for replay and audit. They prevent future data from leaking into a past decision.</span>
        </div>
        {data.snapshots?.data.slice(0, 5).map((snapshot: any) => (
          <div className="list-row" key={snapshot.snapshot_id}>
            <b>{snapshot.symbol}</b>
            <span>seed {snapshot.seed}</span>
            <small>{snapshot.payload_hash.slice(0, 12)}</small>
          </div>
        ))}
      </Panel>
      <Panel title="Feature Version Registry" badge="versioned">
        <div className="list-row single">
          <span>This shows which feature definitions were used. If a feature version changes, old and new results should not be mixed silently.</span>
        </div>
        {data.featureRegistry?.data.slice(0, 5).map((feature: any) => (
          <div className="list-row" key={feature.feature_hash}>
            <b>{feature.name}</b>
            <span>{feature.pipeline_version}</span>
            <small>{feature.feature_hash.slice(0, 12)}</small>
          </div>
        ))}
      </Panel>
      <IntegrityPanel data={data.integrity?.data} />
    </>
  );
}
