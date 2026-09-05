export type SourceMode = "mock" | "simulation" | "replay" | "paper" | "live";
export type CapabilityStatus = "reserved" | "mock" | "beta" | "production";
export type SystemModeValue = "MOCK" | "SIMULATION" | "REPLAY" | "PAPER" | "LIVE";

export interface ResponseMeta {
  request_id: string;
  event_time: string;
  arrival_time: string;
  source: SourceMode;
  quality_score: number;
  trust_score: number;
  replay_snapshot_id: string | null;
  capability_status: CapabilityStatus;
}

export interface ApiEnvelope<T> {
  meta: ResponseMeta;
  data: T;
}

export interface SystemMode {
  mode: SystemModeValue;
  display_label: string;
  immutable: boolean;
  allows_live_orders: boolean;
  allows_broker_credentials: boolean;
  watermark_text: string;
}

export interface TimeProviderState {
  time_mode: "realtime" | "virtual" | "paused" | "stepped";
  virtual_timestamp_ns: number;
  wall_clock_time: string;
  drift_ms: number;
  source: "mock" | "system" | "ntp" | "ptp" | "exchange_sync";
  sequence_number: number;
}

export interface KillSwitchState {
  state: "armed" | "triggered" | "reset_pending";
  reason: string | null;
  source: "user_ui" | "risk_engine" | "circuit_breaker" | "heartbeat_timeout" | "system" | null;
  actor_id: string | null;
  triggered_at: string | null;
  blocks_order_paths: boolean;
}

export interface CapabilityManifestItem {
  name: string;
  status: CapabilityStatus;
  ui_module: string;
  backend_services: string[];
  required_data_contracts: string[];
  mock_replacement_strategy: string;
  required_for_startup: boolean;
  promotion_gates: string[];
}

export interface MarketEvent {
  event_id: string;
  parent_event_id: string | null;
  virtual_timestamp_ns: number;
  source_mode: SystemModeValue;
  sequence_number: number;
  symbol: string;
  payload: Record<string, unknown>;
  watermark: string | null;
}

export interface ClockHealth {
  time: TimeProviderState;
  mode: SystemMode;
  kill_switch: KillSwitchState;
}
