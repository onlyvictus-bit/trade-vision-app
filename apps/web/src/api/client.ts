import { z } from "zod";
import {
  AuditSchema,
  BehaviorAcpSchema,
  BehaviorBenchmarkReportSchema,
  BenchmarkDrilldownSchema,
  BehaviorScenarioCoverageReportSchema,
  BehaviorContextSchema,
  BehaviorDriftSchema,
  BehaviorFrontendPanelMapSchema,
  BehaviorOODSchema,
  BehaviorSafetyReportSchema,
  BehaviorValidationSchema,
  AuditIntegritySchema,
  BehaviorAnalysisSchema,
  BehaviorOutputColumnsSchema,
  BehaviorSpecSchema,
  DayOfWeekMemorySchema,
  CapabilitiesSchema,
  DataQualitySchema,
  DecisionSchema,
  ErrorEnvelopeSchema,
  ExecutionSchema,
          ExecutionSimulationSchema,
          ExecutorAdapterConformanceSchema,
          ExecutorTransportOutboxRecordSchema,
          ExecutorTransportStatusSchema,
          ExecutorTransportTraceSchema,
          TransportFaultHarnessSchema,
          TransportResilienceSchema,
          TransportSecurityPostureSchema,
          TransportSecurityThreatReportSchema,
          DeploymentReadinessSchema,
          DeploymentSmokeSchema,
          FinalProductionReadinessAuditSchema,
          ExecutorDryRunPackageSchema,
          ExecutorGoldenFixtureRegistrySchema,
          ExecutorGoldenRegistryVerificationSchema,
          IntegritySchema,
          FailureLibrarySchema,
          FeatureRegistrySchema,
          GoldenReplayFixtureSchema,
          GoldenReplayVerificationSchema,
          KillSwitchSchema,
          KnowledgeGraphSchema,
          LearningTrustSchema,
          MarketDNASchema,
          MemoryQuarantineSchema,
          MemoryRebuildPlanSchema,
          MicrostructureSchema,
          ModeSchema,
          MockIngestResultSchema,
          OrderPathStatusSchema,
          PipelineSchema,
          PortfolioSchema,
          ReplaySchema,
          ReplayArchiveSchema,
          RealityGapSchema,
          ReleaseApprovalSchema,
          ReleaseEvidenceArtifactSchema,
          ReleaseEvidenceArtifactVerificationSchema,
          ReleaseEvidenceBundleSchema,
          ReleaseChecklistSchema,
          RuntimeReadinessSchema,
          BehaviorChartReplaySchema,
          BehaviorIndicatorExpansionSchema,
          BotHandoffVerificationSchema,
          KronosForecastSchema,
          KronosRuntimeStatusSchema,
          KronosServiceBridgeStatusSchema,
          ReplayIndicatorValidationSchema,
          ReplayIndicatorMatrixSchema,
          MatrixDecisionReadinessSchema,
          TradeLifecycleSimulationSchema,
          TradeLifecycleScenarioComparisonSchema,
          LifecycleEvidenceDrilldownSchema,
          TradeabilityGuidanceSchema,
          BehaviorOhlcvImportSchema,
          RiskSchema,
          RiskSizingSchema,
          SnapshotListSchema,
          TimeSchema,
          StorageStatusSchema,
          ObservabilityStatusSchema,
          PatternMemorySchema,
          SessionRhythmSchema,
          SimilarDayMatchSchema,
          SimilarDayReplaySchema,
          StockDnaSummarySchema,
          StockMemoryProfileSchema,
          TradeDecisionSchema,
          TwinEngineComparisonSchema,
          TwinMachineDashboardSchema,
          WorkspaceLayoutSchema,
  envelope,
} from "./schemas";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiClientError extends Error {
  readonly kind = "api";
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;

  constructor(path: string, status: number, code: string, message: string, retryable: boolean) {
    super(`${path} failed: ${status} ${code} - ${message}`);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

export class ContractValidationError extends Error {
  readonly kind = "contract";
  readonly path: string;

  constructor(path: string, cause: unknown) {
    super(`${path} response failed frontend contract validation.`);
    this.name = "ContractValidationError";
    this.path = path;
    this.cause = cause;
  }
}

async function get<T extends z.ZodTypeAny>(path: string, schema: T): Promise<z.infer<T>> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw await buildApiError(path, response);
  const json = await response.json();
  return parseContract(path, schema, json);
}

async function post<T extends z.ZodTypeAny>(path: string, body: unknown, schema: T, headers: Record<string, string> = {}): Promise<z.infer<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await buildApiError(path, response);
  const json = await response.json();
  return parseContract(path, schema, json);
}

async function del<T extends z.ZodTypeAny>(path: string, schema: T): Promise<z.infer<T>> {
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!response.ok) throw await buildApiError(path, response);
  const json = await response.json();
  return parseContract(path, schema, json);
}

async function buildApiError(path: string, response: Response): Promise<ApiClientError> {
  try {
    const json = await response.json();
    const parsed = ErrorEnvelopeSchema.parse(json);
    return new ApiClientError(path, response.status, parsed.error.code, parsed.error.message, parsed.error.retryable);
  } catch {
    return new ApiClientError(path, response.status, "unparseable_error_envelope", "Backend returned a malformed error response.", false);
  }
}

function parseContract<T extends z.ZodTypeAny>(path: string, schema: T, json: unknown): z.infer<T> {
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    throw new ContractValidationError(path, parsed.error);
  }
  return parsed.data;
}

export const api = {
  auth: () => get("/api/auth/me", envelope(z.object({
    actor_id: z.string(),
    role: z.enum(["viewer", "operator", "risk_manager", "admin"]),
    auth_mode: z.literal("mock_header"),
    permissions: z.array(z.string()),
    live_trading_allowed: z.boolean(),
  }))),
  time: () => get("/api/time", envelope(TimeSchema)),
  mode: () => get("/api/system/mode", envelope(ModeSchema)),
  features: () => get("/api/system/features", envelope(CapabilitiesSchema)),
          killswitch: () => get("/api/system/killswitch", envelope(KillSwitchSchema)),
  storage: () => get("/api/storage/status", envelope(StorageStatusSchema)),
  observability: () => get("/api/observability/status", envelope(ObservabilityStatusSchema)),
  layout: (workspaceId: string) => get(`/api/layout/${workspaceId}`, envelope(WorkspaceLayoutSchema)),
  saveLayout: (workspaceId: string, layout: unknown) => put(`/api/layout/${workspaceId}`, layout, envelope(WorkspaceLayoutSchema)),
  triggerKillSwitch: (reason: string) => post("/api/system/killswitch/trigger", { reason, source: "user_ui", actor_id: "local_user" }, envelope(KillSwitchSchema)),
  resetKillSwitch: () => post("/api/system/killswitch/reset", { actor_id: "local_user", confirmation: "RESET_MOCK_KILL_SWITCH" }, envelope(KillSwitchSchema), { "X-TradeVision-Role": "risk_manager" }),
  pipeline: () => get("/api/system/pipeline", envelope(PipelineSchema)),
  decision: () => get("/api/decision/current", envelope(DecisionSchema)),
  portfolio: () => get("/api/portfolio/state", envelope(PortfolioSchema)),
  risk: () => get("/api/risk/state", envelope(RiskSchema)),
  marketDna: () => get("/api/market/dna", envelope(MarketDNASchema)),
  microstructure: () => get("/api/microstructure/state", envelope(MicrostructureSchema)),
          replay: () => get("/api/replay/session", envelope(ReplaySchema)),
          replayArchive: () => get("/api/replay/archive", envelope(ReplayArchiveSchema)),
  startReplay: (seed: number) => post("/api/replay/start", { scenario_id: "mock_opening_drive", seed }, envelope(ReplaySchema)),
  playReplay: (sessionId: string) => post("/api/replay/play", { session_id: sessionId }, envelope(ReplaySchema)),
  pauseReplay: (sessionId: string) => post("/api/replay/pause", { session_id: sessionId }, envelope(ReplaySchema)),
  stepReplay: (sessionId: string, steps = 1) => post("/api/replay/step", { session_id: sessionId, steps }, envelope(ReplaySchema)),
  seekReplay: (sessionId: string, virtualTimestampNs: number) => post("/api/replay/seek", { session_id: sessionId, virtual_timestamp_ns: virtualTimestampNs }, envelope(ReplaySchema)),
  execution: () => get("/api/execution/simulation", envelope(ExecutionSchema)),
  orderPath: () => get("/api/execution/order-path/status", envelope(OrderPathStatusSchema)),
          dataQuality: () => get("/api/data/quality", envelope(DataQualitySchema)),
          snapshots: () => get("/api/data/snapshots", envelope(SnapshotListSchema)),
          ingestMockData: (seed: number, bars = 64, symbol = "NIFTY-MOCK") => post("/api/data/ingest/mock", { symbol, seed, bars }, envelope(MockIngestResultSchema)),
          featureRegistry: () => get("/api/features/registry", envelope(FeatureRegistrySchema)),
          behaviorImportOhlcvSample: () => post("/api/v1/behavior/data/import/ohlcv", {
            symbol: "INFY",
            timeframe: "1m",
            persist_snapshot: true,
            csv_text: [
              "timestamp,open,high,low,close,volume",
              "2026-01-05T09:15:00+05:30,100,101,99.8,100.5,10000",
              "2026-01-05T09:16:00+05:30,100.5,101.2,100.1,101,12000",
              "2026-01-05T09:17:00+05:30,101,101.4,100.7,101.2,11500",
              "2026-01-05T09:18:00+05:30,101.2,101.8,101,101.6,13000",
            ].join("\n"),
          }, envelope(BehaviorOhlcvImportSchema)),
          behaviorImportLocalReliancePreview: (rows = 390, position: "head" | "tail" = "tail") => get(
            `/api/v1/behavior/data/local/reliance-1m/preview?rows=${rows}&position=${position}&persist_snapshot=true`,
            envelope(BehaviorOhlcvImportSchema),
          ),
          orbTimingSubmit: (payload: unknown) => post(
            "/api/v1/orb/timing-research",
            payload,
            envelope(z.object({}).passthrough()),
          ),
          orbTimingJob: (jobId: string) => get(
            `/api/v1/orb/timing-research/jobs/${encodeURIComponent(jobId)}`,
            envelope(z.object({}).passthrough()),
          ),
          orbTimingRuns: (limit = 10) => get(
            `/api/v1/orb/timing-research/runs?limit=${limit}`,
            envelope(z.array(z.object({}).passthrough())),
          ),
          orbTimingExportUrl: (runId: string) =>
            `${API_BASE}/api/v1/orb/timing-research/runs/${encodeURIComponent(runId)}/export.csv`,
          paperGuidanceRun: (payload: unknown) => post(
            "/api/v1/paper-guidance/run",
            payload,
            envelope(z.object({}).passthrough()),
          ),
          paperGuidanceOrbTickets: (symbol = "RELIANCE", timeframe = "5m") => get(
            `/api/v1/paper-guidance/orb-tickets?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`,
            envelope(z.array(z.object({}).passthrough())),
          ),
          paperGuidancePaperRecords: (symbol = "RELIANCE", timeframe = "5m") => get(
            `/api/v1/paper-guidance/paper-records?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`,
            envelope(z.array(z.object({}).passthrough())),
          ),
          paperGuidanceRecordSimulated: (payload: unknown) => post(
            "/api/v1/paper-guidance/record-simulated",
            payload,
            envelope(z.object({}).passthrough()),
          ),
          paperGuidanceObserveSimulated: (payload: unknown) => post(
            "/api/v1/paper-guidance/paper-records/observe",
            payload,
            envelope(z.object({}).passthrough()),
          ),
          paperGuidancePaperOutcomes: (
            paperRecordId?: string,
            playbookId?: string,
          ) => {
            const params = new URLSearchParams();
            if (paperRecordId) params.set("paper_record_id", paperRecordId);
            if (playbookId) params.set("playbook_id", playbookId);
            return get(
              `/api/v1/paper-guidance/paper-outcomes?${params.toString()}`,
              envelope(z.array(z.object({}).passthrough())),
            );
          },
          paperGuidanceOrbReliability: (
            playbookId: string,
            symbol = "RELIANCE",
            timeframe = "5m",
          ) => get(
            `/api/v1/paper-guidance/orb-reliability/${encodeURIComponent(playbookId)}?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`,
            envelope(z.object({}).passthrough()),
          ),
          paperGuidanceStorageMonitor: () => get(
            "/api/v1/paper-guidance/storage-monitor",
            envelope(z.object({}).passthrough()),
          ),
          integrity: () => get("/api/simulation/integrity", envelope(IntegritySchema)),
  audit: () => get("/api/audit/events", envelope(AuditSchema)),
  auditIntegrity: () => get("/api/audit/integrity", envelope(AuditIntegritySchema)),
  graph: () => get("/api/knowledge/graph", envelope(KnowledgeGraphSchema)),
  behaviorSpec: () => get("/api/v1/behavior/spec", envelope(BehaviorSpecSchema)),
  behaviorColumns: () => get("/api/v1/behavior/output-columns", envelope(BehaviorOutputColumnsSchema)),
  behaviorAnalyze: (symbol = "NIFTY-MOCK", timeframe = "5m", seed = 42) => post("/api/v1/behavior/analyze", { symbol, timeframe, seed }, envelope(BehaviorAnalysisSchema)),
  behaviorContext: () => post("/api/v1/behavior/context/full", mockBehaviorContextPayload(), envelope(BehaviorContextSchema)),
  behaviorSessionRhythm: () => post("/api/v1/behavior/session/rhythm", mockBehaviorSessionPayload(), envelope(SessionRhythmSchema)),
  behaviorDayOfWeekMemory: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/stock/${symbol}/day-of-week-memory`, envelope(DayOfWeekMemorySchema)),
  behaviorStockDnaSummary: (symbol = "NIFTY-MOCK") => post(`/api/v1/behavior/stock/${symbol}/dna/summary`, mockBehaviorSessionPayload(symbol), envelope(StockDnaSummarySchema)),
  behaviorStockMemoryProfile: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/stock/${symbol}/memory-profile/current`, envelope(StockMemoryProfileSchema)),
  behaviorPatternMemory: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/stock/${symbol}/pattern-memory`, envelope(PatternMemorySchema)),
  behaviorSimilarDays: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/similar-days/${symbol}`, envelope(z.array(SimilarDayMatchSchema))),
  behaviorSimilarDayReplay: (symbol = "NIFTY-MOCK", similarDayId = "mock-day-2024-03-11") => get(`/api/v1/behavior/similar-days/${symbol}/replay/${similarDayId}`, envelope(SimilarDayReplaySchema)),
  behaviorFailureLibrary: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/stock/${symbol}/failure-library`, envelope(FailureLibrarySchema)),
  behaviorTrustTable: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/stock/${symbol}/trust-table`, envelope(LearningTrustSchema)),
  behaviorDecision: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/decision/current?symbol=${encodeURIComponent(symbol)}`, envelope(TradeDecisionSchema)),
  behaviorRisk: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/risk/current?symbol=${encodeURIComponent(symbol)}`, envelope(RiskSizingSchema)),
  behaviorExecution: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/execution/current?symbol=${encodeURIComponent(symbol)}`, envelope(ExecutionSimulationSchema)),
  jarvisUsefulness: (symbol = "RELIANCE") => get(`/api/v1/jarvis/usefulness/${encodeURIComponent(symbol)}`, envelope(z.object({}).passthrough())),
  behaviorPanelMap: () => get("/api/v1/behavior/frontend/panel-map", envelope(BehaviorFrontendPanelMapSchema)),
  behaviorRuntimeReadiness: () => get("/api/v1/behavior/runtime/readiness", envelope(RuntimeReadinessSchema)),
  behaviorChartReplay: () => get("/api/v1/behavior/chart/replay/current", envelope(BehaviorChartReplaySchema)),
  behaviorIndicatorExpansion: () => get("/api/v1/behavior/indicators/expansion/current", envelope(BehaviorIndicatorExpansionSchema)),
  behaviorReplayIndicatorChart: () => get("/api/v1/behavior/replay/indicator-chart/current", envelope(ReplayIndicatorValidationSchema)),
  behaviorReplayIndicatorMatrix: () => get("/api/v1/behavior/replay/indicator-matrix/current", envelope(ReplayIndicatorMatrixSchema)),
  behaviorMatrixDecisionReadiness: () => get("/api/v1/behavior/decision/readiness/current", envelope(MatrixDecisionReadinessSchema)),
  behaviorTradeLifecycle: () => get("/api/v1/behavior/lifecycle/current", envelope(TradeLifecycleSimulationSchema)),
  behaviorLifecycleComparison: () => get("/api/v1/behavior/lifecycle/compare/current", envelope(TradeLifecycleScenarioComparisonSchema)),
  behaviorLifecycleEvidence: () => get("/api/v1/behavior/lifecycle/evidence/current", envelope(LifecycleEvidenceDrilldownSchema)),
  behaviorTradeabilityGuidance: () => get("/api/v1/behavior/tradeability/current", envelope(TradeabilityGuidanceSchema)),
  kronosStatus: () => get("/api/v1/kronos/status", envelope(KronosRuntimeStatusSchema)),
  kronosServiceStatus: () => get("/api/v1/kronos/service/status", envelope(KronosServiceBridgeStatusSchema)),
  kronosForecast: () => post("/api/v1/kronos/forecast", { symbol: "NIFTY-MOCK", timeframe: "5m", seed: 42, lookback_candles: 64, forecast_horizon_bars: 12 }, envelope(KronosForecastSchema)),
  twinCurrent: () => get("/api/v1/twin/current", envelope(TwinEngineComparisonSchema)),
  twinDashboard: () => get("/api/v1/twin/dashboard/current", envelope(TwinMachineDashboardSchema)),
  openAlgoVerifyCurrentIntent: () => get("/api/v1/openalgo/verify-intent/current", envelope(BotHandoffVerificationSchema)),
  openAlgoExecutorDryRunCurrent: () => get("/api/v1/openalgo/executor/dry-run/current", envelope(ExecutorDryRunPackageSchema)),
  openAlgoExecutorGoldenFixtures: () => get("/api/v1/openalgo/executor/golden-fixtures", envelope(ExecutorGoldenFixtureRegistrySchema)),
  openAlgoExecutorGoldenVerify: () => get("/api/v1/openalgo/executor/golden-fixtures/verify", envelope(ExecutorGoldenRegistryVerificationSchema)),
  openAlgoExecutorConformance: () => get("/api/v1/openalgo/executor/conformance/current", envelope(ExecutorAdapterConformanceSchema)),
  openAlgoTransportStatus: () => get("/api/v1/openalgo/transport/status", envelope(ExecutorTransportStatusSchema)),
  openAlgoTransportOutbox: () => get("/api/v1/openalgo/transport/outbox?limit=20", envelope(z.array(ExecutorTransportOutboxRecordSchema))),
  openAlgoTransportTraces: () => get("/api/v1/openalgo/transport/traces?limit=20", envelope(z.array(ExecutorTransportTraceSchema))),
  openAlgoAdapterHarness: () => get("/api/v1/openalgo/adapter-harness/status", envelope(z.object({}).passthrough())),
  jarvisOpenAlgoHandoffGate: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/openalgo/handoff-gate/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisOpenAlgoPaperBridge: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/openalgo/paper-bridge/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisPaperExecutionLoop: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/paper-execution-loop/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisDecisionQualityGate: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/decision-quality-gate/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisTradingDecisionOutput: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/trading-decision-output/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisChartOverlayQa: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/chart-overlay-qa/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisEvidenceLatencyBudget: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/evidence-latency-budget/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisEvidenceCache: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/evidence-cache/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisRealtimeFreshness: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/realtime-freshness/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&max_age_seconds=10`, envelope(z.object({}).passthrough())),
  openAlgoResilience: () => get("/api/v1/openalgo/resilience/current?evidence_window=100", envelope(TransportResilienceSchema)),
  openAlgoFaultHarness: () => post("/api/v1/openalgo/resilience/fault-harness", { sample_count: 1000 }, envelope(TransportFaultHarnessSchema)),
  openAlgoSecurityPosture: () => get("/api/v1/openalgo/security/posture", envelope(TransportSecurityPostureSchema)),
  openAlgoSecurityThreatReport: () => get("/api/v1/openalgo/security/threat-report", envelope(TransportSecurityThreatReportSchema)),
  deploymentReadiness: () => get("/api/v1/deployment/readiness", envelope(DeploymentReadinessSchema)),
  deploymentSmoke: () => get("/api/v1/deployment/smoke", envelope(DeploymentSmokeSchema)),
  finalReleaseAudit: () => get("/api/v1/release/final-audit", envelope(FinalProductionReadinessAuditSchema)),
  jarvisFinalProductionAudit: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/final-production-audit/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisReadinessRemediation: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/readiness-remediation/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  behaviorWalkForward: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/validation/walk-forward?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorValidationSchema)),
  behaviorOutOfSample: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/validation/out-of-sample?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorValidationSchema)),
  behaviorDrift: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/safety/drift/current?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorDriftSchema)),
  behaviorOod: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/safety/ood/current?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorOODSchema)),
  behaviorRealityGap: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/safety/reality-gap/current?symbol=${encodeURIComponent(symbol)}`, envelope(RealityGapSchema)),
  behaviorAcpStatus: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/acp/status?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorAcpSchema)),
  behaviorSafetyReport: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/safety/report/current?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorSafetyReportSchema)),
  behaviorSafetyReports: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/safety/reports?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(BehaviorSafetyReportSchema))),
  behaviorQuarantines: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/memory/quarantine?symbol=${encodeURIComponent(symbol)}&active_only=true`, envelope(z.array(MemoryQuarantineSchema))),
  behaviorRebuildPlan: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/memory/rebuild-plan/${encodeURIComponent(symbol)}`, envelope(MemoryRebuildPlanSchema)),
  behaviorGoldenFixtures: () => get("/api/v1/behavior/replay/golden-fixtures", envelope(z.array(GoldenReplayFixtureSchema))),
  behaviorGoldenVerify: (fixtureId = "golden-nifty-mock-golden-opening-drive-42") => get(`/api/v1/behavior/replay/golden-fixtures/${encodeURIComponent(fixtureId)}/verify`, envelope(GoldenReplayVerificationSchema)),
  behaviorBenchmarkReport: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/benchmark/report/current?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorBenchmarkReportSchema)),
  behaviorBenchmarkReports: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/benchmark/reports?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(BehaviorBenchmarkReportSchema))),
  behaviorBenchmarkDrilldown: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/benchmark/report/drilldown/current?symbol=${encodeURIComponent(symbol)}`, envelope(BenchmarkDrilldownSchema)),
  behaviorScenarioCoverage: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/benchmark/scenario-coverage/current?symbol=${encodeURIComponent(symbol)}`, envelope(BehaviorScenarioCoverageReportSchema)),
  behaviorScenarioCoverageReports: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/benchmark/scenario-coverage/reports?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(BehaviorScenarioCoverageReportSchema))),
  behaviorReleaseChecklist: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/release/mock-to-replay/checklist?symbol=${encodeURIComponent(symbol)}`, envelope(ReleaseChecklistSchema)),
  behaviorReleaseChecklists: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/release/checklists?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(ReleaseChecklistSchema))),
  behaviorReleaseApprovals: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/release/approvals?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(ReleaseApprovalSchema))),
  behaviorReleaseEvidence: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/release/evidence/current?symbol=${encodeURIComponent(symbol)}`, envelope(ReleaseEvidenceBundleSchema)),
  behaviorReleaseEvidenceBundles: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/release/evidence/bundles?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(ReleaseEvidenceBundleSchema))),
  behaviorReleaseArtifacts: (symbol = "NIFTY-MOCK") => get(`/api/v1/behavior/release/evidence/artifacts?symbol=${encodeURIComponent(symbol)}`, envelope(z.array(ReleaseEvidenceArtifactSchema))),
  behaviorReleaseArtifactVerify: (artifactId: string) => get(`/api/v1/behavior/release/evidence/artifacts/${encodeURIComponent(artifactId)}/verify`, envelope(ReleaseEvidenceArtifactVerificationSchema)),
  jarvisDecisionRoom: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/decision-room/state/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisDecisionFusion: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/decision-room/fusion/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisMasterPanel: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/decision-room/master-panel/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisReplayDeterminism: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/decision-room/replay-determinism/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisProductionBlockers: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/production-blockers/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisBlockerResolution: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/blocker-resolution/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisPreflightEvidence: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/preflight-evidence/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisGeminiStatus: () => get("/api/v1/jarvis/gemini/status", envelope(z.object({}).passthrough())),
  aiCredentialStatus: () => get("/api/v1/ai/credentials/status", envelope(z.object({}).passthrough())),
  saveGeminiCredential: (slot: number, apiKey: string) => post("/api/v1/ai/credentials/gemini", { slot, api_key: apiKey }, envelope(z.object({}).passthrough())),
  saveGrokCredential: (apiKey: string) => post("/api/v1/ai/credentials/grok", { api_key: apiKey }, envelope(z.object({}).passthrough())),
  testGeminiCredential: (slot?: number | null) => post("/api/v1/ai/credentials/test-gemini", slot ? { slot } : {}, envelope(z.object({}).passthrough())),
  testGrokCredential: () => post("/api/v1/ai/credentials/test-grok", {}, envelope(z.object({}).passthrough())),
  clearGeminiCredential: (slot: number) => del(`/api/v1/ai/credentials/gemini/${encodeURIComponent(slot)}`, envelope(z.object({}).passthrough())),
  clearGrokCredential: () => del("/api/v1/ai/credentials/grok", envelope(z.object({}).passthrough())),
  jarvisGeminiLiveReview: (symbol = "RELIANCE", execute = false, timeframe = "1m") => post(`/api/v1/jarvis/gemini/live-review/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, { execute }, envelope(z.object({}).passthrough())),
  jarvisGrokStatus: () => get("/api/v1/jarvis/grok/status", envelope(z.object({}).passthrough())),
  jarvisGrokGatewayStatus: (checkHealth = false) => get(`/api/v1/jarvis/grok-gateway/status?check_health=${checkHealth ? "true" : "false"}`, envelope(z.object({}).passthrough())),
  jarvisGrokGatewayConnect: () => post("/api/v1/jarvis/grok-gateway/connect", {}, envelope(z.object({}).passthrough())),
  jarvisGrokGatewayReview: (symbol = "RELIANCE", execute = false, timeframe = "1m") => post(`/api/v1/jarvis/grok-gateway/review/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, { execute }, envelope(z.object({}).passthrough())),
  jarvisGrokLiveReview: (symbol = "RELIANCE", execute = false, timeframe = "1m") => post(`/api/v1/jarvis/grok/live-review/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, { execute }, envelope(z.object({}).passthrough())),
  jarvisAiComparison: (symbol = "RELIANCE", executeGemini = false, executeGrok = false, timeframe = "1m") => post(`/api/v1/jarvis/ai-review/compare/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, { execute_gemini: executeGemini, execute_grok: executeGrok }, envelope(z.object({}).passthrough())),
  jarvisAiComparisonHistory: (symbol = "RELIANCE") => get(`/api/v1/jarvis/ai-review/comparison-history/${encodeURIComponent(symbol)}?limit=50&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisAiReviewRefreshGuard: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/ai-review/refresh-guard/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=50&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisAiRefreshAction: (symbol = "RELIANCE", execute = false, timeframe = "1m") => post(`/api/v1/jarvis/ai-review/refresh-action/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=50&stale_after_seconds=900`, { execute }, envelope(z.object({}).passthrough())),
  jarvisAiRefreshResponseSample: (symbol = "RELIANCE", timeframe = "1m") => post(`/api/v1/jarvis/ai-review/refresh-response/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=50&stale_after_seconds=900`, {
    provider: "manual",
    candidate_response: {
      review_status: "valid",
      agrees_with_trade_vision: true,
      pattern_interpretation: "Manual refresh sample: wait until Trade Vision evidence confirms a clean setup.",
      entry_guidance: "Wait for the current Trade Vision entry condition.",
      risk_warning: "External AI refresh is display-only and cannot route orders.",
      best_indicator_for_pattern: ["indicator_snapshot", "vwap_position"],
      avoid_if: ["safety_summary blocking gates appear"],
      confidence_comment: "No confidence boost is allowed from external AI refresh.",
      final_action: "TRADE_VISION_ONLY",
      cited_evidence_keys: ["trade_vision_decision", "indicator_snapshot", "safety_summary"],
    },
  }, envelope(z.object({}).passthrough())),
  jarvisAiRefreshResponseLedger: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/ai-review/refresh-ledger/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=100&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisAiEvidenceDiff: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/ai-review/evidence-diff/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=100`, envelope(z.object({}).passthrough())),
  jarvisProviderDisagreement: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/ai-review/disagreement-explorer/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=100`, envelope(z.object({}).passthrough())),
  jarvisVerifiedReviewPacket: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/ai-review/verified-packet/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=100&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisOpenAlgoSafeIntentBinding: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/openalgo/safe-intent-binding/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=100&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisPaperReadySafetyAudit: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/paper-ready-safety-audit/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&limit=100&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisGeminiOutboundBundle: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/gemini/outbound-bundle/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisGeminiFallbackReadiness: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/gemini/fallback-readiness/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisGeminiLiveReviewHarness: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/gemini/live-review-harness/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisGeminiDecisionRoom: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/gemini/decision-room/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisExternalAiReviewIntake: (symbol = "RELIANCE", source = "gemini", timeframe = "1m") => get(`/api/v1/jarvis/external-ai/review-intake/sample/${encodeURIComponent(symbol)}?source=${encodeURIComponent(source)}&timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisExternalAiReviewAudit: (symbol = "RELIANCE") => get(`/api/v1/jarvis/external-ai/review-audit?symbol=${encodeURIComponent(symbol)}&limit=100`, envelope(z.object({}).passthrough())),
  jarvisExternalAiReliability: (symbol = "RELIANCE") => get(`/api/v1/jarvis/external-ai/reliability?symbol=${encodeURIComponent(symbol)}&timeframe=1m&rows=390&position=tail&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisVerifiedEvidence: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/verified-evidence/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisReviewPreflight: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/review-preflight/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisCorrectionPacket: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/correction-review-packet/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisCorrectionValidation: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/correction-review/sample/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&stale_after_seconds=900`, envelope(z.object({}).passthrough())),
  jarvisCorrectionAudit: (symbol = "RELIANCE") => get(`/api/v1/jarvis/correction-review/audit?symbol=${encodeURIComponent(symbol)}&limit=100`, envelope(z.object({}).passthrough())),
  jarvisCorrectionRecords: (symbol = "RELIANCE") => get(`/api/v1/jarvis/correction-review/records?symbol=${encodeURIComponent(symbol)}&limit=10`, envelope(z.array(z.object({}).passthrough()))),
  jarvisExternalAiAuditIntegrity: (symbol = "RELIANCE") => get(`/api/v1/jarvis/external-ai/audit-integrity?symbol=${encodeURIComponent(symbol)}&limit=100&stale_after_seconds=86400`, envelope(z.object({}).passthrough())),
  jarvisDecisionEvidenceExport: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/decision-evidence/export/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&stale_after_seconds=86400`, envelope(z.object({}).passthrough())),
  jarvisDailyVerifiedAuthority: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/daily-verified-authority/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail&stale_after_seconds=86400`, envelope(z.object({}).passthrough())),
  jarvisIndicatorCombinationMemory: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/indicator-combination-memory/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  jarvisCandleCauseEffectMemory: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/jarvis/candle-cause-effect-memory/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&rows=390&position=tail`, envelope(z.object({}).passthrough())),
  nineCandleHybridDecision: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/decision/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  nineCandleVectorAudit: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/vector-audit/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  nineCandleFeatureManifestIntegrity: () => get(`/api/v1/behavior/9c-dna/feature-manifest/integrity`, envelope(z.object({}).passthrough())),
  nineCandleIndicatorPromotion: (symbol = "RELIANCE", timeframe = "1m", useRealIndicators = false) => get(`/api/v1/behavior/9c-dna/indicator-promotion/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&use_real_indicators=${useRealIndicators ? "true" : "false"}`, envelope(z.object({}).passthrough())),
  nineCandleIndicatorRuntime: (symbol = "RELIANCE", timeframe = "1m", useRealIndicators = true) => get(`/api/v1/behavior/9c-dna/indicator-runtime/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&use_real_indicators=${useRealIndicators ? "true" : "false"}`, envelope(z.object({}).passthrough())),
  indicatorCacheSave: (symbol = "RELIANCE", timeframe = "1m", useRealIndicators = false, forceRecompute = false) => post(`/api/v1/behavior/indicator-cache/save/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&use_real_indicators=${useRealIndicators ? "true" : "false"}&force_recompute=${forceRecompute ? "true" : "false"}`, {}, envelope(z.object({}).passthrough())),
  indicatorCacheStatus: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/indicator-cache/status/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  indicatorCacheResults: (symbol = "RELIANCE", timeframe = "1m", limit = 25) => get(`/api/v1/behavior/indicator-cache/results/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${encodeURIComponent(String(limit))}`, envelope(z.object({}).passthrough())),
  indicatorCacheDelete: (cacheId: string) => del(`/api/v1/behavior/indicator-cache/${encodeURIComponent(cacheId)}`, envelope(z.object({}).passthrough())),
  indicatorSignalHistory: (symbol = "RELIANCE", indicatorId = "si_macd_ta", timeframe = "1m", limit = 50) => get(`/api/v1/behavior/indicators/${encodeURIComponent(indicatorId)}/signal-history/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${encodeURIComponent(String(limit))}`, envelope(z.object({}).passthrough())),
  indicatorReliabilityDrilldown: (symbol = "RELIANCE", indicatorId = "si_macd_ta", timeframe = "1m", limit = 50) => get(`/api/v1/behavior/indicators/${encodeURIComponent(indicatorId)}/reliability-drilldown/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${encodeURIComponent(String(limit))}`, envelope(z.object({}).passthrough())),
  indicatorSignalHistoryIngestCurrent: (symbol = "RELIANCE", timeframe = "1m", maxRecords = 12) => post(`/api/v1/behavior/indicators/reliability/ingest-current`, { symbol, timeframe, max_records: maxRecords, include_neutral: false, use_real_indicators: false }, envelope(z.object({}).passthrough())),
  indicatorSignalHistoryCompletePending: (payload: Record<string, unknown>) => post(`/api/v1/behavior/indicators/reliability/complete-pending`, payload, envelope(z.object({}).passthrough())),
  nineCandleSetupMemory: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/setup-memory/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=25`, envelope(z.object({}).passthrough())),
  nineCandlePathAnalogs: (symbol = "RELIANCE", timeframe = "1m", limit = 8) => get(`/api/v1/behavior/9c-dna/path-analogs/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${encodeURIComponent(String(limit))}`, envelope(z.object({}).passthrough())),
  nineCandleOodStatus: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/ood-status/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  nineCandleHypotheses: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/hypotheses/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  nineCandleCalibration: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/calibration?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  nineCandlePromotionGuard: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/9c-dna/model-promotion-guard?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
  tvProdRed001: (symbol = "RELIANCE", timeframe = "1m") => get(`/api/v1/behavior/red-team/tv-prod-red-001?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`, envelope(z.object({}).passthrough())),
};

function mockBehaviorContextPayload() {
  const base = 1_714_724_800_000_000_000;
  const five = 300_000_000_000;
  const hour = 3_600_000_000_000;
  const bars = [
    [100.0, 101.0, 99.5, 100.8],
    [100.8, 102.0, 100.4, 101.7],
    [101.7, 103.0, 101.2, 102.7],
    [102.7, 104.0, 102.4, 103.5],
  ].map(([open, high, low, close], idx) => ({
    symbol: "NIFTY-MOCK",
    timeframe: "5m",
    timestamp_ns: base + idx * five,
    open,
    high,
    low,
    close,
    volume: 2000 + idx * 250,
    source: "mock",
    sequence_number: idx + 1,
  }));
  const higher = [
    [base - 2 * hour, 96.0, 99.0, 95.0, 98.0],
    [base - hour, 98.0, 102.0, 97.5, 101.0],
  ].map(([timestamp_ns, open, high, low, close], idx) => ({
    symbol: "NIFTY-MOCK",
    timeframe: "1H",
    timestamp_ns,
    open,
    high,
    low,
    close,
    volume: 5000 + idx * 3000,
    source: "mock",
    sequence_number: idx + 1,
  }));
  return {
    series: { symbol: "NIFTY-MOCK", timeframe: "5m", bars, snapshot_id: "frontend-context-mock", schema_version: "candles.v1" },
    direction: "long",
    decision_time_ns: base + 4 * five,
    previous_day_high: 106.0,
    previous_day_low: 96.0,
    previous_close: 100.0,
    opening_range_high: 103.0,
    opening_range_low: 99.5,
    volume_profile_hvn: 102.8,
    volume_profile_lvn: 98.0,
    higher_timeframe_series: [{ symbol: "NIFTY-MOCK", timeframe: "1H", bars: higher, snapshot_id: "frontend-context-1h", schema_version: "candles.v1" }],
    stock_return_pct: 1.4,
    index_return_pct: 0.45,
    sector_return_pct: 0.55,
    global_risk_score: 0.2,
  };
}

function mockBehaviorSessionPayload(symbol = "NIFTY-MOCK") {
  const base = Date.UTC(2024, 5, 3, 3, 45) * 1_000_000; // 09:15 IST, Monday.
  const five = 300_000_000_000;
  const bars = [
    [100.0, 101.0, 99.8, 100.7, 1200],
    [100.7, 101.8, 100.4, 101.5, 1500],
    [101.5, 102.5, 101.1, 102.2, 1900],
    [102.2, 103.0, 101.9, 102.8, 2200],
    [102.8, 103.7, 102.5, 103.4, 2600],
    [103.4, 103.6, 102.9, 103.1, 1000],
    [103.1, 103.4, 102.8, 103.0, 950],
    [103.0, 103.2, 102.6, 102.9, 900],
  ].map(([open, high, low, close, volume], idx) => {
    const lunchOffset = idx >= 5 ? 27 * five : 0;
    return {
      symbol,
      timeframe: "5m",
      timestamp_ns: base + idx * five + lunchOffset,
      open,
      high,
      low,
      close,
      volume,
      source: "mock",
      sequence_number: idx + 1,
    };
  });
  return {
    series: { symbol, timeframe: "5m", bars, snapshot_id: "frontend-session-rhythm", schema_version: "candles.v1" },
    decision_time_ns: bars[bars.length - 1].timestamp_ns,
    timezone_offset_minutes: 330,
    minimum_bars_per_segment: 2,
  };
}

async function put<T extends z.ZodTypeAny>(path: string, body: unknown, schema: T, headers: Record<string, string> = {}): Promise<z.infer<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await buildApiError(path, response);
  const json = await response.json();
  return parseContract(path, schema, json);
}
