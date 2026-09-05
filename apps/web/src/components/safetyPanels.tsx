import { Metric, Panel, money } from "./primitives";

export function RiskPanel({ risk }: { risk?: any }) {
  return (
    <Panel title="Mock Risk Panel" badge="no real money">
      <Metric label="Hypothetical Exposure" value={money(risk?.hypothetical_exposure)} />
      <Metric label="Max Drawdown" value={`${risk?.max_drawdown_simulated ?? 0}%`} />
      <Metric label="VaR 95" value={`${risk?.var95 ?? 0}%`} />
      <p>{risk?.disclaimer}</p>
    </Panel>
  );
}

export function OrderPathPanel({ orderPath }: { orderPath?: any }) {
  return (
    <Panel title="Order Path Guard" badge={orderPath?.simulation_only ? "simulation only" : "blocked"}>
      <Metric label="Live Routing" value={orderPath?.live_order_routing_enabled ? "enabled" : "disabled"} />
      <Metric label="Broker Credentials" value={orderPath?.broker_credentials_configured ? "present" : "absent"} />
      <Metric label="Kill Switch" value={orderPath?.kill_switch_state ?? "pending"} />
      <Metric label="Simulated Orders" value={orderPath?.accepts_simulated_orders ? "allowed" : "blocked"} />
      {orderPath?.blocks_reason && <p>{orderPath.blocks_reason}</p>}
    </Panel>
  );
}

export function IntegrityPanel({ data }: { data?: any }) {
  return (
    <Panel title="Simulation Integrity" badge={data?.data_source ?? "mock"}>
      <p>{data?.disclaimer}</p>
      {data?.assumptions.map((item: string) => <div className="list-row single" key={item}><span>{item}</span></div>)}
    </Panel>
  );
}
