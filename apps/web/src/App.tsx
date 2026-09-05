import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError, ContractValidationError, api } from "./api/client";
import { AiCredentialsPanel } from "./components/aiCredentialsPanel";
import { Card, Metric, Panel, Status, money, pct } from "./components/primitives";
import { IntegrityPanel, OrderPathPanel, RiskPanel } from "./components/safetyPanels";
import { Implementation, Knowledge } from "./components/workspaces/referenceWorkspaces";
import { ReplayEvidencePanels } from "./components/workspaces/replayEvidencePanels";
import { System } from "./components/workspaces/systemWorkspace";
import type { ApiEnvelope } from "@tradevision/contracts";

type Workspace = "cockpit" | "marketdna" | "behavior" | "research" | "jarvis" | "replay" | "knowledge" | "implementation" | "system";

type AppData = {
  auth?: ApiEnvelope<any>;
  layout?: ApiEnvelope<any>;
  time?: ApiEnvelope<any>;
  mode?: ApiEnvelope<any>;
  features?: ApiEnvelope<any>;
          killswitch?: ApiEnvelope<any>;
          storage?: ApiEnvelope<any>;
  observability?: ApiEnvelope<any>;
  pipeline?: ApiEnvelope<any>;
  decision?: ApiEnvelope<any>;
  portfolio?: ApiEnvelope<any>;
  risk?: ApiEnvelope<any>;
  marketDna?: ApiEnvelope<any>;
  microstructure?: ApiEnvelope<any>;
          replay?: ApiEnvelope<any>;
  replayArchive?: ApiEnvelope<any>;
  execution?: ApiEnvelope<any>;
  orderPath?: ApiEnvelope<any>;
          dataQuality?: ApiEnvelope<any>;
          snapshots?: ApiEnvelope<any>;
          featureRegistry?: ApiEnvelope<any>;
  integrity?: ApiEnvelope<any>;
  audit?: ApiEnvelope<any>;
  auditIntegrity?: ApiEnvelope<any>;
  graph?: ApiEnvelope<any>;
  behaviorSpec?: ApiEnvelope<any>;
  behaviorColumns?: ApiEnvelope<any>;
  behaviorAnalysis?: ApiEnvelope<any>;
  behaviorContext?: ApiEnvelope<any>;
  behaviorSession?: ApiEnvelope<any>;
  behaviorDayMemory?: ApiEnvelope<any>;
  stockDnaSummary?: ApiEnvelope<any>;
  patternMemory?: ApiEnvelope<any>;
  similarDays?: ApiEnvelope<any>;
  similarDayReplay?: ApiEnvelope<any>;
  failureLibrary?: ApiEnvelope<any>;
  trustTable?: ApiEnvelope<any>;
  tradeDecision?: ApiEnvelope<any>;
  behaviorRisk?: ApiEnvelope<any>;
  behaviorExecution?: ApiEnvelope<any>;
  behaviorPanelMap?: ApiEnvelope<any>;
  behaviorRuntimeReadiness?: ApiEnvelope<any>;
  behaviorChartReplay?: ApiEnvelope<any>;
  behaviorIndicatorExpansion?: ApiEnvelope<any>;
  behaviorReplayIndicatorChart?: ApiEnvelope<any>;
  behaviorReplayIndicatorMatrix?: ApiEnvelope<any>;
  behaviorMatrixDecisionReadiness?: ApiEnvelope<any>;
  behaviorTradeLifecycle?: ApiEnvelope<any>;
  behaviorLifecycleComparison?: ApiEnvelope<any>;
  behaviorLifecycleEvidence?: ApiEnvelope<any>;
  behaviorTradeabilityGuidance?: ApiEnvelope<any>;
  walkForward?: ApiEnvelope<any>;
  outOfSample?: ApiEnvelope<any>;
  behaviorDrift?: ApiEnvelope<any>;
  behaviorOod?: ApiEnvelope<any>;
  behaviorRealityGap?: ApiEnvelope<any>;
  behaviorAcp?: ApiEnvelope<any>;
  behaviorSafetyReport?: ApiEnvelope<any>;
  behaviorSafetyReports?: ApiEnvelope<any>;
  behaviorQuarantines?: ApiEnvelope<any>;
  behaviorRebuildPlan?: ApiEnvelope<any>;
  behaviorGoldenFixtures?: ApiEnvelope<any>;
  behaviorGoldenVerify?: ApiEnvelope<any>;
  behaviorBenchmarkReport?: ApiEnvelope<any>;
  behaviorBenchmarkReports?: ApiEnvelope<any>;
  behaviorBenchmarkDrilldown?: ApiEnvelope<any>;
  behaviorScenarioCoverage?: ApiEnvelope<any>;
  behaviorScenarioCoverageReports?: ApiEnvelope<any>;
  behaviorReleaseChecklist?: ApiEnvelope<any>;
  behaviorReleaseChecklists?: ApiEnvelope<any>;
  behaviorReleaseApprovals?: ApiEnvelope<any>;
  behaviorReleaseEvidence?: ApiEnvelope<any>;
  behaviorReleaseEvidenceBundles?: ApiEnvelope<any>;
  behaviorReleaseArtifacts?: ApiEnvelope<any>;
  jarvisDecisionRoom?: ApiEnvelope<any>;
  jarvisDecisionFusion?: ApiEnvelope<any>;
  jarvisMasterPanel?: ApiEnvelope<any>;
  jarvisReplayDeterminism?: ApiEnvelope<any>;
  jarvisProductionBlockers?: ApiEnvelope<any>;
  jarvisBlockerResolution?: ApiEnvelope<any>;
  jarvisPreflightEvidence?: ApiEnvelope<any>;
  jarvisGeminiStatus?: ApiEnvelope<any>;
  aiCredentialStatus?: ApiEnvelope<any>;
  jarvisGeminiLiveReview?: ApiEnvelope<any>;
  jarvisGrokStatus?: ApiEnvelope<any>;
  jarvisGrokLiveReview?: ApiEnvelope<any>;
  jarvisAiComparison?: ApiEnvelope<any>;
  jarvisAiComparisonHistory?: ApiEnvelope<any>;
  jarvisAiReviewRefreshGuard?: ApiEnvelope<any>;
  jarvisAiRefreshAction?: ApiEnvelope<any>;
  jarvisAiRefreshResponseSample?: ApiEnvelope<any>;
  jarvisAiRefreshResponseLedger?: ApiEnvelope<any>;
  jarvisAiEvidenceDiff?: ApiEnvelope<any>;
  jarvisProviderDisagreement?: ApiEnvelope<any>;
  jarvisVerifiedReviewPacket?: ApiEnvelope<any>;
  jarvisOpenAlgoSafeIntentBinding?: ApiEnvelope<any>;
  jarvisPaperReadySafetyAudit?: ApiEnvelope<any>;
  jarvisGeminiOutboundBundle?: ApiEnvelope<any>;
  jarvisGeminiFallbackReadiness?: ApiEnvelope<any>;
  jarvisGeminiLiveReviewHarness?: ApiEnvelope<any>;
  jarvisGeminiDecisionRoom?: ApiEnvelope<any>;
  jarvisExternalAiReviewIntake?: ApiEnvelope<any>;
  jarvisExternalAiReviewAudit?: ApiEnvelope<any>;
  jarvisExternalAiReliability?: ApiEnvelope<any>;
  jarvisVerifiedEvidence?: ApiEnvelope<any>;
  jarvisReviewPreflight?: ApiEnvelope<any>;
  jarvisCorrectionPacket?: ApiEnvelope<any>;
  jarvisCorrectionValidation?: ApiEnvelope<any>;
  jarvisCorrectionAudit?: ApiEnvelope<any>;
  jarvisCorrectionRecords?: ApiEnvelope<any[]>;
  jarvisExternalAiAuditIntegrity?: ApiEnvelope<any>;
  jarvisDecisionEvidenceExport?: ApiEnvelope<any>;
  jarvisDailyVerifiedAuthority?: ApiEnvelope<any>;
  jarvisIndicatorCombinationMemory?: ApiEnvelope<any>;
  jarvisCandleCauseEffectMemory?: ApiEnvelope<any>;
  nineCandleHybrid?: ApiEnvelope<any>;
  nineCandleVectorAudit?: ApiEnvelope<any>;
  nineCandleFeatureManifestIntegrity?: ApiEnvelope<any>;
  nineCandleIndicatorPromotion?: ApiEnvelope<any>;
  nineCandleIndicatorRuntime?: ApiEnvelope<any>;
  indicatorCacheStatus?: ApiEnvelope<any>;
  indicatorCacheResults?: ApiEnvelope<any>;
  indicatorSignalHistory?: ApiEnvelope<any>;
  indicatorReliabilityDrilldown?: ApiEnvelope<any>;
  nineCandleSetupMemory?: ApiEnvelope<any>;
  nineCandlePathAnalogs?: ApiEnvelope<any>;
  nineCandleOodStatus?: ApiEnvelope<any>;
  nineCandleHypotheses?: ApiEnvelope<any>;
  nineCandleCalibration?: ApiEnvelope<any>;
  nineCandlePromotionGuard?: ApiEnvelope<any>;
  tvProdRed001?: ApiEnvelope<any>;
  jarvisUsefulness?: ApiEnvelope<any>;
  stockMemoryProfile?: ApiEnvelope<any>;
  kronosStatus?: ApiEnvelope<any>;
  kronosServiceStatus?: ApiEnvelope<any>;
  kronosForecast?: ApiEnvelope<any>;
  twinCurrent?: ApiEnvelope<any>;
  twinDashboard?: ApiEnvelope<any>;
  openAlgoVerifier?: ApiEnvelope<any>;
  openAlgoDryRun?: ApiEnvelope<any>;
  openAlgoGoldenFixtures?: ApiEnvelope<any>;
  openAlgoGoldenVerify?: ApiEnvelope<any>;
  openAlgoConformance?: ApiEnvelope<any>;
  openAlgoTransportStatus?: ApiEnvelope<any>;
  openAlgoTransportOutbox?: ApiEnvelope<any>;
  openAlgoTransportTraces?: ApiEnvelope<any>;
  openAlgoAdapterHarness?: ApiEnvelope<any>;
  jarvisOpenAlgoHandoffGate?: ApiEnvelope<any>;
  jarvisOpenAlgoPaperBridge?: ApiEnvelope<any>;
  jarvisPaperExecutionLoop?: ApiEnvelope<any>;
  jarvisDecisionQualityGate?: ApiEnvelope<any>;
  jarvisTradingDecisionOutput?: ApiEnvelope<any>;
  jarvisChartOverlayQa?: ApiEnvelope<any>;
  jarvisEvidenceLatencyBudget?: ApiEnvelope<any>;
  jarvisEvidenceCache?: ApiEnvelope<any>;
  jarvisRealtimeFreshness?: ApiEnvelope<any>;
  openAlgoResilience?: ApiEnvelope<any>;
  openAlgoFaultHarness?: ApiEnvelope<any>;
  openAlgoSecurityPosture?: ApiEnvelope<any>;
  openAlgoSecurityThreatReport?: ApiEnvelope<any>;
  deploymentReadiness?: ApiEnvelope<any>;
  deploymentSmoke?: ApiEnvelope<any>;
  finalReleaseAudit?: ApiEnvelope<any>;
  jarvisFinalProductionAudit?: ApiEnvelope<any>;
  jarvisReadinessRemediation?: ApiEnvelope<any>;
};

type UiIssue = {
  kind: "offline" | "api" | "contract" | "unknown";
  title: string;
  detail: string;
};

const FRONTEND_API_LOAD_CONCURRENCY = 4;

async function runBounded(
  tasks: Array<() => Promise<any>>,
  concurrency = FRONTEND_API_LOAD_CONCURRENCY,
  onTaskError?: (error: unknown, index: number) => void,
): Promise<any[]> {
  const results: any[] = new Array(tasks.length);
  let nextIndex = 0;
  const workerCount = Math.min(Math.max(1, concurrency), tasks.length);
  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      while (nextIndex < tasks.length) {
        const currentIndex = nextIndex;
        nextIndex += 1;
        try {
          results[currentIndex] = await tasks[currentIndex]();
        } catch (error) {
          results[currentIndex] = undefined;
          onTaskError?.(error, currentIndex);
        }
      }
    }),
  );
  return results;
}

const workspaces: { id: Workspace; label: string }[] = [
  { id: "cockpit", label: "Cockpit" },
  { id: "marketdna", label: "MarketDNA" },
  { id: "behavior", label: "Behavior" },
  { id: "research", label: "Research" },
  { id: "jarvis", label: "Jarvis" },
  { id: "replay", label: "Replay" },
  { id: "knowledge", label: "Knowledge" },
  { id: "implementation", label: "Implementation" },
  { id: "system", label: "System" },
];

export function App() {
  const [active, setActive] = useState<Workspace>(() => {
    const hash = window.location.hash.replace("#", "") as Workspace;
    if (workspaces.some((workspace) => workspace.id === hash)) return hash;
    const persisted = readPersistedWorkspace();
    return persisted ?? "cockpit";
  });
  const [data, setData] = useState<AppData>({});
  const [offline, setOffline] = useState(false);
  const [issue, setIssue] = useState<UiIssue | null>(null);
  const [, setLoading] = useState(true);
  const refreshInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    try {
      const loadErrors: Array<{ index: number; error: unknown }> = [];
      const criticalTvProdRed001 = await api.tvProdRed001().catch((error) => {
        loadErrors.push({ index: -1, error });
        return undefined;
      });
      if (criticalTvProdRed001) {
        setData((current) => ({ ...current, tvProdRed001: criticalTvProdRed001 }));
      }
      const [
        auth,
        layout,
        time,
        mode,
        features,
                killswitch,
                storage,
        observability,
        pipeline,
        decision,
        portfolio,
        risk,
        marketDna,
        microstructure,
                replay,
        replayArchive,
        execution,
        orderPath,
                dataQuality,
                snapshots,
                featureRegistry,
        integrity,
        audit,
        auditIntegrity,
        graph,
        behaviorSpec,
        behaviorColumns,
        behaviorAnalysis,
        behaviorContext,
        behaviorSession,
        behaviorDayMemory,
        stockDnaSummary,
        patternMemory,
        similarDays,
        similarDayReplay,
        failureLibrary,
        trustTable,
        tradeDecision,
        behaviorRisk,
        behaviorExecution,
        behaviorPanelMap,
        behaviorRuntimeReadiness,
        behaviorChartReplay,
        behaviorIndicatorExpansion,
        behaviorReplayIndicatorChart,
        behaviorReplayIndicatorMatrix,
        behaviorMatrixDecisionReadiness,
        behaviorTradeLifecycle,
        behaviorLifecycleComparison,
        behaviorLifecycleEvidence,
        behaviorTradeabilityGuidance,
        walkForward,
        outOfSample,
        behaviorDrift,
        behaviorOod,
        behaviorRealityGap,
        behaviorAcp,
        behaviorSafetyReport,
        behaviorSafetyReports,
        behaviorQuarantines,
        behaviorRebuildPlan,
        behaviorGoldenFixtures,
        behaviorGoldenVerify,
        behaviorBenchmarkReport,
        behaviorBenchmarkReports,
        behaviorBenchmarkDrilldown,
        behaviorScenarioCoverage,
        behaviorScenarioCoverageReports,
        behaviorReleaseChecklist,
        behaviorReleaseChecklists,
        behaviorReleaseApprovals,
        behaviorReleaseEvidence,
        behaviorReleaseEvidenceBundles,
        behaviorReleaseArtifacts,
        jarvisDecisionRoom,
        jarvisDecisionFusion,
        jarvisMasterPanel,
        jarvisReplayDeterminism,
        jarvisProductionBlockers,
        jarvisBlockerResolution,
        jarvisPreflightEvidence,
        jarvisGeminiStatus,
        aiCredentialStatus,
        jarvisGeminiLiveReview,
        jarvisGrokStatus,
        jarvisGrokLiveReview,
        jarvisAiComparison,
        jarvisAiComparisonHistory,
        jarvisAiReviewRefreshGuard,
        jarvisAiRefreshAction,
        jarvisAiRefreshResponseSample,
        jarvisAiRefreshResponseLedger,
        jarvisAiEvidenceDiff,
        jarvisProviderDisagreement,
        jarvisVerifiedReviewPacket,
        jarvisOpenAlgoSafeIntentBinding,
        jarvisPaperReadySafetyAudit,
        jarvisGeminiOutboundBundle,
        jarvisGeminiFallbackReadiness,
        jarvisGeminiLiveReviewHarness,
        jarvisGeminiDecisionRoom,
        jarvisExternalAiReviewIntake,
        jarvisExternalAiReviewAudit,
        jarvisExternalAiReliability,
        jarvisVerifiedEvidence,
        jarvisReviewPreflight,
        jarvisCorrectionPacket,
        jarvisCorrectionValidation,
        jarvisCorrectionAudit,
        jarvisCorrectionRecords,
        jarvisExternalAiAuditIntegrity,
        jarvisDecisionEvidenceExport,
        jarvisDailyVerifiedAuthority,
        jarvisIndicatorCombinationMemory,
        jarvisCandleCauseEffectMemory,
        nineCandleHybrid,
        nineCandleVectorAudit,
        nineCandleFeatureManifestIntegrity,
        nineCandleIndicatorPromotion,
        nineCandleIndicatorRuntime,
        indicatorCacheStatus,
        indicatorCacheResults,
        indicatorSignalHistory,
        indicatorReliabilityDrilldown,
        nineCandleSetupMemory,
        nineCandlePathAnalogs,
        nineCandleOodStatus,
        nineCandleHypotheses,
        nineCandleCalibration,
        nineCandlePromotionGuard,
        tvProdRed001,
        jarvisUsefulness,
        stockMemoryProfile,
        kronosStatus,
        kronosServiceStatus,
        kronosForecast,
        twinCurrent,
        twinDashboard,
        openAlgoVerifier,
        openAlgoDryRun,
        openAlgoGoldenFixtures,
        openAlgoGoldenVerify,
        openAlgoConformance,
        openAlgoTransportStatus,
        openAlgoTransportOutbox,
        openAlgoTransportTraces,
        openAlgoAdapterHarness,
        jarvisOpenAlgoHandoffGate,
        jarvisOpenAlgoPaperBridge,
        jarvisPaperExecutionLoop,
        jarvisDecisionQualityGate,
        jarvisTradingDecisionOutput,
        jarvisChartOverlayQa,
        jarvisEvidenceLatencyBudget,
        jarvisEvidenceCache,
        jarvisRealtimeFreshness,
        openAlgoResilience,
        openAlgoFaultHarness,
        openAlgoSecurityPosture,
        openAlgoSecurityThreatReport,
        deploymentReadiness,
        deploymentSmoke,
        finalReleaseAudit,
        jarvisFinalProductionAudit,
        jarvisReadinessRemediation,
      ] = await runBounded([
        () => api.auth(),
        () => api.layout(active).catch(() => undefined),
        () => api.time(),
        () => api.mode(),
        () => api.features(),
                () => api.killswitch(),
                () => api.storage(),
        () => api.observability(),
        () => api.pipeline(),
        () => api.decision(),
        () => api.portfolio(),
        () => api.risk(),
        () => api.marketDna(),
        () => api.microstructure(),
                () => api.replay(),
        () => api.replayArchive(),
        () => api.execution(),
        () => api.orderPath(),
                () => api.dataQuality(),
                () => api.snapshots(),
                () => api.featureRegistry(),
        () => api.integrity(),
        () => api.audit(),
        () => api.auditIntegrity(),
        () => api.graph(),
        () => api.behaviorSpec(),
        () => api.behaviorColumns(),
        () => api.behaviorAnalyze(),
        () => api.behaviorContext(),
        () => api.behaviorSessionRhythm(),
        () => api.behaviorDayOfWeekMemory(),
        () => api.behaviorStockDnaSummary(),
        () => api.behaviorPatternMemory(),
        () => api.behaviorSimilarDays(),
        () => api.behaviorSimilarDayReplay(),
        () => api.behaviorFailureLibrary(),
        () => api.behaviorTrustTable(),
        () => api.behaviorDecision(),
        () => api.behaviorRisk(),
        () => api.behaviorExecution(),
        () => api.behaviorPanelMap(),
        () => api.behaviorRuntimeReadiness(),
        () => api.behaviorChartReplay(),
        () => api.behaviorIndicatorExpansion(),
        () => api.behaviorReplayIndicatorChart(),
        () => api.behaviorReplayIndicatorMatrix(),
        () => api.behaviorMatrixDecisionReadiness(),
        () => api.behaviorTradeLifecycle(),
        () => api.behaviorLifecycleComparison(),
        () => api.behaviorLifecycleEvidence(),
        () => api.behaviorTradeabilityGuidance(),
        () => api.behaviorWalkForward(),
        () => api.behaviorOutOfSample(),
        () => api.behaviorDrift(),
        () => api.behaviorOod(),
        () => api.behaviorRealityGap(),
        () => api.behaviorAcpStatus(),
        () => api.behaviorSafetyReport(),
        () => api.behaviorSafetyReports(),
        () => api.behaviorQuarantines(),
        () => api.behaviorRebuildPlan(),
        () => api.behaviorGoldenFixtures(),
        () => api.behaviorGoldenVerify(),
        () => api.behaviorBenchmarkReport(),
        () => api.behaviorBenchmarkReports(),
        () => api.behaviorBenchmarkDrilldown(),
        () => api.behaviorScenarioCoverage(),
        () => api.behaviorScenarioCoverageReports(),
        () => api.behaviorReleaseChecklist(),
        () => api.behaviorReleaseChecklists(),
        () => api.behaviorReleaseApprovals(),
        () => api.behaviorReleaseEvidence(),
        () => api.behaviorReleaseEvidenceBundles(),
        () => api.behaviorReleaseArtifacts(),
        () => api.jarvisDecisionRoom(),
        () => api.jarvisDecisionFusion(),
        () => api.jarvisMasterPanel(),
        () => api.jarvisReplayDeterminism(),
        () => api.jarvisProductionBlockers(),
        () => api.jarvisBlockerResolution(),
        () => api.jarvisPreflightEvidence(),
        () => api.jarvisGeminiStatus(),
        () => api.aiCredentialStatus(),
        () => api.jarvisGeminiLiveReview("RELIANCE", false),
        () => api.jarvisGrokStatus(),
        () => api.jarvisGrokLiveReview("RELIANCE", false),
        () => api.jarvisAiComparison("RELIANCE", false, false),
        () => api.jarvisAiComparisonHistory("RELIANCE"),
        () => api.jarvisAiReviewRefreshGuard("RELIANCE"),
        () => api.jarvisAiRefreshAction("RELIANCE", false),
        () => api.jarvisAiRefreshResponseSample("RELIANCE"),
        () => api.jarvisAiRefreshResponseLedger("RELIANCE"),
        () => api.jarvisAiEvidenceDiff("RELIANCE"),
        () => api.jarvisProviderDisagreement("RELIANCE"),
        () => api.jarvisVerifiedReviewPacket("RELIANCE"),
        () => api.jarvisOpenAlgoSafeIntentBinding("RELIANCE"),
        () => api.jarvisPaperReadySafetyAudit("RELIANCE"),
        () => api.jarvisGeminiOutboundBundle(),
        () => api.jarvisGeminiFallbackReadiness(),
        () => api.jarvisGeminiLiveReviewHarness(),
        () => api.jarvisGeminiDecisionRoom(),
        () => api.jarvisExternalAiReviewIntake(),
        () => api.jarvisExternalAiReviewAudit(),
        () => api.jarvisExternalAiReliability(),
        () => api.jarvisVerifiedEvidence(),
        () => api.jarvisReviewPreflight(),
        () => api.jarvisCorrectionPacket(),
        () => api.jarvisCorrectionValidation(),
        () => api.jarvisCorrectionAudit(),
        () => api.jarvisCorrectionRecords(),
        () => api.jarvisExternalAiAuditIntegrity(),
        () => api.jarvisDecisionEvidenceExport(),
        () => api.jarvisDailyVerifiedAuthority(),
        () => api.jarvisIndicatorCombinationMemory(),
        () => api.jarvisCandleCauseEffectMemory(),
        () => api.nineCandleHybridDecision(),
        () => api.nineCandleVectorAudit(),
        () => api.nineCandleFeatureManifestIntegrity(),
        () => api.nineCandleIndicatorPromotion(),
        () => api.nineCandleIndicatorRuntime(),
        () => api.indicatorCacheStatus(),
        () => api.indicatorCacheResults(),
        () => api.indicatorSignalHistory(),
        () => api.indicatorReliabilityDrilldown(),
        () => api.nineCandleSetupMemory(),
        () => api.nineCandlePathAnalogs(),
        () => api.nineCandleOodStatus(),
        () => api.nineCandleHypotheses(),
        () => api.nineCandleCalibration(),
        () => api.nineCandlePromotionGuard(),
        () => Promise.resolve(criticalTvProdRed001),
        () => api.jarvisUsefulness(),
        () => api.behaviorStockMemoryProfile(),
        () => api.kronosStatus(),
        () => api.kronosServiceStatus(),
        () => api.kronosForecast(),
        () => api.twinCurrent(),
        () => api.twinDashboard(),
        () => api.openAlgoVerifyCurrentIntent(),
        () => api.openAlgoExecutorDryRunCurrent(),
        () => api.openAlgoExecutorGoldenFixtures(),
        () => api.openAlgoExecutorGoldenVerify(),
        () => api.openAlgoExecutorConformance(),
        () => api.openAlgoTransportStatus(),
        () => api.openAlgoTransportOutbox(),
        () => api.openAlgoTransportTraces(),
        () => api.openAlgoAdapterHarness(),
        () => api.jarvisOpenAlgoHandoffGate(),
        () => api.jarvisOpenAlgoPaperBridge(),
        () => api.jarvisPaperExecutionLoop(),
        () => api.jarvisDecisionQualityGate(),
        () => api.jarvisTradingDecisionOutput(),
        () => api.jarvisChartOverlayQa(),
        () => api.jarvisEvidenceLatencyBudget(),
        () => api.jarvisEvidenceCache(),
        () => api.jarvisRealtimeFreshness(),
        () => api.openAlgoResilience(),
        () => api.openAlgoFaultHarness(),
        () => api.openAlgoSecurityPosture(),
        () => api.openAlgoSecurityThreatReport(),
        () => api.deploymentReadiness(),
        () => api.deploymentSmoke(),
        () => api.finalReleaseAudit(),
        () => api.jarvisFinalProductionAudit(),
        () => api.jarvisReadinessRemediation(),
      ], FRONTEND_API_LOAD_CONCURRENCY, (error, index) => loadErrors.push({ index, error }));
              setData({ auth, layout, time, mode, features, killswitch, storage, observability, pipeline, decision, portfolio, risk, marketDna, microstructure, replay, replayArchive, execution, orderPath, dataQuality, snapshots, featureRegistry, integrity, audit, auditIntegrity, graph, behaviorSpec, behaviorColumns, behaviorAnalysis, behaviorContext, behaviorSession, behaviorDayMemory, stockDnaSummary, patternMemory, similarDays, similarDayReplay, failureLibrary, trustTable, tradeDecision, behaviorRisk, behaviorExecution, behaviorPanelMap, behaviorRuntimeReadiness, behaviorChartReplay, behaviorIndicatorExpansion, behaviorReplayIndicatorChart, behaviorReplayIndicatorMatrix, behaviorMatrixDecisionReadiness, behaviorTradeLifecycle, behaviorLifecycleComparison, behaviorLifecycleEvidence, behaviorTradeabilityGuidance, walkForward, outOfSample, behaviorDrift, behaviorOod, behaviorRealityGap, behaviorAcp, behaviorSafetyReport, behaviorSafetyReports, behaviorQuarantines, behaviorRebuildPlan, behaviorGoldenFixtures, behaviorGoldenVerify, behaviorBenchmarkReport, behaviorBenchmarkReports, behaviorBenchmarkDrilldown, behaviorScenarioCoverage, behaviorScenarioCoverageReports, behaviorReleaseChecklist, behaviorReleaseChecklists, behaviorReleaseApprovals, behaviorReleaseEvidence, behaviorReleaseEvidenceBundles, behaviorReleaseArtifacts, jarvisDecisionRoom, jarvisDecisionFusion, jarvisMasterPanel, jarvisReplayDeterminism, jarvisProductionBlockers, jarvisBlockerResolution, jarvisPreflightEvidence, jarvisGeminiStatus, aiCredentialStatus, jarvisGeminiLiveReview, jarvisGrokStatus, jarvisGrokLiveReview, jarvisAiComparison, jarvisGeminiOutboundBundle, jarvisGeminiFallbackReadiness, jarvisGeminiLiveReviewHarness, jarvisGeminiDecisionRoom, jarvisExternalAiReviewIntake, jarvisExternalAiReviewAudit, jarvisExternalAiReliability, jarvisVerifiedEvidence, jarvisReviewPreflight, jarvisCorrectionPacket, jarvisCorrectionValidation, jarvisCorrectionAudit, jarvisCorrectionRecords, jarvisExternalAiAuditIntegrity, jarvisDecisionEvidenceExport, jarvisDailyVerifiedAuthority, jarvisIndicatorCombinationMemory, jarvisCandleCauseEffectMemory, nineCandleHybrid, nineCandleVectorAudit, nineCandleFeatureManifestIntegrity, nineCandleIndicatorPromotion, nineCandleIndicatorRuntime, indicatorCacheStatus, indicatorCacheResults, indicatorSignalHistory, indicatorReliabilityDrilldown, nineCandleSetupMemory, nineCandlePathAnalogs, nineCandleOodStatus, nineCandleHypotheses, nineCandleCalibration, nineCandlePromotionGuard, tvProdRed001, jarvisUsefulness, stockMemoryProfile, kronosStatus, kronosServiceStatus, kronosForecast, twinCurrent, twinDashboard, openAlgoVerifier, openAlgoDryRun, openAlgoGoldenFixtures, openAlgoGoldenVerify, openAlgoConformance, openAlgoTransportStatus, openAlgoTransportOutbox, openAlgoTransportTraces, openAlgoAdapterHarness, jarvisOpenAlgoHandoffGate, jarvisOpenAlgoPaperBridge, jarvisPaperExecutionLoop, jarvisDecisionQualityGate, jarvisTradingDecisionOutput, jarvisChartOverlayQa, jarvisEvidenceLatencyBudget, jarvisEvidenceCache, jarvisRealtimeFreshness, openAlgoResilience, openAlgoFaultHarness, openAlgoSecurityPosture, openAlgoSecurityThreatReport, deploymentReadiness, deploymentSmoke, finalReleaseAudit, jarvisFinalProductionAudit, jarvisReadinessRemediation });
      setData((current) => current ? { ...current, jarvisAiComparisonHistory, jarvisAiReviewRefreshGuard, jarvisAiRefreshAction, jarvisAiRefreshResponseSample, jarvisAiRefreshResponseLedger, jarvisAiEvidenceDiff, jarvisProviderDisagreement, jarvisVerifiedReviewPacket, jarvisOpenAlgoSafeIntentBinding, jarvisPaperReadySafetyAudit } : current);
      const coreUnavailable = loadErrors.length > 0 && !time && !mode && !features;
      setOffline(coreUnavailable);
      setIssue(loadErrors.length > 0 ? {
        kind: coreUnavailable ? "offline" : "api",
        title: coreUnavailable ? "Backend Offline" : "Partial Evidence Load",
        detail: coreUnavailable
          ? "The API could not be reached. No trading action is possible."
          : `${loadErrors.length} evidence endpoint(s) failed. Affected panels stay fail-closed.`,
      } : null);
    } catch (error) {
      console.error(error);
      const normalized = normalizeUiIssue(error);
      setIssue(normalized);
      setOffline(normalized.kind === "offline");
    } finally {
      refreshInFlight.current = false;
      setLoading(false);
    }
  }, [active]);

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 30000);
    return () => window.clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const idx = Number(event.key);
      if (idx >= 1 && idx <= workspaces.length) setActive(workspaces[idx - 1].id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  useEffect(() => {
    if (window.location.hash !== `#${active}`) {
      window.history.replaceState(null, "", `#${active}`);
    }
    window.localStorage.setItem("tradevision.workspace.v1", JSON.stringify({ version: 1, active }));
    const layout = data.layout?.data;
    if (layout?.workspace_id === active && layout.active_workspace !== active) {
      api.saveLayout(active, { ...layout, active_workspace: active }).catch(console.error);
    }
  }, [active]);

  const mode = data.mode?.data.mode ?? "MOCK";
  const killTriggered = data.killswitch?.data.state === "triggered";

  return (
    <div className="app">
      <ModeWatermark text={data.mode?.data.watermark_text ?? "MOCK - PRACTICE MODE"} />
      {offline && <div className="offline">Backend offline. Showing safe shell only. No trading action is possible.</div>}
      {issue && !offline && <div className={`issue-banner ${issue.kind}`}><b>{issue.title}</b><span>{issue.detail}</span></div>}
      {killTriggered && <div className="kill-curtain">KILL SWITCH TRIGGERED - ALL ORDER PATHS BLOCKED</div>}
      <aside className="rail">
        <div className="brand">TV</div>
        {workspaces.map((workspace, index) => (
          <button key={workspace.id} className={active === workspace.id ? "active" : ""} onClick={() => setActive(workspace.id)}>
            <b>{index + 1}</b>
            <span>{workspace.label}</span>
          </button>
        ))}
      </aside>
      <main className="main">
        <TopBar data={data} offline={offline} onRefresh={refresh} />
        <KillSwitchBar state={data.killswitch?.data} onTrigger={async () => { await api.triggerKillSwitch("Manual UI trigger from root KillSwitchBar"); await refresh(); }} onReset={async () => { await api.resetKillSwitch(); await refresh(); }} />
        <WorkspaceView active={active} data={data} setActive={setActive} mode={mode} onRefresh={refresh} />
      </main>
    </div>
  );
}

function readPersistedWorkspace(): Workspace | null {
  try {
    const raw = window.localStorage.getItem("tradevision.workspace.v1");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed.version === 1 && workspaces.some((workspace) => workspace.id === parsed.active) ? parsed.active : null;
  } catch {
    return null;
  }
}

function normalizeUiIssue(error: unknown): UiIssue {
  if (error instanceof ApiClientError) {
    return {
      kind: "api",
      title: `API Error: ${error.code}`,
      detail: error.message,
    };
  }
  if (error instanceof ContractValidationError) {
    return {
      kind: "contract",
      title: "Contract Validation Failed",
      detail: error.message,
    };
  }
  if (error instanceof TypeError) {
    return {
      kind: "offline",
      title: "Backend Offline",
      detail: "The API could not be reached. No trading action is possible.",
    };
  }
  return {
    kind: "unknown",
    title: "Unknown Data Load Failure",
    detail: error instanceof Error ? error.message : "Unexpected frontend data loading failure.",
  };
}

function ModeWatermark({ text }: { text: string }) {
  return <div className="mode-watermark">{text}</div>;
}

function TopBar({ data, offline, onRefresh }: { data: AppData; offline: boolean; onRefresh: () => void }) {
  const time = data.time?.data;
  const features = data.features?.data.capabilities ?? [];
  const reserved = features.filter((f: any) => f.status === "reserved").length;
  const mock = features.filter((f: any) => f.status === "mock").length;
  return (
    <header className="topbar">
      <div>
        <h1>Trade Vision</h1>
        <p>Safe full-stack vertical slice. MOCK mode. No broker route.</p>
      </div>
      <div className="status-grid">
        <Status label="Mode" value={data.mode?.data.display_label ?? "MOCK"} />
        <Status label="Virtual Time" value={time ? String(time.virtual_timestamp_ns) : "pending"} />
        <Status label="Drift" value={`${time?.drift_ms ?? 0} ms`} />
                <Status label="Capabilities" value={`${mock} mock / ${reserved} reserved`} />
                <Status label="Storage" value={data.storage?.data.status ?? "pending"} tone={data.storage?.data.status === "ready" ? "good" : undefined} />
                <Status label="Actor" value={`${data.auth?.data.actor_id ?? "pending"} / ${data.auth?.data.role ?? "mock"}`} />
                <Status label="Layout" value={`v${data.layout?.data.version ?? 1} / ${data.layout?.data.workspace_id ?? "pending"}`} />
                <Status label="API" value={offline ? "offline" : "online"} tone={offline ? "bad" : "good"} />
        <button className="refresh" onClick={onRefresh}>Refresh</button>
      </div>
    </header>
  );
}

function KillSwitchBar({ state, onTrigger, onReset }: { state?: any; onTrigger: () => void; onReset: () => void }) {
  const triggered = state?.state === "triggered";
  return (
    <section className={`killbar ${triggered ? "triggered" : ""}`}>
      <div>
        <b>Kill Switch</b>
        <span>{triggered ? state?.reason : "Armed. All future order-path stubs must check this state."}</span>
      </div>
      <div className="actions">
        <button className="danger" onClick={onTrigger}>Trigger</button>
        <button onClick={onReset}>Reset MOCK</button>
      </div>
    </section>
  );
}

function WorkspaceView({ active, data, setActive, mode, onRefresh }: { active: Workspace; data: AppData; setActive: (w: Workspace) => void; mode: string; onRefresh: () => Promise<void> }) {
  if (active === "cockpit") return <Cockpit data={data} setActive={setActive} />;
  if (active === "marketdna") return <MarketDNA data={data} />;
  if (active === "behavior") return <BehaviorDNA data={data} />;
  if (active === "research") return <Research data={data} />;
  if (active === "jarvis") return <JarvisDecisionRoom data={data} onRefresh={onRefresh} />;
  if (active === "replay") return <Replay data={data} />;
  if (active === "knowledge") return <Knowledge data={data} />;
  if (active === "implementation") return <Implementation data={data} />;
  return <System data={data} mode={mode} />;
}

function Cockpit({ data, setActive }: { data: AppData; setActive: (w: Workspace) => void }) {
  const decision = data.decision?.data;
  return (
    <div className="workspace">
      <Panel title="Command Board" span="wide" badge={decision?.final_action ?? "WAIT"}>
        <div className="hero-number">{pct(decision?.confidence)} confidence</div>
        <p>{decision?.narrative.text}</p>
        <div className="vote-grid">
          {decision?.votes.map((vote: any) => <Card key={vote.engine} title={vote.engine} value={vote.vote} note={`${pct(vote.confidence)} - ${vote.reason}`} />)}
        </div>
      </Panel>
      <RiskPanel risk={data.risk?.data} />
      <OrderPathPanel orderPath={data.orderPath?.data} />
      <Panel title="Portfolio Governor" badge="mock">
        <Metric label="Gross Exposure" value={`${data.portfolio?.data.gross_exposure_pct ?? 0}%`} />
        <Metric label="Sector Concentration" value={`${data.portfolio?.data.sector_concentration_pct ?? 0}%`} />
        <Metric label="Cluster Risk" value={data.portfolio?.data.correlation_cluster_risk ?? "pending"} />
      </Panel>
      <IntegrityPanel data={data.integrity?.data} />
      <Panel title="Narrative Audit" span="wide" badge="read-only">
        {decision?.audit[0]?.explanation_chain.map((step: string) => <div className="list-row" key={step}>{step}</div>)}
      </Panel>
      <Panel title="Next Safe Action" badge="guided">
        <p>Review replay determinism and graph state before implementing advanced engines.</p>
        <button onClick={() => setActive("replay")}>Open Replay</button>
      </Panel>
    </div>
  );
}

function MarketDNA({ data }: { data: AppData }) {
  const dna = data.marketDna?.data;
  const micro = data.microstructure?.data;
  return (
    <div className="workspace">
      <Panel title="MarketDNA Gated Fusion" span="wide" badge={dna?.status ?? "mock"}>
        <div className="dna-grid">
          <Metric label="Price" value={pct(dna?.price_score)} />
          <Metric label="Volatility" value={pct(dna?.volatility_score)} />
          <Metric label="Options" value={pct(dna?.options_score)} />
          <Metric label="Breadth" value={pct(dna?.breadth_score)} />
          <Metric label="Events" value={pct(dna?.event_score)} />
          <Metric label="Flow" value={pct(dna?.flow_score)} />
        </div>
      </Panel>
      <Panel title="Calibrated Probability">
        <Metric label="Breakout" value={pct(dna?.calibrated_breakout_probability)} />
        <Metric label="Failure" value={pct(dna?.calibrated_failure_probability)} />
      </Panel>
      <Panel title="Microstructure State" badge={micro?.status ?? "mock"}>
        <Metric label="OBI" value={String(micro?.order_book_imbalance ?? "pending")} />
        <Metric label="Absorption" value={String(micro?.absorption_events ?? 0)} />
        <Metric label="Spoof Warnings" value={String(micro?.spoofing_warnings ?? 0)} />
      </Panel>
      <IntegrityPanel data={data.integrity?.data} />
    </div>
  );
}

function BehaviorDNA({ data }: { data: AppData }) {
  const spec = data.behaviorSpec?.data;
  const analysis = data.behaviorAnalysis?.data;
  const context = data.behaviorContext?.data;
  const session = data.behaviorSession?.data;
  const dayMemory = data.behaviorDayMemory?.data;
  const stockSummary = data.stockDnaSummary?.data;
  const patternMemory = data.patternMemory?.data;
  const similarDays = data.similarDays?.data ?? [];
  const similarReplay = data.similarDayReplay?.data;
  const failureLibrary = data.failureLibrary?.data;
  const trustTable = data.trustTable?.data;
  const tradeDecision = data.tradeDecision?.data;
  const behaviorRisk = data.behaviorRisk?.data;
  const behaviorExecution = data.behaviorExecution?.data;
  const panelMap = data.behaviorPanelMap?.data;
  const walkForward = data.walkForward?.data;
  const outOfSample = data.outOfSample?.data;
  const behaviorDrift = data.behaviorDrift?.data;
  const behaviorOod = data.behaviorOod?.data;
  const behaviorRealityGap = data.behaviorRealityGap?.data;
  const behaviorAcp = data.behaviorAcp?.data;
  const behaviorSafetyReport = data.behaviorSafetyReport?.data;
  const behaviorSafetyReports = data.behaviorSafetyReports?.data ?? [];
  const behaviorQuarantines = data.behaviorQuarantines?.data ?? [];
  const behaviorRebuildPlan = data.behaviorRebuildPlan?.data;
  const behaviorGoldenFixtures = data.behaviorGoldenFixtures?.data ?? [];
  const behaviorGoldenVerify = data.behaviorGoldenVerify?.data;
  const behaviorBenchmarkReport = data.behaviorBenchmarkReport?.data;
  const behaviorBenchmarkReports = data.behaviorBenchmarkReports?.data ?? [];
  const behaviorBenchmarkDrilldown = data.behaviorBenchmarkDrilldown?.data;
  const behaviorScenarioCoverage = data.behaviorScenarioCoverage?.data;
  const behaviorScenarioCoverageReports = data.behaviorScenarioCoverageReports?.data ?? [];
  const behaviorReleaseChecklist = data.behaviorReleaseChecklist?.data;
  const behaviorReleaseChecklists = data.behaviorReleaseChecklists?.data ?? [];
  const behaviorReleaseApprovals = data.behaviorReleaseApprovals?.data ?? [];
  const behaviorReleaseEvidence = data.behaviorReleaseEvidence?.data;
  const behaviorReleaseEvidenceBundles = data.behaviorReleaseEvidenceBundles?.data ?? [];
  const behaviorReleaseArtifacts = data.behaviorReleaseArtifacts?.data ?? [];
  const result = analysis?.result ?? {};
  const columns = data.behaviorColumns?.data ?? [];
  const lowEvidence = result.minimum_sample_pass === false;
  return (
    <div className="workspace">
      <Panel title="Behavior Intelligence Contract Lock" span="wide" badge={spec?.live_trading_blocked ? "live blocked" : "check"}>
        <p>{spec?.purpose}</p>
        <div className="dna-grid">
          <Metric label="Layer Contracts" value={String(spec?.layer_contracts?.length ?? 0)} />
          <Metric label="Output Columns" value={String(columns.length)} />
          <Metric label="Verbatim Constants" value={String(spec?.verbatim_registry?.length ?? 0)} />
        </div>
        <p>{spec?.universal_agreement_rule}</p>
      </Panel>
      <Panel title="Frontend Panel Contract Map" span="wide" badge={`${panelMap?.total_panels ?? 0} panels`}>
        <div className="dna-grid">
          <Metric label="Mock Panels" value={String(panelMap?.mock_panels ?? 0)} />
          <Metric label="Reserved Panels" value={String(panelMap?.reserved_panels ?? 0)} />
          <Metric label="Map Version" value={panelMap?.map_version ?? "pending"} />
        </div>
        {panelMap?.safety_invariants?.map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
        <div className="capability-table compact">
          {panelMap?.panels?.slice(0, 12).map((panel: any) => (
            <div key={panel.panel_id}>
              <b>{panel.title}</b>
              <span>{panel.manifest_status} / {panel.fallback_state}</span>
              <small>{panel.contract_name} via {panel.endpoint}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Current Behavior Decision" badge={String(result.final_trade_decision ?? "WATCH_ONLY")}>
        <Metric label="Symbol" value={analysis?.symbol ?? "NIFTY-MOCK"} />
        <Metric label="Run ID" value={analysis?.run_id ?? "pending"} />
        <Metric label="Market State" value={String(result.market_state ?? "pending")} />
        <Metric label="Fakeout Probability" value={`${result.fakeout_probability_pct ?? 0}%`} />
        <Metric label="Trade Allowed" value={result.trade_allowed ? "yes" : "no"} />
        {lowEvidence && <p>{String(result.no_trade_reason ?? spec?.low_evidence_message ?? "Low evidence")}</p>}
      </Panel>
      <Panel title="Universal Agreement Decision Engine" span="wide" badge={tradeDecision?.final_trade_decision ?? "pending"}>
        <div className="dna-grid">
          <Metric label="Allowed" value={tradeDecision?.trade_allowed ? "yes" : "no"} />
          <Metric label="Agreement" value={tradeDecision?.universal_agreement_pass ? "pass" : "blocked"} />
          <Metric label="Confidence" value={`${tradeDecision?.confidence_pct ?? 0}%`} />
          <Metric label="Live Route" value={tradeDecision?.live_trade_route_attempted ? "attempted" : "never"} />
          <Metric label="No-Trade" value={tradeDecision?.no_trade?.active ? "active" : "clear"} />
        </div>
        <p>{tradeDecision?.narrative_explanation ?? "Decision engine is loading."}</p>
        {tradeDecision?.no_trade?.wait_for?.map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
      </Panel>
      <Panel title="Agreement Checks + Safety Gates" span="wide" badge="read-only">
        <div className="capability-table compact">
          {Object.entries(tradeDecision?.agreement_checks ?? {}).map(([name, passed]) => (
            <div key={name}><b>{name}</b><span>{passed ? "pass" : "blocked"}</span><small>universal agreement</small></div>
          ))}
          {tradeDecision?.gates?.map((gate: any) => (
            <div key={gate.gate}><b>{gate.gate}</b><span>{gate.passed ? "pass" : gate.severity}</span><small>{gate.reason}</small></div>
          ))}
        </div>
      </Panel>
      <Panel title="Human-Readable Reason Tree" span="wide" badge={tradeDecision?.reason_tree?.read_only ? "explanation only" : "check"}>
        {tradeDecision?.reason_tree?.ordered_reasons?.map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
        <div className="list-row single"><span>Narrative cannot execute orders: {tradeDecision?.reason_tree?.cannot_execute_orders ? "true" : "pending"}</span></div>
        <div className="list-row single"><span>Narrative cannot override calibrated probabilities: {tradeDecision?.reason_tree?.cannot_override_calibrated_probabilities ? "true" : "pending"}</span></div>
      </Panel>
      <Panel title="Risk Sizing + Capital Safety" span="wide" badge={behaviorRisk?.trade_allowed ? "candidate sized" : "blocked"}>
        <div className="dna-grid">
          <Metric label="Position Size" value={String(behaviorRisk?.position_size ?? 0)} />
          <Metric label="Risk %" value={`${behaviorRisk?.risk_per_trade_pct ?? 0}%`} />
          <Metric label="Capital" value={money(behaviorRisk?.capital_to_use ?? 0)} />
          <Metric label="Max Loss" value={money(behaviorRisk?.max_loss_amount ?? 0)} />
          <Metric label="Reward" value={money(behaviorRisk?.reward_amount ?? 0)} />
          <Metric label="R:R" value={String(behaviorRisk?.risk_reward ?? 0)} />
        </div>
        <p>{behaviorRisk?.sizing_formula ?? "Risk sizing is loading."}</p>
        {behaviorRisk?.block_reasons?.map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
      </Panel>
      <Panel title="Portfolio Exposure + Cooldown" span="wide" badge={behaviorRisk?.daily_loss?.cooldown_active ? "cooldown" : "clear"}>
        <div className="dna-grid">
          <Metric label="Sector" value={`${behaviorRisk?.portfolio?.sector_exposure_pct ?? 0}% ${behaviorRisk?.portfolio?.sector ?? ""}`} />
          <Metric label="Index" value={`${behaviorRisk?.portfolio?.index_exposure_pct ?? 0}% ${behaviorRisk?.portfolio?.index ?? ""}`} />
          <Metric label="Heat" value={`${behaviorRisk?.portfolio?.portfolio_heat_pct ?? 0}%`} />
          <Metric label="Correlation" value={behaviorRisk?.portfolio?.correlation_risk ?? "pending"} />
          <Metric label="Daily P&L" value={money(behaviorRisk?.daily_loss?.daily_pnl ?? 0)} />
          <Metric label="Cooldown" value={behaviorRisk?.daily_loss?.cooldown_active ? `${behaviorRisk.daily_loss.cooldown_minutes}m` : "clear"} />
        </div>
        {[...(behaviorRisk?.portfolio?.reasons ?? []), ...(behaviorRisk?.daily_loss?.reasons ?? [])].map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
      </Panel>
      <Panel title="Execution Fill Realism" span="wide" badge={behaviorExecution?.fill_status ?? "pending"}>
        <div className="dna-grid">
          <Metric label="Requested" value={String(behaviorExecution?.requested_quantity ?? 0)} />
          <Metric label="Filled" value={String(behaviorExecution?.filled_quantity ?? 0)} />
          <Metric label="Unfilled" value={String(behaviorExecution?.unfilled_quantity ?? 0)} />
          <Metric label="Fill Probability" value={`${behaviorExecution?.fill_probability_pct ?? 0}%`} />
          <Metric label="Fill Price" value={behaviorExecution?.fill_price ? money(behaviorExecution.fill_price) : "none"} />
          <Metric label="Fill Quality" value={behaviorExecution?.fill_quality ?? "pending"} />
        </div>
        <p>{behaviorExecution?.missed_trade_reason ?? behaviorExecution?.no_fill_reason ?? "Execution simulation has no missed-trade warning."}</p>
        {behaviorExecution?.safety_notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
      </Panel>
      <Panel title="Execution Cost Breakdown" span="wide" badge={behaviorExecution?.adverse_selection_risk ?? "pending"}>
        <div className="dna-grid">
          <Metric label="Spread Cost" value={`${behaviorExecution?.costs?.spread_cost_pct ?? 0}%`} />
          <Metric label="Latency Slip" value={`${behaviorExecution?.costs?.latency_slippage_pct ?? 0}%`} />
          <Metric label="Market Impact" value={`${behaviorExecution?.costs?.market_impact_pct ?? 0}%`} />
          <Metric label="Adverse Cost" value={`${behaviorExecution?.costs?.adverse_selection_cost_pct ?? 0}%`} />
          <Metric label="Total Cost" value={`${behaviorExecution?.costs?.total_cost_pct ?? 0}%`} />
          <Metric label="Queue Estimate" value={pct(behaviorExecution?.queue_position_estimate)} />
        </div>
        <div className="list-row single"><span>{behaviorExecution?.market_impact_model ?? "Market impact model pending."}</span></div>
        <div className="list-row single"><span>{behaviorExecution?.latency_model ?? "Latency model pending."}</span></div>
        <div className="list-row single"><span>Live route attempted: {behaviorExecution?.live_route_attempted ? "true" : "false"}</span></div>
      </Panel>
      <Panel title="Walk-Forward Validation" span="wide" badge={walkForward?.promotion_allowed ? "promotion pass" : "blocked"}>
        <div className="dna-grid">
          <Metric label="Folds" value={String(walkForward?.folds?.length ?? 0)} />
          <Metric label="Win Rate" value={`${walkForward?.aggregate_win_rate_pct ?? 0}%`} />
          <Metric label="Profit Factor" value={String(walkForward?.aggregate_profit_factor ?? 0)} />
          <Metric label="Expectancy" value={`${walkForward?.aggregate_expectancy_r ?? 0}R`} />
          <Metric label="Max DD" value={`${walkForward?.aggregate_max_drawdown_pct ?? 0}%`} />
          <Metric label="Leakage" value={walkForward?.no_future_leakage ? "pass" : "blocked"} />
        </div>
        {walkForward?.promotion_blockers?.map((blocker: string) => (
          <div className="list-row single" key={blocker}><span>{blocker}</span></div>
        ))}
        <div className="capability-table compact">
          {walkForward?.folds?.map((fold: any) => (
            <div key={fold.fold_index}>
              <b>Fold {fold.fold_index}</b>
              <span>{fold.train_start_day}-{fold.train_end_day} {"->"} {fold.test_start_day}-{fold.test_end_day}</span>
              <small>PF {fold.profit_factor}, Exp {fold.expectancy_r}R, trades {fold.trade_count}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Out-of-Sample Validation" span="wide" badge={outOfSample?.no_future_leakage ? "leakage pass" : "check"}>
        <div className="dna-grid">
          <Metric label="Trades" value={String(outOfSample?.total_trades ?? 0)} />
          <Metric label="Win Rate" value={`${outOfSample?.aggregate_win_rate_pct ?? 0}%`} />
          <Metric label="Profit Factor" value={String(outOfSample?.aggregate_profit_factor ?? 0)} />
          <Metric label="Expectancy" value={`${outOfSample?.aggregate_expectancy_r ?? 0}R`} />
          <Metric label="Live Blocked" value={outOfSample?.live_trading_blocked ? "yes" : "check"} />
          <Metric label="Deterministic" value={outOfSample?.deterministic ? "yes" : "check"} />
        </div>
        {outOfSample?.notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
      </Panel>
      <Panel title="Model Drift Detector" span="wide" badge={behaviorDrift?.drift_status ?? "pending"}>
        <div className="dna-grid">
          <Metric label="Drift Score" value={pct(behaviorDrift?.drift_score)} />
          <Metric label="PSI" value={String(behaviorDrift?.population_stability_index ?? 0)} />
          <Metric label="Mean Shift Z" value={String(behaviorDrift?.mean_shift_z ?? 0)} />
          <Metric label="Vol Shift" value={String(behaviorDrift?.volatility_shift_ratio ?? 0)} />
          <Metric label="Confidence Multiplier" value={pct(behaviorDrift?.confidence_multiplier)} />
          <Metric label="Quarantine" value={behaviorDrift?.memory_quarantine_required ? "required" : "clear"} />
        </div>
        {behaviorDrift?.promotion_blockers?.map((blocker: string) => (
          <div className="list-row single" key={blocker}><span>{blocker}</span></div>
        ))}
        {behaviorDrift?.notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
      </Panel>
      <Panel title="OOD Confidence Guard" span="wide" badge={behaviorOod?.ood_status ?? "pending"}>
        <div className="dna-grid">
          <Metric label="OOD Score" value={pct(behaviorOod?.ood_score)} />
          <Metric label="Max Distance" value={pct(behaviorOod?.max_feature_distance)} />
          <Metric label="Confidence" value={behaviorOod?.confidence_blocked ? "blocked" : "allowed"} />
          <Metric label="Trade" value={behaviorOod?.trade_blocked ? "blocked" : "not blocked"} />
        </div>
        <div className="capability-table compact">
          {behaviorOod?.feature_results?.map((feature: any) => (
            <div key={feature.feature_name}>
              <b>{feature.feature_name}</b>
              <span>{feature.status} / {pct(feature.distance_score)}</span>
              <small>{feature.reason}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Reality Gap Detector" span="wide" badge={behaviorRealityGap?.severity ?? "pending"}>
        <div className="dna-grid">
          <Metric label="Gap Score" value={pct(behaviorRealityGap?.reality_gap_score)} />
          <Metric label="Slippage Drift" value={`${behaviorRealityGap?.slippage_drift_pct ?? 0}%`} />
          <Metric label="Fill Drift" value={`${behaviorRealityGap?.fill_rate_drift_pct ?? 0}%`} />
          <Metric label="Latency Drift" value={`${behaviorRealityGap?.latency_drift_ms ?? 0}ms`} />
          <Metric label="PnL Drift" value={`${behaviorRealityGap?.pnl_drift_r ?? 0}R`} />
          <Metric label="Alert" value={behaviorRealityGap?.alert ? "active" : "clear"} />
        </div>
        {behaviorRealityGap?.promotion_blockers?.map((blocker: string) => (
          <div className="list-row single" key={blocker}><span>{blocker}</span></div>
        ))}
        {behaviorRealityGap?.notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
      </Panel>
      <Panel title="ACP Safety Hardening" span="wide" badge={behaviorAcp?.promotion_allowed ? "promotion pass" : "promotion blocked"}>
        <div className="dna-grid">
          <Metric label="Pass" value={String(behaviorAcp?.pass_count ?? 0)} />
          <Metric label="Fail" value={String(behaviorAcp?.fail_count ?? 0)} />
          <Metric label="Live Trading" value={behaviorAcp?.live_trading_blocked ? "blocked" : "check"} />
          <Metric label="Safety Version" value={behaviorAcp?.safety_version ?? "pending"} />
        </div>
        <div className="capability-table compact">
          {behaviorAcp?.checks?.map((check: any) => (
            <div key={check.check_id}>
              <b>{check.check_id}</b>
              <span>{check.status}</span>
              <small>{check.evidence}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Immutable Safety Report Store" span="wide" badge={behaviorSafetyReport?.promotion_allowed ? "promotion pass" : "blocked"}>
        <div className="dna-grid">
          <Metric label="Report ID" value={behaviorSafetyReport?.report_id?.slice(0, 24) ?? "pending"} />
          <Metric label="Immutable" value={behaviorSafetyReport?.immutable ? "yes" : "check"} />
          <Metric label="Report Hash" value={behaviorSafetyReport?.report_hash?.slice(0, 16) ?? "pending"} />
          <Metric label="History" value={String(behaviorSafetyReports.length)} />
          <Metric label="Quarantine" value={behaviorSafetyReport?.memory_quarantine_required ? "required" : "clear"} />
          <Metric label="Confidence" value={behaviorSafetyReport?.confidence_blocked ? "blocked" : "clear"} />
        </div>
        {behaviorSafetyReport?.notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
      </Panel>
      <Panel title="Memory Quarantine Policy" span="wide" badge={`${behaviorQuarantines.length} active`}>
        <div className="dna-grid">
          <Metric label="Active Records" value={String(behaviorQuarantines.length)} />
          <Metric label="Promotion" value={behaviorQuarantines.length > 0 ? "blocked" : "clear"} />
          <Metric label="Read Policy" value={behaviorQuarantines[0]?.read_policy ?? "normal"} />
          <Metric label="Affected Memory" value={String(behaviorQuarantines[0]?.affected_memory_ids?.length ?? 0)} />
        </div>
        {behaviorQuarantines.length === 0 && <p>No active memory quarantine for the mock symbol.</p>}
        {behaviorQuarantines.map((record: any) => (
          <div className="list-row" key={record.quarantine_id}>
            <b>{record.status}</b>
            <span>{record.reason}</span>
            <small>{record.quarantine_id.slice(0, 18)}</small>
          </div>
        ))}
      </Panel>
      <Panel title="Memory Rebuild Plan" span="wide" badge={behaviorRebuildPlan?.estimated_safe_status ?? "pending"}>
        <div className="dna-grid">
          <Metric label="Allowed" value={behaviorRebuildPlan?.allowed_to_rebuild ? "yes" : "not needed"} />
          <Metric label="Inputs" value={String(behaviorRebuildPlan?.required_inputs?.length ?? 0)} />
          <Metric label="Steps" value={String(behaviorRebuildPlan?.rebuild_steps?.length ?? 0)} />
          <Metric label="Gates" value={String(behaviorRebuildPlan?.promotion_gates?.length ?? 0)} />
        </div>
        <div className="capability-table compact">
          {behaviorRebuildPlan?.promotion_gates?.map((gate: string) => (
            <div key={gate}><b>Gate</b><span>{gate}</span><small>required before release</small></div>
          ))}
        </div>
      </Panel>
      <Panel title="Golden Replay Fixtures" span="wide" badge={`${behaviorGoldenFixtures.length} fixtures`}>
        <div className="capability-table compact">
          {behaviorGoldenFixtures.map((fixture: any) => (
            <div key={fixture.fixture_id}>
              <b>{fixture.fixture_id}</b>
              <span>{fixture.scenario_id} / seed {fixture.seed}</span>
              <small>{fixture.expected_chain_hash.slice(0, 16)}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Golden Replay Verification" span="wide" badge={behaviorGoldenVerify?.passed ? "passed" : "check"}>
        <div className="dna-grid">
          <Metric label="Fixture" value={behaviorGoldenVerify?.fixture?.fixture_id ?? "pending"} />
          <Metric label="Events" value={String(behaviorGoldenVerify?.actual_event_count ?? 0)} />
          <Metric label="Deterministic" value={behaviorGoldenVerify?.deterministic ? "yes" : "check"} />
          <Metric label="Live Trading" value={behaviorGoldenVerify?.live_trading_blocked ? "blocked" : "check"} />
          <Metric label="Chain Hash" value={behaviorGoldenVerify?.actual_chain_hash?.slice(0, 16) ?? "pending"} />
        </div>
        {behaviorGoldenVerify?.issues?.length === 0 && <p>Golden replay chain matches the fixture exactly.</p>}
        {behaviorGoldenVerify?.issues?.map((issue: string) => (
          <div className="list-row single" key={issue}><span>{issue}</span></div>
        ))}
      </Panel>
      <Panel title="Benchmark Report Store" span="wide" badge={behaviorBenchmarkReport?.promotion_allowed ? "promotion pass" : "blocked"}>
        <div className="dna-grid">
          <Metric label="Report ID" value={behaviorBenchmarkReport?.report_id?.slice(0, 24) ?? "pending"} />
          <Metric label="History" value={String(behaviorBenchmarkReports.length)} />
          <Metric label="Report Hash" value={behaviorBenchmarkReport?.report_hash?.slice(0, 16) ?? "pending"} />
          <Metric label="WF Profit Factor" value={String(behaviorBenchmarkReport?.metrics?.walk_forward_profit_factor ?? 0)} />
          <Metric label="OOS Profit Factor" value={String(behaviorBenchmarkReport?.metrics?.out_of_sample_profit_factor ?? 0)} />
          <Metric label="Golden Passed" value={`${behaviorBenchmarkReport?.metrics?.golden_replay_pass_count ?? 0}/${behaviorBenchmarkReport?.metrics?.golden_replay_total ?? 0}`} />
        </div>
        {behaviorBenchmarkReport?.promotion_blockers?.map((blocker: string) => (
          <div className="list-row single" key={blocker}><span>{blocker}</span></div>
        ))}
        {behaviorBenchmarkReport?.notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
      </Panel>
      <Panel title="Benchmark Drilldown Evidence" span="wide" badge={behaviorBenchmarkDrilldown?.live_trading_blocked ? "live blocked" : "check"}>
        <div className="dna-grid">
          <Metric label="Report" value={behaviorBenchmarkDrilldown?.report_id?.slice(0, 24) ?? "pending"} />
          <Metric label="WF PF" value={String(behaviorBenchmarkDrilldown?.metric_groups?.walk_forward?.profit_factor ?? 0)} />
          <Metric label="OOS PF" value={String(behaviorBenchmarkDrilldown?.metric_groups?.out_of_sample?.profit_factor ?? 0)} />
          <Metric label="Golden" value={`${behaviorBenchmarkDrilldown?.metric_groups?.golden_replay?.passed ?? 0}/${behaviorBenchmarkDrilldown?.metric_groups?.golden_replay?.total ?? 0}`} />
        </div>
        {behaviorBenchmarkDrilldown?.validation_summary?.slice(0, 3).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
        {behaviorBenchmarkDrilldown?.promotion_summary?.slice(0, 4).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
      </Panel>
      <Panel title="Scenario Coverage Drilldown" span="wide" badge={behaviorScenarioCoverage?.promotion_allowed ? "coverage pass" : "coverage blocked"}>
        <div className="dna-grid">
          <Metric label="Coverage ID" value={behaviorScenarioCoverage?.coverage_id?.slice(0, 24) ?? "pending"} />
          <Metric label="Coverage Score" value={`${behaviorScenarioCoverage?.coverage_score_pct ?? 0}%`} />
          <Metric label="Deterministic Pass" value={`${behaviorScenarioCoverage?.deterministic_pass_rate_pct ?? 0}%`} />
          <Metric label="Scenarios" value={`${behaviorScenarioCoverage?.passed_scenarios ?? 0}/${behaviorScenarioCoverage?.total_scenarios ?? 0}`} />
          <Metric label="Families Covered" value={`${behaviorScenarioCoverage?.covered_scenario_families?.length ?? 0}/${behaviorScenarioCoverage?.required_scenario_families?.length ?? 0}`} />
          <Metric label="History" value={String(behaviorScenarioCoverageReports.length)} />
        </div>
        <div className="capability-table compact">
          {behaviorScenarioCoverage?.scenario_items?.map((item: any) => (
            <div key={item.fixture_id}>
              <b>{item.scenario_family}</b>
              <span>{item.coverage_status} / {item.scenario_id}</span>
              <small>{item.fixture_id} - seed {item.seed} - chain {item.chain_hash.slice(0, 16)}</small>
            </div>
          ))}
        </div>
        {(behaviorScenarioCoverage?.missing_scenario_families ?? []).map((family: string) => (
          <div className="list-row single" key={family}><span>Missing scenario family: {family}</span></div>
        ))}
        {(behaviorScenarioCoverage?.promotion_blockers ?? []).map((blocker: string) => (
          <div className="list-row single" key={blocker}><span>{blocker}</span></div>
        ))}
        <p>Live trading: {behaviorScenarioCoverage?.live_trading_blocked ? "blocked" : "check"}. This is evidence coverage only, not a trade permission.</p>
      </Panel>
      <Panel title="Mock-to-Replay Release Checklist" span="wide" badge={behaviorReleaseChecklist?.release_allowed ? "release allowed" : "blocked"}>
        <div className="dna-grid">
          <Metric label="Target" value={behaviorReleaseChecklist?.target_mode ?? "REPLAY"} />
          <Metric label="Pass" value={String(behaviorReleaseChecklist?.pass_count ?? 0)} />
          <Metric label="Fail" value={String(behaviorReleaseChecklist?.fail_count ?? 0)} />
          <Metric label="Technical" value={behaviorReleaseChecklist?.technical_release_pass ? "pass" : "blocked"} />
          <Metric label="Manual Approval" value={behaviorReleaseChecklist?.manual_approval_required ? "required" : "not required"} />
          <Metric label="Live Trading" value={behaviorReleaseChecklist?.live_trading_blocked ? "blocked" : "check"} />
        </div>
        <div className="capability-table compact">
          {behaviorReleaseChecklist?.gates?.map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id} {gate.category}</b>
              <span>{gate.status}</span>
              <small>{gate.description}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Release Checklist History" span="wide" badge={`${behaviorReleaseChecklists.length} records`}>
        <div className="capability-table compact">
          {behaviorReleaseChecklists.slice(0, 8).map((checklist: any) => (
            <div key={checklist.checklist_id}>
              <b>{checklist.checklist_id.slice(0, 18)}</b>
              <span>{checklist.release_allowed ? "allowed" : "blocked"} / {checklist.target_mode}</span>
              <small>{checklist.pass_count} pass, {checklist.fail_count} fail</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Mock-to-Replay Approval Audit" span="wide" badge={`${behaviorReleaseApprovals.length} records`}>
        <div className="dna-grid">
          <Metric label="Latest Status" value={behaviorReleaseApprovals[0]?.status ?? "none"} />
          <Metric label="Latest Actor" value={behaviorReleaseApprovals[0]?.approved_by ?? behaviorReleaseApprovals[0]?.requested_by ?? "pending"} />
          <Metric label="Live Trading" value={behaviorReleaseApprovals[0]?.live_trading_blocked === false ? "check" : "blocked"} />
          <Metric label="Target Mode" value={behaviorReleaseApprovals[0]?.target_mode ?? "REPLAY"} />
        </div>
        <div className="capability-table compact">
          {behaviorReleaseApprovals.slice(0, 8).map((approval: any) => (
            <div key={approval.approval_id}>
              <b>{approval.approval_id.slice(0, 18)}</b>
              <span>{approval.status} / {approval.approval_scope}</span>
              <small>requested by {approval.requested_by}; expires {approval.expires_at}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Release Evidence Bundle" span="wide" badge={behaviorReleaseEvidence?.live_trading_blocked ? "live blocked" : "check"}>
        <div className="dna-grid">
          <Metric label="Bundle ID" value={behaviorReleaseEvidence?.bundle_id?.slice(0, 24) ?? "pending"} />
          <Metric label="Bundle Hash" value={behaviorReleaseEvidence?.bundle_hash?.slice(0, 16) ?? "pending"} />
          <Metric label="Approval" value={behaviorReleaseEvidence?.approval?.status ?? "missing"} />
          <Metric label="Final Blockers" value={String(behaviorReleaseEvidence?.final_blockers?.length ?? 0)} />
          <Metric label="History" value={String(behaviorReleaseEvidenceBundles.length)} />
          <Metric label="Immutable" value={behaviorReleaseEvidence?.immutable ? "yes" : "check"} />
        </div>
        <div className="capability-table compact">
          {Object.entries(behaviorReleaseEvidence?.evidence_index ?? {}).map(([key, value]) => (
            <div key={key}><b>{key}</b><span>{String(value).slice(0, 34)}</span><small>evidence index</small></div>
          ))}
        </div>
        {behaviorReleaseEvidence?.final_blockers?.map((blocker: string) => (
          <div className="list-row single" key={blocker}><span>{blocker}</span></div>
        ))}
      </Panel>
      <Panel title="Release Artifact Export Store" span="wide" badge={`${behaviorReleaseArtifacts.length} artifacts`}>
        <div className="dna-grid">
          <Metric label="Latest Artifact" value={behaviorReleaseArtifacts[0]?.artifact_id?.slice(0, 24) ?? "none"} />
          <Metric label="Manifest SHA" value={behaviorReleaseArtifacts[0]?.manifest_sha256?.slice(0, 16) ?? "pending"} />
          <Metric label="Bundle SHA" value={behaviorReleaseArtifacts[0]?.bundle_sha256?.slice(0, 16) ?? "pending"} />
          <Metric label="Broker Credentials" value={behaviorReleaseArtifacts[0]?.contains_broker_credentials ? "check" : "absent"} />
          <Metric label="Live Orders" value={behaviorReleaseArtifacts[0]?.contains_live_orders ? "check" : "absent"} />
          <Metric label="Live Trading" value={behaviorReleaseArtifacts[0]?.live_trading_blocked === false ? "check" : "blocked"} />
        </div>
        <div className="capability-table compact">
          {behaviorReleaseArtifacts.slice(0, 6).map((artifact: any) => (
            <div key={artifact.artifact_id}>
              <b>{artifact.artifact_id.slice(0, 18)}</b>
              <span>{artifact.artifact_format} / {artifact.target_mode}</span>
              <small>{artifact.manifest_file_path}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Context Engines" badge={String(context?.final_context_bias ?? "mock")}>
        <Metric label="Context Quality" value={String(context?.context_quality_score ?? "pending")} />
        <Metric label="Blocks Trade" value={context?.blocks_trade ? "yes" : "no"} />
        <Metric label="VWAP State" value={String(context?.levels?.vwap_state ?? "pending")} />
        <Metric label="ORB State" value={String(context?.levels?.opening_range_state ?? "pending")} />
        <Metric label="CPR State" value={String(context?.levels?.cpr_state ?? "pending")} />
        <Metric label="HTF Confirmed" value={context?.htf?.confirmed ? "yes" : "no"} />
        <Metric label="Gap Type" value={String(context?.gap?.gap_type ?? "pending")} />
        <Metric label="Market Alignment" value={String(context?.market?.market_alignment ?? "pending")} />
      </Panel>
      <Panel title="Context Reason Tree" badge="read-only">
        {Object.entries(context?.reason_tree ?? {}).map(([key, value]) => (
          <div className="list-row" key={key}><b>{key}</b><span>{value as string}</span><small>context</small></div>
        ))}
      </Panel>
      <Panel title="Session Rhythm + Stock DNA" span="wide" badge={stockSummary?.learning_status ?? "mock_seeded"}>
        <div className="dna-grid">
          <Metric label="Current Phase" value={String(session?.current_session_phase ?? "pending")} />
          <Metric label="Day" value={String(session?.day_of_week ?? "pending")} />
          <Metric label="Best Window" value={String(session?.best_trade_window ?? "pending")} />
          <Metric label="Worst Window" value={String(session?.worst_trade_window ?? "pending")} />
          <Metric label="Fakeout Window" value={String(session?.fakeout_window ?? "pending")} />
          <Metric label="Personality" value={pct(session?.session_personality_score)} />
        </div>
        <p>{stockSummary?.stock_personality_summary ?? "Stock-specific session memory is loading."}</p>
        {stockSummary?.risk_warnings?.slice(0, 4).map((warning: string) => (
          <div className="list-row single" key={warning}><span>{warning}</span></div>
        ))}
      </Panel>
      <Panel title="Day-of-Week Memory" badge={dayMemory?.blocks_strong_probability ? "low evidence" : "usable"}>
        <Metric label="Total Samples" value={String(dayMemory?.total_samples ?? 0)} />
        <Metric label="Minimum Sample" value={String(dayMemory?.minimum_sample_size ?? 30)} />
        <Metric label="Strong Probability" value={dayMemory?.blocks_strong_probability ? "blocked" : "allowed"} />
        <p>{dayMemory?.dominant_day_note ?? "No day-of-week memory loaded."}</p>
        {dayMemory?.records?.filter((record: any) => record.sample_count > 0).map((record: any) => (
          <div className="list-row" key={record.day_of_week}>
            <b>{record.day_of_week}</b>
            <span>{record.behavior_note}</span>
            <small>{record.sample_count} samples</small>
          </div>
        ))}
      </Panel>
      <Panel title="Session Segment Scores" span="wide" badge="causal bars">
        <div className="capability-table compact">
          {session?.segments?.map((segment: any) => (
            <div key={segment.session_phase}>
              <b>{segment.window_start}-{segment.window_end}</b>
              <span>{segment.trend_bias}</span>
              <small>quality {pct(segment.trade_quality_score)} / fakeout {pct(segment.fakeout_risk)}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Pattern Memory + Similar-Day Replay" span="wide" badge={patternMemory?.evidence_quality ?? "LOW"}>
        <div className="dna-grid">
          <Metric label="Vector Fields" value={String(patternMemory?.vector_fields?.length ?? 0)} />
          <Metric label="Historical Matches" value={String(patternMemory?.historical_match_count ?? 0)} />
          <Metric label="Minimum Sample" value={String(patternMemory?.minimum_sample_size ?? 30)} />
          <Metric label="Continuation" value={`${patternMemory?.continuation_probability_pct ?? 0}%`} />
          <Metric label="Fakeout" value={`${patternMemory?.fakeout_probability_pct ?? 0}%`} />
          <Metric label="Avg Move ATR" value={String(patternMemory?.average_next_move_atr ?? 0)} />
        </div>
        <p>{patternMemory?.no_trade_reason ?? "Pattern memory is replay-ready, but still requires downstream risk gates."}</p>
        <div className="list-row single"><span>Best invalidation: {patternMemory?.best_invalidation ?? "pending"}</span></div>
        <div className="list-row single"><span>Replay events: {similarReplay?.events?.length ?? 0}; deterministic: {similarReplay?.deterministic ? "yes" : "pending"}</span></div>
      </Panel>
      <Panel title="Similar-Day Matches" span="wide" badge={`${similarDays.length} matches`}>
        <div className="capability-table compact">
          {similarDays.map((match: any) => (
            <div key={match.match_id}>
              <b>{match.similar_day_id}</b>
              <span>{match.similarity_score_pct}% / {match.outcome_label}</span>
              <small>{match.feature_match_summary}</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Outcome Learning + Trust Table" span="wide" badge={trustTable?.calibration_status ?? "LOW_EVIDENCE"}>
        <div className="dna-grid">
          <Metric label="Aggregate Trust" value={pct(trustTable?.aggregate_trust_score)} />
          <Metric label="Minimum Sample" value={trustTable?.minimum_sample_pass ? "pass" : "blocked"} />
          <Metric label="Trust Records" value={String(trustTable?.records?.length ?? 0)} />
          <Metric label="Calibration" value={String(trustTable?.calibration_status ?? "pending")} />
        </div>
        {trustTable?.notes?.map((note: string) => (
          <div className="list-row single" key={note}><span>{note}</span></div>
        ))}
        <div className="capability-table compact">
          {trustTable?.records?.map((record: any) => (
            <div key={record.trust_id}>
              <b>{record.pattern_id}</b>
              <span>trust {pct(record.trust_score)} / actual {record.actual_success_rate_pct}%</span>
              <small>{record.sample_count} samples, {record.evidence_quality} evidence</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Failure Pattern Library" span="wide" badge={failureLibrary?.most_common_failure ?? "learning"}>
        <div className="dna-grid">
          <Metric label="Failures Stored" value={String(failureLibrary?.failures?.length ?? 0)} />
          <Metric label="Most Common" value={String(failureLibrary?.most_common_failure ?? "none")} />
          <Metric label="Library Version" value={String(failureLibrary?.library_version ?? "pending")} />
        </div>
        {failureLibrary?.no_trade_lessons?.map((lesson: string) => (
          <div className="list-row single" key={lesson}><span>{lesson}</span></div>
        ))}
        <div className="capability-table compact">
          {failureLibrary?.failures?.slice(0, 8).map((failure: any) => (
            <div key={failure.failure_id}>
              <b>{failure.failure_reason}</b>
              <span>{failure.pattern_id} / {failure.outcome_label}</span>
              <small>{failure.severity} severity</small>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Day Shape Vector" badge="13 fields">
        <Metric label="Gap" value={String(patternMemory?.day_shape_vector?.gap_pct ?? 0)} />
        <Metric label="First 15m" value={String(patternMemory?.day_shape_vector?.first_15m_return ?? 0)} />
        <Metric label="First 30m Range" value={String(patternMemory?.day_shape_vector?.first_30m_range ?? 0)} />
        <Metric label="VWAP Position" value={String(patternMemory?.day_shape_vector?.vwap_position_score ?? 0)} />
        <Metric label="High Break" value={String(patternMemory?.day_shape_vector?.high_break_time ?? "pending")} />
        <Metric label="Low Break" value={String(patternMemory?.day_shape_vector?.low_break_time ?? "pending")} />
      </Panel>
      <Panel title="Reason Tree" badge="read-only">
        {Object.entries(analysis?.reason_tree ?? {}).map(([key, value]) => (
          <div className="list-row" key={key}><b>{key}</b><span>{value as string}</span><small>audit</small></div>
        ))}
      </Panel>
      <Panel title="32 Layer Contracts" span="wide" badge="locked">
        <div className="capability-table compact">
          {spec?.layer_contracts?.map((contract: any) => (
            <div key={contract.contract_name}><b>{contract.layer_index}. {contract.layer_name}</b><span>{contract.status}</span><small>{contract.contract_name}</small></div>
          ))}
        </div>
      </Panel>
      <Panel title="74 Output Columns" span="wide" badge="exact set">
        <div className="capability-table compact">
          {columns.map((column: any) => (
            <div key={column.name}><b>{column.index}. {column.name}</b><span>{column.group}</span><small>{analysis?.columns?.includes(column.name) ? "present" : "missing"}</small></div>
          ))}
        </div>
      </Panel>
      <Panel title="Stock-App Migration Source" badge="reserved">
        <p>{spec?.stock_app_source_root}</p>
        <div className="list-row single"><span>Chart screens, indicators, research signals, backtests, and tests migrate through point-in-time/replay guards.</span></div>
      </Panel>
      <Panel title="Safety Gates" badge="mock">
        {analysis?.safety_gates?.map((gate: string) => <div className="list-row single" key={gate}><span>{gate}</span></div>)}
      </Panel>
    </div>
  );
}

function ChartReplayWorkbench({ chart }: { chart: any }) {
  const points = chart?.chart_points ?? [];
  const viewport = chart?.viewport;
  if (!chart || !viewport || points.length === 0) {
    return <p>Chart replay data is loading. No trading action is possible.</p>;
  }
  const width = 860;
  const height = 260;
  const pad = 24;
  const priceSpan = Math.max(0.01, viewport.max_price - viewport.min_price);
  const xFor = (idx: number) => pad + (idx / Math.max(1, points.length - 1)) * (width - pad * 2);
  const yFor = (price: number) => pad + ((viewport.max_price - price) / priceSpan) * (height - pad * 2);
  const pathFor = (key: string) =>
    points
      .map((point: any, idx: number) => {
        const value = point.indicator_overlay?.[key];
        if (value === null || value === undefined) return "";
        return `${idx === 0 ? "M" : "L"} ${xFor(idx).toFixed(2)} ${yFor(Number(value)).toFixed(2)}`;
      })
      .filter(Boolean)
      .join(" ");
  const selectedIndex = Math.max(0, Math.min(points.length - 1, (chart.selected_sequence_number ?? points.length) - 1));
  const selectedX = xFor(selectedIndex);
  return (
    <div className="chart-replay">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Replay candlestick chart with VWAP and EMA overlays">
        <rect className="plot-bg" x="0" y="0" width={width} height={height} rx="8" />
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
          <line key={ratio} className="grid" x1={pad} x2={width - pad} y1={pad + ratio * (height - pad * 2)} y2={pad + ratio * (height - pad * 2)} />
        ))}
        <path className="overlay vwap" d={pathFor("vwap")} />
        <path className="overlay ema" d={pathFor("ema_5")} />
        <path className="overlay sma" d={pathFor("sma_3")} />
        {points.map((point: any, idx: number) => {
          const x = xFor(idx);
          const yHigh = yFor(point.high);
          const yLow = yFor(point.low);
          const yOpen = yFor(point.open);
          const yClose = yFor(point.close);
          const top = Math.min(yOpen, yClose);
          const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));
          const bullish = point.close >= point.open;
          return (
            <g key={`${point.timestamp_ns}-${idx}`} className={bullish ? "bullish" : "bearish"}>
              <line x1={x} x2={x} y1={yHigh} y2={yLow} />
              <rect x={x - 5} y={top} width="10" height={bodyHeight} rx="1" />
            </g>
          );
        })}
        <line className="selected" x1={selectedX} x2={selectedX} y1={pad} y2={height - pad} />
      </svg>
      <div className="legend">
        <span className="vwap-dot">VWAP</span>
        <span className="ema-dot">EMA 5</span>
        <span className="sma-dot">SMA 3</span>
        <span>Selected candle #{chart.selected_sequence_number}</span>
      </div>
    </div>
  );
}

function ImportedOhlcvPreview({ importResult }: { importResult: any }) {
  const bars = (importResult?.series?.bars ?? []).slice(-96);
  const bounds = useMemo(() => {
    const highs = bars.map((bar: any) => Number(bar.high));
    const lows = bars.map((bar: any) => Number(bar.low));
    const min = Math.min(...lows);
    const max = Math.max(...highs);
    return { min, max: max === min ? max + 1 : max };
  }, [bars]);
  if (!importResult || bars.length === 0) {
    return <p>Import your downloaded RELIANCE data to see the candle preview.</p>;
  }
  const width = 860;
  const height = 240;
  const pad = 24;
  const step = (width - pad * 2) / Math.max(bars.length, 1);
  const yFor = (price: number) => pad + ((bounds.max - price) / (bounds.max - bounds.min)) * (height - pad * 2);
  return (
    <div className="chart-replay">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Imported RELIANCE one-minute candlestick preview">
        <rect className="plot-bg" x="0" y="0" width={width} height={height} rx="8" />
        {bars.map((bar: any, idx: number) => {
          const x = pad + idx * step + step / 2;
          const open = Number(bar.open);
          const close = Number(bar.close);
          const high = Number(bar.high);
          const low = Number(bar.low);
          const top = yFor(Math.max(open, close));
          const bottom = yFor(Math.min(open, close));
          const bullish = close >= open;
          return (
            <g key={`${bar.timestamp_ns}-${idx}`} className={bullish ? "bullish" : "bearish"}>
              <line x1={x} x2={x} y1={yFor(high)} y2={yFor(low)} />
              <rect x={x - Math.max(1.5, step * 0.22)} y={top} width={Math.max(3, step * 0.44)} height={Math.max(2, bottom - top)} rx="1" />
            </g>
          );
        })}
      </svg>
      <div className="legend">
        <span>{importResult.symbol} {importResult.timeframe}</span>
        <span>{bars.length} displayed / {importResult.parsed_bar_count} imported</span>
        <span>First {new Date(Number(bars[0]?.timestamp_ns ?? 0) / 1_000_000).toLocaleString()}</span>
        <span>Last {new Date(Number(bars[bars.length - 1]?.timestamp_ns ?? 0) / 1_000_000).toLocaleString()}</span>
      </div>
    </div>
  );
}

const ORB_TIMEFRAME_MINUTES: Record<string, number> = {
  "1m": 1,
  "5m": 5,
  "15m": 15,
  "1H": 60,
};

function buildOrbGuidancePayload(
  importResult: any,
  primaryTimeframe: "1m" | "5m" | "15m",
  direction: "long" | "short",
  replayForwardBars = 0,
) {
  const source = importResult?.series;
  if (!source?.bars?.length) {
    throw new Error("Downloaded RELIANCE candle data is unavailable.");
  }
  const allSeries = buildOrbSeriesMap(source);
  const fullPrimary = allSeries[primaryTimeframe];
  const cutoff = Math.max(
    1,
    fullPrimary.bars.length - Math.max(0, replayForwardBars),
  );
  const primary = {
    ...fullPrimary,
    bars: fullPrimary.bars.slice(0, cutoff),
    snapshot_id: `${fullPrimary.snapshot_id ?? "local"}-decision-${cutoff}`,
  };
  if (!primary?.bars?.length) {
    throw new Error(`No complete ${primaryTimeframe} candles could be built.`);
  }
  const last = primary.bars[primary.bars.length - 1];
  const durationNs =
    ORB_TIMEFRAME_MINUTES[primaryTimeframe] * 60 * 1_000_000_000;
  const decisionTimeNs = Number(last.timestamp_ns) + durationNs;
  const hierarchy = ["1m", "5m", "15m", "1H"];
  const primaryIndex = hierarchy.indexOf(primaryTimeframe);
  const higher = hierarchy
    .slice(primaryIndex + 1)
    .map((timeframe) => ({
      ...allSeries[timeframe],
      bars: (allSeries[timeframe]?.bars ?? []).filter(
        (bar: any) =>
          Number(bar.timestamp_ns) +
            ORB_TIMEFRAME_MINUTES[timeframe] * 60 * 1_000_000_000 <=
          decisionTimeNs,
      ),
    }))
    .filter((series) => series?.bars?.length);
  return {
    symbol: String(primary.symbol ?? "RELIANCE").toUpperCase(),
    timeframe: primaryTimeframe,
    series: primary,
    decision_time_ns: decisionTimeNs,
    direction,
    higher_timeframe_series: higher,
    required_higher_timeframes: higher.map((series) => series.timeframe),
    include_kronos: false,
    include_orb_playbook: true,
    timezone_offset_minutes: 330,
  };
}

function buildOrbSeriesMap(source: any): Record<string, any> {
  return {
    "1m": source,
    "5m": resampleNseSeries(source, "5m"),
    "15m": resampleNseSeries(source, "15m"),
    "1H": resampleNseSeries(source, "1H"),
  };
}

function buildOrbLifecycleSeries(
  importResult: any,
  primaryTimeframe: "1m" | "5m" | "15m",
  decisionTimeNs: number,
) {
  const source = importResult?.series;
  if (!source?.bars?.length) {
    throw new Error("Replay candles are unavailable for lifecycle evaluation.");
  }
  const full = buildOrbSeriesMap(source)[primaryTimeframe];
  const bars = (full?.bars ?? []).filter(
    (bar: any) => Number(bar.timestamp_ns) >= decisionTimeNs,
  );
  if (!bars.length) {
    throw new Error(
      "No closed candles remain after the ORB decision. Increase Replay forward bars and analyze again.",
    );
  }
  return {
    ...full,
    bars,
    snapshot_id: `${full.snapshot_id ?? "local"}-outcome-${decisionTimeNs}`,
    schema_version: `${full.schema_version ?? "candles.v1"}.orb-outcome`,
  };
}

function resampleNseSeries(source: any, timeframe: "5m" | "15m" | "1H") {
  const bucketMinutes = ORB_TIMEFRAME_MINUTES[timeframe];
  const groups = new Map<string, { startMs: number; bars: any[] }>();
  for (const bar of source.bars ?? []) {
    const utcMs = Number(bar.timestamp_ns) / 1_000_000;
    const localMs = utcMs + 330 * 60_000;
    const local = new Date(localMs);
    const minutes = local.getUTCHours() * 60 + local.getUTCMinutes();
    const sessionOffset = minutes - (9 * 60 + 15);
    if (sessionOffset < 0 || sessionOffset >= 375) continue;
    const bucket = Math.floor(sessionOffset / bucketMinutes);
    const dayStartLocalMs = Date.UTC(
      local.getUTCFullYear(),
      local.getUTCMonth(),
      local.getUTCDate(),
    );
    const bucketStartLocalMs =
      dayStartLocalMs +
      (9 * 60 + 15 + bucket * bucketMinutes) * 60_000;
    const bucketStartUtcMs = bucketStartLocalMs - 330 * 60_000;
    const key = `${local.getUTCFullYear()}-${local.getUTCMonth()}-${local.getUTCDate()}-${bucket}`;
    const current = groups.get(key) ?? {
      startMs: bucketStartUtcMs,
      bars: [],
    };
    current.bars.push(bar);
    groups.set(key, current);
  }
  const bars = Array.from(groups.values())
    .filter((group) => group.bars.length === bucketMinutes)
    .sort((a, b) => a.startMs - b.startMs)
    .map((group, index) => {
      const rows = group.bars.sort(
        (a, b) => Number(a.timestamp_ns) - Number(b.timestamp_ns),
      );
      const first = rows[0];
      const last = rows[rows.length - 1];
      return {
        symbol: String(source.symbol ?? first.symbol ?? "RELIANCE").toUpperCase(),
        timeframe,
        timestamp_ns: Math.round(group.startMs * 1_000_000),
        open: Number(first.open),
        high: Math.max(...rows.map((row) => Number(row.high))),
        low: Math.min(...rows.map((row) => Number(row.low))),
        close: Number(last.close),
        volume: rows.reduce(
          (total, row) => total + Number(row.volume ?? 0),
          0,
        ),
        source: "user_csv",
        sequence_number: index + 1,
      };
    });
  return {
    symbol: String(source.symbol ?? "RELIANCE").toUpperCase(),
    timeframe,
    bars,
    snapshot_id: `${source.snapshot_id ?? "local-reliance"}:${timeframe}:closed`,
    schema_version: source.schema_version ?? "candles.v1",
  };
}

function formatPrice(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0
    ? numeric.toFixed(2)
    : "pending";
}

function JarvisDecisionRoom({ data, onRefresh }: { data: AppData; onRefresh: () => Promise<void> }) {
  const [stockChartReloadKey, setStockChartReloadKey] = useState(0);
  const [indicatorCacheSaving, setIndicatorCacheSaving] = useState(false);
  const [indicatorCacheDeleting, setIndicatorCacheDeleting] = useState<string | null>(null);
  const [indicatorCacheSaveResult, setIndicatorCacheSaveResult] = useState<any | null>(null);
  const [indicatorCacheDeleteResult, setIndicatorCacheDeleteResult] = useState<any | null>(null);
  const [indicatorCacheError, setIndicatorCacheError] = useState<string | null>(null);
  const [grokGatewayBusy, setGrokGatewayBusy] = useState<"connect" | "review" | null>(null);
  const [grokGatewayStatus, setGrokGatewayStatus] = useState<any | null>(null);
  const [grokGatewayReview, setGrokGatewayReview] = useState<any | null>(null);
  const [grokGatewayError, setGrokGatewayError] = useState<string | null>(null);
  const [orbTimeframe, setOrbTimeframe] = useState<"1m" | "5m" | "15m">("5m");
  const [orbDirection, setOrbDirection] = useState<"long" | "short">("long");
  const [orbGuidanceBusy, setOrbGuidanceBusy] = useState(false);
  const [orbGuidance, setOrbGuidance] = useState<any | null>(null);
  const [orbGuidanceError, setOrbGuidanceError] = useState<string | null>(null);
  const [orbPaperRecords, setOrbPaperRecords] = useState<any[]>([]);
  const [orbPaperRecordBusy, setOrbPaperRecordBusy] = useState(false);
  const [orbPaperRecordResult, setOrbPaperRecordResult] = useState<any | null>(null);
  const [orbReplayForwardBars, setOrbReplayForwardBars] = useState(6);
  const [orbReplayImport, setOrbReplayImport] = useState<any | null>(null);
  const [orbPaperOutcomes, setOrbPaperOutcomes] = useState<any[]>([]);
  const [orbLifecycleBusy, setOrbLifecycleBusy] = useState(false);
  const [orbLifecycleResult, setOrbLifecycleResult] = useState<any | null>(null);
  const [orbReliability, setOrbReliability] = useState<any | null>(null);
  const [orbStorageMonitor, setOrbStorageMonitor] = useState<any | null>(null);
  const [jarvisTab, setJarvisTab] = useState<"trade" | "evidence" | "execution" | "vault">("trade");
  const room = data.jarvisDecisionRoom?.data;
  const fusion = data.jarvisDecisionFusion?.data;
  const masterPanel = data.jarvisMasterPanel?.data;
  const replayDeterminism = data.jarvisReplayDeterminism?.data;
  const productionBlockers = data.jarvisProductionBlockers?.data;
  const blockerResolution = data.jarvisBlockerResolution?.data;
  const preflightEvidence = data.jarvisPreflightEvidence?.data;
  const adapterHarness = data.openAlgoAdapterHarness?.data;
  const openAlgoHandoffGate = data.jarvisOpenAlgoHandoffGate?.data;
  const openAlgoPaperBridge = data.jarvisOpenAlgoPaperBridge?.data;
  const paperExecutionLoop = data.jarvisPaperExecutionLoop?.data;
  const decisionQualityGate = data.jarvisDecisionQualityGate?.data;
  const tradingDecisionOutput = data.jarvisTradingDecisionOutput?.data;
  const chartOverlayQa = data.jarvisChartOverlayQa?.data;
  const evidenceLatencyBudget = data.jarvisEvidenceLatencyBudget?.data;
  const evidenceCache = data.jarvisEvidenceCache?.data;
  const realtimeFreshness = data.jarvisRealtimeFreshness?.data;
  const decision = room?.trade_vision_decision;
  const safety = room?.safety_summary;
  const gemini = room?.gemini_summary;
  const geminiReview = room?.gemini_review_summary;
  const geminiStatus = data.jarvisGeminiStatus?.data;
  const geminiLiveReview = data.jarvisGeminiLiveReview?.data;
  const grokStatus = data.jarvisGrokStatus?.data;
  const grokLiveReview = data.jarvisGrokLiveReview?.data;
  const aiComparison = data.jarvisAiComparison?.data;
  const aiComparisonHistory = data.jarvisAiComparisonHistory?.data;
  const aiReviewRefreshGuard = data.jarvisAiReviewRefreshGuard?.data;
  const aiRefreshAction = data.jarvisAiRefreshAction?.data;
  const aiRefreshResponseSample = data.jarvisAiRefreshResponseSample?.data;
  const aiRefreshResponseLedger = data.jarvisAiRefreshResponseLedger?.data;
  const aiEvidenceDiff = data.jarvisAiEvidenceDiff?.data;
  const providerDisagreement = data.jarvisProviderDisagreement?.data;
  const verifiedReviewPacket = data.jarvisVerifiedReviewPacket?.data;
  const openAlgoSafeIntentBinding = data.jarvisOpenAlgoSafeIntentBinding?.data;
  const paperReadySafetyAudit = data.jarvisPaperReadySafetyAudit?.data;
  const geminiOutbound = data.jarvisGeminiOutboundBundle?.data;
  const geminiFallbackReadiness = data.jarvisGeminiFallbackReadiness?.data;
  const geminiLiveReviewHarness = data.jarvisGeminiLiveReviewHarness?.data;
  const geminiDecisionRoom = data.jarvisGeminiDecisionRoom?.data;
  const externalAiIntake = data.jarvisExternalAiReviewIntake?.data;
  const externalAiAudit = data.jarvisExternalAiReviewAudit?.data;
  const externalAiReliability = data.jarvisExternalAiReliability?.data;
  const verifiedEvidence = data.jarvisVerifiedEvidence?.data;
  const reviewPreflight = data.jarvisReviewPreflight?.data;
  const correctionPacket = data.jarvisCorrectionPacket?.data;
  const correctionValidation = data.jarvisCorrectionValidation?.data;
  const correctionAudit = data.jarvisCorrectionAudit?.data;
  const correctionRecords = data.jarvisCorrectionRecords?.data ?? [];
  const externalAiAuditIntegrity = data.jarvisExternalAiAuditIntegrity?.data;
  const decisionEvidenceExport = data.jarvisDecisionEvidenceExport?.data;
  const dailyVerifiedAuthority = data.jarvisDailyVerifiedAuthority?.data;
  const indicatorCombinationMemory = data.jarvisIndicatorCombinationMemory?.data;
  const candleCauseEffectMemory = data.jarvisCandleCauseEffectMemory?.data;
  const nineCandleHybrid = data.nineCandleHybrid?.data;
  const nineCandleVectorAudit = data.nineCandleVectorAudit?.data;
  const nineCandleFeatureManifestIntegrity = data.nineCandleFeatureManifestIntegrity?.data;
  const nineCandleIndicatorPromotion = data.nineCandleIndicatorPromotion?.data;
  const nineCandleIndicatorRuntime = data.nineCandleIndicatorRuntime?.data;
  const indicatorCacheStatus = data.indicatorCacheStatus?.data;
  const indicatorCacheResults = data.indicatorCacheResults?.data;
  const indicatorSignalHistory = data.indicatorSignalHistory?.data;
  const indicatorReliabilityDrilldown = data.indicatorReliabilityDrilldown?.data;
  const indicatorReliability = indicatorReliabilityDrilldown?.reliability;
  const indicatorHistory = indicatorReliabilityDrilldown?.history ?? indicatorSignalHistory;
  const indicatorCacheRows = (indicatorCacheResults?.results ?? indicatorCacheStatus?.rows ?? []) as any[];
  const failedIndicatorCacheRow = indicatorCacheRows.find((row: any) => row?.cache_integrity_status !== "verified");
  const clearIndicatorCacheCandidate = failedIndicatorCacheRow ?? indicatorCacheRows[0];
  const nineCandleSetupMemory = data.nineCandleSetupMemory?.data;
  const nineCandlePathAnalogs = data.nineCandlePathAnalogs?.data;
  const nineCandleOodStatus = data.nineCandleOodStatus?.data;
  const nineCandleHypotheses = data.nineCandleHypotheses?.data;
  const nineCandleCalibration = data.nineCandleCalibration?.data;
  const nineCandlePromotionGuard = data.nineCandlePromotionGuard?.data;
  const tvProdRed001 = data.tvProdRed001?.data;
  const hasTvProdRed001 = Boolean(tvProdRed001?.red_team_id);
  const calibrationBins = Array.isArray(nineCandleCalibration) ? nineCandleCalibration : (nineCandleCalibration?.bins ?? []);
  const calibrationSampleCount = Array.isArray(calibrationBins)
    ? calibrationBins.reduce((total: number, row: any) => total + Number(row?.sample_count ?? 0), 0)
    : 0;
  const kronos = room?.kronos_summary;
  const openalgo = room?.openalgo_summary;
  const arbiter = room?.decision_arbiter;
  const paperReality = room?.paper_reality_check;
  const widgets = room?.extended_widgets;
  const usefulness = room?.usefulness_summary ?? data.jarvisUsefulness?.data;
  const usefulnessRecord = room?.usefulness_record;
  const indicators = room?.indicator_snapshot ?? {};
  const packet = room?.packet_metadata ?? {};
  const health = room?.system_health_matrix;
  const uiContract = room?.ui_contract;
  const multiTf = room?.multi_timeframe_alignment;
  const entryZone = decision?.best_entry_zone ?? tradingDecisionOutput?.trade_plan?.entry_zone ?? [];
  const entryText = Array.isArray(entryZone) && entryZone.length ? entryZone.join(" - ") : "wait for trigger";
  const stopLoss = decision?.stop_loss ?? tradingDecisionOutput?.trade_plan?.stop_loss ?? "pending";
  const target = decision?.target ?? tradingDecisionOutput?.trade_plan?.target ?? "pending";
  const invalidation = decision?.invalidation_level ?? tradingDecisionOutput?.trade_plan?.invalidation_level ?? "pending";
  const finalAction = tradingDecisionOutput?.trade_plan?.display_action ?? room?.final_action ?? decision?.final_trade_decision ?? "WAIT";
  const rawChartSymbol = String(room?.symbol ?? "RELIANCE").toUpperCase();
  const stockAppSymbol = rawChartSymbol.includes(".") ? rawChartSymbol : `${rawChartSymbol}.NS`;
  const chartSymbol = encodeURIComponent(stockAppSymbol);
  const chartTimeframe = encodeURIComponent(String(room?.timeframe ?? "1m"));
  const stockAppChartUrl = `http://127.0.0.1:8766/?embed=chart&symbol=${chartSymbol}&interval=${chartTimeframe}`;
  const stockAppFullUrl = `http://127.0.0.1:8766/?symbol=${chartSymbol}&interval=${chartTimeframe}`;
  const orbTicket = orbGuidance?.orb_ticket;
  const orbEntry = orbTicket?.entry_plan;
  const orbRange = orbTicket?.opening_range;
  const orbSignal = orbTicket?.signal;
  const orbProof = orbTicket?.proof_metrics;
  const jarvisTabs = [
    { id: "trade", label: "Trade Decision Room", note: "chart, AI, MTF, memory, entry plan" },
    { id: "evidence", label: "Evidence & Data Lab", note: "data proof, replay, cache, QA" },
    { id: "execution", label: "Execution / OpenAlgo Lab", note: "handoff, dry-run, paper readiness" },
    { id: "vault", label: "Ops & Audit Vault", note: "provider ops, release, correction audit" },
  ] as const;
  const actionClass = String(finalAction).toLowerCase().replace(/[^a-z0-9]+/g, "-") || "wait";
  const activeBlocker = [
    ...(safety?.blocking_gates ?? []),
    ...(decisionQualityGate?.quality_flags ?? []).filter((flag: any) => flag?.severity === "block").map((flag: any) => flag.name),
    ...(providerDisagreement?.reason_cards ?? []).filter((reason: any) => reason?.severity === "block").map((reason: any) => reason.description),
  ].find(Boolean) ?? "no active blocker loaded";
  const aiAgreement = aiComparison?.agreement_matrix?.agreement_state ?? providerDisagreement?.explorer_state ?? geminiReview?.safe_final_action ?? "pending";
  const kronosLine = arbiter?.kronos_status ?? kronos?.status ?? "reserved";
  useEffect(() => {
    let active = true;
    Promise.all([
      api.paperGuidancePaperRecords(rawChartSymbol, orbTimeframe),
      api.paperGuidancePaperOutcomes(),
      api.paperGuidanceStorageMonitor(),
    ])
      .then(([records, outcomes, monitor]) => {
        if (!active) return;
        setOrbPaperRecords(records.data);
        setOrbPaperOutcomes(outcomes.data);
        setOrbStorageMonitor(monitor.data);
      })
      .catch(() => {
        if (!active) return;
        setOrbPaperRecords([]);
        setOrbPaperOutcomes([]);
        setOrbStorageMonitor(null);
      });
    return () => {
      active = false;
    };
  }, [rawChartSymbol, orbTimeframe]);
  useEffect(() => {
    let active = true;
    if (!orbTicket?.playbook_id) {
      setOrbReliability(null);
      return () => {
        active = false;
      };
    }
    api
      .paperGuidanceOrbReliability(
        orbTicket.playbook_id,
        rawChartSymbol,
        orbTimeframe,
      )
      .then((response) => {
        if (active) setOrbReliability(response.data);
      })
      .catch(() => {
        if (active) setOrbReliability(null);
      });
    return () => {
      active = false;
    };
  }, [orbTicket?.playbook_id, rawChartSymbol, orbTimeframe]);

  const runOrbGuidance = async () => {
    setOrbGuidanceBusy(true);
    setOrbGuidanceError(null);
    setOrbPaperRecordResult(null);
    setOrbLifecycleResult(null);
    try {
      const imported = await api.behaviorImportLocalReliancePreview(390, "tail");
      const payload = buildOrbGuidancePayload(
        imported.data,
        orbTimeframe,
        orbDirection,
        orbReplayForwardBars,
      );
      const response = await api.paperGuidanceRun(payload);
      setOrbReplayImport(imported.data);
      setOrbGuidance(response.data);
    } catch (error) {
      setOrbGuidanceError(normalizeUiIssue(error).detail);
      setOrbGuidance(null);
    } finally {
      setOrbGuidanceBusy(false);
    }
  };

  const recordOrbPaperTrade = async () => {
    if (!orbTicket?.can_record_paper || !orbTicket?.guidance_id) return;
    const approved = window.confirm(
      "Record this exact ORB ticket as a local simulated paper trade? This creates no broker order.",
    );
    if (!approved) return;
    setOrbPaperRecordBusy(true);
    setOrbGuidanceError(null);
    try {
      const response = await api.paperGuidanceRecordSimulated({
        guidance_id: orbTicket.guidance_id,
        source_snapshot_hash: orbTicket.source_snapshot_hash,
        approved_by: "local-operator",
        approval_text: "RECORD_SIMULATED_PAPER_TRADE",
        quantity: 1,
        note: "Recorded from Jarvis ORB guidance screen.",
      });
      setOrbPaperRecordResult(response.data);
      const records = await api.paperGuidancePaperRecords(
        rawChartSymbol,
        orbTimeframe,
      );
      setOrbPaperRecords(records.data);
    } catch (error) {
      setOrbGuidanceError(normalizeUiIssue(error).detail);
    } finally {
      setOrbPaperRecordBusy(false);
    }
  };
  const evaluateOrbPaperLifecycle = async () => {
    const paper =
      orbPaperRecordResult ??
      orbPaperRecords.find(
        (record: any) => record.guidance_id === orbTicket?.guidance_id,
      );
    if (!paper || !orbTicket || !orbReplayImport) {
      setOrbGuidanceError(
        "Run ORB replay analysis and record its simulated paper ticket before evaluating the result.",
      );
      return;
    }
    const approved = window.confirm(
      "Evaluate this recorded paper ticket against later closed replay candles? This is local simulation only.",
    );
    if (!approved) return;
    setOrbLifecycleBusy(true);
    setOrbGuidanceError(null);
    try {
      const series = buildOrbLifecycleSeries(
        orbReplayImport,
        orbTimeframe,
        Number(orbTicket.decision_time_ns),
      );
      const last = series.bars[series.bars.length - 1];
      const durationNs =
        ORB_TIMEFRAME_MINUTES[orbTimeframe] * 60 * 1_000_000_000;
      const response = await api.paperGuidanceObserveSimulated({
        paper_record_id: paper.paper_record_id,
        source_snapshot_hash: paper.source_snapshot_hash,
        series,
        observation_time_ns: Number(last.timestamp_ns) + durationNs,
        max_holding_bars: orbReplayForwardBars,
        observation_text: "EVALUATE_SIMULATED_PAPER_OUTCOME",
      });
      setOrbLifecycleResult(response.data);
      const [outcomes, reliability, monitor] = await Promise.all([
        api.paperGuidancePaperOutcomes(),
        api.paperGuidanceOrbReliability(
          paper.playbook_id,
          rawChartSymbol,
          orbTimeframe,
        ),
        api.paperGuidanceStorageMonitor(),
      ]);
      setOrbPaperOutcomes(outcomes.data);
      setOrbReliability(reliability.data);
      setOrbStorageMonitor(monitor.data);
    } catch (error) {
      setOrbGuidanceError(normalizeUiIssue(error).detail);
    } finally {
      setOrbLifecycleBusy(false);
    }
  };
  const runGrokGatewayConnect = async () => {
    setGrokGatewayBusy("connect");
    setGrokGatewayError(null);
    try {
      const result = await api.jarvisGrokGatewayConnect();
      setGrokGatewayStatus(result.data);
    } catch (error) {
      setGrokGatewayError(normalizeUiIssue(error).detail);
    } finally {
      setGrokGatewayBusy(null);
    }
  };

  const runGrokGatewayReview = async () => {
    setGrokGatewayBusy("review");
    setGrokGatewayError(null);
    try {
      const result = await api.jarvisGrokGatewayReview(rawChartSymbol, true, String(room?.timeframe ?? "1m"));
      setGrokGatewayReview(result.data);
    } catch (error) {
      setGrokGatewayError(normalizeUiIssue(error).detail);
    } finally {
      setGrokGatewayBusy(null);
    }
  };

  const saveIndicatorCache = async (forceRecompute = false) => {
    setIndicatorCacheSaving(true);
    setIndicatorCacheError(null);
    try {
      const response = await api.indicatorCacheSave(rawChartSymbol, String(room?.timeframe ?? "1m"), true, forceRecompute);
      setIndicatorCacheSaveResult(response.data);
      await onRefresh();
    } catch (error) {
      setIndicatorCacheError(error instanceof Error ? error.message : "Indicator cache save failed.");
    } finally {
      setIndicatorCacheSaving(false);
    }
  };
  const deleteIndicatorCache = async (cacheId: string) => {
    setIndicatorCacheDeleting(cacheId);
    setIndicatorCacheError(null);
    try {
      const response = await api.indicatorCacheDelete(cacheId);
      setIndicatorCacheDeleteResult(response.data);
      await onRefresh();
    } catch (error) {
      setIndicatorCacheError(error instanceof Error ? error.message : "Indicator cache delete failed.");
    } finally {
      setIndicatorCacheDeleting(null);
    }
  };
  return (
    <div className="workspace jarvis-workspace" data-active-tab={jarvisTab}>
      <div className={`jarvis-command-ticket action-${actionClass}`}>
        <div className="jarvis-command-main">
          <span>Action</span>
          <strong>{finalAction}</strong>
          <small>{decision?.entry_condition ?? tradingDecisionOutput?.reason ?? "Wait for verified chart, indicator, history, MTF, AI, and safety evidence."}</small>
        </div>
        <div><span>Entry</span><b>{entryText}</b></div>
        <div><span>SL</span><b>{String(stopLoss)}</b></div>
        <div><span>Target</span><b>{String(target)}</b></div>
        <div><span>Invalid</span><b>{String(invalidation)}</b></div>
        <div><span>Confidence</span><b>{`${decision?.confidence_cap_pct ?? tradingDecisionOutput?.confidence?.confidence_cap_pct ?? 0}%`}</b></div>
        <div><span>Blocker</span><b>{String(activeBlocker).slice(0, 72)}</b></div>
        <div><span>MTF</span><b>{multiTf?.arbiter_modifier ?? "pending"}</b></div>
        <div><span>AI / Kronos</span><b>{aiAgreement} / {kronosLine}</b></div>
      </div>

      <div className="jarvis-tabbar" role="tablist" aria-label="Jarvis workspace tabs">
        {jarvisTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={jarvisTab === tab.id ? "active" : ""}
            onClick={() => setJarvisTab(tab.id)}
            role="tab"
            aria-selected={jarvisTab === tab.id}
          >
            <b>{tab.label}</b>
            <span>{tab.note}</span>
          </button>
        ))}
      </div>

      <Panel title="Trader Decision Brief" span="full" category="decision" tab="trade" badge={finalAction}>
        <div className="trader-brief-grid">
          <div className="trader-brief-primary">
            <span>Decision</span>
            <strong>{finalAction}</strong>
            <small>{decision?.entry_condition ?? tradingDecisionOutput?.headline ?? "Wait for verified chart, indicator, history, MTF, and safety evidence."}</small>
          </div>
          <div><span>Entry</span><b>{entryText}</b></div>
          <div><span>SL</span><b>{String(stopLoss)}</b></div>
          <div><span>Target</span><b>{String(target)}</b></div>
          <div><span>Invalid</span><b>{String(invalidation)}</b></div>
          <div><span>MTF</span><b>{multiTf?.arbiter_modifier ?? "pending"}</b><small>{multiTf?.dominant_conflict ?? "no conflict loaded"}</small></div>
          <div><span>Pattern Now</span><b>{tradingDecisionOutput?.pattern_now?.candle_pattern ?? decision?.scenario_label ?? room?.candle_structure?.pattern ?? "pending"}</b><small>{tradingDecisionOutput?.pattern_now?.wick_body_read ?? candleCauseEffectMemory?.effect_label ?? "candle memory loading"}</small></div>
          <div><span>Indicator Memory</span><b>{indicatorCombinationMemory?.evidence_quality ?? "pending"}</b><small>{indicatorCombinationMemory?.sequence_memory?.interpretation ?? tradingDecisionOutput?.sequential_signal_story?.interpretation ?? "sequence not loaded"}</small></div>
          <div><span>Similar History</span><b>{`${room?.similar_history?.matches_used ?? nineCandleHybrid?.memory?.total_matches ?? 0} used`}</b><small>{`9C W/F ${nineCandleHybrid?.memory?.winner_like_matches ?? 0}/${nineCandleHybrid?.memory?.failure_like_matches ?? 0}`}</small></div>
          <div><span>AI One-Line</span><b>{aiComparison?.agreement_matrix?.agreement_state ?? providerDisagreement?.explorer_state ?? "pending"}</b><small>{aiComparison?.final_interpretation ?? geminiReview?.candidate_response?.entry_guidance ?? "Gemini/Grok review not trusted yet"}</small></div>
          <div><span>Kronos</span><b>{arbiter?.kronos_status ?? kronos?.status ?? "reserved"}</b><small>{kronos?.mode ?? "forecast prior only"}</small></div>
          <div><span>Safety</span><b>{safety?.overall_status ?? decisionQualityGate?.quality_state ?? "pending"}</b><small>{(safety?.blocking_gates ?? decisionQualityGate?.quality_flags?.map((flag: any) => flag.name) ?? []).slice(0, 2).join(" | ") || "no block loaded"}</small></div>
        </div>
        <div className="trade-action-row">
          <a href="#research">Chart + Indicators</a>
          <a href="#replay">Replay Evidence</a>
          <button type="button" onClick={() => setJarvisTab("trade")}>AI/Kronos review</button>
          <button type="button" onClick={() => setJarvisTab("evidence")}>Evidence details</button>
        </div>
      </Panel>

      <Panel
        title="ORB Paper Guidance"
        span="full"
        category="decision"
        tab="trade"
        badge={orbGuidance?.final_band ?? "READY TO ANALYZE"}
      >
        <div className="orb-guidance-toolbar">
          <div className="orb-timeframe-control" role="group" aria-label="ORB timeframe">
            {(["1m", "5m", "15m"] as const).map((timeframe) => (
              <button
                key={timeframe}
                type="button"
                className={orbTimeframe === timeframe ? "active" : ""}
                onClick={() => setOrbTimeframe(timeframe)}
                disabled={orbGuidanceBusy}
              >
                {timeframe}
              </button>
            ))}
          </div>
          <div className="orb-timeframe-control" role="group" aria-label="ORB direction">
            {(["long", "short"] as const).map((direction) => (
              <button
                key={direction}
                type="button"
                className={orbDirection === direction ? "active" : ""}
                onClick={() => setOrbDirection(direction)}
                disabled={orbGuidanceBusy}
              >
                {direction.toUpperCase()}
              </button>
            ))}
          </div>
          <div className="orb-timeframe-control" role="group" aria-label="Replay forward candles">
            {([3, 6, 12] as const).map((bars) => (
              <button
                key={bars}
                type="button"
                className={orbReplayForwardBars === bars ? "active" : ""}
                onClick={() => setOrbReplayForwardBars(bars)}
                disabled={orbGuidanceBusy || orbPaperRecordBusy || orbLifecycleBusy}
                title="Reserve later closed candles for explicit paper-outcome evaluation"
              >
                +{bars}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="orb-primary-action"
            onClick={runOrbGuidance}
            disabled={orbGuidanceBusy}
            data-testid="orb-run-guidance"
          >
            {orbGuidanceBusy ? "Analyzing closed candles..." : "Analyze RELIANCE ORB"}
          </button>
          <button
            type="button"
            className="orb-paper-action"
            onClick={recordOrbPaperTrade}
            disabled={!orbTicket?.can_record_paper || orbPaperRecordBusy}
            data-testid="orb-record-paper"
          >
            {orbPaperRecordBusy ? "Recording..." : "Record Simulated Paper"}
          </button>
          <button
            type="button"
            className="orb-lifecycle-action"
            onClick={evaluateOrbPaperLifecycle}
            disabled={
              orbLifecycleBusy ||
              !orbTicket?.can_record_paper ||
              !orbReplayImport ||
              !(
                orbPaperRecordResult ??
                orbPaperRecords.find(
                  (record: any) => record.guidance_id === orbTicket?.guidance_id,
                )
              )
            }
            data-testid="orb-evaluate-paper"
          >
            {orbLifecycleBusy ? "Evaluating closed candles..." : "Evaluate Replay Result"}
          </button>
          <span className="orb-safety-label">LOCAL SIMULATION ONLY · NO BROKER ORDER</span>
        </div>

        <div className="orb-decision-strip">
          <div className={`orb-action action-${String(orbGuidance?.final_band ?? "WAIT").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
            <span>Jarvis action</span>
            <strong>{orbGuidance?.final_band ?? "RUN ANALYSIS"}</strong>
            <small>{orbTicket?.candidate_state ?? "Loads downloaded 1m data and builds closed-candle MTF evidence."}</small>
          </div>
          <div><span>Signal</span><b>{orbSignal?.signal_type ?? "pending"}</b><small>{orbSignal?.side ?? "none"}</small></div>
          <div><span>Entry trigger</span><b>{formatPrice(orbEntry?.entry)}</b><small>not a fill</small></div>
          <div><span>Stop</span><b>{formatPrice(orbEntry?.stop)}</b><small>{orbEntry?.invalidation ?? "pending"}</small></div>
          <div><span>Target</span><b>{formatPrice(orbEntry?.target)}</b><small>{orbEntry ? `${orbEntry.r_ratio}R` : "pending"}</small></div>
          <div><span>MTF</span><b>{orbTicket ? (orbTicket.mtf_complete ? "ALIGNED" : "BLOCKED") : "pending"}</b><small>{orbGuidance?.mtf_evidence?.usable_timeframes?.join(" / ") || "5m / 15m / 1H built on run"}</small></div>
        </div>

        <div className="orb-guidance-body">
          <div className="orb-range-map">
            <header><b>Opening Range</b><span>{orbRange?.locked ? "LOCKED" : "NOT LOCKED"}</span></header>
            <div className="orb-range-line">
              <span>ORH {formatPrice(orbRange?.opening_range_high)}</span>
              <i />
              <span>ORL {formatPrice(orbRange?.opening_range_low)}</span>
            </div>
            <div className="orb-compact-grid">
              <Metric label="Range Width" value={formatPrice(orbRange?.opening_range_width)} />
              <Metric label="Window" value={orbRange ? `${orbRange.range_start_local}-${orbRange.range_end_local}` : "pending"} />
              <Metric label="Playbook" value={orbTicket?.playbook_id ? String(orbTicket.playbook_id).slice(0, 12) : "none"} />
              <Metric label="Proof" value={orbTicket?.proof_id ? String(orbTicket.proof_id).slice(0, 12) : "none"} />
            </div>
          </div>

          <div className="orb-proof-block">
            <header><b>Historical Proof</b><span>{orbProof ? "SERVER VERIFIED" : "NO ACTIVE PROOF"}</span></header>
            <div className="orb-compact-grid">
              <Metric label="Trades" value={String(orbProof?.trade_count ?? 0)} />
              <Metric label="Win Rate" value={orbProof ? `${Math.round(Number(orbProof.win_rate) * 100)}%` : "pending"} />
              <Metric label="Profit Factor" value={orbProof ? Number(orbProof.profit_factor).toFixed(2) : "pending"} />
              <Metric label="Net R" value={orbProof ? Number(orbProof.net_r).toFixed(2) : "pending"} />
              <Metric label="Evidence" value={`${orbTicket?.historical_match_count ?? 0}/${orbTicket?.minimum_evidence_count ?? 30}`} />
              <Metric label="Liquidity" value={orbTicket?.liquidity_grade ?? "pending"} />
            </div>
          </div>

          <div className="orb-blocker-block">
            <header><b>Why act or wait</b><span>{orbTicket?.can_record_paper ? "ELIGIBLE" : "WAIT-FIRST"}</span></header>
            <div className="orb-reason-list">
              {(orbTicket?.blockers ?? ["Run analysis to load verified ORB, MTF, risk, and memory gates."]).slice(0, 4).map((reason: string) => (
                <div key={reason} className="orb-blocker">{reason}</div>
              ))}
              {(orbTicket?.reasons ?? []).slice(0, 3).map((reason: string) => (
                <div key={reason} className="orb-support">{reason}</div>
              ))}
            </div>
          </div>
        </div>

        {orbGuidanceError && <div className="orb-error" role="alert">{orbGuidanceError}</div>}
        {orbPaperRecordResult && (
          <div className="orb-paper-confirmation" data-testid="orb-paper-recorded">
            Recorded locally: {orbPaperRecordResult.paper_record_id}. Entry {formatPrice(orbPaperRecordResult.entry)}, stop {formatPrice(orbPaperRecordResult.stop)}, target {formatPrice(orbPaperRecordResult.target)}. No broker order was created.
          </div>
        )}
        {orbLifecycleResult && (
          <div
            className={`orb-lifecycle-result outcome-${String(orbLifecycleResult.outcome_label).toLowerCase()}`}
            data-testid="orb-paper-outcome"
          >
            <div>
              <span>Replay outcome</span>
              <strong>{orbLifecycleResult.outcome_label}</strong>
              <small>{orbLifecycleResult.reason}</small>
            </div>
            <div>
              <span>Simulated fill</span>
              <strong>{formatPrice(orbLifecycleResult.simulated_fill_price)}</strong>
              <small>{orbLifecycleResult.fill_status} / {orbLifecycleResult.lifecycle_status}</small>
            </div>
            <div>
              <span>Path</span>
              <strong>{Number(orbLifecycleResult.net_r ?? 0).toFixed(2)}R net</strong>
              <small>MFE {formatPrice(orbLifecycleResult.mfe)} / MAE {formatPrice(orbLifecycleResult.mae)}</small>
            </div>
            <div>
              <span>Execution cost</span>
              <strong>{Number(orbLifecycleResult.costs?.total_cost_r ?? 0).toFixed(3)}R</strong>
              <small>spread + slippage + impact + brokerage</small>
            </div>
          </div>
        )}
        <div className="orb-feedback-strip">
          <div>
            <span>Paper reliability</span>
            <strong>{orbReliability?.reliability_state ?? "NO COMPLETED EVIDENCE"}</strong>
            <small>
              {orbReliability
                ? `${orbReliability.completed_sample_count}/${orbReliability.minimum_sample_count} outcomes / Bayesian ${Math.round(Number(orbReliability.bayesian_win_rate) * 100)}%`
                : "Only completed point-in-time outcomes are counted"}
            </small>
          </div>
          <div>
            <span>Store integrity</span>
            <strong>{orbStorageMonitor?.integrity_passed ? "PASS" : "PENDING / BLOCKED"}</strong>
            <small>
              {orbStorageMonitor
                ? `${orbStorageMonitor.paper_record_count} intents / ${orbStorageMonitor.completed_outcome_count} completed / ${orbStorageMonitor.orphan_outcome_count} orphan`
                : "monitor not loaded"}
            </small>
          </div>
          <div>
            <span>Replay window</span>
            <strong>+{orbReplayForwardBars} {orbTimeframe} bars</strong>
            <small>reserved after guidance; closed candles only</small>
          </div>
        </div>
        <div className="orb-paper-ledger">
          <b>Simulated paper ledger</b>
          <span>{orbPaperRecords.length} record(s) for {rawChartSymbol} {orbTimeframe}</span>
          {orbPaperRecords.slice(0, 3).map((record: any) => {
            const outcome = orbPaperOutcomes.find(
              (item: any) => item.paper_record_id === record.paper_record_id,
            );
            return (
              <div key={record.paper_record_id}>
                <strong>{record.side} · {formatPrice(record.entry)}</strong>
                <span>
                  SL {formatPrice(record.stop)} · Target {formatPrice(record.target)} ·{" "}
                  {outcome?.outcome_label ?? record.status}
                </span>
                <small>
                  {new Date(record.approved_at).toLocaleString()} · human approved ·{" "}
                  {outcome
                    ? `${Number(outcome.net_r ?? 0).toFixed(2)}R net`
                    : "awaiting explicit replay evaluation"}
                </small>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel title="Jarvis Trading Cockpit" span="chart" tab="trade" badge={finalAction}>
        <div className="dna-grid">
          <Metric label="Symbol" value={room?.symbol ?? "RELIANCE"} />
          <Metric label="Timeframe" value={room?.timeframe ?? "1m"} />
          <Metric label="Packet" value={(packet.packet_id ?? "pending").slice(0, 12)} />
          <Metric label="Expires" value={packet.valid_until ? new Date(packet.valid_until).toLocaleTimeString() : "pending"} />
          <Metric label="Health" value={health?.overall_health ?? "pending"} />
          <Metric label="Panels" value={`${uiContract?.core_panel_count ?? 0} core`} />
          <Metric label="Final Action" value={room?.final_action ?? "WAIT"} />
          <Metric label="Trading" value={room?.trade_allowed ? "allowed" : "blocked"} />
        </div>
        <div className="trade-ticket-row">
          <div><span>Entry</span><b>{entryText}</b></div>
          <div><span>Stop Loss</span><b>{String(stopLoss)}</b></div>
          <div><span>Target</span><b>{String(target)}</b></div>
          <div><span>Invalid</span><b>{String(invalidation)}</b></div>
        </div>
        <div className="trade-action-row">
          <a href="#research">Chart + Indicators</a>
          <a href="#replay">Replay</a>
          <a href="#behavior">Pattern Memory</a>
          <button onClick={() => window.location.reload()}>Refresh Evidence</button>
        </div>
        {health?.persistent_banner_required && (
          <div className="list-row single"><span>Jarvis health is {health.overall_health}. The room remains safe and routing stays blocked.</span></div>
        )}
        <JarvisCandleChart room={room} decisionOutput={tradingDecisionOutput} />
      </Panel>

      <Panel title="Decision Ticket" span="side" tab="trade" badge={tradingDecisionOutput?.output_version ?? "v1.23"}>
        <div className="decision-stack">
          <Metric label="Action" value={finalAction} />
          <Metric label="Pattern" value={tradingDecisionOutput?.pattern_now?.candle_pattern ?? decision?.scenario_label ?? "pending"} />
          <Metric label="Bias" value={decision?.scenario_bias ?? tradingDecisionOutput?.pattern_now?.structure_read ?? "pending"} />
          <Metric label="R:R" value={String(decision?.risk_reward ?? tradingDecisionOutput?.trade_plan?.risk_reward ?? "pending")} />
          <Metric label="Confidence Cap" value={`${decision?.confidence_cap_pct ?? tradingDecisionOutput?.confidence?.confidence_cap_pct ?? 0}%`} />
          <Metric label="OpenAlgo" value={paperReadySafetyAudit?.go_no_go?.openalgo_paper_inspection ?? "NO_GO"} />
        </div>
        <div className="decision-note">
          {decision?.entry_condition ?? tradingDecisionOutput?.reason ?? "Waiting for verified evidence. No trading action is possible from this screen."}
        </div>
        <div className="trade-action-row vertical">
          <a href="#research">Open Research Screen</a>
          <a href="#replay">Open Replay Screen</a>
          <a href="#implementation">Open Build Map</a>
        </div>
      </Panel>

      <Panel title="Stock-App Chart, Indicators, Replay, Signals" span="full" tab="trade" badge="original chart engine">
        <div className="stock-app-shell">
          <div className="stock-app-toolbar">
            <span>Symbol {decodeURIComponent(chartSymbol)} | Timeframe {decodeURIComponent(chartTimeframe)}</span>
            <a href={stockAppFullUrl} target="_blank" rel="noreferrer">Open Full Chart</a>
            <a href={`${stockAppFullUrl}#research`} target="_blank" rel="noreferrer">Open Research</a>
            <a href={`${stockAppFullUrl}#backtest`} target="_blank" rel="noreferrer">Open Backtest</a>
            <button onClick={() => setStockChartReloadKey((value) => value + 1)}>Reload Chart</button>
          </div>
          <iframe
            key={stockChartReloadKey}
            className="stock-app-chart-frame"
            src={stockAppChartUrl}
            title="Stock-app chart with indicators, replay, signals, ML overlays, and maximize controls"
          />
          <div className="stock-app-footnote">
            This panel runs the original stock-app chart terminal. Use its built-in indicator button, replay bar, signal panels, and maximize/minimize controls inside the chart.
          </div>
        </div>
      </Panel>

      <Panel title="9-Candle Hybrid Intelligence" span="wide" tab="trade" badge={nineCandleHybrid?.decision ?? "WAIT"}>
        <div className="dna-grid">
          <Metric label="Decision" value={nineCandleHybrid?.decision ?? "WAIT"} />
          <Metric label="Features" value={String(nineCandleHybrid?.feature_manifest?.feature_count ?? 0)} />
          <Metric label="Manifest" value={String(nineCandleHybrid?.feature_manifest?.feature_manifest_version ?? "pending")} />
          <Metric label="Total Matches" value={String(nineCandleHybrid?.memory?.total_matches ?? 0)} />
          <Metric label="Winner-Like" value={String(nineCandleHybrid?.memory?.winner_like_matches ?? 0)} />
          <Metric label="Failure-Like" value={String(nineCandleHybrid?.memory?.failure_like_matches ?? 0)} />
          <Metric label="Winner Similarity" value={String(nineCandleHybrid?.memory?.winner_similarity ?? "pending")} />
          <Metric label="Failure Similarity" value={String(nineCandleHybrid?.memory?.failure_similarity ?? "pending")} />
          <Metric label="Target First" value={`${Math.round(Number(nineCandleHybrid?.model?.calibrated_target_prob ?? 0) * 100)}%`} />
          <Metric label="Stop First" value={`${Math.round(Number(nineCandleHybrid?.model?.calibrated_stop_prob ?? 0) * 100)}%`} />
          <Metric label="Fakeout Risk" value={`${Math.round(Number(nineCandleHybrid?.model?.calibrated_fakeout_prob ?? 0) * 100)}%`} />
          <Metric label="Expected R Cost" value={String(nineCandleHybrid?.model?.expected_r_after_cost ?? "pending")} />
          <Metric label="Model" value={String(nineCandleHybrid?.model?.model_version ?? "pending")} />
          <Metric label="Probability Usable" value={nineCandleHybrid?.model?.usable_for_probability ? "yes" : "no"} />
          <Metric label="Evidence" value={nineCandleHybrid?.trust?.evidence_quality ?? "pending"} />
          <Metric label="Drift" value={nineCandleHybrid?.trust?.drift_status ?? "pending"} />
          <Metric label="HTF" value={nineCandleHybrid?.trust?.htf_status ?? "pending"} />
          <Metric label="Routing" value={nineCandleHybrid?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <p>{nineCandleHybrid?.final_reason ?? "9-candle hybrid intelligence is loading. It remains research-only and cannot execute orders."}</p>
        <b>Evidence Source Check</b>
        <div className="dna-grid">
          <Metric label="Path Matches" value={String(nineCandlePathAnalogs?.total_matches ?? nineCandleHybrid?.memory?.total_matches ?? 0)} />
          <Metric label="Winner / Failure" value={`${nineCandlePathAnalogs?.winner_like_matches ?? 0} / ${nineCandlePathAnalogs?.failure_like_matches ?? 0}`} />
          <Metric label="Temporal Diversity" value={String(nineCandlePathAnalogs?.temporal_diversity_score ?? "pending")} />
          <Metric label="Vector Audit" value={nineCandleVectorAudit?.wait_required ? "WAIT" : "PASS"} />
          <Metric label="Vector Range" value={nineCandleVectorAudit?.normalized_range_pass ? "pass" : "pending"} />
          <Metric label="Manifest Integrity" value={nineCandleFeatureManifestIntegrity?.wait_required ? "WAIT" : "PASS"} />
          <Metric label="Norm Policies" value={String(nineCandleFeatureManifestIntegrity?.normalization_methods?.length ?? 0)} />
          <Metric label="Missing Mask" value={`${nineCandleVectorAudit?.missing_mask_count ?? 0}/${nineCandleVectorAudit?.feature_value_count ?? 0}`} />
          <Metric label="Indicator Promotion" value={`${nineCandleIndicatorPromotion?.explanation_only_count ?? 0} explain / ${nineCandleIndicatorPromotion?.probability_eligible_count ?? 0} prob`} />
          <Metric label="Indicator Masked" value={`${nineCandleIndicatorPromotion?.masked_count ?? 0}/${nineCandleIndicatorPromotion?.total_indicators ?? 0}`} />
          <Metric label="Runtime Scope" value={nineCandleIndicatorRuntime?.runtime_state ?? "pending"} />
          <Metric label="Level Runtime" value={`${nineCandleIndicatorRuntime?.level_runtime_selected_count ?? nineCandleIndicatorRuntime?.selected_indicator_count ?? 0} indicators`} />
          <Metric label="9C Vector Runtime" value={`${nineCandleIndicatorRuntime?.vector_promoted_indicator_count ?? nineCandleVectorAudit?.promoted_runtime_indicator_count ?? 0} promoted`} />
          <Metric label="Vector Only" value={`${nineCandleIndicatorRuntime?.vector_promoted_not_level_selected_count ?? 0} indicators`} />
          <Metric label="PTA Probe" value={`${nineCandleIndicatorRuntime?.pta_marker_output_count ?? 0}/${nineCandleIndicatorRuntime?.pta_marker_selected_count ?? 0}`} />
          <Metric label="Runtime Cache" value={`${nineCandleIndicatorRuntime?.indicator_cache_hit_count ?? 0} hit / ${nineCandleIndicatorRuntime?.indicator_cache_miss_count ?? 0} miss`} />
          <Metric label="Slow Runtime" value={`${nineCandleIndicatorRuntime?.slow_indicator_count ?? 0} indicators`} />
          <Metric label="Runtime Trading" value={nineCandleIndicatorRuntime?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Saved 9C Setups" value={`${nineCandleSetupMemory?.setup_count ?? 0} saved / ${nineCandleSetupMemory?.pending_setup_count ?? 0} pending`} />
          <Metric label="Outcome Labels" value={String(nineCandleSetupMemory?.label_count ?? 0)} />
          <Metric label="Feature Order" value={nineCandleVectorAudit?.feature_order_pass ? "pass" : "pending"} />
          <Metric label="OOD Gate" value={String(nineCandleOodStatus?.gate?.status ?? "pending").toUpperCase()} />
          <Metric label="Nearest Distance" value={String(nineCandleOodStatus?.nearest_distance ?? "pending")} />
          <Metric label="KNN p95" value={String(nineCandleOodStatus?.knn_distance_95th_percentile ?? "pending")} />
          <Metric label="Primary Hypothesis" value={nineCandleHypotheses?.primary_hypothesis?.id ?? "pending"} />
          <Metric label="Hypothesis Prob" value={`${Math.round(Number(nineCandleHypotheses?.primary_hypothesis?.raw_probability ?? 0) * 100)}%`} />
          <Metric label="Calibration Samples" value={String(nineCandlePromotionGuard?.calibration_sample_count ?? calibrationSampleCount)} />
          <Metric label="Promotion" value={nineCandlePromotionGuard?.promotion_allowed ? "allowed" : "blocked"} />
        </div>
        <div className="capability-table compact">
          {(nineCandlePathAnalogs?.top_matches ?? []).slice(0, 5).map((match: any) => (
            <div key={match.window_id}>
              <b>{match.window_id}</b>
              <span>{match.outcome_label} | sim:{Number(match.similarity_score ?? 0).toFixed(3)} | recency:{Number(match.recency_weight ?? 0).toFixed(2)}</span>
              <small>horizon:{match.horizon ?? "pending"} | week:{match.week_id ?? "pending"} | manifest:{nineCandlePathAnalogs?.feature_manifest_version ?? "pending"}</small>
            </div>
          ))}
          {(nineCandleHypotheses?.hypotheses ?? []).slice(0, 3).map((hypothesis: any) => (
            <div key={hypothesis.id}>
              <b>{hypothesis.id} / {hypothesis.direction}</b>
              <span>rule:{Number(hypothesis.rule_score ?? 0).toFixed(3)} prob:{Number(hypothesis.raw_probability ?? 0).toFixed(3)}</span>
              <small>invalid:{hypothesis.invalidation_level} confirm:{hypothesis.confirmation_trigger}</small>
            </div>
          ))}
          {(nineCandlePromotionGuard?.block_reasons ?? []).map((reason: string) => (
            <div key={reason}>
              <b>Promotion Block</b>
              <span>{reason}</span>
              <small>Kronos/AI/model output remains research-only until promotion gates pass.</small>
            </div>
          ))}
          {nineCandleIndicatorRuntime && (
            <div>
              <b>Runtime Scope</b>
              <span>
                level:{nineCandleIndicatorRuntime.level_runtime_selected_count ?? nineCandleIndicatorRuntime.selected_indicator_count ?? 0}
                {" | "}
                vector:{nineCandleIndicatorRuntime.vector_promoted_indicator_count ?? 0}
                {" | "}
                PTA:{nineCandleIndicatorRuntime.pta_marker_output_count ?? 0}/{nineCandleIndicatorRuntime.pta_marker_selected_count ?? 0}
                {" | "}
                cache:{nineCandleIndicatorRuntime.indicator_cache_hit_count ?? 0}/{(nineCandleIndicatorRuntime.indicator_cache_hit_count ?? 0) + (nineCandleIndicatorRuntime.indicator_cache_miss_count ?? 0)}
                {" | "}
                slow:{nineCandleIndicatorRuntime.slow_indicator_count ?? 0}
              </span>
              <small>{(nineCandleIndicatorRuntime.runtime_scope_notes ?? []).join(" ") || "Runtime scope is loading."}</small>
            </div>
          )}
          {(nineCandleIndicatorRuntime?.slow_indicator_ids ?? []).slice(0, 6).map((indicatorId: string) => (
            <div key={`slow-runtime-${indicatorId}`}>
              <b>{indicatorId}</b>
              <span>slow runtime warning</span>
              <small>Displayed for evidence visibility only; slow indicators cannot unlock probability or order routing.</small>
            </div>
          ))}
          {(nineCandleIndicatorRuntime?.vector_promoted_not_level_selected_ids ?? []).slice(0, 8).map((indicatorId: string) => (
            <div key={`vector-only-${indicatorId}`}>
              <b>{indicatorId}</b>
              <span>9C vector promoted, not a level-overlay runtime source</span>
              <small>Used for last-9 indicator sequence visibility only; probability and order routing remain blocked.</small>
            </div>
          ))}
          {(nineCandleIndicatorPromotion?.promotion_rows ?? []).filter((row: any) => row.promoted_for_runtime).slice(0, 8).map((row: any) => (
            <div key={`indicator-promotion-${row.indicator_id}`}>
              <b>{row.indicator_id}</b>
              <span>{row.current_state} | {row.runtime_status}</span>
              <small>{(row.blocking_reasons ?? []).slice(0, 2).join(", ") || "no blocker"}</small>
            </div>
          ))}
        </div>
        <div className="capability-table compact">
          {(nineCandleHybrid?.hybrid_decision?.safety_gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}: {String(gate.status).toUpperCase()}</b>
              <span>{gate.name}</span>
              <small>{gate.evidence}</small>
            </div>
          ))}
        </div>
        <b>Indicator Drilldown</b>
        <div className="capability-table compact">
          {(nineCandleHybrid?.indicator_drilldown ?? []).slice(0, 18).map((row: any) => (
            <div key={row.indicator_id}>
              <b>{row.indicator_id}</b>
              <span>W:{row.matched_winner_count} F:{row.matched_failure_count} align:{Math.round(Number(row.current_alignment ?? 0) * 100)}%</span>
              <small>{(row.last_9_signals ?? []).join(" -> ")} | {row.historical_effect}{row.missing_reason ? ` | ${row.missing_reason}` : ""}</small>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Indicator Reliability Drilldown v1.83" span="wide" tab="trade" badge={indicatorReliability?.reliability_state ?? "history"}>
        <div className="dna-grid">
          <Metric label="Indicator" value={indicatorReliability?.indicator_id ?? "si_macd_ta"} />
          <Metric label="Purpose" value={indicatorReliability?.purpose ?? "pending"} />
          <Metric label="Category" value={indicatorReliability?.category ?? "pending"} />
          <Metric label="Timeframe" value={indicatorReliability?.timeframe ?? "1m"} />
          <Metric label="History Source" value={indicatorReliability?.history_source ?? "pending"} />
          <Metric label="Persisted Rows" value={String(indicatorReliability?.persisted_history_count ?? indicatorHistory?.record_count ?? 0)} />
          <Metric label="Counted Samples" value={String(indicatorReliability?.sample_count ?? indicatorHistory?.counted_record_count ?? 0)} />
          <Metric label="Minimum Pass" value={indicatorReliability?.minimum_sample_pass ? "pass" : "low"} />
          <Metric label="Success" value={`${Math.round(Number(indicatorReliability?.bayesian_success_rate ?? 0) * 100)}%`} />
          <Metric label="Failure" value={`${Math.round(Number(indicatorReliability?.bayesian_failure_rate ?? 0) * 100)}%`} />
          <Metric label="Delay Bars" value={String(indicatorReliability?.confirmation_delay_bars ?? "pending")} />
          <Metric label="Lag Weight" value={String(indicatorReliability?.lag_weight ?? "pending")} />
          <Metric label="Vote Multiplier" value={String(indicatorReliability?.reliability_multiplier_for_lag_vote ?? "pending")} />
          <Metric label="Fixture Fallback" value={indicatorReliability?.fixture_fallback_used ? "yes" : "no"} />
          <Metric label="Probability" value={indicatorReliability?.used_for_probability ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={indicatorReliability?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <p>{indicatorReliabilityDrilldown?.trader_summary ?? "Indicator reliability history is loading. It can reduce confidence, but cannot approve trades."}</p>
        <div className="actions compact-actions">
          <button
            onClick={async () => {
              await api.indicatorSignalHistoryIngestCurrent();
              await onRefresh();
            }}
          >
            Ingest Current Signals
          </button>
          <small>v1.84 writes current closed-candle signals as pending history only; future outcome labels are not guessed.</small>
        </div>
        <div className="capability-table compact">
          {(indicatorHistory?.records ?? []).slice(0, 8).map((record: any) => (
            <div key={record.history_id}>
              <b>{record.indicator_id} / {record.signal_direction}</b>
              <span>{record.label?.outcome_label ?? "pending"} | counted:{record.counted_in_reliability ? "yes" : "no"} | strength:{record.signal_strength ?? 0}</span>
              <small>{record.session_phase} / {record.regime_id} / {new Date(Number(record.signal_time_ns ?? 0) / 1_000_000).toLocaleString()}</small>
            </div>
          ))}
          {(!indicatorHistory?.records || indicatorHistory.records.length === 0) && (
            <div>
              <b>No persisted labels yet</b>
              <span>Fixture fallback remains active</span>
              <small>v1.83 storage is ready; real rows appear here after save-history records are written.</small>
            </div>
          )}
          {(indicatorReliability?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}: {gate.passed ? "PASS" : "BLOCK"}</b>
              <span>{gate.name}</span>
              <small>{gate.evidence}</small>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="TV-PROD-RED-001 Manipulated-Wick Safety Proof" span="wide" tab="evidence" category="governance" badge={hasTvProdRed001 ? (tvProdRed001?.passed ? "red-team pass" : "release blocked") : "loading"}>
        <div className="dna-grid">
          <Metric label="Scenario" value={tvProdRed001?.scenario ?? "2.4x ATR manipulated-wick day"} />
          <Metric label="Result" value={hasTvProdRed001 ? (tvProdRed001?.passed ? "PASS" : "BLOCK") : "pending"} />
          <Metric label="Decision" value={tvProdRed001?.decision ?? "WAIT"} />
          <Metric label="Volatility OOD" value={tvProdRed001?.volatility_status?.volatility_ood ? "true" : "pending"} />
          <Metric label="Raw Matches" value={String(tvProdRed001?.raw_match_count ?? 0)} />
          <Metric label="After Vol Bucket" value={String(tvProdRed001?.matched_after_vol_bucketing ?? 0)} />
          <Metric label="Continuation Boost" value={String(tvProdRed001?.arbiter?.continuation_boost ?? "pending")} />
          <Metric label="Cache" value={tvProdRed001?.cache_status ?? "pending"} />
          <Metric label="Reference Only" value={tvProdRed001?.cache_reference_only ? "yes" : "pending"} />
          <Metric label="Paper Candidate" value={tvProdRed001?.paper_candidate_allowed ? "unsafe" : "blocked"} />
          <Metric label="Trade Allowed" value={tvProdRed001?.trade_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={tvProdRed001?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live Trading" value={hasTvProdRed001 && tvProdRed001?.live_trading_blocked === false ? "unsafe" : "blocked"} />
          <Metric label="Release" value={hasTvProdRed001 ? (tvProdRed001?.release_blocking ? "blocked" : "gate clear") : "pending"} />
        </div>
        <p>
          This panel displays the backend red-team proof for the manipulated-wick failure mode. It is release evidence only:
          it cannot create trades, promote confidence, or bypass WAIT-first behavior.
        </p>
        <div className="capability-table compact">
          {(tvProdRed001?.checks ?? []).map((check: any) => (
            <div key={check.check_id}>
              <b>{check.check_id}</b>
              <span>{check.passed ? "pass" : "fail"}</span>
              <small>{check.evidence}</small>
            </div>
          ))}
        </div>
        <div className="capability-table compact">
          <div>
            <b>Arbiter Flags</b>
            <span>{(tvProdRed001?.arbiter?.consulted_flags ?? []).join(", ") || "pending"}</span>
            <small>Manipulated-looking evidence must be consulted before analog confidence is trusted.</small>
          </div>
          <div>
            <b>Volatility Bucket</b>
            <span>{tvProdRed001?.volatility_status?.volatility_bucket ?? "pending"}</span>
            <small>Threshold source: {tvProdRed001?.volatility_status?.threshold_source ?? "pending"}</small>
          </div>
        </div>
      </Panel>

      <Panel title="Indicator Result Cache" span="wide" tab="evidence" category="infra" badge={indicatorCacheStatus?.cache_status ?? "miss"}>
        <div className="dna-grid">
          <Metric label="Module" value={indicatorCacheStatus?.cache_version ?? "pending"} />
          <Metric label="Schema" value={indicatorCacheStatus?.cache_schema_version ?? "indicator-result-cache.v1"} />
          <Metric label="Symbol" value={indicatorCacheStatus?.symbol ?? rawChartSymbol} />
          <Metric label="Timeframe" value={indicatorCacheStatus?.timeframe ?? String(room?.timeframe ?? "1m")} />
          <Metric label="Stored" value={String(indicatorCacheStatus?.stored_count ?? 0)} />
          <Metric label="Verified" value={String(indicatorCacheStatus?.verified_count ?? 0)} />
          <Metric label="Failed" value={String(indicatorCacheStatus?.failed_count ?? 0)} />
          <Metric label="Slow Saved" value={String(indicatorCacheStatus?.slow_indicator_count ?? 0)} />
          <Metric label="Size" value={`${indicatorCacheStatus?.cache_size_bytes ?? 0} bytes`} />
          <Metric label="Source Hash" value={String(indicatorCacheStatus?.source_snapshot_hash ?? "pending").slice(0, 12)} />
          <Metric label="Snapshot" value={String(indicatorCacheStatus?.source_snapshot_id ?? "pending").slice(0, 12)} />
          <Metric label="Registry" value={String(indicatorCacheStatus?.indicator_registry_version ?? "pending")} />
          <Metric label="Manifest" value={String(indicatorCacheStatus?.feature_manifest_version ?? "pending")} />
          <Metric label="Promoted Hash" value={String(indicatorCacheStatus?.promoted_indicator_hash ?? "pending").slice(0, 12)} />
          <Metric label="Probability" value={indicatorCacheStatus?.used_for_probability ? "unsafe" : "blocked"} />
          <Metric label="Trading" value={indicatorCacheStatus?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={indicatorCacheStatus?.live_trading_blocked === false ? "unsafe" : "blocked"} />
          <Metric label="Closed Candle" value={indicatorCacheStatus?.closed_candle_only ? "yes" : "pending"} />
        </div>
        <div className="trade-action-row">
          <button type="button" onClick={() => onRefresh()} disabled={indicatorCacheSaving || Boolean(indicatorCacheDeleting)}>
            Reload Status
          </button>
          <button type="button" onClick={() => saveIndicatorCache(false)} disabled={indicatorCacheSaving || Boolean(indicatorCacheDeleting)}>
            {indicatorCacheSaving ? "Saving..." : "Save Indicator Results"}
          </button>
          <button type="button" onClick={() => saveIndicatorCache(true)} disabled={indicatorCacheSaving || Boolean(indicatorCacheDeleting)}>
            Force Recompute
          </button>
          <button
            type="button"
            onClick={() => clearIndicatorCacheCandidate?.cache_id && deleteIndicatorCache(clearIndicatorCacheCandidate.cache_id)}
            disabled={!clearIndicatorCacheCandidate?.cache_id || indicatorCacheSaving || Boolean(indicatorCacheDeleting)}
          >
            {failedIndicatorCacheRow ? "Clear First Failed" : "Clear First Row"}
          </button>
          <a href="#research">Open Research</a>
        </div>
        <p>
          Persistent cache is for speed and audit only. It stores exact indicator outputs by symbol, timeframe,
          source snapshot hash, registry version, manifest version, and promoted indicator hash. It cannot enable
          probability, paper-candidate promotion, or order routing.
        </p>
        {indicatorCacheSaveResult && (
          <div className="dna-grid">
            <Metric label="Last Save" value={indicatorCacheSaveResult.cache_status ?? "pending"} />
            <Metric label="Saved" value={String(indicatorCacheSaveResult.saved_count ?? 0)} />
            <Metric label="Reused" value={String(indicatorCacheSaveResult.reused_count ?? 0)} />
            <Metric label="Hit Rate" value={String(indicatorCacheSaveResult.cache_hit_rate ?? 0)} />
            <Metric label="Quarantine" value={indicatorCacheSaveResult.quarantine_status ?? "pending"} />
            <Metric label="Reference Only" value={indicatorCacheSaveResult.reference_only ? "yes" : "pending"} />
          </div>
        )}
        {indicatorCacheDeleteResult && (
          <div className="list-row single">
            <span>Deleted cache row {String(indicatorCacheDeleteResult.cache_id ?? "pending").slice(0, 18)}: {indicatorCacheDeleteResult.deleted ? "yes" : "not found"}</span>
          </div>
        )}
        {indicatorCacheError && (
          <div className="list-row single warning">
            <span>{indicatorCacheError}</span>
          </div>
        )}
        <div className="capability-table compact">
          {indicatorCacheRows.slice(0, 10).map((row: any) => (
            <div key={row.cache_id}>
              <b>{row.indicator_id}</b>
              <span>
                {row.runtime_status} | {row.cache_integrity_status ?? "pending"} | output:{row.output_present ? "yes" : "no"}
                {" | "}
                {row.latency_ms ?? 0}ms
              </span>
              <small>
                {String(row.artifact_sha256 ?? "").slice(0, 16)} | {String(row.cache_id ?? "").slice(0, 18)} | {row.artifact_uri}
              </small>
              <button
                type="button"
                className="mini-danger"
                onClick={() => deleteIndicatorCache(row.cache_id)}
                disabled={!row.cache_id || indicatorCacheSaving || indicatorCacheDeleting === row.cache_id}
              >
                {indicatorCacheDeleting === row.cache_id ? "Clearing..." : "Clear Row"}
              </button>
            </div>
          ))}
          {indicatorCacheRows.length === 0 && (
            <div>
              <b>No Cache Rows</b>
              <span>Save indicator results to create a reusable reference cache.</span>
              <small>The cache remains speed/audit only and cannot approve trades.</small>
            </div>
          )}
        </div>
      </Panel>

      <Panel title="Trading Decision Output" span="wide" tab="trade" badge={tradingDecisionOutput?.output_version ?? "v1.23"}>
        <div className="dna-grid">
          <Metric label="State" value={tradingDecisionOutput?.output_state ?? "pending"} />
          <Metric label="Action" value={tradingDecisionOutput?.trade_plan?.display_action ?? "WAIT"} />
          <Metric label="Pattern" value={tradingDecisionOutput?.pattern_now?.candle_pattern ?? "pending"} />
          <Metric label="Structure" value={tradingDecisionOutput?.pattern_now?.scenario_label ?? "pending"} />
          <Metric label="VWAP" value={tradingDecisionOutput?.pattern_now?.vwap_position ?? "pending"} />
          <Metric label="RSI" value={String(tradingDecisionOutput?.pattern_now?.rsi14 ?? "pending")} />
          <Metric label="Entry Zone" value={(tradingDecisionOutput?.trade_plan?.entry_zone ?? []).join(" - ") || "wait"} />
          <Metric label="Stop" value={String(tradingDecisionOutput?.trade_plan?.stop_loss ?? "pending")} />
          <Metric label="Target" value={String(tradingDecisionOutput?.trade_plan?.target ?? "pending")} />
          <Metric label="Invalidation" value={String(tradingDecisionOutput?.trade_plan?.invalidation_level ?? "pending")} />
          <Metric label="Similar Cases" value={String(tradingDecisionOutput?.similar_history_cases?.length ?? 0)} />
          <Metric label="Trust" value={tradingDecisionOutput?.quality_and_safety?.decision_trust_allowed ? "allowed" : "blocked"} />
          <Metric label="Routing" value={tradingDecisionOutput?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <p>{tradingDecisionOutput?.headline ?? "Trading decision output is loading. No trade action is possible from this panel."}</p>
        <div className="list-row">
          <b>Chart Focus</b>
          <span>{tradingDecisionOutput?.chart_screen_focus?.display_bars_available ?? 0} bars | close {String(tradingDecisionOutput?.chart_screen_focus?.latest_close ?? "pending")}</span>
          <small>Overlay entry/SL/target/invalidation on the chart screen. This is a research view only.</small>
        </div>
        <div className="list-row">
          <b>Candle Read</b>
          <span>{tradingDecisionOutput?.pattern_now?.wick_body_read ?? "pending"}</span>
          <small>{tradingDecisionOutput?.pattern_now?.structure_read ?? "Waiting for pattern structure."}</small>
        </div>
        <div className="list-row">
          <b>Sequential Indicator Story</b>
          <span>{(tradingDecisionOutput?.sequential_signal_story?.current_sequence ?? []).join(" -> ") || "pending"}</span>
          <small>{tradingDecisionOutput?.sequential_signal_story?.interpretation ?? "No sequence story yet."}</small>
        </div>
        <b>Evidence Rows</b>
        <div className="capability-table compact">
          {(tradingDecisionOutput?.indicator_and_candle_evidence ?? []).map((row: any) => (
            <div key={row.row_id}>
              <b>{row.label}</b>
              <span>{String(row.state ?? "pending")}</span>
              <small>{row.interpretation ?? "research-only evidence"}</small>
            </div>
          ))}
        </div>
        <b>Similar Historical Cases</b>
        {(tradingDecisionOutput?.similar_history_cases ?? []).slice(0, 8).map((item: any, index: number) => (
          <div className="list-row" key={`${item.source}-${item.date}-${index}`}>
            <b>{item.date ?? "unknown date"} | {item.source}</b>
            <span>{item.similarity_score_pct ? `${item.similarity_score_pct}%` : item.outcome}</span>
            <small>{item.why_useful ?? "Similar evidence item."}</small>
          </div>
        ))}
        {(tradingDecisionOutput?.blocker_rows ?? []).slice(0, 8).map((item: any, index: number) => (
          <div className="list-row" key={`${item.source}-${index}`}>
            <b>{item.source}: {item.severity}</b>
            <span>{item.reason}</span>
            <small>{item.repair ?? "Manual review required."}</small>
          </div>
        ))}
        <p>{tradingDecisionOutput?.explain_like_trader ?? "Explain-like-trader output is loading."}</p>
        {(tradingDecisionOutput?.next_best_actions ?? []).map((item: string) => (
          <div className="list-row single" key={item}><span>NEXT: {item}</span></div>
        ))}
      </Panel>

      <Panel title="Chart Overlay QA" tab="evidence" category="governance" badge={chartOverlayQa?.qa_version ?? "v1.25"}>
        <Metric label="State" value={chartOverlayQa?.qa_state ?? "pending"} />
        <Metric label="Nonblank" value={chartOverlayQa?.chart_nonblank ? "yes" : "no"} />
        <Metric label="Bars" value={String(chartOverlayQa?.bar_count ?? 0)} />
        <Metric label="Similar Markers" value={String(chartOverlayQa?.similar_marker_count ?? 0)} />
        <Metric label="Blocker Chips" value={String(chartOverlayQa?.blocker_chip_count ?? 0)} />
        <Metric label="Routing" value={chartOverlayQa?.order_routing_enabled ? "unsafe" : "blocked"} />
        {(chartOverlayQa?.overlay_labels ?? []).map((label: any) => (
          <div className="list-row" key={label.label}>
            <b>{label.label}</b>
            <span>{Array.isArray(label.value) ? label.value.join(" - ") : String(label.value ?? "pending")}</span>
            <small>{label.visible ? "visible" : "missing"}</small>
          </div>
        ))}
        {(chartOverlayQa?.checks ?? []).map((check: any) => (
          <div className="list-row" key={check.check_id}>
            <b>{check.check_id}: {check.passed ? "PASS" : check.effect.toUpperCase()}</b>
            <span>{check.name}</span>
            <small>{check.reason}</small>
          </div>
        ))}
        <p>{chartOverlayQa?.operator_message ?? "Chart overlay QA is loading. Visual decision overlays remain research-only."}</p>
      </Panel>

      <Panel title="Evidence Assembly Latency Budget" span="wide" tab="evidence" category="infra" badge={evidenceLatencyBudget?.latency_budget_version ?? "v1.27"}>
        <div className="dna-grid">
          <Metric label="State" value={evidenceLatencyBudget?.budget_state ?? "pending"} />
          <Metric label="Total" value={`${Number(evidenceLatencyBudget?.total_latency_ms ?? 0).toFixed(1)} ms`} />
          <Metric label="Budget" value={`${Number(evidenceLatencyBudget?.total_budget_ms ?? 0).toFixed(0)} ms`} />
          <Metric label="Slow Stages" value={String(evidenceLatencyBudget?.slow_stage_count ?? 0)} />
          <Metric label="Cache" value={evidenceLatencyBudget?.cache_status ?? "checking"} />
          <Metric label="Fast Path Safe" value={evidenceLatencyBudget?.fast_path_safe ? "yes" : "checking"} />
          <Metric label="Routing" value={evidenceLatencyBudget?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        {(evidenceLatencyBudget?.stage_timings ?? []).slice(0, 12).map((stage: any) => (
          <div className="list-row" key={stage.stage}>
            <b>{stage.stage}</b>
            <span>{Number(stage.elapsed_ms ?? 0).toFixed(1)} / {Number(stage.budget_ms ?? 0).toFixed(0)} ms</span>
            <small>{stage.status}</small>
          </div>
        ))}
        {(evidenceLatencyBudget?.degradation_recommendations ?? []).slice(0, 4).map((item: any) => (
          <div className="list-row" key={`${item.stage}-${item.status}`}>
            <b>{item.stage}: {item.status}</b>
            <span>{item.recommendation}</span>
            <small>degrade to WAIT before any execution handoff</small>
          </div>
        ))}
        <p>{evidenceLatencyBudget?.operator_message ?? "Latency budget is loading. Slow evidence must reduce action, never increase it."}</p>
      </Panel>

      <Panel title="Realtime Freshness Gate" tab="trade" badge={realtimeFreshness?.freshness_version ?? "v1.29"}>
        <Metric label="State" value={realtimeFreshness?.freshness_state ?? "pending"} />
        <Metric label="Safe Action" value={realtimeFreshness?.safe_display_action ?? "WAIT"} />
        <Metric label="Trust Effect" value={realtimeFreshness?.trust_effect ?? "checking"} />
        <Metric label="Age" value={`${Number(realtimeFreshness?.cache_age_seconds ?? 0).toFixed(1)} s`} />
        <Metric label="Max Age" value={`${Number(realtimeFreshness?.max_age_seconds ?? 0).toFixed(0)} s`} />
        <Metric label="Force WAIT" value={realtimeFreshness?.force_wait ? "yes" : "no"} />
        {(realtimeFreshness?.checks ?? []).map((check: any) => (
          <div className="list-row" key={check.check_id}>
            <b>{check.check_id}: {check.passed ? "PASS" : check.effect.toUpperCase()}</b>
            <span>{check.name}</span>
            <small>{check.reason}</small>
          </div>
        ))}
        <p>{realtimeFreshness?.operator_message ?? "Realtime freshness gate is loading. Stale evidence must display WAIT."}</p>
      </Panel>

      <Panel title="Jarvis Evidence Cache Freshness" tab="evidence" category="infra" badge={evidenceCache?.cache_version ?? "v1.28"}>
        <Metric label="Status" value={evidenceCache?.cache_status ?? "pending"} />
        <Metric label="Fresh" value={evidenceCache?.cache_fresh ? "yes" : "checking"} />
        <Metric label="Age" value={`${Number(evidenceCache?.cache_age_seconds ?? 0).toFixed(1)} s`} />
        <Metric label="TTL" value={`${Number(evidenceCache?.cache_ttl_seconds ?? 0).toFixed(0)} s`} />
        <Metric label="Routing" value={evidenceCache?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="list-row single">
          <span>Cache key: {String(evidenceCache?.cache_key_hash ?? "pending").slice(0, 16)}</span>
        </div>
        <p>{evidenceCache?.operator_message ?? "Evidence cache is loading. Cached evidence remains research-only."}</p>
      </Panel>

      <Panel title="Jarvis Master Decision Panel" span="wide" tab="trade" badge={masterPanel?.final_action ?? "v1.03"}>
        <div className="dna-grid">
          <Metric label="State" value={masterPanel?.decision_state ?? "pending"} />
          <Metric label="Final Action" value={masterPanel?.final_action ?? "WAIT"} />
          <Metric label="Panel Hash" value={String(masterPanel?.panel_hash ?? "pending").slice(0, 12)} />
          <Metric label="Latest Close" value={String(masterPanel?.chart_decision_focus?.latest_close ?? "pending")} />
          <Metric label="Candle" value={masterPanel?.chart_decision_focus?.candle_pattern ?? "pending"} />
          <Metric label="VWAP" value={masterPanel?.chart_decision_focus?.vwap_position ?? "pending"} />
          <Metric label="Gemini Keys" value={`${masterPanel?.gemini_fallback_policy?.configured_key_slots ?? 0}/${masterPanel?.gemini_fallback_policy?.fallback_key_slots_supported ?? 5}`} />
          <Metric label="Routing" value={masterPanel?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <p>{masterPanel?.purpose ?? "One new Jarvis panel combines all decision evidence without changing older panels."}</p>
        <div className="capability-table compact">
          {(masterPanel?.evidence_stack ?? []).map((item: any) => (
            <div key={item.source}>
              <b>{item.source}</b>
              <span>{item.state}</span>
              <small>{(item.reasons ?? []).slice(0, 2).join(" | ") || "read-only evidence"}</small>
            </div>
          ))}
        </div>
        <b>Minimal New Safety Gate Chain</b>
        <div className="capability-table compact">
          {(masterPanel?.minimal_safety_gate_chain ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <div className="dna-grid">
          <Metric label="Entry" value={(masterPanel?.decision_guide?.entry_zone ?? []).join(" - ") || "wait"} />
          <Metric label="Stop" value={String(masterPanel?.decision_guide?.stop_loss ?? "pending")} />
          <Metric label="Target" value={String(masterPanel?.decision_guide?.target ?? "pending")} />
          <Metric label="Invalidation" value={String(masterPanel?.decision_guide?.invalidation_level ?? "pending")} />
          <Metric label="Backend Keys" value={masterPanel?.gemini_fallback_policy?.backend_only_keys ? "yes" : "no"} />
          <Metric label="Keys Exposed" value={masterPanel?.gemini_fallback_policy?.keys_exposed_to_frontend ? "unsafe" : "no"} />
        </div>
        {(masterPanel?.decision_guide?.wait_for ?? []).slice(0, 4).map((item: string) => (
          <div className="list-row single" key={`master-wait-${item}`}><span>WAIT: {item}</span></div>
        ))}
        {(masterPanel?.engine_agreement?.conflicts ?? []).slice(0, 4).map((item: string) => (
          <div className="list-row single" key={`master-conflict-${item}`}><span>CONFLICT: {item}</span></div>
        ))}
        <p>New panel only: {masterPanel?.integration_rule?.new_panel_only ? "active" : "pending"}. Existing Jarvis panels continue below for audit and drilldown.</p>
      </Panel>

      <Panel title="Decision Evidence Export" span="wide" tab="evidence" category="governance" badge={decisionEvidenceExport?.export_version ?? "v1.14"}>
        <div className="dna-grid">
          <Metric label="State" value={decisionEvidenceExport?.export_state ?? "pending"} />
          <Metric label="Packet" value={String(decisionEvidenceExport?.packet_id ?? "pending").slice(0, 12)} />
          <Metric label="Export Hash" value={String(decisionEvidenceExport?.export_hash ?? "pending").slice(0, 12)} />
          <Metric label="Sections" value={String(decisionEvidenceExport?.section_count ?? 0)} />
          <Metric label="Blocks" value={String(decisionEvidenceExport?.blocking_count ?? 0)} />
          <Metric label="Warnings" value={String(decisionEvidenceExport?.warning_count ?? 0)} />
          <Metric label="Review Only" value={decisionEvidenceExport?.review_use_only ? "yes" : "pending"} />
          <Metric label="Network" value={decisionEvidenceExport?.network_call_performed ? "unsafe" : "no call"} />
          <Metric label="Routing" value={decisionEvidenceExport?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={decisionEvidenceExport?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <p>{decisionEvidenceExport?.operator_message ?? "Decision evidence export is loading. No execution or external network call is possible."}</p>
        <div className="capability-table compact">
          {(decisionEvidenceExport?.evidence_sections ?? []).slice(0, 10).map((section: any) => (
            <div key={section.section_id}>
              <b>{section.name}</b>
              <span>{String(section.payload_hash ?? "").slice(0, 12)}</span>
              <small>{(section.citable_keys ?? []).join(", ")}</small>
            </div>
          ))}
        </div>
        {(decisionEvidenceExport?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <div className="list-row single"><span>{decisionEvidenceExport?.download_filename ?? "The review packet filename will appear after export generation."}</span></div>
      </Panel>

      <Panel title="Daily Verified Data Authority" tab="trade" badge={dailyVerifiedAuthority?.authority_version ?? "v1.15"}>
        <Metric label="State" value={dailyVerifiedAuthority?.authority_state ?? "pending"} />
        <Metric label="Daily" value={dailyVerifiedAuthority?.daily_available ? "available" : "missing"} />
        <Metric label="Weekly" value={dailyVerifiedAuthority?.weekly_available ? "available" : "missing"} />
        <Metric label="HTF Confirm" value={dailyVerifiedAuthority?.htf_confirmation_available ? "yes" : "no"} />
        <Metric label="Cap" value={`${dailyVerifiedAuthority?.decision_confidence_cap_pct ?? 0}%`} />
        <Metric label="Decision Trust" value={dailyVerifiedAuthority?.decision_trust_allowed ? "allowed" : "blocked"} />
        <Metric label="External Daily Claims" value={dailyVerifiedAuthority?.external_ai_daily_claims_allowed ? "allowed" : "blocked"} />
        <Metric label="Routing" value={dailyVerifiedAuthority?.order_routing_enabled ? "unsafe" : "blocked"} />
        {(dailyVerifiedAuthority?.timeframe_records ?? []).map((record: any) => (
          <div className="list-row" key={record.timeframe}>
            <b>{record.timeframe}: {record.available ? "available" : "missing"}</b>
            <span>{record.state}</span>
            <small>{record.source_key} | stale={String(record.stale)} | citable={String(record.citable)}</small>
          </div>
        ))}
        {(dailyVerifiedAuthority?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{dailyVerifiedAuthority?.operator_message ?? "Daily verified authority is loading. Daily/weekly claims are blocked until verified."}</p>
      </Panel>

      <Panel title="Indicator Combination Memory" tab="trade" badge={indicatorCombinationMemory?.memory_version ?? "v1.16"}>
        <Metric label="State" value={indicatorCombinationMemory?.memory_state ?? "pending"} />
        <Metric label="Matches" value={String(indicatorCombinationMemory?.historical_match_count ?? 0)} />
        <Metric label="Minimum" value={indicatorCombinationMemory?.minimum_sample_pass ? "pass" : "low"} />
        <Metric label="Evidence" value={indicatorCombinationMemory?.evidence_quality ?? "pending"} />
        <Metric label="Sequence" value={indicatorCombinationMemory?.non_same_candle_sequence_detected ? "non-same candle" : "pending"} />
        <Metric label="Continuation" value={`${indicatorCombinationMemory?.continuation_probability_pct ?? 0}%`} />
        <Metric label="Fakeout" value={`${indicatorCombinationMemory?.fakeout_probability_pct ?? 0}%`} />
        <Metric label="Routing" value={indicatorCombinationMemory?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="capability-table compact">
          {(indicatorCombinationMemory?.combination_rows ?? []).map((row: any) => (
            <div key={row.group}>
              <b>{row.group}</b>
              <span>{row.available ? "available" : "missing"}</span>
              <small>{Object.entries(row.current_values ?? {}).map(([key, value]) => `${key}:${String(value)}`).join(" | ")}</small>
            </div>
          ))}
        </div>
        <div className="list-row">
          <b>Ordered Sequence</b>
          <span>{(indicatorCombinationMemory?.sequence_memory?.ordered_indicators ?? []).join(" -> ") || "pending"}</span>
          <small>{(indicatorCombinationMemory?.sequence_memory?.candle_offsets ?? []).join(", ")} | {indicatorCombinationMemory?.sequence_memory?.interpretation ?? "No sequence interpretation yet."}</small>
        </div>
        {(indicatorCombinationMemory?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{indicatorCombinationMemory?.operator_message ?? "Indicator combination memory is loading. No trade authority is possible."}</p>
      </Panel>

      <Panel title="Candle Cause/Effect Memory" tab="trade" badge={candleCauseEffectMemory?.memory_version ?? "v1.17"}>
        <Metric label="State" value={candleCauseEffectMemory?.memory_state ?? "pending"} />
        <Metric label="Effect" value={candleCauseEffectMemory?.effect_label ?? "pending"} />
        <Metric label="Matches" value={String(candleCauseEffectMemory?.historical_match_count ?? 0)} />
        <Metric label="Minimum" value={candleCauseEffectMemory?.minimum_sample_pass ? "pass" : "low"} />
        <Metric label="Evidence" value={candleCauseEffectMemory?.evidence_quality ?? "pending"} />
        <Metric label="Continuation" value={`${candleCauseEffectMemory?.continuation_probability_pct ?? 0}%`} />
        <Metric label="Reversal" value={`${candleCauseEffectMemory?.reversal_probability_pct ?? 0}%`} />
        <Metric label="Fakeout" value={`${candleCauseEffectMemory?.fakeout_probability_pct ?? 0}%`} />
        <Metric label="Expected" value={candleCauseEffectMemory?.expected_next_effect ?? "pending"} />
        <Metric label="Routing" value={candleCauseEffectMemory?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="capability-table compact">
          <div>
            <b>Previous Candle</b>
            <span>{candleCauseEffectMemory?.previous_candle_anatomy?.direction ?? "pending"}</span>
            <small>
              body:{String(candleCauseEffectMemory?.previous_candle_anatomy?.body_pct ?? "n/a")} |
              upper:{String(candleCauseEffectMemory?.previous_candle_anatomy?.upper_wick_pct ?? "n/a")} |
              lower:{String(candleCauseEffectMemory?.previous_candle_anatomy?.lower_wick_pct ?? "n/a")}
            </small>
          </div>
          <div>
            <b>Current Candle</b>
            <span>{candleCauseEffectMemory?.current_candle_anatomy?.direction ?? "pending"}</span>
            <small>
              body:{String(candleCauseEffectMemory?.current_candle_anatomy?.body_pct ?? "n/a")} |
              upper:{String(candleCauseEffectMemory?.current_candle_anatomy?.upper_wick_pct ?? "n/a")} |
              lower:{String(candleCauseEffectMemory?.current_candle_anatomy?.lower_wick_pct ?? "n/a")}
            </small>
          </div>
          <div>
            <b>Deltas</b>
            <span>{candleCauseEffectMemory?.cause_effect_features?.direction_changed ? "direction changed" : "same direction"}</span>
            <small>
              body:{String(candleCauseEffectMemory?.cause_effect_features?.body_pct_delta ?? "n/a")} |
              upper:{String(candleCauseEffectMemory?.cause_effect_features?.upper_wick_pct_delta ?? "n/a")} |
              lower:{String(candleCauseEffectMemory?.cause_effect_features?.lower_wick_pct_delta ?? "n/a")}
            </small>
          </div>
        </div>
        <div className="list-row">
          <b>Best Analog Dates</b>
          <span>{(candleCauseEffectMemory?.best_matching_dates ?? []).slice(0, 5).join(", ") || "pending"}</span>
          <small>{candleCauseEffectMemory?.no_trade_reason ?? "Analog evidence is research-only and cannot approve a trade."}</small>
        </div>
        {(candleCauseEffectMemory?.analog_examples ?? []).slice(0, 4).map((analog: any) => (
          <div className="list-row" key={`${analog.historical_timestamp_ns}-${analog.outcome}`}>
            <b>{analog.historical_date}: {analog.outcome}</b>
            <span>{analog.similarity_score_pct}% similar</span>
            <small>{analog.previous_direction} {"->"} {analog.current_direction} {"->"} {analog.next_direction}</small>
          </div>
        ))}
        {(candleCauseEffectMemory?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{candleCauseEffectMemory?.operator_message ?? "Candle cause/effect memory is loading. No trade authority is possible."}</p>
      </Panel>

      <Panel title="Jarvis Unified Fusion Panel" span="wide" tab="trade" badge={fusion?.final_view ?? "v0.97"}>
        <div className="dna-grid">
          <Metric label="Room State" value={fusion?.room_state ?? "pending"} />
          <Metric label="Final View" value={fusion?.final_view ?? "WAIT"} />
          <Metric label="Fusion Hash" value={String(fusion?.fusion_hash ?? "pending").slice(0, 12)} />
          <Metric label="Latest Close" value={String(fusion?.chart_and_indicator_focus?.latest_close ?? "pending")} />
          <Metric label="Candle" value={fusion?.chart_and_indicator_focus?.candle_pattern ?? "pending"} />
          <Metric label="VWAP" value={fusion?.chart_and_indicator_focus?.vwap_position ?? "pending"} />
          <Metric label="RSI" value={String(fusion?.chart_and_indicator_focus?.rsi14 ?? "pending")} />
          <Metric label="Gemini Slots" value={`${fusion?.gemini_fallback?.configured_key_slots ?? 0}/${fusion?.gemini_fallback?.fallback_key_slots_supported ?? 5}`} />
        </div>
        <p>{fusion?.single_panel_purpose ?? "Combines all advisory evidence into one safe research view."}</p>
        <div className="capability-table compact">
          {(fusion?.engine_votes ?? []).map((vote: any) => (
            <div key={vote.engine}>
              <b>{vote.engine}</b>
              <span>{vote.action}</span>
              <small>{(vote.reasons ?? []).slice(0, 2).join(" | ") || "read-only evidence"}</small>
            </div>
          ))}
        </div>
        <b>New Safety Gate Chain</b>
        <div className="capability-table compact">
          {(fusion?.safety_gate_chain ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <div className="dna-grid">
          <Metric label="Entry" value={(fusion?.decision_guide?.entry_zone ?? []).join(" - ") || "wait"} />
          <Metric label="Stop" value={String(fusion?.decision_guide?.stop_loss ?? "pending")} />
          <Metric label="Target" value={String(fusion?.decision_guide?.target ?? "pending")} />
          <Metric label="Invalidation" value={String(fusion?.decision_guide?.invalidation_level ?? "pending")} />
          <Metric label="MTF Align" value={`${Math.round((fusion?.evidence_quality?.multi_timeframe_alignment_score ?? 0) * 100)}%`} />
          <Metric label="Similar" value={`${fusion?.evidence_quality?.similar_matches ?? 0}/${fusion?.evidence_quality?.similar_total_found ?? 0}`} />
        </div>
        {(fusion?.decision_guide?.wait_for ?? []).slice(0, 4).map((item: string) => (
          <div className="list-row single" key={`wait-${item}`}><span>WAIT: {item}</span></div>
        ))}
        {(fusion?.agreement?.conflicts ?? []).slice(0, 4).map((item: string) => (
          <div className="list-row single" key={`conflict-${item}`}><span>CONFLICT: {item}</span></div>
        ))}
        <p>New-panel-only mode is {fusion?.ui_rule?.new_panel_only ? "active" : "pending"}; old Jarvis panels remain preserved below.</p>
      </Panel>

      <Panel title="Jarvis Replay Determinism" span="wide" tab="evidence" category="governance" badge={replayDeterminism?.deterministic ? "v0.98 stable" : "v0.98 check"}>
        <div className="dna-grid">
          <Metric label="Deterministic" value={replayDeterminism?.deterministic ? "yes" : "pending/no"} />
          <Metric label="Hash Match" value={replayDeterminism?.hash_match ? "yes" : "no"} />
          <Metric label="First Hash" value={String(replayDeterminism?.first_hash ?? "pending").slice(0, 12)} />
          <Metric label="Second Hash" value={String(replayDeterminism?.second_hash ?? "pending").slice(0, 12)} />
          <Metric label="Sections" value={String(replayDeterminism?.canonical_section_count ?? 0)} />
          <Metric label="Ignored Volatile" value={String(replayDeterminism?.ignored_volatile_fields?.length ?? 0)} />
          <Metric label="Routing" value={replayDeterminism?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live Trading" value={replayDeterminism?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <p>v0.98 hashes only decision-relevant chart, indicator, similar-history, decision, safety, and arbiter evidence. Runtime timestamps, packet IDs, audit IDs, and usefulness records are ignored.</p>
        <div className="capability-table compact">
          {Object.entries(replayDeterminism?.replay_scope ?? {}).map(([key, value]) => (
            <div key={key}>
              <b>{key}</b>
              <span>{value ? "yes" : "no"}</span>
              <small>Replay scope</small>
            </div>
          ))}
        </div>
        {(replayDeterminism?.diff_paths ?? []).slice(0, 6).map((path: string) => (
          <div className="list-row single" key={path}><span>DIFF: {path}</span></div>
        ))}
        {(!replayDeterminism?.diff_paths || replayDeterminism.diff_paths.length === 0) && (
          <div className="list-row single"><span>No decision-relevant replay differences detected.</span></div>
        )}
      </Panel>

      <Panel title="Production Readiness Blockers" span="wide" tab="vault" category="governance" badge={productionBlockers?.overall_status ?? "v0.99"}>
        <div className="dna-grid">
          <Metric label="Overall" value={productionBlockers?.overall_status ?? "pending"} />
          <Metric label="Research" value={productionBlockers?.stage_statuses?.research_stack?.status ?? "pending"} />
          <Metric label="Paper" value={productionBlockers?.stage_statuses?.paper_mode?.status ?? "pending"} />
          <Metric label="OpenAlgo" value={productionBlockers?.stage_statuses?.openalgo_handoff?.status ?? "pending"} />
          <Metric label="Live" value={productionBlockers?.stage_statuses?.live_trading?.status ?? "blocked"} />
          <Metric label="Blockers" value={String(productionBlockers?.blocker_count ?? 0)} />
          <Metric label="Warnings" value={String(productionBlockers?.warn_count ?? 0)} />
          <Metric label="Hash" value={String(productionBlockers?.report_hash ?? "pending").slice(0, 12)} />
        </div>
        <div className="capability-table compact">
          {(productionBlockers?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.status}</span>
              <small>{gate.name} / {gate.stage}</small>
            </div>
          ))}
        </div>
        {(productionBlockers?.next_actions ?? []).slice(0, 6).map((action: string) => (
          <div className="list-row single" key={action}><span>{action}</span></div>
        ))}
        <p>
          Scope: research stack candidate is {productionBlockers?.production_scope?.research_stack_candidate ? "true" : "false"},
          paper candidate is {productionBlockers?.production_scope?.paper_mode_candidate ? "true" : "false"},
          live candidate is {productionBlockers?.production_scope?.live_mode_candidate ? "true" : "false"}.
          OpenAlgo remains {productionBlockers?.openalgo_handoff?.allowed_scope ?? "dry-run/research only"}.
        </p>
      </Panel>

      <Panel title="Blocker Resolution Pack" span="wide" tab="vault" category="governance" badge={blockerResolution?.overall_status ?? "v1.00"}>
        <div className="dna-grid">
          <Metric label="Status" value={blockerResolution?.overall_status ?? "pending"} />
          <Metric label="Remediations" value={String(blockerResolution?.remediation_count ?? 0)} />
          <Metric label="Must Fix" value={String(blockerResolution?.must_fix_count ?? 0)} />
          <Metric label="Manual Review" value={String(blockerResolution?.manual_review_count ?? 0)} />
          <Metric label="Pack Hash" value={String(blockerResolution?.pack_hash ?? "pending").slice(0, 12)} />
          <Metric label="Routing" value={blockerResolution?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Export" value={blockerResolution?.can_export_to_openalgo ? "enabled" : "blocked"} />
          <Metric label="Live" value={blockerResolution?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          {(blockerResolution?.remediation_items ?? []).map((item: any) => (
            <div key={item.item_id}>
              <b>{item.item_id}</b>
              <span>{item.severity}</span>
              <small>{item.title}</small>
            </div>
          ))}
        </div>
        {(blockerResolution?.operator_runbook ?? []).slice(0, 5).map((step: any) => (
          <div className="list-row" key={step.step}>
            <b>{step.step}. {step.title}</b>
            <span>{step.command}</span>
            <small>{step.expected}</small>
          </div>
        ))}
        <b>Verification Commands</b>
        {(blockerResolution?.verification_commands ?? []).slice(0, 5).map((command: string) => (
          <div className="list-row single" key={command}><span>{command}</span></div>
        ))}
        <p>Secrets and manual approvals cannot be auto-fixed by Trade Vision. The pack is an operator runbook for research/dry-run readiness only.</p>
      </Panel>

      <Panel title="Preflight Evidence Runner" span="wide" tab="vault" category="governance" badge={preflightEvidence?.overall_status ?? "v1.01"}>
        <div className="dna-grid">
          <Metric label="Status" value={preflightEvidence?.overall_status ?? "pending"} />
          <Metric label="Checks" value={String(preflightEvidence?.check_count ?? 0)} />
          <Metric label="Pass" value={String(preflightEvidence?.pass_count ?? 0)} />
          <Metric label="Warn" value={String(preflightEvidence?.warn_count ?? 0)} />
          <Metric label="Fail" value={String(preflightEvidence?.fail_count ?? 0)} />
          <Metric label="Hash" value={String(preflightEvidence?.preflight_hash ?? "pending").slice(0, 12)} />
          <Metric label="Paper Review" value={preflightEvidence?.operator_decision?.paper_review_allowed ? "allowed" : "blocked"} />
          <Metric label="OpenAlgo Dry Run" value={preflightEvidence?.operator_decision?.openalgo_dry_run_allowed ? "allowed" : "blocked"} />
        </div>
        <div className="capability-table compact">
          {(preflightEvidence?.checklist ?? []).map((check: any) => (
            <div key={check.check_id}>
              <b>{check.check_id}</b>
              <span>{check.status}</span>
              <small>{check.name}</small>
            </div>
          ))}
        </div>
        <div className="capability-table compact">
          {Object.entries(preflightEvidence?.evidence_snapshots ?? {}).map(([name, snapshot]: [string, any]) => (
            <div key={name}>
              <b>{name}</b>
              <span>{snapshot.overall_status ?? snapshot.ready ?? snapshot.research_stack_ready ?? snapshot.configured ?? "captured"}</span>
              <small>{snapshot.version ?? "version pending"}</small>
            </div>
          ))}
        </div>
        {(preflightEvidence?.minimum_evidence_bundle ?? []).map((artifact: any) => (
          <div className="list-row" key={artifact.name}>
            <b>{artifact.name}</b>
            <span>{artifact.version ?? "pending"}</span>
            <small>{artifact.hash ? String(artifact.hash).slice(0, 16) : "hash not required"}</small>
          </div>
        ))}
        <p>{preflightEvidence?.operator_decision?.reason ?? "Preflight evidence cannot approve live trading."}</p>
      </Panel>

      <Panel title="Local OpenAlgo Adapter Harness" span="wide" tab="execution" category="infra" badge={adapterHarness?.readiness?.dry_run_handoff_ready ? "v1.02 ready" : "v1.02 setup"}>
        <div className="dna-grid">
          <Metric label="Files" value={adapterHarness?.readiness?.adapter_files_ready ? "ready" : "missing"} />
          <Metric label="Config" value={adapterHarness?.readiness?.configuration_ready ? "ready" : "needed"} />
          <Metric label="Health" value={adapterHarness?.readiness?.signed_health_ready ? "ok" : "not ok"} />
          <Metric label="Dry Run" value={adapterHarness?.readiness?.dry_run_handoff_ready ? "ready" : "blocked"} />
          <Metric label="Manual Start" value={adapterHarness?.readiness?.manual_start_required ? "required" : "not required"} />
          <Metric label="Hash" value={String(adapterHarness?.harness_hash ?? "pending").slice(0, 12)} />
          <Metric label="Routing" value={adapterHarness?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={adapterHarness?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          {Object.entries(adapterHarness?.files ?? {}).map(([name, value]) => (
            <div key={name}>
              <b>{name}</b>
              <span>{value ? "present" : "missing"}</span>
              <small>adapter source</small>
            </div>
          ))}
        </div>
        <div className="list-row">
          <b>Manual Launch</b>
          <span>{adapterHarness?.launch_plan?.manual_command ?? "pending"}</span>
          <small>{adapterHarness?.launch_plan?.reason_auto_start_disabled ?? "operator-controlled"}</small>
        </div>
        {(adapterHarness?.next_actions ?? []).map((action: string) => (
          <div className="list-row single" key={action}><span>{action}</span></div>
        ))}
        <p>The adapter harness validates signed dry-run review only. It cannot place orders, pass broker credentials, or enable live routing.</p>
      </Panel>

      <Panel title="OpenAlgo Handoff Gate" span="wide" tab="execution" category="infra" badge={openAlgoHandoffGate?.handoff_gate_version ?? "v1.20"}>
        <div className="dna-grid">
          <Metric label="State" value={openAlgoHandoffGate?.handoff_state ?? "pending"} />
          <Metric label="Dry Run Handoff" value={openAlgoHandoffGate?.dry_run_handoff_allowed ? "allowed" : "blocked"} />
          <Metric label="Enqueue" value={openAlgoHandoffGate?.enqueue_allowed ? "allowed" : "blocked"} />
          <Metric label="Auto Delivery" value={openAlgoHandoffGate?.automatic_delivery_allowed ? "allowed" : "blocked"} />
          <Metric label="Package Verify" value={openAlgoHandoffGate?.package_verification?.verified ? "pass" : "pending"} />
          <Metric label="Bot Review" value={openAlgoHandoffGate?.bot_handoff_verification?.rejected ? "manual required" : "accepted"} />
          <Metric label="Transport" value={openAlgoHandoffGate?.transport_summary?.configured ? "configured" : "not configured"} />
          <Metric label="Adapter Health" value={openAlgoHandoffGate?.transport_summary?.health_ok ? "ok" : "not ok"} />
          <Metric label="Routing" value={openAlgoHandoffGate?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={openAlgoHandoffGate?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          <div>
            <b>Intent</b>
            <span>{openAlgoHandoffGate?.intent_summary?.side ?? "NO_TRADE"}</span>
            <small>{String(openAlgoHandoffGate?.intent_summary?.intent_signature ?? "pending").slice(0, 16)} | expires {openAlgoHandoffGate?.intent_summary?.valid_until ?? "pending"}</small>
          </div>
          <div>
            <b>Package</b>
            <span>{String(openAlgoHandoffGate?.package_summary?.package_id ?? "pending").slice(0, 16)}</span>
            <small>dry-run {String(openAlgoHandoffGate?.package_summary?.dry_run_only ?? false)} | broker order {String(openAlgoHandoffGate?.package_summary?.broker_order_created ?? false)}</small>
          </div>
          <div>
            <b>Transport</b>
            <span>{openAlgoHandoffGate?.transport_summary?.circuit_state ?? "pending"}</span>
            <small>auth {String(openAlgoHandoffGate?.transport_summary?.service_auth_configured ?? false)} | manual {String(openAlgoHandoffGate?.transport_summary?.manual_review_count ?? 0)} | dead {String(openAlgoHandoffGate?.transport_summary?.dead_letter_count ?? 0)}</small>
          </div>
        </div>
        {(openAlgoHandoffGate?.bot_handoff_verification?.rejection_reasons ?? []).slice(0, 5).map((reason: string) => (
          <div className="list-row single" key={reason}><span>REQUIRES REVIEW: {reason}</span></div>
        ))}
        {(openAlgoHandoffGate?.adapter_harness_summary?.next_actions ?? []).slice(0, 5).map((action: string) => (
          <div className="list-row single" key={action}><span>NEXT: {action}</span></div>
        ))}
        {(openAlgoHandoffGate?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{openAlgoHandoffGate?.operator_message ?? "OpenAlgo handoff gate is loading. No broker order or route is possible."}</p>
      </Panel>

      <Panel title="OpenAlgo Paper Bridge Hardening" span="wide" tab="execution" category="infra" badge={openAlgoPaperBridge?.bridge_version ?? "v1.31"}>
        <div className="dna-grid">
          <Metric label="State" value={openAlgoPaperBridge?.bridge_state ?? "pending"} />
          <Metric label="Scope" value={openAlgoPaperBridge?.safe_external_scope ?? "paper_or_sim_review_only"} />
          <Metric label="Inspect" value={openAlgoPaperBridge?.openalgo_may_inspect ? "allowed" : "blocked"} />
          <Metric label="Execute" value={openAlgoPaperBridge?.openalgo_may_execute ? "unsafe" : "blocked"} />
          <Metric label="Paper Intent" value={openAlgoPaperBridge?.paper_intent_allowed ? "review" : "blocked"} />
          <Metric label="Live Intent" value={openAlgoPaperBridge?.live_intent_allowed ? "unsafe" : "blocked"} />
          <Metric label="Manual Review" value={openAlgoPaperBridge?.manual_operator_review_required ? "required" : "missing"} />
          <Metric label="Routing" value={openAlgoPaperBridge?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <div className="list-row single">
          <span>Intent {String(openAlgoPaperBridge?.intent_signature ?? "pending").slice(0, 16)} | Package {String(openAlgoPaperBridge?.package_hash ?? "pending").slice(0, 16)} | Handoff {String(openAlgoPaperBridge?.handoff_hash ?? "pending").slice(0, 16)}</span>
        </div>
        {(openAlgoPaperBridge?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        {(openAlgoPaperBridge?.required_external_executor_checks ?? []).slice(0, 8).map((check: string) => (
          <div className="list-row single" key={check}><span>Executor must {check}</span></div>
        ))}
        <p>{openAlgoPaperBridge?.operator_message ?? "OpenAlgo paper bridge hardening is loading. Live execution remains blocked."}</p>
      </Panel>

      <Panel title="Paper Execution Loop Gate" span="wide" tab="trade" badge={paperExecutionLoop?.paper_loop_version ?? "v1.21"}>
        <div className="dna-grid">
          <Metric label="Loop State" value={paperExecutionLoop?.loop_state ?? "pending"} />
          <Metric label="Paper Loop" value={paperExecutionLoop?.paper_loop_allowed ? "allowed" : "blocked"} />
          <Metric label="External Handoff" value={paperExecutionLoop?.external_executor_handoff_allowed ? "allowed" : "blocked"} />
          <Metric label="Confidence Boost" value={paperExecutionLoop?.confidence_boost_allowed ? "allowed" : "blocked"} />
          <Metric label="Paper State" value={paperExecutionLoop?.paper_intent_lifecycle?.current_state ?? "pending"} />
          <Metric label="Manual Review" value={paperExecutionLoop?.paper_intent_lifecycle?.manual_review_required ? "required" : "pending"} />
          <Metric label="Lifecycle" value={paperExecutionLoop?.shadow_lifecycle?.lifecycle_status ?? "pending"} />
          <Metric label="Outcome" value={paperExecutionLoop?.shadow_lifecycle?.outcome_label ?? "pending"} />
          <Metric label="Fill" value={paperExecutionLoop?.shadow_lifecycle?.fill_status ?? "pending"} />
          <Metric label="MFE" value={String(paperExecutionLoop?.shadow_lifecycle?.expected_MFE ?? "pending")} />
          <Metric label="MAE" value={String(paperExecutionLoop?.shadow_lifecycle?.expected_MAE ?? "pending")} />
          <Metric label="Routing" value={paperExecutionLoop?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={paperExecutionLoop?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          <div>
            <b>Jarvis Decision</b>
            <span>{paperExecutionLoop?.jarvis_decision_summary?.final_action ?? "WAIT"}</span>
            <small>{paperExecutionLoop?.jarvis_decision_summary?.decision ?? "No execution authority."}</small>
          </div>
          <div>
            <b>Scenario Evidence</b>
            <span>{paperExecutionLoop?.scenario_evidence_summary?.comparison_version ?? "pending"}</span>
            <small>evidence {paperExecutionLoop?.scenario_evidence_summary?.evidence_version ?? "pending"} | hash {String(paperExecutionLoop?.scenario_evidence_summary?.scenario_hash ?? "pending").slice(0, 12)}</small>
          </div>
          <div>
            <b>Tradeability</b>
            <span>{paperExecutionLoop?.tradeability_summary?.readiness_action ?? "pending"}</span>
            <small>promotion {paperExecutionLoop?.tradeability_summary?.promotion_allowed ? "allowed" : "blocked"} | trade {paperExecutionLoop?.tradeability_summary?.trade_allowed ? "allowed" : "blocked"}</small>
          </div>
        </div>
        {(paperExecutionLoop?.shadow_lifecycle?.trade_state_path ?? []).slice(0, 10).map((state: string, index: number) => (
          <div className="list-row single" key={`${state}-${index}`}><span>STATE {index + 1}: {state}</span></div>
        ))}
        {(paperExecutionLoop?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{paperExecutionLoop?.operator_message ?? "Paper execution loop gate is loading. Paper simulation remains blocked until safety evidence is complete."}</p>
      </Panel>

      <Panel title="Jarvis Decision Quality Gate" span="wide" tab="trade" badge={decisionQualityGate?.quality_gate_version ?? "v1.22"}>
        <div className="dna-grid">
          <Metric label="Quality State" value={decisionQualityGate?.quality_state ?? "pending"} />
          <Metric label="Review Display" value={decisionQualityGate?.review_display_allowed ? "allowed" : "blocked"} />
          <Metric label="External AI Display" value={decisionQualityGate?.external_ai_display_allowed ? "allowed" : "blocked"} />
          <Metric label="Decision Trust" value={decisionQualityGate?.decision_trust_allowed ? "allowed" : "blocked"} />
          <Metric label="External Stale" value={decisionQualityGate?.external_ai_quality?.stale_review_history ? "yes" : "no"} />
          <Metric label="Low Evidence" value={decisionQualityGate?.external_ai_quality?.low_evidence_detected ? "yes" : "no"} />
          <Metric label="Disagreement" value={decisionQualityGate?.external_ai_quality?.disagreement_detected ? "yes" : "no"} />
          <Metric label="Daily Authority" value={decisionQualityGate?.daily_data_quality?.authority_state ?? "pending"} />
          <Metric label="Blocked Claims" value={String(decisionQualityGate?.verified_evidence_quality?.blocked_claim_count ?? 0)} />
          <Metric label="Paper Loop" value={decisionQualityGate?.paper_loop_quality?.loop_state ?? "pending"} />
          <Metric label="OpenAlgo" value={decisionQualityGate?.openalgo_handoff_quality?.handoff_state ?? "pending"} />
          <Metric label="Routing" value={decisionQualityGate?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={decisionQualityGate?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          <div>
            <b>Decision Packet</b>
            <span>{decisionQualityGate?.decision_summary?.final_action ?? "WAIT"}</span>
            <small>{decisionQualityGate?.decision_summary?.trade_vision_decision ?? "No trade authority."} | {String(decisionQualityGate?.decision_summary?.packet_id ?? "pending").slice(0, 12)}</small>
          </div>
          <div>
            <b>Daily/Weekly Data</b>
            <span>{decisionQualityGate?.daily_data_quality?.daily_available ? "daily ok" : "daily missing"} / {decisionQualityGate?.daily_data_quality?.weekly_available ? "weekly ok" : "weekly missing"}</span>
            <small>cap {String(decisionQualityGate?.daily_data_quality?.decision_confidence_cap_pct ?? "pending")}% | HTF {decisionQualityGate?.daily_data_quality?.htf_confirmation_available ? "available" : "missing"}</small>
          </div>
          <div>
            <b>External Review</b>
            <span>{decisionQualityGate?.external_ai_quality?.reliability_state ?? "pending"}</span>
            <small>records {String(decisionQualityGate?.external_ai_quality?.record_count ?? 0)} | accepted {String(decisionQualityGate?.external_ai_quality?.accepted_count ?? 0)}</small>
          </div>
        </div>
        {(decisionQualityGate?.quality_flags ?? []).map((flag: any) => (
          <div className="list-row" key={flag.flag_id}>
            <b>{flag.flag_id}: {flag.severity}</b>
            <span>{flag.name}</span>
            <small>{flag.repair}</small>
          </div>
        ))}
        {(decisionQualityGate?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{decisionQualityGate?.operator_message ?? "Decision quality gate is loading. External AI, paper loop, and OpenAlgo evidence remain read-only."}</p>
      </Panel>

      <Panel title="Trade Vision Decision" tab="trade" badge={decision?.final_trade_decision ?? "pending"}>
        <Metric label="Scenario" value={decision?.scenario_label ?? "pending"} />
        <Metric label="Bias" value={decision?.scenario_bias ?? "pending"} />
        <Metric label="Confidence Cap" value={`${decision?.confidence_cap_pct ?? 0}%`} />
        <Metric label="Entry Zone" value={(decision?.best_entry_zone ?? []).join(" - ") || "pending"} />
        <Metric label="Stop Loss" value={String(decision?.stop_loss ?? "pending")} />
        <Metric label="Target" value={String(decision?.target ?? "pending")} />
        <Metric label="Invalidation" value={String(decision?.invalidation_level ?? "pending")} />
        <Metric label="R:R" value={String(decision?.risk_reward ?? "pending")} />
        <p>{decision?.entry_condition ?? "Waiting for evidence packet."}</p>
        {(decision?.reason_tree ?? []).map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
      </Panel>

      <Panel title="Wait / Avoid Rules" tab="trade" badge="v0.87">
        <b>Wait For</b>
        {(decision?.wait_for ?? []).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
        <b>Avoid If</b>
        {(decision?.avoid_if ?? []).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
      </Panel>

      <Panel title="Evidence Inspector" tab="trade" badge={room?.similar_history?.evidence_quality ?? "evidence"}>
        <Metric label="Candle" value={room?.candle_structure?.pattern ?? "pending"} />
        <Metric label="Body" value={`${room?.candle_structure?.body_pct ?? 0}%`} />
        <Metric label="Upper Wick" value={`${room?.candle_structure?.upper_wick_pct ?? 0}%`} />
        <Metric label="Lower Wick" value={`${room?.candle_structure?.lower_wick_pct ?? 0}%`} />
        <Metric label="RSI 14" value={String(indicators.rsi14 ?? "pending")} />
        <Metric label="EMA State" value={String(indicators.ema_state ?? "pending")} />
        <Metric label="VWAP" value={String(indicators.vwap_position ?? "pending")} />
        <Metric label="Volume Z" value={String(indicators.volume_z ?? "pending")} />
        <small>{indicators.full_indicator_matrix_status ?? "Full indicator registry remains available in existing drill-down panels."}</small>
      </Panel>

      <Panel title="Multi-Timeframe Alignment" tab="trade" badge={multiTf?.arbiter_modifier ?? "pending"}>
        <Metric label="Alignment" value={`${Math.round((multiTf?.alignment_score ?? 0) * 100)}%`} />
        <Metric label="Conflict" value={multiTf?.dominant_conflict ?? "pending"} />
        <Metric label="HTF Closed Candle" value={multiTf?.htf_confirmation_available ? "available" : "not available"} />
        <div className="capability-table compact">
          {Object.entries(multiTf?.timeframes ?? {}).map(([timeframe, state]) => (
            <div key={timeframe}>
              <b>{timeframe}</b>
              <span>{String(state)}</span>
              <small>Closed-candle rule enforced</small>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Sequential Signals" tab="trade" badge={`${room?.sequential_signals?.length ?? 0} found`}>
        {(room?.sequential_signals ?? []).map((signal: any) => (
          <div className="list-row" key={`${signal.name}-${signal.timing}`}>
            <b>{signal.name}</b>
            <span>{signal.timing} / {signal.direction}</span>
          </div>
        ))}
        {(!room?.sequential_signals || room.sequential_signals.length === 0) && <p>No sequential signal chain is available in the current packet.</p>}
      </Panel>

      <Panel title="Similar History" tab="trade" badge={`${room?.similar_history?.total_matches_found ?? 0} windows`}>
        <Metric label="Minimum Sample" value={room?.similar_history?.minimum_sample_pass ? "pass" : "not yet"} />
        <Metric label="Matches Used" value={String(room?.similar_history?.matches_used ?? 0)} />
        {(room?.similar_history?.matches ?? []).map((match: any) => (
          <div className="list-row" key={`${match.start_timestamp_ns}-${match.end_timestamp_ns}`}>
            <b>{new Date(Number(match.start_timestamp_ns) / 1_000_000).toLocaleString()}</b>
            <span>{match.similarity_score_pct}% similar | {match.outcome}</span>
          </div>
        ))}
      </Panel>

      <Panel title="Safety And Arbiter" tab="trade" badge={safety?.overall_status ?? "pending"}>
        <Metric label="Data Quality" value={`${Math.round((safety?.data_quality_score ?? 0) * 100)}%`} />
        <Metric label="Evidence" value={safety?.minimum_evidence_pass ? "pass" : "capped"} />
        <Metric label="Routing" value={safety?.order_routing_enabled ? "unsafe" : "blocked"} />
        <Metric label="Live Trading" value={safety?.live_trading_blocked ? "blocked" : "unsafe"} />
        {(safety?.blocking_gates ?? []).map((gate: string) => <div className="list-row single" key={gate}><span>BLOCK: {gate}</span></div>)}
        {(safety?.warning_gates ?? []).map((gate: string) => <div className="list-row single" key={gate}><span>WARN: {gate}</span></div>)}
      </Panel>

      <Panel title="Unified Decision Arbiter" tab="trade" badge={arbiter?.arbiter_state ?? "v0.92"}>
        <Metric label="Arbiter Action" value={arbiter?.final_action ?? "WAIT"} />
        <Metric label="Trade Vision" value={arbiter?.trade_vision_action ?? "pending"} />
        <Metric label="Gemini" value={arbiter?.gemini_safe_action ?? "pending"} />
        <Metric label="Gemini Accepted" value={arbiter?.gemini_review_accepted ? "yes" : "no"} />
        <Metric label="Kronos" value={arbiter?.kronos_status ?? "reserved"} />
        <Metric label="OpenAlgo" value={arbiter?.openalgo_status ?? "reserved"} />
        <Metric label="Export" value={arbiter?.can_export_to_openalgo ? "available" : "blocked"} />
        <Metric label="Human Approval" value={arbiter?.human_approval_required ? "required" : "not required"} />
        {(arbiter?.conflict_reasons ?? []).map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
        <div className="capability-table compact">
          {(arbiter?.hard_gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="System Health Matrix" tab="evidence" category="infra" badge={health?.overall_health ?? "pending"}>
        <Metric label="Refresh" value={`${health?.refresh_interval_seconds ?? 10}s`} />
        <Metric label="Banner" value={health?.persistent_banner_required ? "required" : "not needed"} />
        {(health?.rows ?? []).map((row: any) => (
          <div className="list-row" key={row.component}>
            <b>{row.component}</b>
            <span>{row.status}</span>
            <small>{row.detail}</small>
          </div>
        ))}
      </Panel>

      <Panel title="External Review Slots" tab="trade" badge="advisory only">
        <Metric label="Gemini" value={`${gemini?.status ?? "unavailable"} / ${gemini?.configured_key_slots ?? 0} keys`} />
        <Metric label="Grok" value={`${grokStatus?.status ?? "unavailable"} / ${grokStatus?.api_key_source ?? "missing"}`} />
        <Metric label="Kronos" value={`${kronos?.status ?? "reserved"} / ${kronos?.mode ?? "unknown"}`} />
        <Metric label="OpenAlgo" value={openalgo?.status ?? "reserved"} />
        <p>Gemini supports five backend-only fallback API key slots. Grok uses a backend-only xAI/Grok API key. Kronos and OpenAlgo remain advisory and cannot override Trade Vision safety.</p>
      </Panel>

      <Panel title="Gemini Live Review Fallback" span="wide" tab="trade" category="ai_ops" badge={geminiLiveReview?.live_review_version ?? "v1.35"}>
        <div className="dna-grid">
          <Metric label="Execute" value={geminiLiveReview?.execute_requested ? "requested" : "safe preview"} />
          <Metric label="Allowed" value={geminiLiveReview?.live_call_allowed ? "yes" : "no"} />
          <Metric label="Performed" value={geminiLiveReview?.live_call_performed ? "yes" : "no"} />
          <Metric label="Slot" value={String(geminiLiveReview?.successful_slot ?? "none")} />
          <Metric label="Attempts" value={String(geminiLiveReview?.attempt_count ?? 0)} />
          <Metric label="Display" value={geminiLiveReview?.display_allowed ? "allowed" : "blocked"} />
          <Metric label="Safe Action" value={geminiLiveReview?.safe_final_action ?? "TRADE_VISION_ONLY"} />
          <Metric label="Saved Review" value={String(geminiLiveReview?.saved_review_id ?? "pending").slice(0, 18)} />
        </div>
        <p>{geminiLiveReview?.operator_message ?? "Gemini live review is loading. It remains research-only and cannot override Jarvis safety."}</p>
        <div className="capability-table compact">
          {(geminiLiveReview?.attempts ?? []).map((attempt: any) => (
            <div key={`gemini-attempt-${attempt.slot}`}>
              <b>Slot {attempt.slot}</b>
              <span>{attempt.success ? "success" : "failed"}</span>
              <small>Status {String(attempt.status_code ?? "n/a")} | latency {String(attempt.latency_ms ?? "n/a")} ms | {attempt.error_message ?? "no error"}</small>
            </div>
          ))}
          {(geminiLiveReview?.gates ?? []).map((gate: any) => (
            <div key={gate.check_id}>
              <b>{gate.check_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <pre className="json-preview">{JSON.stringify(geminiLiveReview?.candidate_response ?? {}, null, 2)}</pre>
      </Panel>

      <Panel title="Grok Live Review" span="wide" tab="trade" category="ai_ops" badge={grokLiveReview?.live_review_version ?? "v1.36"}>
        <div className="dna-grid">
          <Metric label="Provider" value={grokStatus?.status ?? "pending"} />
          <Metric label="Key Source" value={grokStatus?.api_key_source ?? "missing"} />
          <Metric label="Execute" value={grokLiveReview?.execute_requested ? "requested" : "safe preview"} />
          <Metric label="Allowed" value={grokLiveReview?.live_call_allowed ? "yes" : "no"} />
          <Metric label="Performed" value={grokLiveReview?.live_call_performed ? "yes" : "no"} />
          <Metric label="Display" value={grokLiveReview?.display_allowed ? "allowed" : "blocked"} />
          <Metric label="Safe Action" value={grokLiveReview?.safe_final_action ?? "TRADE_VISION_ONLY"} />
          <Metric label="Saved Review" value={String(grokLiveReview?.saved_review_id ?? "pending").slice(0, 18)} />
        </div>
        <p>{grokLiveReview?.operator_message ?? "Grok live review is loading. It remains research-only and cannot override Jarvis safety."}</p>
        <div className="capability-table compact">
          <div>
            <b>API Call</b>
            <span>{grokLiveReview?.live_call?.success ? "success" : "not accepted"}</span>
            <small>Status {String(grokLiveReview?.live_call?.status_code ?? "n/a")} | latency {String(grokLiveReview?.live_call?.latency_ms ?? "n/a")} ms | {grokLiveReview?.live_call?.error_message ?? "no error"}</small>
          </div>
          {(grokLiveReview?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <pre className="json-preview">{JSON.stringify(grokLiveReview?.candidate_response ?? {}, null, 2)}</pre>
      </Panel>

      <Panel title="Local Grok Gateway" span="wide" tab="trade" category="ai_ops" badge={grokGatewayStatus?.gateway_state ?? "local"}>
        <div className="toolbar">
          <button onClick={runGrokGatewayConnect} disabled={grokGatewayBusy !== null}>
            {grokGatewayBusy === "connect" ? "Checking..." : "Connect Grok Gateway"}
          </button>
          <button onClick={runGrokGatewayReview} disabled={grokGatewayBusy !== null || grokGatewayStatus?.url_valid === false}>
            {grokGatewayBusy === "review" ? "Waiting for Grok..." : "Send Evidence To Grok"}
          </button>
          <button onClick={onRefresh} disabled={grokGatewayBusy !== null}>Refresh</button>
        </div>
        <div className="dna-grid">
          <Metric label="Gateway" value={grokGatewayStatus?.gateway_state ?? "pending"} />
          <Metric label="URL" value={grokGatewayStatus?.gateway_url_masked ?? "http://127.0.0.1:8899"} />
          <Metric label="Health" value={grokGatewayStatus?.health_check?.state ?? "not checked"} />
          <Metric label="Health Latency" value={grokGatewayStatus?.health_check?.latency_ms != null ? `${grokGatewayStatus.health_check.latency_ms} ms` : "n/a"} />
          <Metric label="Model" value={grokGatewayStatus?.selected_model ?? "grok/grok-4-fast"} />
          <Metric label="Ask Timeout" value={`${grokGatewayStatus?.ask_timeout_ms ?? 45000} ms`} />
          <Metric label="Thinking" value={grokGatewayBusy === "review" ? "waiting_for_reply" : grokGatewayReview?.thinking_state ?? "idle"} />
          <Metric label="Safe Action" value={grokGatewayReview?.safe_final_action ?? "TRADE_VISION_ONLY"} />
        </div>
        {grokGatewayError ? <p className="error-text">{grokGatewayError}</p> : null}
        <p>{grokGatewayReview?.operator_message ?? grokGatewayStatus?.operator_message ?? "Local Grok gateway is reviewer-only. If Grok takes too long, this panel shows waiting until backend timeout, then timeout/fail-safe."}</p>
        <div className="capability-table compact">
          <div>
            <b>Single-Box Gateway Config Path</b>
            <span>{grokGatewayStatus?.single_box_paths?.gateway_config_path ?? "data\\secrets\\grok_gateway.local.json"}</span>
            <small>Allowed keys: enabled, gateway_url, model, health_timeout_ms, ask_timeout_ms. No username/password/cookies/session tokens.</small>
          </div>
          <div>
            <b>Official Grok API Vault Path</b>
            <span>{grokGatewayStatus?.single_box_paths?.official_api_key_vault_path ?? "data\\secrets\\ai_credentials.enc"}</span>
            <small>Encrypted backend vault. Save API keys through backend/UI, not by editing this file manually.</small>
          </div>
          <div>
            <b>Config File</b>
            <span>{grokGatewayStatus?.single_box_paths?.gateway_config_file_exists ? "found" : "not created"}</span>
            <small>{grokGatewayStatus?.single_box_paths?.operator_note ?? "Local-only config. Trade Vision does not store Grok browser passwords."}</small>
          </div>
          {(grokGatewayStatus?.single_box_paths?.unsupported_secret_keys_detected ?? []).length > 0 ? (
            <div>
              <b>Unsupported Secret Keys</b>
              <span>{(grokGatewayStatus?.single_box_paths?.unsupported_secret_keys_detected ?? []).join(", ")}</span>
              <small>These keys are ignored by Trade Vision for safety.</small>
            </div>
          ) : null}
          <div>
            <b>Gateway Call</b>
            <span>{grokGatewayReview?.gateway_call?.state ?? "idle"}</span>
            <small>Status {String(grokGatewayReview?.gateway_call?.status_code ?? "n/a")} | latency {String(grokGatewayReview?.gateway_call?.latency_ms ?? "n/a")} ms | {grokGatewayReview?.gateway_call?.error_message ?? "no error"}</small>
          </div>
          {(grokGatewayReview?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Sent Evidence Packet</h4>
            <pre className="json-preview">{JSON.stringify(grokGatewayReview?.sent_packet_preview ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Full Grok Reply</h4>
            <pre className="json-preview">{grokGatewayReview?.raw_response_text || JSON.stringify(grokGatewayReview?.candidate_response ?? {}, null, 2)}</pre>
          </div>
        </div>
      </Panel>

      <Panel title="Gemini vs Grok Comparison Room" span="wide" tab="trade" badge={aiComparison?.comparison_version ?? "v1.37"}>
        <div className="dna-grid">
          <Metric label="Agreement" value={aiComparison?.agreement_matrix?.agreement_state ?? "pending"} />
          <Metric label="Gemini" value={aiComparison?.agreement_matrix?.gemini_action ?? "pending"} />
          <Metric label="Grok" value={aiComparison?.agreement_matrix?.grok_action ?? "pending"} />
          <Metric label="Displayable" value={String(aiComparison?.agreement_matrix?.displayable_provider_count ?? 0)} />
          <Metric label="Safe Action" value={aiComparison?.safe_final_action ?? "TRADE_VISION_ONLY"} />
          <Metric label="Confidence Boost" value={aiComparison?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Blocks" value={String(aiComparison?.blocking_count ?? 0)} />
          <Metric label="Warnings" value={String(aiComparison?.warning_count ?? 0)} />
        </div>
        <p>{aiComparison?.final_interpretation ?? "Comparison room is loading. External AI remains research-only."}</p>
        <div className="capability-table compact">
          <div>
            <b>Evidence Packet</b>
            <span>{String(aiComparison?.evidence_packet_hash ?? "pending").slice(0, 16)}</span>
            <small>Same packet must be used for Gemini and Grok.</small>
          </div>
          {(aiComparison?.agreement_matrix?.missing_core_evidence ?? []).slice(0, 8).map((key: string) => (
            <div key={`missing-${key}`}>
              <b>Missing Evidence</b>
              <span>{key}</span>
              <small>External AI did not cite this core evidence key.</small>
            </div>
          ))}
          {(aiComparison?.agreement_matrix?.hallucinated_evidence_keys ?? []).slice(0, 8).map((key: string) => (
            <div key={`hallucinated-${key}`}>
              <b>Hallucinated Evidence</b>
              <span>{key}</span>
              <small>Unsupported evidence key was rejected.</small>
            </div>
          ))}
          {(aiComparison?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Gemini Reply</h4>
            <pre className="json-preview">{JSON.stringify(aiComparison?.gemini?.candidate_response ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Grok Reply</h4>
            <pre className="json-preview">{JSON.stringify(aiComparison?.grok?.candidate_response ?? {}, null, 2)}</pre>
          </div>
        </div>
      </Panel>

      <Panel title="AI Comparison History Guard" span="wide" tab="vault" category="ai_ops" badge={aiComparisonHistory?.history_version ?? "v1.38"}>
        <div className="dna-grid">
          <Metric label="State" value={aiComparisonHistory?.history_state ?? "pending"} />
          <Metric label="Records" value={String(aiComparisonHistory?.record_count ?? 0)} />
          <Metric label="Latest" value={aiComparisonHistory?.latest_agreement_state ?? "none"} />
          <Metric label="Safe Action" value={aiComparisonHistory?.latest_safe_final_action ?? "TRADE_VISION_ONLY"} />
          <Metric label="Age" value={aiComparisonHistory?.latest_age_seconds !== null && aiComparisonHistory?.latest_age_seconds !== undefined ? `${aiComparisonHistory.latest_age_seconds}s` : "missing"} />
          <Metric label="Stale" value={aiComparisonHistory?.stale_comparison_history ? "stale" : "fresh"} />
          <Metric label="Agree Rate" value={`${Math.round((aiComparisonHistory?.agreement_rate ?? 0) * 100)}%`} />
          <Metric label="Conflict Rate" value={`${Math.round((aiComparisonHistory?.conflict_rate ?? 0) * 100)}%`} />
          <Metric label="Unavailable" value={`${Math.round((aiComparisonHistory?.unavailable_rate ?? 0) * 100)}%`} />
          <Metric label="Boost" value={aiComparisonHistory?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={aiComparisonHistory?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={aiComparisonHistory?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          {(aiComparisonHistory?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Gemini Health</h4>
            <pre className="json-preview">{JSON.stringify(aiComparisonHistory?.provider_health?.gemini ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Grok Health</h4>
            <pre className="json-preview">{JSON.stringify(aiComparisonHistory?.provider_health?.grok ?? {}, null, 2)}</pre>
          </div>
        </div>
        <p>{aiComparisonHistory?.operator_message ?? "Comparison history is loading. Trade Vision remains the authority."}</p>
      </Panel>

      <Panel title="AI Review Refresh Guard" span="wide" tab="vault" category="ai_ops" badge={aiReviewRefreshGuard?.refresh_guard_version ?? "v1.39"}>
        <div className="dna-grid">
          <Metric label="State" value={aiReviewRefreshGuard?.refresh_state ?? "pending"} />
          <Metric label="Needs Refresh" value={aiReviewRefreshGuard?.needs_external_ai_refresh ? "yes" : "no"} />
          <Metric label="Comparison Hash" value={aiReviewRefreshGuard?.comparison_hash_matches_current ? "match" : "mismatch"} />
          <Metric label="Review Hash" value={aiReviewRefreshGuard?.external_review_hash_matches_current ? "match" : "mismatch"} />
          <Metric label="Comparison Stale" value={aiReviewRefreshGuard?.comparison_stale ? "stale" : "fresh"} />
          <Metric label="Review Stale" value={aiReviewRefreshGuard?.external_review_stale ? "stale" : "fresh"} />
          <Metric label="Latest State" value={aiReviewRefreshGuard?.latest_comparison_agreement_state ?? "none"} />
          <Metric label="Warnings" value={String(aiReviewRefreshGuard?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(aiReviewRefreshGuard?.blocking_count ?? 0)} />
          <Metric label="Boost" value={aiReviewRefreshGuard?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={aiReviewRefreshGuard?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={aiReviewRefreshGuard?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          {(aiReviewRefreshGuard?.refresh_targets ?? []).map((target: any) => (
            <div key={target.target_id}>
              <b>{target.target_id}</b>
              <span>{target.order_authority ? "unsafe" : "no order authority"}</span>
              <small>{target.reason}</small>
            </div>
          ))}
          {(aiReviewRefreshGuard?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <p>{aiReviewRefreshGuard?.operator_message ?? "Refresh guard is loading. External AI remains display-only."}</p>
      </Panel>

      <Panel title="AI Refresh Action Harness" span="wide" tab="vault" category="ai_ops" badge={aiRefreshAction?.harness_version ?? "v1.40"}>
        <div className="dna-grid">
          <Metric label="State" value={aiRefreshAction?.harness_state ?? "pending"} />
          <Metric label="Refresh Needed" value={aiRefreshAction?.refresh_needed ? "yes" : "no"} />
          <Metric label="Operator Review" value={aiRefreshAction?.ready_for_operator_review ? "ready" : "blocked"} />
          <Metric label="Provider Refresh" value={aiRefreshAction?.ready_for_provider_refresh ? "ready" : "blocked"} />
          <Metric label="Bundle Hashes" value={aiRefreshAction?.bundle_hashes_match_current ? "match" : "mismatch"} />
          <Metric label="Network" value={aiRefreshAction?.network_call_allowed ? "unsafe" : "blocked"} />
          <Metric label="Performed" value={aiRefreshAction?.network_call_performed ? "unsafe" : "no"} />
          <Metric label="Packet" value={String(aiRefreshAction?.packet_hash ?? "pending").slice(0, 16)} />
          <Metric label="Warnings" value={String(aiRefreshAction?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(aiRefreshAction?.blocking_count ?? 0)} />
          <Metric label="Routing" value={aiRefreshAction?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={aiRefreshAction?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          {(aiRefreshAction?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Gemini Refresh Request</h4>
            <pre className="json-preview">{JSON.stringify(aiRefreshAction?.provider_requests?.gemini ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Grok Refresh Request</h4>
            <pre className="json-preview">{JSON.stringify(aiRefreshAction?.provider_requests?.grok ?? {}, null, 2)}</pre>
          </div>
        </div>
        <p>{aiRefreshAction?.operator_message ?? "Refresh action harness is loading. No provider call or trade is performed."}</p>
      </Panel>

      <Panel title="AI Refresh Response Intake" span="wide" tab="vault" category="ai_ops" badge={aiRefreshResponseSample?.intake_replay_version ?? "v1.41"}>
        <div className="dna-grid">
          <Metric label="Status" value={aiRefreshResponseSample?.replay_status ?? "pending"} />
          <Metric label="Provider" value={aiRefreshResponseSample?.provider ?? "manual"} />
          <Metric label="Display" value={aiRefreshResponseSample?.display_allowed ? "allowed" : "blocked"} />
          <Metric label="Packet Hash" value={aiRefreshResponseSample?.packet_hash_matches ? "match" : "missing/mismatch"} />
          <Metric label="Schema" value={aiRefreshResponseSample?.validation?.schema_validation_passed ? "pass" : "fail"} />
          <Metric label="Hallucination" value={aiRefreshResponseSample?.validation?.hallucination_detected ? "detected" : "none"} />
          <Metric label="Unsafe Override" value={aiRefreshResponseSample?.validation?.unsafe_override_attempted ? "blocked" : "none"} />
          <Metric label="Warnings" value={String(aiRefreshResponseSample?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(aiRefreshResponseSample?.blocking_count ?? 0)} />
          <Metric label="Boost" value={aiRefreshResponseSample?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={aiRefreshResponseSample?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={aiRefreshResponseSample?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="capability-table compact">
          {(aiRefreshResponseSample?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <pre className="json-preview">{JSON.stringify(aiRefreshResponseSample?.review_record ?? {}, null, 2)}</pre>
        <p>{aiRefreshResponseSample?.operator_message ?? "Refresh response intake is loading. External AI cannot alter the trading decision."}</p>
      </Panel>

      <Panel title="AI Refresh Response Ledger" span="wide" tab="vault" category="ai_ops" badge={aiRefreshResponseLedger?.ledger_version ?? "v1.42"}>
        <div className="dna-grid">
          <Metric label="State" value={aiRefreshResponseLedger?.ledger_state ?? "pending"} />
          <Metric label="Records" value={String(aiRefreshResponseLedger?.record_count ?? 0)} />
          <Metric label="Accepted" value={String(aiRefreshResponseLedger?.accepted_count ?? 0)} />
          <Metric label="Blocked" value={String(aiRefreshResponseLedger?.blocked_count ?? 0)} />
          <Metric label="Rejected" value={String(aiRefreshResponseLedger?.rejected_count ?? 0)} />
          <Metric label="Stale" value={String(aiRefreshResponseLedger?.stale_count ?? 0)} />
          <Metric label="Hash Mismatch" value={String(aiRefreshResponseLedger?.hash_mismatch_count ?? 0)} />
          <Metric label="Unsafe" value={String(aiRefreshResponseLedger?.unsafe_authority_count ?? 0)} />
          <Metric label="Warnings" value={String(aiRefreshResponseLedger?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(aiRefreshResponseLedger?.blocking_count ?? 0)} />
          <Metric label="Boost" value={aiRefreshResponseLedger?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={aiRefreshResponseLedger?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <div className="capability-table compact">
          {(aiRefreshResponseLedger?.provider_summaries ?? []).map((provider: any) => (
            <div key={provider.provider}>
              <b>{provider.provider}</b>
              <span>{provider.latest_status} / {provider.display_reliability_pct}% display</span>
              <small>records {provider.record_count}, stale {provider.stale_count}, hash mismatch {provider.hash_mismatch_count}</small>
            </div>
          ))}
          {(aiRefreshResponseLedger?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <pre className="json-preview">{JSON.stringify(aiRefreshResponseLedger?.recent_records ?? [], null, 2)}</pre>
        <p>{aiRefreshResponseLedger?.operator_message ?? "Refresh response ledger is loading. History can explain reliability, but cannot approve a trade."}</p>
      </Panel>

      <Panel title="AI Response Evidence Diff" span="wide" tab="trade" category="ai_ops" badge={aiEvidenceDiff?.diff_version ?? "v1.43"}>
        <div className="dna-grid">
          <Metric label="State" value={aiEvidenceDiff?.diff_state ?? "pending"} />
          <Metric label="Source" value={aiEvidenceDiff?.record_source ?? "none"} />
          <Metric label="Hash" value={aiEvidenceDiff?.record_hash_matches_current ? "current" : "stale/missing"} />
          <Metric label="Supported" value={String(aiEvidenceDiff?.supported_count ?? 0)} />
          <Metric label="Missing" value={String(aiEvidenceDiff?.missing_count ?? 0)} />
          <Metric label="Conflicts" value={String(aiEvidenceDiff?.conflict_count ?? 0)} />
          <Metric label="Available Keys" value={String(aiEvidenceDiff?.available_evidence_key_count ?? 0)} />
          <Metric label="Warnings" value={String(aiEvidenceDiff?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(aiEvidenceDiff?.blocking_count ?? 0)} />
          <Metric label="Boost" value={aiEvidenceDiff?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={aiEvidenceDiff?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={aiEvidenceDiff?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Action And Risk Diff</h4>
            <pre className="json-preview">{JSON.stringify({ action: aiEvidenceDiff?.action_diff ?? {}, risk: aiEvidenceDiff?.risk_diff ?? {} }, null, 2)}</pre>
          </div>
          <div>
            <h4>Claim Summary</h4>
            <pre className="json-preview">{JSON.stringify(aiEvidenceDiff?.claim_summary ?? {}, null, 2)}</pre>
          </div>
        </div>
        <div className="capability-table compact">
          {(aiEvidenceDiff?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
          {(aiEvidenceDiff?.cited_key_diffs ?? []).slice(0, 12).map((item: any, index: number) => (
            <div key={`${item.evidence_key}-${index}`}>
              <b>{item.evidence_key}</b>
              <span>{item.status}</span>
              <small>{item.reason}</small>
            </div>
          ))}
          {(aiEvidenceDiff?.indicator_diffs ?? []).map((item: any, index: number) => (
            <div key={`${item.indicator}-${index}`}>
              <b>{item.indicator}</b>
              <span>{item.status}</span>
              <small>{item.reason}</small>
            </div>
          ))}
        </div>
        <p>{aiEvidenceDiff?.operator_message ?? "AI response evidence diff is loading. Diff output is display-only and cannot approve trades."}</p>
      </Panel>

      <Panel title="Provider Disagreement Explorer" span="wide" tab="trade" badge={providerDisagreement?.explorer_version ?? "v1.44"}>
        <div className="dna-grid">
          <Metric label="State" value={providerDisagreement?.explorer_state ?? "pending"} />
          <Metric label="Disagreements" value={String(providerDisagreement?.disagreement_count ?? 0)} />
          <Metric label="Categories" value={(providerDisagreement?.categories ?? []).join(", ") || "none"} />
          <Metric label="Warnings" value={String(providerDisagreement?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(providerDisagreement?.blocking_count ?? 0)} />
          <Metric label="Boost" value={providerDisagreement?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={providerDisagreement?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="OpenAlgo" value={providerDisagreement?.can_export_to_openalgo ? "unsafe" : "blocked"} />
          <Metric label="Live" value={providerDisagreement?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Provider Views</h4>
            <pre className="json-preview">{JSON.stringify(providerDisagreement?.provider_views ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Next Verification Steps</h4>
            <div className="capability-table compact">
              {(providerDisagreement?.next_verification_steps ?? []).map((step: string) => (
                <div key={step}>
                  <b>VERIFY</b>
                  <span>required</span>
                  <small>{step}</small>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="capability-table compact">
          {(providerDisagreement?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
          {(providerDisagreement?.reason_cards ?? []).map((reason: any, index: number) => (
            <div key={`${reason.category}-${reason.source}-${index}`}>
              <b>{reason.category} / {reason.source}</b>
              <span>{reason.severity}</span>
              <small>{reason.description}</small>
            </div>
          ))}
        </div>
        <p>{providerDisagreement?.operator_message ?? "Provider disagreement explorer is loading. It explains conflicts but cannot approve trades."}</p>
      </Panel>

      <Panel title="Final Paper-Ready Safety Audit" span="wide" tab="execution" category="governance" badge={paperReadySafetyAudit?.paper_ready_audit_version ?? "v1.47"}>
        <div className="dna-grid">
          <Metric label="Final State" value={paperReadySafetyAudit?.final_state ?? "pending"} />
          <Metric label="Research" value={paperReadySafetyAudit?.go_no_go?.research_dashboard ?? "NO_GO"} />
          <Metric label="Paper Review" value={paperReadySafetyAudit?.go_no_go?.openalgo_paper_inspection ?? "NO_GO"} />
          <Metric label="Live Broker" value={paperReadySafetyAudit?.go_no_go?.live_broker_trading ?? "NO_GO"} />
          <Metric label="Trading Bot" value={paperReadySafetyAudit?.go_no_go?.autonomous_trading_bot ?? "NO_GO"} />
          <Metric label="Audit Hash" value={String(paperReadySafetyAudit?.audit_hash ?? "pending").slice(0, 16)} />
          <Metric label="Blocks" value={String(paperReadySafetyAudit?.blocking_count ?? 0)} />
          <Metric label="Warnings" value={String(paperReadySafetyAudit?.warning_count ?? 0)} />
          <Metric label="Trade" value={paperReadySafetyAudit?.trade_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={paperReadySafetyAudit?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="OpenAlgo Export" value={paperReadySafetyAudit?.can_export_to_openalgo ? "unsafe" : "blocked"} />
          <Metric label="Live" value={paperReadySafetyAudit?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Artifact Summary</h4>
            <pre className="json-preview">{JSON.stringify(paperReadySafetyAudit?.artifact_summary ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Remaining Before Live</h4>
            <div className="capability-table compact">
              {(paperReadySafetyAudit?.remaining_before_live ?? []).map((item: string) => (
                <div key={item}>
                  <b>LIVE BLOCKER</b>
                  <span>required</span>
                  <small>{item}</small>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="capability-table compact">
          {(paperReadySafetyAudit?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <p>{paperReadySafetyAudit?.operator_message ?? "Final paper-ready safety audit is loading. Live trading remains blocked."}</p>
      </Panel>

      <Panel title="Gemini/Grok Verified Review Packet" span="wide" tab="vault" category="ai_ops" badge={verifiedReviewPacket?.verified_packet_version ?? "v1.45"}>
        <div className="dna-grid">
          <Metric label="State" value={verifiedReviewPacket?.packet_state ?? "pending"} />
          <Metric label="Evidence Hash" value={String(verifiedReviewPacket?.evidence_packet_hash ?? "pending").slice(0, 16)} />
          <Metric label="Refresh Hash" value={String(verifiedReviewPacket?.refresh_packet_hash ?? "none").slice(0, 16)} />
          <Metric label="Export Hash" value={String(verifiedReviewPacket?.copy_safe_export_hash ?? "pending").slice(0, 16)} />
          <Metric label="Secret Scan" value={verifiedReviewPacket?.secret_scan?.secret_like_value_detected ? "blocked" : "clean"} />
          <Metric label="Warnings" value={String(verifiedReviewPacket?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(verifiedReviewPacket?.blocking_count ?? 0)} />
          <Metric label="Network" value={verifiedReviewPacket?.network_call_allowed ? "unsafe" : "blocked"} />
          <Metric label="Performed" value={verifiedReviewPacket?.network_call_performed ? "unsafe" : "no"} />
          <Metric label="Routing" value={verifiedReviewPacket?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="OpenAlgo" value={verifiedReviewPacket?.can_export_to_openalgo ? "unsafe" : "blocked"} />
          <Metric label="Live" value={verifiedReviewPacket?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="comparison-grid">
          {(["gemini", "grok"] as const).map((provider) => {
            const packet = verifiedReviewPacket?.providers?.[provider] ?? {};
            return (
              <div key={provider}>
                <h4>{provider.toUpperCase()} Packet</h4>
                <div className="capability-table compact">
                  <div><b>Status</b><span>{packet.provider_status?.status ?? "unknown"}</span><small>{packet.provider_status?.selected_model ?? "model unknown"}</small></div>
                  <div><b>Request</b><span>{String(packet.request_hash ?? "none").slice(0, 16)}</span><small>evidence {String(packet.evidence_packet_hash ?? "none").slice(0, 16)}</small></div>
                  <div><b>Latest Review</b><span>{packet.latest_review_status ?? "none"}</span><small>{packet.latest_review_id ?? "no saved response"}</small></div>
                  <div><b>Response Hash</b><span>{packet.latest_response_packet_hash_matches ? "match" : "missing/mismatch"}</span><small>{String(packet.latest_response_hash ?? "none").slice(0, 18)}</small></div>
                </div>
                <pre className="json-preview">{JSON.stringify(packet.request_preview ?? {}, null, 2)}</pre>
              </div>
            );
          })}
        </div>
        <div className="capability-table compact">
          {(verifiedReviewPacket?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
          {(verifiedReviewPacket?.secret_scan?.secret_like_paths ?? []).map((path: string) => (
            <div key={path}>
              <b>SECRET PATH</b>
              <span>blocked</span>
              <small>{path}</small>
            </div>
          ))}
        </div>
        <pre className="json-preview">{JSON.stringify(verifiedReviewPacket?.copy_safe_export_packet ?? {}, null, 2)}</pre>
        <p>{verifiedReviewPacket?.operator_message ?? "Verified provider packet is loading. It is for operator review only and cannot call providers or trade."}</p>
      </Panel>

      <Panel title="OpenAlgo-Safe Intent Preview Binding" span="wide" tab="execution" category="infra" badge={openAlgoSafeIntentBinding?.binding_version ?? "v1.46"}>
        <div className="dna-grid">
          <Metric label="State" value={openAlgoSafeIntentBinding?.preview_state ?? "pending"} />
          <Metric label="Binding Hash" value={String(openAlgoSafeIntentBinding?.binding_hash ?? "pending").slice(0, 16)} />
          <Metric label="Inspect" value={openAlgoSafeIntentBinding?.openalgo_may_inspect ? "allowed" : "blocked"} />
          <Metric label="Execute" value={openAlgoSafeIntentBinding?.openalgo_may_execute ? "unsafe" : "blocked"} />
          <Metric label="Trading Bot" value={openAlgoSafeIntentBinding?.trading_bot_may_execute ? "unsafe" : "blocked"} />
          <Metric label="Human Approval" value={openAlgoSafeIntentBinding?.external_human_approval_required ? "required" : "missing"} />
          <Metric label="Risk Check" value={openAlgoSafeIntentBinding?.external_risk_check_required ? "required" : "missing"} />
          <Metric label="Account Check" value={openAlgoSafeIntentBinding?.external_account_state_required ? "required" : "missing"} />
          <Metric label="Warnings" value={String(openAlgoSafeIntentBinding?.warning_count ?? 0)} />
          <Metric label="Blocks" value={String(openAlgoSafeIntentBinding?.blocking_count ?? 0)} />
          <Metric label="Routing" value={openAlgoSafeIntentBinding?.order_routing_enabled ? "unsafe" : "blocked"} />
          <Metric label="Live" value={openAlgoSafeIntentBinding?.live_trading_blocked ? "blocked" : "unsafe"} />
        </div>
        <div className="comparison-grid">
          <div>
            <h4>Intent Preview</h4>
            <pre className="json-preview">{JSON.stringify(openAlgoSafeIntentBinding?.intent_preview ?? {}, null, 2)}</pre>
          </div>
          <div>
            <h4>Binding Summary</h4>
            <pre className="json-preview">{JSON.stringify({
              jarvis: openAlgoSafeIntentBinding?.jarvis_summary ?? {},
              verified_packet: openAlgoSafeIntentBinding?.verified_packet_summary ?? {},
              disagreement: openAlgoSafeIntentBinding?.disagreement_summary ?? {},
              openalgo: openAlgoSafeIntentBinding?.openalgo_summary ?? {},
            }, null, 2)}</pre>
          </div>
        </div>
        <div className="capability-table compact">
          {(openAlgoSafeIntentBinding?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <p>{openAlgoSafeIntentBinding?.operator_message ?? "OpenAlgo-safe intent binding is loading. It binds evidence for paper/sim review only and cannot execute."}</p>
      </Panel>

      <Panel title="OpenAlgo Report Evidence" tab="trade" badge={openalgo?.effect ?? "v0.93"}>
        <Metric label="Report" value={openalgo?.report_available ? "imported" : "not imported"} />
        <Metric label="Report ID" value={String(openalgo?.latest_report_id ?? "none").slice(0, 18)} />
        <Metric label="Fill Quality" value={openalgo?.fill_quality ?? "unknown"} />
        <Metric label="Slippage" value={openalgo?.slippage_bps !== null && openalgo?.slippage_bps !== undefined ? `${openalgo.slippage_bps} bps` : "unknown"} />
        <Metric label="Routing" value={openalgo?.order_routing_enabled ? "unsafe" : "blocked"} />
        <Metric label="Live Trading" value={openalgo?.live_trading_blocked ? "blocked" : "unsafe"} />
        {(openalgo?.rejection_reasons ?? []).map((reason: string) => (
          <div className="list-row single" key={reason}><span>REJECT: {reason}</span></div>
        ))}
        {(openalgo?.warnings ?? []).map((warning: string) => (
          <div className="list-row single" key={warning}><span>WARN: {warning}</span></div>
        ))}
        <p>Imported OpenAlgo reports are evidence only. They can reduce confidence or trigger review, but cannot approve an entry or create a broker order.</p>
      </Panel>

      <Panel title="Paper Execution Reality Check" tab="trade" badge={paperReality?.jarvis_effect?.effect ?? "v0.94"}>
        <Metric label="Entry" value={paperReality?.entry_price !== null && paperReality?.entry_price !== undefined ? String(paperReality.entry_price) : "pending"} />
        <Metric label="Observed Fill" value={paperReality?.observed_fill_price !== null && paperReality?.observed_fill_price !== undefined ? String(paperReality.observed_fill_price) : "pending"} />
        <Metric label="Stop" value={paperReality?.stop_loss !== null && paperReality?.stop_loss !== undefined ? String(paperReality.stop_loss) : "pending"} />
        <Metric label="Target" value={paperReality?.target !== null && paperReality?.target !== undefined ? String(paperReality.target) : "pending"} />
        <Metric label="Adjusted R:R" value={paperReality?.adjusted_risk_reward !== null && paperReality?.adjusted_risk_reward !== undefined ? String(paperReality.adjusted_risk_reward) : "pending"} />
        <Metric label="Cost" value={`${paperReality?.all_in_cost_bps ?? 0} bps`} />
        <Metric label="Fill Quality" value={paperReality?.fill_quality ?? "unknown"} />
        <Metric label="Latency" value={`${paperReality?.latency_ms ?? 0} ms`} />
        {(paperReality?.jarvis_effect?.reasons ?? []).map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
        <div className="capability-table compact">
          {(paperReality?.gates ?? []).map((gate: any) => (
            <div key={gate.gate_id}>
              <b>{gate.gate_id}</b>
              <span>{gate.passed ? "pass" : gate.effect.toUpperCase()}</span>
              <small>{gate.name}</small>
            </div>
          ))}
        </div>
        <p>Reality check is paper-only. Bad fill, high cost, weak adjusted R:R, or missing report can downgrade the idea but can never approve a trade.</p>
      </Panel>

      <Panel title="Jarvis Trust And Priority" tab="trade" badge={widgets?.trust_score_dashboard?.trust_label ?? "v0.95"}>
        <Metric label="Trust" value={`${widgets?.trust_score_dashboard?.trust_score_pct ?? 0}%`} />
        <Metric label="Evidence" value={widgets?.trust_score_dashboard?.evidence_quality ?? "LOW"} />
        <Metric label="Matches" value={String(widgets?.trust_score_dashboard?.similar_matches ?? 0)} />
        <Metric label="Priority" value={widgets?.watchlist_priority_ranker?.priority_label ?? "pending"} />
        <Metric label="Warnings" value={String(widgets?.trust_score_dashboard?.warning_count ?? 0)} />
        <Metric label="Blocks" value={String(widgets?.trust_score_dashboard?.block_count ?? 0)} />
        {(widgets?.watchlist_priority_ranker?.drivers ?? []).map((driver: string) => (
          <div className="list-row single" key={driver}><span>{driver}</span></div>
        ))}
        <p>Priority is for research focus only. It cannot auto-trade or bypass the arbiter.</p>
      </Panel>

      <Panel title="Jarvis Usefulness Memory" tab="trade" badge={usefulness?.calibration_status ?? "v0.96"}>
        <Metric label="Average" value={`${usefulness?.average_usefulness_pct ?? 0}%`} />
        <Metric label="Records" value={String(usefulness?.record_count ?? 0)} />
        <Metric label="Pending Outcomes" value={String(usefulness?.pending_outcome_count ?? 0)} />
        <Metric label="Minimum History" value={usefulness?.minimum_history_pass ? "pass" : "building"} />
        <Metric label="Latest Score" value={`${Math.round(Number(usefulnessRecord?.usefulness_score ?? 0) * 100)}%`} />
        <Metric label="Latest Label" value={usefulnessRecord?.usefulness_label ?? "pending"} />
        {(usefulness?.latest_records ?? []).slice(0, 5).map((record: any) => (
          <div className="list-row" key={record.usefulness_id}>
            <b>{record.final_action} / {record.usefulness_label}</b>
            <span>{Math.round(Number(record.usefulness_score ?? 0) * 100)}%</span>
            <small>{record.scenario_label} | outcome pending {String(record.pending_outcome_label)}</small>
          </div>
        ))}
        <p>Usefulness memory tracks whether Jarvis guidance deserves future trust. It is calibration memory, not trading permission.</p>
      </Panel>

      <Panel title="Jarvis Action Checklist" tab="trade" badge={`${widgets?.action_checklist?.ready_count ?? 0}/${widgets?.action_checklist?.total_count ?? 0}`}>
        {(widgets?.action_checklist?.items ?? []).map((item: any) => (
          <div className="list-row" key={item.step}>
            <b>{item.passed ? "PASS" : "CHECK"} {item.step}</b>
            <span>{item.label}</span>
            <small>{item.detail}</small>
          </div>
        ))}
        <p>{widgets?.action_checklist?.operator_message ?? "Checklist is loading. No trading action is possible."}</p>
      </Panel>

      <Panel title="Analog Timeline" tab="trade" badge={`${widgets?.analog_timeline?.items?.length ?? 0} analogs`}>
        {(widgets?.analog_timeline?.items ?? []).map((item: any) => (
          <div className="list-row" key={`${item.label}-${item.timestamp_ns}`}>
            <b>{item.label}</b>
            <span>{item.similarity_score_pct}% similar</span>
            <small>{new Date(Number(item.timestamp_ns) / 1_000_000).toLocaleString()} | {item.verify_hint}</small>
          </div>
        ))}
        {(widgets?.analog_timeline?.items ?? []).length === 0 && <p>{widgets?.analog_timeline?.empty_state ?? "No analog timeline is available."}</p>}
      </Panel>

      <Panel title="Gemini Decision Review Room" span="wide" tab="trade" category="ai_ops" badge={geminiDecisionRoom?.decision_room_version ?? "v1.30"}>
        <div className="dna-grid">
          <Metric label="Safe Action" value={geminiDecisionRoom?.safe_final_action ?? "TRADE_VISION_ONLY"} />
          <Metric label="Provider" value={geminiDecisionRoom?.provider_status ?? "unavailable"} />
          <Metric label="Keys" value={`${geminiDecisionRoom?.configured_key_slots ?? 0}/${geminiDecisionRoom?.fallback_key_slots_supported ?? 5}`} />
          <Metric label="Freshness" value={geminiDecisionRoom?.freshness_state ?? "pending"} />
          <Metric label="Review Display" value={geminiDecisionRoom?.review_display_allowed ? "allowed" : "blocked"} />
          <Metric label="Network" value={geminiDecisionRoom?.network_call_allowed ? "unsafe" : "blocked"} />
          <Metric label="Confidence Boost" value={geminiDecisionRoom?.confidence_boost_allowed ? "unsafe" : "blocked"} />
          <Metric label="Routing" value={geminiDecisionRoom?.order_routing_enabled ? "unsafe" : "blocked"} />
        </div>
        <div className="list-row single">
          <span>Request {String(geminiDecisionRoom?.outbound_request_hash ?? "pending").slice(0, 12)} | Evidence {String(geminiDecisionRoom?.evidence_packet_hash ?? "pending").slice(0, 12)} | Redactions {String(geminiDecisionRoom?.redaction_count ?? 0)}</span>
        </div>
        {(geminiDecisionRoom?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{geminiDecisionRoom?.operator_message ?? "Gemini decision room is loading. External AI remains reviewer-only."}</p>
      </Panel>

      <AiCredentialsPanel status={data.aiCredentialStatus?.data} />

      <Panel title="Gemini Provider Manager" tab="vault" category="ai_ops" badge={geminiStatus?.provider_version ?? "v0.89"}>
        <Metric label="Status" value={geminiStatus?.status ?? "unavailable"} />
        <Metric label="Mode" value={geminiStatus?.mode ?? "safe stub"} />
        <Metric label="Model" value={geminiStatus?.selected_model ?? "pending"} />
        <Metric label="Schema" value={geminiStatus?.review_schema_version ?? "pending"} />
        <Metric label="Circuit" value={geminiStatus?.circuit_breaker?.state ?? "open"} />
        <Metric label="Timeout" value={`${geminiStatus?.timeout_ms ?? 2000} ms`} />
        <Metric label="Cost Ceiling" value={`$${geminiStatus?.quota_policy?.daily_cost_ceiling_usd ?? 5}/day`} />
        <Metric label="Prompt" value={geminiStatus?.prompt_policy?.policy_version ?? "pending"} />
        <div className="capability-table compact">
          {(geminiStatus?.key_slots ?? []).map((slot: any) => (
            <div key={slot.slot}>
              <b>{slot.env_name}</b>
              <span>{slot.configured ? "configured" : "empty"}</span>
              <small>priority {slot.priority}; no key value, suffix, or fingerprint exposed</small>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Gemini Fallback Readiness" tab="vault" category="ai_ops" badge={geminiFallbackReadiness?.readiness_version ?? "v1.18"}>
        <Metric label="State" value={geminiFallbackReadiness?.readiness_state ?? "pending"} />
        <Metric label="Configured" value={`${geminiFallbackReadiness?.configured_key_slots ?? 0}/${geminiFallbackReadiness?.fallback_key_slots_supported ?? 5}`} />
        <Metric label="Backend Only" value={geminiFallbackReadiness?.backend_only_keys ? "yes" : "no"} />
        <Metric label="Keys Exposed" value={geminiFallbackReadiness?.keys_exposed_to_frontend ? "unsafe" : "no"} />
        <Metric label="Forbidden Fields" value={String((geminiFallbackReadiness?.forbidden_key_material_paths ?? []).length)} />
        <Metric label="Dry Run" value={geminiFallbackReadiness?.dry_run_only ? "yes" : "pending"} />
        <Metric label="Network" value={geminiFallbackReadiness?.network_call_allowed ? "unsafe" : "blocked"} />
        <Metric label="Live Call" value={geminiFallbackReadiness?.live_call_performed ? "unsafe" : "no"} />
        <Metric label="Circuit" value={geminiFallbackReadiness?.circuit_state ?? "pending"} />
        <Metric label="Routing" value={geminiFallbackReadiness?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="capability-table compact">
          {(geminiFallbackReadiness?.public_key_slots ?? []).map((slot: any) => (
            <div key={slot.slot}>
              <b>{slot.env_name}</b>
              <span>{slot.configured ? "configured" : "empty"}</span>
              <small>priority {slot.priority} | cooldown {slot.cooldown_until ?? "none"} | error {slot.last_error ?? "none"}</small>
            </div>
          ))}
        </div>
        <div className="list-row">
          <b>Rotation</b>
          <span>
            rate:{geminiFallbackReadiness?.rotation_policy?.rotate_on_rate_limit ? "yes" : "no"} |
            quota:{geminiFallbackReadiness?.rotation_policy?.rotate_on_quota ? "yes" : "no"} |
            transient:{geminiFallbackReadiness?.rotation_policy?.rotate_on_transient_error ? "yes" : "no"}
          </span>
          <small>retry per key: {String(geminiFallbackReadiness?.rotation_policy?.retry_per_key ?? "pending")}</small>
        </div>
        {(geminiFallbackReadiness?.forbidden_key_material_paths ?? []).map((path: string) => (
          <div className="list-row single" key={path}><span>FORBIDDEN KEY MATERIAL: {path}</span></div>
        ))}
        {(geminiFallbackReadiness?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{geminiFallbackReadiness?.operator_message ?? "Gemini fallback readiness is loading. Network calls and trading authority remain blocked."}</p>
      </Panel>

      <Panel title="Gemini Live Review Harness" tab="vault" category="ai_ops" badge={geminiLiveReviewHarness?.harness_version ?? "v1.19"}>
        <Metric label="State" value={geminiLiveReviewHarness?.execution_state ?? "pending"} />
        <Metric label="Execute" value={geminiLiveReviewHarness?.execute_requested ? "requested" : "dry run"} />
        <Metric label="Live Gate" value={geminiLiveReviewHarness?.live_network_gate_enabled ? "enabled" : "disabled"} />
        <Metric label="Network" value={geminiLiveReviewHarness?.network_call_attempted ? "attempted" : "not attempted"} />
        <Metric label="Live Call" value={geminiLiveReviewHarness?.live_call_performed ? "performed" : "no"} />
        <Metric label="Model" value={geminiLiveReviewHarness?.selected_model ?? "pending"} />
        <Metric label="Key Slot" value={String(geminiLiveReviewHarness?.selected_key_slot ?? "none")} />
        <Metric label="Key Exposed" value={geminiLiveReviewHarness?.selected_key_material_exposed ? "unsafe" : "no"} />
        <Metric label="Request Hash" value={String(geminiLiveReviewHarness?.request_body_hash ?? "pending").slice(0, 12)} />
        <Metric label="Routing" value={geminiLiveReviewHarness?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="capability-table compact">
          <div>
            <b>Endpoint</b>
            <span>{geminiLiveReviewHarness?.endpoint_method ?? "POST"}</span>
            <small>{geminiLiveReviewHarness?.endpoint_url ?? "Gemini generateContent endpoint pending"}</small>
          </div>
          <div>
            <b>Request Preview</b>
            <span>{geminiLiveReviewHarness?.request_body_preview?.contents_count ?? 0} contents</span>
            <small>{geminiLiveReviewHarness?.request_body_preview?.text_chars ?? 0} chars | API key included: {String(geminiLiveReviewHarness?.request_body_preview?.contains_api_key ?? false)}</small>
          </div>
          <div>
            <b>Response Validation</b>
            <span>{geminiLiveReviewHarness?.response_validation?.accepted_for_display ? "display allowed" : "not trusted"}</span>
            <small>schema:{String(geminiLiveReviewHarness?.response_validation?.schema_validation_passed ?? false)} | hallucination:{String(geminiLiveReviewHarness?.response_validation?.hallucination_detected ?? false)}</small>
          </div>
        </div>
        {(geminiLiveReviewHarness?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <p>{geminiLiveReviewHarness?.operator_message ?? "Gemini live review harness is loading. It does not call the network from the frontend."}</p>
      </Panel>

      <Panel title="Gemini Outbound Review Bundle" tab="vault" category="ai_ops" badge={geminiOutbound?.bundle_version ?? "v1.04"}>
        <Metric label="Dry Run" value={geminiOutbound?.dry_run_only ? "yes" : "pending"} />
        <Metric label="Live Call" value={geminiOutbound?.live_call_performed ? "unsafe" : "no"} />
        <Metric label="Network" value={geminiOutbound?.network_call_allowed ? "unsafe" : "blocked"} />
        <Metric label="Request Hash" value={String(geminiOutbound?.request_hash ?? "pending").slice(0, 12)} />
        <Metric label="Configured Keys" value={`${geminiOutbound?.configured_key_slots ?? 0}/${geminiOutbound?.fallback_key_slots_supported ?? 5}`} />
        <Metric label="Redactions" value={String(geminiOutbound?.sanitization?.redaction_count ?? 0)} />
        <Metric label="Secrets" value={geminiOutbound?.sanitization?.secrets_included ? "unsafe" : "excluded"} />
        <Metric label="Routing" value={geminiOutbound?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="capability-table compact">
          {(geminiOutbound?.key_rotation_plan ?? []).map((slot: any) => (
            <div key={slot.slot}>
              <b>{slot.env_name}</b>
              <span>{slot.configured ? "configured" : "empty"}</span>
              <small>priority {slot.priority}; no fingerprint or key value displayed</small>
            </div>
          ))}
        </div>
        {(geminiOutbound?.validation_before_send ?? []).map((check: any) => (
          <div className="list-row single" key={check.check_id}><span>{check.check_id}: {check.passed ? "PASS" : check.effect.toUpperCase()} - {check.name}</span></div>
        ))}
        <p>{geminiOutbound?.failure_policy?.on_timeout ?? "If Gemini is unavailable, Jarvis continues Trade Vision-only."}</p>
      </Panel>

      <Panel title="External AI Review Intake" tab="vault" category="ai_ops" badge={externalAiIntake?.intake_version ?? "v1.05"}>
        <Metric label="Source" value={externalAiIntake?.source ?? "gemini"} />
        <Metric label="Status" value={externalAiIntake?.intake_status ?? "pending"} />
        <Metric label="Display" value={externalAiIntake?.display_allowed ? "allowed" : "blocked"} />
        <Metric label="Safe Action" value={externalAiIntake?.safe_final_action ?? "TRADE_VISION_ONLY"} />
        <Metric label="Schema" value={externalAiIntake?.validation?.schema_validation_passed ? "pass" : "fail"} />
        <Metric label="Hallucination" value={externalAiIntake?.validation?.hallucination_detected ? "detected" : "none"} />
        <Metric label="Redactions" value={String(externalAiIntake?.sanitization?.redaction_count ?? 0)} />
        <Metric label="Routing" value={externalAiIntake?.order_routing_enabled ? "unsafe" : "blocked"} />
        <p>{externalAiIntake?.sanitized_candidate_response?.pattern_interpretation ?? "External AI response intake is waiting for validated JSON."}</p>
        <div className="list-row single"><span>{externalAiIntake?.sanitized_candidate_response?.entry_guidance ?? "No external entry guidance is trusted yet."}</span></div>
        <div className="list-row single"><span>{externalAiIntake?.sanitized_candidate_response?.risk_warning ?? "External AI risk warning unavailable."}</span></div>
        {(externalAiIntake?.validation?.hallucinated_evidence_keys ?? []).map((key: string) => (
          <div className="list-row single" key={key}><span>REJECTED CITATION: {key}</span></div>
        ))}
        {(externalAiIntake?.jarvis_effect?.reasons ?? []).map((reason: string) => (
          <div className="list-row single" key={reason}><span>{reason}</span></div>
        ))}
      </Panel>

      <Panel title="External AI Review Audit" tab="vault" category="ai_ops" badge={externalAiAudit?.summary_version ?? "v1.06"}>
        <Metric label="Records" value={String(externalAiAudit?.record_count ?? 0)} />
        <Metric label="Accepted" value={String(externalAiAudit?.accepted_count ?? 0)} />
        <Metric label="Rejected" value={String(externalAiAudit?.rejected_count ?? 0)} />
        <Metric label="Latest" value={externalAiAudit?.latest_status ?? "none"} />
        <Metric label="Sources" value={(externalAiAudit?.sources ?? []).join(", ") || "none"} />
        <Metric label="Boost" value={externalAiAudit?.confidence_boost_allowed ? "unsafe" : "blocked"} />
        <Metric label="Routing" value={externalAiAudit?.order_routing_enabled ? "unsafe" : "blocked"} />
        <Metric label="Live" value={externalAiAudit?.live_trading_blocked ? "blocked" : "unsafe"} />
        <p>Every external AI review is stored by hash and status for audit. Accepted reviews can be displayed only; rejected reviews remain useful as safety evidence.</p>
      </Panel>

      <Panel title="External AI Reliability Gate" tab="trade" category="ai_ops" badge={externalAiReliability?.reliability_version ?? "v1.07"}>
        <Metric label="State" value={externalAiReliability?.reliability_state ?? "pending"} />
        <Metric label="Records" value={String(externalAiReliability?.record_count ?? 0)} />
        <Metric label="Disagreement" value={externalAiReliability?.disagreement_detected ? "detected" : "none"} />
        <Metric label="Low Evidence" value={externalAiReliability?.low_evidence_detected ? "detected" : "no"} />
        <Metric label="Stale Review" value={externalAiReliability?.stale_review_history ? "stale" : "fresh"} />
        <Metric label="Daily Misses" value={String(externalAiReliability?.verified_daily_data?.missed_verified_daily_facts?.length ?? 0)} />
        <Metric label="Unverified Daily" value={externalAiReliability?.verified_daily_data?.unverified_daily_claims ? "blocked" : "none"} />
        <Metric label="Boost" value={externalAiReliability?.confidence_boost_allowed ? "unsafe" : "blocked"} />
        <Metric label="Trading" value={externalAiReliability?.trade_allowed ? "unsafe" : "blocked"} />
        <Metric label="Routing" value={externalAiReliability?.order_routing_enabled ? "unsafe" : "blocked"} />
        <Metric label="Live" value={externalAiReliability?.live_trading_blocked ? "blocked" : "unsafe"} />
        {(externalAiReliability?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        {(externalAiReliability?.verified_daily_data?.facts ?? []).map((fact: any) => (
          <div className="list-row" key={fact.fact_id}>
            <b>{fact.fact_id}</b>
            <span>{String(fact.value)}</span>
            <small>{fact.source}</small>
          </div>
        ))}
        <p>{externalAiReliability?.operator_message ?? "External AI reliability is pending. Trade Vision remains the verified authority."}</p>
      </Panel>

      <Panel title="Verified Evidence Certificate" tab="evidence" category="governance" badge={verifiedEvidence?.certificate_version ?? "v1.08"}>
        <Metric label="State" value={verifiedEvidence?.certificate_state ?? "pending"} />
        <Metric label="Allowed Keys" value={String(verifiedEvidence?.allowed_evidence_keys?.length ?? 0)} />
        <Metric label="Sections" value={String(verifiedEvidence?.evidence_sections?.length ?? 0)} />
        <Metric label="Missed Items" value={String(verifiedEvidence?.external_ai_missed_items?.length ?? 0)} />
        <Metric label="Blocked Claims" value={String(verifiedEvidence?.external_ai_blocked_claims?.length ?? 0)} />
        <Metric label="Closed Candle" value={verifiedEvidence?.daily_data_authority?.closed_candle_only ? "yes" : "pending"} />
        <Metric label="Boost" value={verifiedEvidence?.confidence_boost_allowed ? "unsafe" : "blocked"} />
        <Metric label="Routing" value={verifiedEvidence?.order_routing_enabled ? "unsafe" : "blocked"} />
        <div className="capability-table compact">
          {(verifiedEvidence?.evidence_sections ?? []).map((section: any) => (
            <div key={section.section_id}>
              <b>{section.section_id}</b>
              <span>{section.name}</span>
              <small>{(section.citable_keys ?? []).join(", ")}</small>
            </div>
          ))}
        </div>
        {(verifiedEvidence?.external_ai_missed_items ?? []).map((item: any) => (
          <div className="list-row" key={item.item_id}>
            <b>{item.item_id}</b>
            <span>{item.severity}</span>
            <small>{item.reason}</small>
          </div>
        ))}
        {(verifiedEvidence?.external_ai_blocked_claims ?? []).map((claim: any) => (
          <div className="list-row" key={claim.claim_id}>
            <b>{claim.claim_id}</b>
            <span>{claim.claim_type}</span>
            <small>{claim.repair}</small>
          </div>
        ))}
        {(verifiedEvidence?.gates ?? []).map((gate: any) => (
          <div className="list-row single" key={gate.gate_id}><span>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()} - {gate.name}</span></div>
        ))}
        <p>{verifiedEvidence?.operator_message ?? "Verified evidence certificate is loading. External AI has no authority."}</p>
      </Panel>

      <Panel title="Review Preflight Verdict" tab="evidence" category="governance" badge={reviewPreflight?.review_preflight_version ?? "v1.09"}>
        <Metric label="Verdict" value={reviewPreflight?.verdict_state ?? "pending"} />
        <Metric label="Blocks" value={String(reviewPreflight?.blocking_count ?? 0)} />
        <Metric label="Warnings" value={String(reviewPreflight?.warning_count ?? 0)} />
        <Metric label="Evidence Keys" value={String(reviewPreflight?.verified_evidence_summary?.allowed_evidence_key_count ?? 0)} />
        <Metric label="Missed Items" value={String(reviewPreflight?.verified_evidence_summary?.missed_item_count ?? 0)} />
        <Metric label="AI Reliability" value={reviewPreflight?.external_ai_summary?.reliability_state ?? "pending"} />
        <Metric label="OpenAlgo Dry Run" value={reviewPreflight?.preflight_summary?.openalgo_dry_run_allowed ? "allowed" : "blocked"} />
        <Metric label="Live" value={reviewPreflight?.live_trading_blocked ? "blocked" : "unsafe"} />
        <div className="capability-table compact">
          {(reviewPreflight?.review_targets ?? []).map((target: any) => (
            <div key={target.target_id}>
              <b>{target.target_id}</b>
              <span>{target.allowed ? "allowed" : "blocked"}</span>
              <small>{target.rule}</small>
            </div>
          ))}
        </div>
        {(reviewPreflight?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        {(reviewPreflight?.required_before_resubmission ?? []).slice(0, 6).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
        <p>{reviewPreflight?.operator_message ?? "Review preflight is loading. No external review or routing is trusted."}</p>
      </Panel>

      <Panel title="Correction Review Packet" tab="vault" category="ai_ops" badge={correctionPacket?.packet_version ?? "v1.10"}>
        <Metric label="State" value={correctionPacket?.packet_state ?? "pending"} />
        <Metric label="Correction Ready" value={correctionPacket?.ready_for_correction_review ? "yes" : "blocked"} />
        <Metric label="Decision Trust" value={correctionPacket?.ready_for_decision_trust ? "unsafe" : "blocked"} />
        <Metric label="Network" value={correctionPacket?.network_call_allowed ? "unsafe" : "blocked"} />
        <Metric label="Redactions" value={String(correctionPacket?.sanitization?.redaction_count ?? 0)} />
        <Metric label="Secrets" value={correctionPacket?.sanitization?.secrets_included ? "unsafe" : "excluded"} />
        <Metric label="Packet Hash" value={String(correctionPacket?.packet_hash ?? "pending").slice(0, 12)} />
        <Metric label="Request Hash" value={String(correctionPacket?.request_hash ?? "pending").slice(0, 12)} />
        <Metric label="OpenAlgo" value={correctionPacket?.ready_for_openalgo ? "unsafe" : "blocked"} />
        {(correctionPacket?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        <div className="capability-table compact">
          <div>
            <b>Must Address</b>
            <span>{(correctionPacket?.correction_contract?.must_address_missing_items ?? []).join(", ") || "none"}</span>
            <small>External AI must explain these missed evidence items.</small>
          </div>
          <div>
            <b>Blocked Claims</b>
            <span>{(correctionPacket?.correction_contract?.must_remove_blocked_claims ?? []).join(", ") || "none"}</span>
            <small>Unsupported daily/HTF claims must be removed or cited.</small>
          </div>
        </div>
        {(correctionPacket?.required_before_send ?? []).slice(0, 5).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
        <p>{correctionPacket?.operator_message ?? "Correction packet is loading. No external network call is made."}</p>
      </Panel>

      <Panel title="Correction Response Validator" tab="vault" category="ai_ops" badge={correctionValidation?.validation_version ?? "v1.11"}>
        <Metric label="Display" value={correctionValidation?.display_status ?? "pending"} />
        <Metric label="Accepted" value={correctionValidation?.accepted_for_correction_display ? "yes" : "blocked"} />
        <Metric label="Safe Action" value={correctionValidation?.safe_final_action ?? "TRADE_VISION_ONLY"} />
        <Metric label="Schema" value={correctionValidation?.base_validation?.schema_validation_passed ? "pass" : "fail"} />
        <Metric label="Hallucination" value={correctionValidation?.base_validation?.hallucination_detected ? "detected" : "none"} />
        <Metric label="Citations" value={correctionValidation?.citation_validation?.passed ? "allowed" : "blocked"} />
        <Metric label="Missing Items" value={correctionValidation?.missing_item_validation?.passed ? "addressed" : "open"} />
        <Metric label="Blocked Claims" value={correctionValidation?.blocked_claim_validation?.passed ? "removed" : "open"} />
        <Metric label="Daily Claims" value={correctionValidation?.daily_claim_validation?.passed ? "verified" : "blocked"} />
        <Metric label="Routing" value={correctionValidation?.order_routing_enabled ? "unsafe" : "blocked"} />
        {(correctionValidation?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        {(correctionValidation?.required_resubmission_items ?? []).slice(0, 6).map((item: string) => (
          <div className="list-row single" key={item}><span>{item}</span></div>
        ))}
        <p>Validated correction responses remain display-only and cannot alter Trade Vision, OpenAlgo, or risk gates.</p>
      </Panel>

      <Panel title="Correction Response Audit" tab="vault" category="ai_ops" badge={correctionAudit?.summary_version ?? "v1.12"}>
        <Metric label="Records" value={String(correctionAudit?.record_count ?? 0)} />
        <Metric label="Accepted" value={String(correctionAudit?.accepted_count ?? 0)} />
        <Metric label="Rejected" value={String(correctionAudit?.rejected_count ?? 0)} />
        <Metric label="Latest" value={correctionAudit?.latest_status ?? "none"} />
        <Metric label="Sources" value={(correctionAudit?.sources ?? []).join(", ") || "none"} />
        <Metric label="Packet Hash" value={String(correctionAudit?.latest_packet_hash ?? "pending").slice(0, 12)} />
        <Metric label="Routing" value={correctionAudit?.order_routing_enabled ? "unsafe" : "blocked"} />
        <Metric label="Live" value={correctionAudit?.live_trading_blocked ? "blocked" : "unsafe"} />
        {(correctionRecords ?? []).slice(0, 5).map((record: any) => (
          <div className="list-row" key={record.validation_id}>
            <b>{record.display_status}</b>
            <span>{record.source} / {record.safe_final_action}</span>
            <small>{String(record.validation_hash ?? "").slice(0, 12)} | {record.created_at}</small>
          </div>
        ))}
        <p>Every correction validation is stored by hash. Accepted means display-only; it never grants decision, OpenAlgo, or broker authority.</p>
      </Panel>

      <Panel title="External AI Audit Integrity" tab="vault" category="governance" badge={externalAiAuditIntegrity?.integrity_version ?? "v1.13"}>
        <Metric label="State" value={externalAiAuditIntegrity?.integrity_state ?? "pending"} />
        <Metric label="External Reviews" value={String(externalAiAuditIntegrity?.external_review_count ?? 0)} />
        <Metric label="Corrections" value={String(externalAiAuditIntegrity?.correction_response_count ?? 0)} />
        <Metric label="External Accepted" value={String(externalAiAuditIntegrity?.accepted_external_review_count ?? 0)} />
        <Metric label="Correction Accepted" value={String(externalAiAuditIntegrity?.accepted_correction_response_count ?? 0)} />
        <Metric label="Empty Ledger" value={externalAiAuditIntegrity?.ledger_empty_warning ? "warning" : "no"} />
        <Metric label="Stale History" value={externalAiAuditIntegrity?.stale_review_history ? "stale" : "fresh"} />
        <Metric label="Authority Issues" value={String(externalAiAuditIntegrity?.authority_issues?.length ?? 0)} />
        <Metric label="Verified Daily Policy" value={externalAiAuditIntegrity?.verified_daily_data_policy?.only_trade_vision_verified_daily_data_allowed ? "Trade Vision only" : "unsafe"} />
        <Metric label="Routing" value={externalAiAuditIntegrity?.order_routing_enabled ? "unsafe" : "blocked"} />
        <Metric label="Live" value={externalAiAuditIntegrity?.live_trading_blocked ? "blocked" : "unsafe"} />
        {(externalAiAuditIntegrity?.gates ?? []).map((gate: any) => (
          <div className="list-row" key={gate.gate_id}>
            <b>{gate.gate_id}: {gate.passed ? "PASS" : gate.effect.toUpperCase()}</b>
            <span>{gate.name}</span>
            <small>{gate.reason}</small>
          </div>
        ))}
        {[
          ...(externalAiAuditIntegrity?.external_review_issues ?? []),
          ...(externalAiAuditIntegrity?.correction_response_issues ?? []),
          ...(externalAiAuditIntegrity?.authority_issues ?? []),
        ].slice(0, 6).map((issue: any) => (
          <div className="list-row" key={`${issue.record_type}-${issue.record_id}-${issue.issue_type}`}>
            <b>{issue.issue_type}</b>
            <span>{issue.record_type}</span>
            <small>{issue.detail}</small>
          </div>
        ))}
        <p>{externalAiAuditIntegrity?.operator_message ?? "External AI audit integrity is loading. Decision authority stays inside Trade Vision."}</p>
      </Panel>

      <Panel title="Gemini Review Display" tab="trade" badge={geminiReview?.display_status ?? "sample"}>
        <Metric label="Source" value={geminiReview?.review_source ?? "not live"} />
        <Metric label="Live Call" value={geminiReview?.live_gemini_called ? "yes" : "no"} />
        <Metric label="Display" value={geminiReview?.display_allowed ? "allowed" : "blocked"} />
        <Metric label="Schema" value={geminiReview?.validation?.schema_validation_passed ? "pass" : "fail"} />
        <Metric label="Hallucination" value={geminiReview?.validation?.hallucination_detected ? "detected" : "none"} />
        <Metric label="Safe Action" value={geminiReview?.safe_final_action ?? "TRADE_VISION_ONLY"} />
        <p>{geminiReview?.candidate_response?.pattern_interpretation ?? "Gemini sample review is pending."}</p>
        <div className="list-row single"><span>{geminiReview?.candidate_response?.entry_guidance ?? "No external entry guidance is trusted yet."}</span></div>
        <div className="list-row single"><span>{geminiReview?.candidate_response?.risk_warning ?? "Risk warning unavailable."}</span></div>
        {(geminiReview?.candidate_response?.best_indicator_for_pattern ?? []).map((item: string) => (
          <div className="list-row single" key={item}><span>Relevant evidence: {item}</span></div>
        ))}
      </Panel>
    </div>
  );
}

function JarvisCandleChart({ room, decisionOutput }: { room: any; decisionOutput?: any }) {
  const bars = room?.chart_context?.bars ?? [];
  const overlays = room?.chart_context?.overlays ?? {};
  if (!room || bars.length === 0) return <p>Jarvis chart evidence is loading. No trading action is possible.</p>;
  const width = 860;
  const height = 260;
  const pad = 24;
  const highs = bars.map((bar: any) => Number(bar.high));
  const lows = bars.map((bar: any) => Number(bar.low));
  const decisionOverlay = decisionOutput?.chart_screen_focus ?? {};
  const entryZone = decisionOverlay.overlay_entry_zone ?? overlays.entry_zone ?? [];
  const overlayValues = [
    overlays.stop_loss,
    overlays.target,
    overlays.support,
    overlays.resistance,
    overlays.vwap,
    decisionOverlay.overlay_stop_loss,
    decisionOverlay.overlay_target,
    decisionOverlay.overlay_invalidation_level,
    ...(entryZone ?? []),
  ].filter((value) => typeof value === "number");
  const min = Math.min(...lows, ...overlayValues);
  const max = Math.max(...highs, ...overlayValues);
  const span = Math.max(0.01, max - min);
  const step = (width - pad * 2) / Math.max(bars.length, 1);
  const yFor = (price: number) => pad + ((max - price) / span) * (height - pad * 2);
  const line = (key: string, value: number | undefined, klass: string, label: string, testId: string) => {
    if (typeof value !== "number") return null;
    const y = yFor(value);
    return (
      <g key={key}>
        <line data-testid={testId} className={klass} x1={pad} x2={width - pad} y1={y} y2={y} />
        <text className={`overlay-label ${klass.replace("overlay ", "")}`} x={width - pad - 126} y={Math.max(14, y - 5)}>{label}: {value}</text>
      </g>
    );
  };
  const zoneTop = typeof entryZone?.[1] === "number" ? yFor(entryZone[1]) : null;
  const zoneBottom = typeof entryZone?.[0] === "number" ? yFor(entryZone[0]) : null;
  const similarMarkers = (decisionOutput?.similar_history_cases ?? []).slice(0, 5);
  const blockerRows = (decisionOutput?.blocker_rows ?? []).slice(0, 4);
  return (
    <div className="chart-replay" data-testid="jarvis-decision-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Jarvis decision room chart with entry stop target and evidence overlays">
        <rect className="plot-bg" x="0" y="0" width={width} height={height} rx="8" />
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
          <line key={ratio} className="grid" x1={pad} x2={width - pad} y1={pad + ratio * (height - pad * 2)} y2={pad + ratio * (height - pad * 2)} />
        ))}
        {zoneTop !== null && zoneBottom !== null && (
          <rect data-testid="jarvis-chart-entry-zone" className="entry-zone" x={pad} y={Math.min(zoneTop, zoneBottom)} width={width - pad * 2} height={Math.max(4, Math.abs(zoneBottom - zoneTop))} rx="4" />
        )}
        {bars.map((bar: any, idx: number) => {
          const x = pad + idx * step + step / 2;
          const open = Number(bar.open);
          const close = Number(bar.close);
          const high = Number(bar.high);
          const low = Number(bar.low);
          const top = yFor(Math.max(open, close));
          const bottom = yFor(Math.min(open, close));
          const bullish = close >= open;
          return (
            <g key={`${bar.timestamp_ns}-${idx}`} className={bullish ? "bullish" : "bearish"}>
              <line x1={x} x2={x} y1={yFor(high)} y2={yFor(low)} />
              <rect x={x - Math.max(1.5, step * 0.22)} y={top} width={Math.max(3, step * 0.44)} height={Math.max(2, bottom - top)} rx="1" />
            </g>
          );
        })}
        {similarMarkers.map((item: any, index: number) => {
          const x = pad + ((index + 1) / Math.max(2, similarMarkers.length + 1)) * (width - pad * 2);
          return (
            <g key={`${item.source}-${item.date}-${index}`} className="similar-marker" data-testid="jarvis-chart-similar-marker">
              <circle cx={x} cy={pad + 14} r="5" />
              <text x={x + 8} y={pad + 18}>{item.date ?? item.source}</text>
            </g>
          );
        })}
        {line("target", decisionOverlay.overlay_target ?? overlays.target, "overlay target", "Target", "jarvis-chart-target-line")}
        {line("stop", decisionOverlay.overlay_stop_loss ?? overlays.stop_loss, "overlay stop", "SL", "jarvis-chart-stop-line")}
        {line("invalidation", decisionOverlay.overlay_invalidation_level ?? overlays.support, "overlay invalidation", "Invalid", "jarvis-chart-invalidation-line")}
        {line("vwap", overlays.vwap, "overlay vwap", "VWAP", "jarvis-chart-vwap-line")}
      </svg>
      <div className="legend">
        <span className="entry-dot">Entry {(entryZone ?? []).join(" - ")}</span>
        <span className="stop-dot">SL {decisionOverlay.overlay_stop_loss ?? overlays.stop_loss}</span>
        <span className="target-dot">Target {decisionOverlay.overlay_target ?? overlays.target}</span>
        <span className="invalid-dot">Invalid {decisionOverlay.overlay_invalidation_level ?? overlays.support}</span>
        <span>VWAP {overlays.vwap}</span>
      </div>
      <div className="chart-chip-row">
        <span>{decisionOutput?.output_state ?? "decision output pending"}</span>
        <span>{decisionOutput?.pattern_now?.structure_read ?? "structure pending"}</span>
        {blockerRows.map((item: any, index: number) => (
          <span key={`${item.source}-${index}`} className="warn-chip" data-testid="jarvis-chart-blocker-chip">{item.source}: {item.severity}</span>
        ))}
      </div>
    </div>
  );
}

function Research({ data }: { data: AppData }) {
          const dq = data.dataQuality?.data;
          const readiness = data.behaviorRuntimeReadiness?.data;
          const chartReplay = data.behaviorChartReplay?.data;
          const indicatorExpansion = data.behaviorIndicatorExpansion?.data;
          const replayIndicatorChart = data.behaviorReplayIndicatorChart?.data;
          const replayIndicatorMatrix = data.behaviorReplayIndicatorMatrix?.data;
          const matrixDecisionReadiness = data.behaviorMatrixDecisionReadiness?.data;
          const tradeLifecycle = data.behaviorTradeLifecycle?.data;
          const lifecycleComparison = data.behaviorLifecycleComparison?.data;
          const lifecycleEvidence = data.behaviorLifecycleEvidence?.data;
          const tradeabilityGuidance = data.behaviorTradeabilityGuidance?.data;
          const stockMemoryProfile = data.stockMemoryProfile?.data;
          const kronosStatus = data.kronosStatus?.data;
          const kronosServiceStatus = data.kronosServiceStatus?.data;
          const kronosForecast = data.kronosForecast?.data;
          const twinCurrent = data.twinCurrent?.data;
          const twinDashboard = data.twinDashboard?.data;
          const openAlgoVerifier = data.openAlgoVerifier?.data;
          const openAlgoDryRun = data.openAlgoDryRun?.data;
          const openAlgoGoldenFixtures = data.openAlgoGoldenFixtures?.data;
          const openAlgoGoldenVerify = data.openAlgoGoldenVerify?.data;
          const openAlgoConformance = data.openAlgoConformance?.data;
          const openAlgoTransportStatus = data.openAlgoTransportStatus?.data;
          const openAlgoTransportOutbox = data.openAlgoTransportOutbox?.data ?? [];
          const openAlgoTransportTraces = data.openAlgoTransportTraces?.data ?? [];
          const openAlgoResilience = data.openAlgoResilience?.data;
          const openAlgoFaultHarness = data.openAlgoFaultHarness?.data;
          const openAlgoSecurityPosture = data.openAlgoSecurityPosture?.data;
          const openAlgoSecurityThreatReport = data.openAlgoSecurityThreatReport?.data;
          const deploymentReadiness = data.deploymentReadiness?.data;
          const deploymentSmoke = data.deploymentSmoke?.data;
          const finalReleaseAudit = data.finalReleaseAudit?.data;
          const jarvisFinalProductionAudit = data.jarvisFinalProductionAudit?.data;
          const jarvisReadinessRemediation = data.jarvisReadinessRemediation?.data;
          const [ingesting, setIngesting] = useState(false);
          const [importingOhlcv, setImportingOhlcv] = useState(false);
          const [ohlcvImport, setOhlcvImport] = useState<any | null>(null);
          async function ingest() {
            setIngesting(true);
            try {
              await api.ingestMockData(101, 96);
              window.location.reload();
            } finally {
              setIngesting(false);
            }
          }
          async function importOhlcv() {
            setImportingOhlcv(true);
            try {
              const result = await api.behaviorImportOhlcvSample();
              setOhlcvImport(result.data);
            } finally {
              setImportingOhlcv(false);
            }
          }
          async function importDownloadedReliance() {
            setImportingOhlcv(true);
            try {
              const result = await api.behaviorImportLocalReliancePreview(390, "tail");
              setOhlcvImport(result.data);
            } finally {
              setImportingOhlcv(false);
            }
          }
          const [timingSymbols, setTimingSymbols] = useState("RELIANCE, SBIN, TCS, INFY");
          const [timingRunning, setTimingRunning] = useState(false);
          const [timingProgress, setTimingProgress] = useState("");
          const [timingResult, setTimingResult] = useState<any | null>(null);
          const [timingError, setTimingError] = useState<string | null>(null);
          async function runTimingResearch() {
            setTimingRunning(true);
            setTimingError(null);
            setTimingResult(null);
            try {
              const symbols = timingSymbols.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
              if (symbols.length === 0) throw new Error("Enter at least one symbol");
              const jobResp = await api.orbTimingSubmit({
                symbols_source: "explicit",
                symbols,
                timeframe: "5m",
              });
              const jobId = (jobResp.data as any).job_id as string;
              let job: any = null;
              for (let i = 0; i < 600; i++) {
                await new Promise((r) => setTimeout(r, 2000));
                const resp = await api.orbTimingJob(jobId);
                job = resp.data as any;
                setTimingProgress(`${job.progress_pct ?? 0}% ${job.current_symbol ?? ""}`);
                if (job.status === "completed" || job.status === "failed") break;
              }
              if (job?.status === "completed") {
                setTimingResult(job.result);
              } else {
                setTimingError(job?.error ?? "research job did not complete");
              }
            } catch (err: any) {
              setTimingError(String(err?.message ?? err));
            } finally {
              setTimingRunning(false);
            }
          }
          return (
            <div className="workspace">
              <Panel title="Research Workbench" span="wide" badge="mock">
                <div className="toolbar">
                  <button onClick={ingest} disabled={ingesting}>{ingesting ? "Ingesting..." : "Ingest Mock PIT Snapshot"}</button>
                  <button onClick={importOhlcv} disabled={importingOhlcv}>{importingOhlcv ? "Importing..." : "Import Sample OHLCV CSV"}</button>
                  <button onClick={importDownloadedReliance} disabled={importingOhlcv}>{importingOhlcv ? "Importing..." : "Import Downloaded RELIANCE 1m"}</button>
                  <span>{data.snapshots?.data.length ?? 0} immutable snapshots</span>
                  <span>{data.featureRegistry?.data.length ?? 0} feature versions</span>
                </div>
                <div className="dna-grid">
                  <Metric label="Output Groups" value={String(readiness?.total_output_groups ?? 0)} />
                  <Metric label="Self Indicators" value={`${readiness?.self_indicator_returned ?? 0}/${readiness?.self_indicator_total ?? 0}`} />
                  <Metric label="PTA Markers" value={String(readiness?.pta_marker_total ?? 0)} />
                  <Metric label="Non-empty Sample" value={String(readiness?.non_empty_sample_outputs ?? 0)} />
                  <Metric label="No-signal Sample" value={String(readiness?.empty_no_signal_outputs ?? 0)} />
                  <Metric label="Indicator Tests" value={`${readiness?.automated_indicator_tests_passed ?? 0} pass / ${readiness?.automated_indicator_tests_skipped ?? 0} skip`} />
                </div>
                <div className="capability-table compact">
                  {readiness?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
      </Panel>
              <Panel title="ORB Timing Lab (v1.97)" span="wide" badge="research only">
                <div className="toolbar">
                  <input
                    value={timingSymbols}
                    onChange={(e) => setTimingSymbols(e.target.value)}
                    placeholder="RELIANCE, SBIN, TCS"
                    style={{ minWidth: 280 }}
                  />
                  <button onClick={runTimingResearch} disabled={timingRunning}>
                    {timingRunning ? `Running ${timingProgress}` : "Run Timing Research"}
                  </button>
                  {timingResult && (
                    <a href={api.orbTimingExportUrl(timingResult.run_id)}>Download CSV</a>
                  )}
                </div>
                {timingError && <small style={{ color: "#ff6b6b" }}>{timingError}</small>}
                {timingResult && (
                  <div className="capability-table compact">
                    {timingResult.leaderboard?.map((entry: any) => (
                      <div key={entry.symbol}>
                        <b>{entry.symbol}</b>
                        <span>
                          {entry.verdict === "OK"
                            ? `BEST ${entry.best_window_composite?.[0]}-${entry.best_window_composite?.[1]}`
                            : entry.verdict}
                        </span>
                        <small>
                          score {(entry.top_composite_score ?? 0).toFixed(2)} · spread {(entry.composite_spread ?? 0).toFixed(2)} · days {entry.session_days ?? 0}
                        </small>
                      </div>
                    ))}
                  </div>
                )}
                {timingResult && (
                  <small>
                    Window wins: {JSON.stringify(timingResult.universe_window_win_counts ?? {})} · Research only — no trade authority. Default windows: 09:20 / 09:30 / 09:35 / 09:40.
                  </small>
                )}
                {!timingResult && !timingError && (
                  <small>Per-stock ORB clock-window research (09:20 / 09:30 / 09:35 / 09:40) on 5m HSTRY data. Research only — no trade authority.</small>
                )}
              </Panel>
              <Panel title="Stock Memory Profile" span="wide" badge={stockMemoryProfile?.minimum_sample_pass ? "evidence pass" : "low evidence"}>
                <div className="dna-grid">
                  <Metric label="Snapshots" value={String(stockMemoryProfile?.snapshot_count ?? 0)} />
                  <Metric label="Memory Records" value={String(stockMemoryProfile?.memory_record_count ?? 0)} />
                  <Metric label="Similar History" value={String(stockMemoryProfile?.historical_match_count ?? 0)} />
                  <Metric label="Minimum Sample" value={stockMemoryProfile?.minimum_sample_pass ? "pass" : "blocked"} />
                  <Metric label="Freshness" value={`${Math.round((stockMemoryProfile?.freshness_score ?? 0) * 100)}%`} />
                  <Metric label="Live Trading" value={stockMemoryProfile?.live_trading_blocked ? "blocked" : "unsafe"} />
                </div>
                <p>{stockMemoryProfile?.stock_dna_summary?.stock_personality_summary ?? "Stock DNA memory profile is waiting for backend evidence."}</p>
                <div className="capability-table compact">
                  <div>
                    <b>Session</b>
                    <span>{String(stockMemoryProfile?.session_summary?.current_session_phase ?? "pending")}</span>
                    <small>Best {String(stockMemoryProfile?.session_summary?.best_trade_window ?? "n/a")} | Worst {String(stockMemoryProfile?.session_summary?.worst_trade_window ?? "n/a")}</small>
                  </div>
                  <div>
                    <b>Pattern Memory</b>
                    <span>{String(stockMemoryProfile?.pattern_memory_summary?.similarity_pattern ?? "pending")}</span>
                    <small>
                      Continue {Number(stockMemoryProfile?.pattern_memory_summary?.continuation_probability_pct ?? 0).toFixed(1)}% | Fakeout {Number(stockMemoryProfile?.pattern_memory_summary?.fakeout_probability_pct ?? 0).toFixed(1)}%
                    </small>
                  </div>
                  <div>
                    <b>Trust</b>
                    <span>{String(stockMemoryProfile?.trust_summary?.calibration_status ?? "pending")}</span>
                    <small>Aggregate {Math.round(Number(stockMemoryProfile?.trust_summary?.aggregate_trust_score ?? 0) * 100)}% | records {String(stockMemoryProfile?.trust_summary?.record_count ?? 0)}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {(stockMemoryProfile?.no_trade_memory_reasons ?? []).map((reason: string) => (
                    <div key={reason}>
                      <b>Memory Guard</b>
                      <span>{stockMemoryProfile?.trade_allowed ? "unsafe" : "blocked"}</span>
                      <small>{reason}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {stockMemoryProfile?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Kronos Forecast Engine" span="wide" badge={kronosStatus?.service_status ?? "reserved"}>
                <div className="dna-grid">
                  <Metric label="Repo" value={kronosStatus?.repo_present ? "present" : "reserved"} />
                  <Metric label="Service" value={kronosStatus?.service_present ? "present" : "reserved"} />
                  <Metric label="Bridge" value={kronosServiceStatus?.health_ok ? "service ready" : kronosServiceStatus?.fallback_to_mock ? "mock fallback" : "reserved"} />
                  <Metric label="Mode" value={kronosStatus?.mode ?? "mock"} />
                  <Metric label="Model" value={kronosForecast?.model_name ?? kronosStatus?.selected_model ?? "none"} />
                  <Metric label="Confidence" value={`${Math.round((kronosForecast?.forecast_confidence ?? 0) * 100)}%`} />
                  <Metric label="Live Trading" value={kronosForecast?.live_trading_blocked ? "blocked" : "unsafe"} />
                </div>
                <p>
                  Kronos is a research-only forecast prior. It receives point-in-time candle context and cannot execute orders, override no-trade, or override risk.
                </p>
                <div className="capability-table compact">
                  <div>
                    <b>v0.46 Service Bridge</b>
                    <span>{kronosServiceStatus?.service_status ?? "reserved"}</span>
                    <small>{kronosServiceStatus?.fallback_reason ?? "No bridge status loaded yet."}</small>
                  </div>
                  <div>
                    <b>Isolation</b>
                    <span>{kronosServiceStatus?.dependency_isolated ? "isolated" : "check"}</span>
                    <small>Heavy ML imports in main API: {String(kronosServiceStatus?.api_imports_heavy_ml ?? false)}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  <div>
                    <b>Input Guard</b>
                    <span>{kronosForecast?.input_validation?.passed ? "pass" : "blocked"}</span>
                    <small>
                      Candles {kronosForecast?.input_validation?.candle_count ?? 0} | Future {String(kronosForecast?.input_validation?.future_candle_rejected ?? false)} | Granularity {String(kronosForecast?.input_validation?.granularity_mismatch_rejected ?? false)}
                    </small>
                  </div>
                  <div>
                    <b>Sampled Forecast Path</b>
                    <span>{kronosForecast?.forecast_path?.trend_direction ?? "UNKNOWN"}</span>
                    <small>
                      Return {Number(kronosForecast?.forecast_path?.expected_return_pct ?? 0).toFixed(2)}% | Move {Number(kronosForecast?.forecast_path?.expected_move_atr ?? 0).toFixed(2)} ATR
                    </small>
                  </div>
                  <div>
                    <b>Uncertainty</b>
                    <span>{kronosForecast?.uncertainty?.discarded_for_high_uncertainty ? "discarded" : "usable"}</span>
                    <small>Score {Math.round((kronosForecast?.uncertainty?.uncertainty_score ?? 0) * 100)}% | Valid until {String(kronosForecast?.expiry?.valid_until ?? "pending")}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {(kronosForecast?.input_validation?.blockers ?? kronosForecast?.notes ?? []).map((item: string) => (
                    <div key={item}>
                      <b>Kronos Guard</b>
                      <span>{kronosForecast?.kronos_cannot_execute_orders ? "cannot execute" : "unsafe"}</span>
                      <small>{item}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Twin Machine Arbiter" span="wide" badge={twinCurrent?.agreement_state ?? "pending"}>
                <div className="dna-grid">
                  <Metric label="Behavior" value={twinCurrent?.behavior_decision ?? "pending"} />
                  <Metric label="Kronos" value={twinCurrent?.kronos_direction ?? "UNKNOWN"} />
                  <Metric label="Action" value={twinCurrent?.arbiter_action ?? "WAIT"} />
                  <Metric label="Agreement" value={`${Math.round((twinCurrent?.agreement_score ?? 0) * 100)}%`} />
                  <Metric label="Trade Allowed" value={twinCurrent?.trade_allowed ? "yes" : "no"} />
                  <Metric label="Order Routing" value={twinCurrent?.order_routing_enabled ? "enabled" : "disabled"} />
                </div>
                <p>
                  Twin Arbiter compares Behavior DNA with Kronos. Conflict reduces action to WAIT or NO TRADE; it never upgrades unsafe setups.
                </p>
                <div className="capability-table compact">
                  {(twinCurrent?.conflict_reasons ?? []).map((reason: string) => (
                    <div key={reason}>
                      <b>Conflict / Evidence</b>
                      <span>{twinCurrent?.agreement_state ?? "pending"}</span>
                      <small>{reason}</small>
                    </div>
                  ))}
                  <div>
                    <b>Evidence Hash</b>
                    <span>{String(twinCurrent?.evidence_hash ?? "").slice(0, 16)}</span>
                    <small>Twin hash {String(twinCurrent?.twin_agreement_hash ?? "").slice(0, 16)} | live {twinCurrent?.live_trading_blocked ? "blocked" : "unsafe"}</small>
                  </div>
                </div>
              </Panel>
              <Panel title="Twin Machine Dashboard" span="wide" badge={twinDashboard?.recommended_workspace_action ?? "WAIT"}>
                <div className="dna-grid">
                  <Metric label="Behavior DNA" value={twinDashboard?.comparison?.behavior_decision ?? "pending"} />
                  <Metric label="Kronos Prior" value={twinDashboard?.comparison?.kronos_direction ?? "UNKNOWN"} />
                  <Metric label="Workspace Action" value={twinDashboard?.recommended_workspace_action ?? "WAIT"} />
                  <Metric label="Fan Points" value={String(twinDashboard?.forecast_path_points?.length ?? 0)} />
                  <Metric label="Reliability Samples" value={String(twinDashboard?.reliability?.sample_count ?? 0)} />
                  <Metric label="OpenAlgo Order" value={twinDashboard?.openalgo_intent_preview?.broker_order_created ? "created" : "preview only"} />
                </div>
                <p>
                  v0.47 displays the two-machine comparison: Behavior DNA remains the memory/risk authority, Kronos is the candle-path prior, and the Twin Arbiter blocks conflict before any future OpenAlgo handoff.
                </p>
                <div className="capability-table compact">
                  <div>
                    <b>Ghost Path</b>
                    <span>{String(twinDashboard?.ghost_path_summary?.direction ?? "UNKNOWN")}</span>
                    <small>
                      Return {Number(twinDashboard?.ghost_path_summary?.expected_return_pct ?? 0).toFixed(2)}% | ATR {Number(twinDashboard?.ghost_path_summary?.expected_move_atr ?? 0).toFixed(2)} | uncertainty {Math.round(Number(twinDashboard?.ghost_path_summary?.uncertainty_score ?? 0) * 100)}%
                    </small>
                  </div>
                  <div>
                    <b>Reliability Leaderboard</b>
                    <span>{String(twinDashboard?.reliability_leaderboard?.[0]?.engine ?? "pending")}</span>
                    <small>{(twinDashboard?.reliability_leaderboard ?? []).map((row: any) => `${row.engine}:${Math.round(Number(row.score ?? 0) * 100)}%`).join(" | ")}</small>
                  </div>
                  <div>
                    <b>OpenAlgo Preview</b>
                    <span>{twinDashboard?.openalgo_intent_preview?.export_status ?? "preview_only"}</span>
                    <small>Side {twinDashboard?.openalgo_intent_preview?.side ?? "NO_TRADE"} | permission {twinDashboard?.openalgo_intent_preview?.mode_permission ?? "mock_preview_only"} | routing {twinDashboard?.openalgo_intent_preview?.order_routing_enabled ? "enabled" : "disabled"}</small>
                  </div>
                  <div>
                    <b>Intent Signature</b>
                    <span>{String(twinDashboard?.openalgo_intent_preview?.intent_signature ?? "").slice(0, 16)}</span>
                    <small>Duplicate key {String(twinDashboard?.openalgo_intent_preview?.duplicate_key ?? "").slice(0, 16)} | expired {String(twinDashboard?.openalgo_intent_preview?.expired ?? false)}</small>
                  </div>
                  <div>
                    <b>Human Veto / Kill Switch</b>
                    <span>{twinDashboard?.openalgo_intent_preview?.human_veto_required ? "required" : "missing"}</span>
                    <small>Kill rechecked {String(twinDashboard?.openalgo_intent_preview?.kill_switch_rechecked ?? false)} | veto active {String(twinDashboard?.openalgo_intent_preview?.human_veto_active ?? false)}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {(twinDashboard?.safety_gate_matrix ?? []).map((gate: any) => (
                    <div key={gate.gate}>
                      <b>{gate.gate}</b>
                      <span>{gate.passed ? "pass" : "block"}</span>
                      <small>{gate.effect}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(twinDashboard?.conflict_explorer ?? []).map((item: any) => (
                    <div key={`${item.source}-${item.reason}`}>
                      <b>{item.source}</b>
                      <span>{item.state}</span>
                      <small>{item.reason}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  <div>
                    <b>v0.49 Bot Gate</b>
                    <span>{openAlgoVerifier?.rejected ? "rejected" : "review only"}</span>
                    <small>Signature {openAlgoVerifier?.signature_valid ? "valid" : "invalid"} | duplicate {String(openAlgoVerifier?.duplicate_detected ?? false)} | expired {String(openAlgoVerifier?.expired ?? false)}</small>
                  </div>
                  <div>
                    <b>External Checks</b>
                    <span>{openAlgoVerifier?.accepted_for_external_review ? "accepted" : "blocked"}</span>
                    <small>Human {String(openAlgoVerifier?.external_human_approval_present ?? false)} | risk {String(openAlgoVerifier?.external_risk_check_passed ?? false)} | account {String(openAlgoVerifier?.external_account_state_checked ?? false)}</small>
                  </div>
                  <div>
                    <b>Bot Verification Hash</b>
                    <span>{String(openAlgoVerifier?.verification_hash ?? "").slice(0, 16)}</span>
                    <small>Broker order {String(openAlgoVerifier?.broker_order_created ?? false)} | routing {String(openAlgoVerifier?.order_routing_enabled ?? false)}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {(openAlgoVerifier?.rejection_reasons ?? []).map((reason: string) => (
                    <div key={reason}>
                      <b>Bot Gate Rejection</b>
                      <span>blocked</span>
                      <small>{reason}</small>
                    </div>
                  ))}
                </div>
                <p>Hash {(twinDashboard?.dashboard_hash ?? "").slice(0, 16)} | live {twinDashboard?.live_trading_blocked ? "blocked" : "unsafe"}</p>
              </Panel>
              <Panel title="OpenAlgo Executor Dry-Run Package" span="wide" badge={openAlgoDryRun?.dry_run_only ? "v0.50 dry-run" : "pending"}>
                <div className="dna-grid">
                  <Metric label="Package" value={String(openAlgoDryRun?.package_id ?? "pending").slice(0, 24)} />
                  <Metric label="Executor" value={openAlgoDryRun?.target_executor ?? "openalgo"} />
                  <Metric label="Package SHA" value={String(openAlgoDryRun?.package_sha256 ?? "").slice(0, 16) || "pending"} />
                  <Metric label="Manifest SHA" value={String(openAlgoDryRun?.manifest_sha256 ?? "").slice(0, 16) || "pending"} />
                  <Metric label="Broker Order" value={openAlgoDryRun?.broker_order_created ? "unsafe" : "none"} />
                  <Metric label="Live Trading" value={openAlgoDryRun?.live_trading_blocked ? "blocked" : "unsafe"} />
                </div>
                <p>
                  v0.50 creates a JSON dry-run bundle for an external OpenAlgo/trading-bot adapter to inspect. It is evidence packaging only: no broker credentials, no broker order, and no route leaves Trade Vision.
                </p>
                <div className="capability-table compact">
                  <div>
                    <b>Package File</b>
                    <span>{String(openAlgoDryRun?.package_size_bytes ?? 0)} bytes</span>
                    <small>{openAlgoDryRun?.package_file_path ?? "package path pending"}</small>
                  </div>
                  <div>
                    <b>Manifest File</b>
                    <span>{String(openAlgoDryRun?.manifest_size_bytes ?? 0)} bytes</span>
                    <small>{openAlgoDryRun?.manifest_file_path ?? "manifest path pending"}</small>
                  </div>
                  <div>
                    <b>Verification State</b>
                    <span>{openAlgoDryRun?.verification?.accepted_for_external_review ? "review-ready" : "rejected"}</span>
                    <small>{String(openAlgoDryRun?.verification?.verification_hash ?? "").slice(0, 16)} | rejected {String(openAlgoDryRun?.verification?.rejected ?? true)}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {(openAlgoDryRun?.executor_required_checks ?? []).slice(0, 6).map((check: string) => (
                    <div key={check}>
                      <b>Executor Must Check</b>
                      <span>external</span>
                      <small>{check}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(openAlgoDryRun?.rejection_examples ?? []).map((example: any) => (
                    <div key={example.case_id}>
                      <b>{example.case_id}</b>
                      <span>{example.expected_executor_action}</span>
                      <small>{example.title}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Executor Golden Contract Fixtures" span="wide" badge={openAlgoGoldenVerify?.all_passed ? "v0.51 verified" : "check"}>
                <div className="dna-grid">
                  <Metric label="Fixtures" value={String(openAlgoGoldenFixtures?.fixture_count ?? 0)} />
                  <Metric label="Passed" value={`${openAlgoGoldenVerify?.passed_count ?? 0}/${openAlgoGoldenVerify?.fixture_count ?? 0}`} />
                  <Metric label="Deterministic" value={openAlgoGoldenFixtures?.deterministic ? "yes" : "check"} />
                  <Metric label="Registry SHA" value={String(openAlgoGoldenFixtures?.registry_hash ?? "").slice(0, 16) || "pending"} />
                  <Metric label="Broker Order" value={openAlgoGoldenVerify?.broker_order_created ? "unsafe" : "none"} />
                  <Metric label="Live Trading" value={openAlgoGoldenVerify?.live_trading_blocked ? "blocked" : "unsafe"} />
                </div>
                <p>
                  v0.51 freezes accepted-review, missing-check, duplicate, and expired examples into stable JSON fixtures. A future OpenAlgo adapter must reproduce these outcomes before integration can progress.
                </p>
                <div className="capability-table compact">
                  {(openAlgoGoldenFixtures?.fixtures ?? []).map((fixture: any) => {
                    const verification = (openAlgoGoldenVerify?.verifications ?? []).find((item: any) => item.fixture_id === fixture.fixture_id);
                    return (
                      <div key={fixture.fixture_id}>
                        <b>{fixture.scenario}</b>
                        <span>{verification?.passed ? "pass" : "fail"}</span>
                        <small>
                          Expected {fixture.expected_rejected ? "reject" : "external review only"} | hash {String(fixture.expected_package_hash ?? "").slice(0, 12)}
                        </small>
                      </div>
                    );
                  })}
                </div>
                <div className="capability-table compact">
                  {(openAlgoGoldenVerify?.verifications ?? []).flatMap((verification: any) =>
                    (verification.issues ?? []).map((issue: string) => (
                      <div key={`${verification.fixture_id}-${issue}`}>
                        <b>{verification.fixture_id}</b>
                        <span>failed</span>
                        <small>{issue}</small>
                      </div>
                    )),
                  )}
                </div>
              </Panel>
              <Panel title="OpenAlgo Adapter Conformance" span="wide" badge={openAlgoConformance?.all_passed ? "v0.52 conformant" : "blocked"}>
                <div className="dna-grid">
                  <Metric label="Adapter" value={openAlgoConformance?.adapter_name ?? "pending"} />
                  <Metric label="Version" value={openAlgoConformance?.adapter_version ?? "pending"} />
                  <Metric label="Cases" value={`${openAlgoConformance?.passed_count ?? 0}/${openAlgoConformance?.expected_fixture_count ?? 0}`} />
                  <Metric label="Registry" value={openAlgoConformance?.registry_hash_matches ? "match" : "mismatch"} />
                  <Metric label="Promotion" value={openAlgoConformance?.promotion_allowed ? "unsafe" : "blocked"} />
                  <Metric label="Routing" value={openAlgoConformance?.order_routing_enabled ? "unsafe" : "disabled"} />
                </div>
                <p>
                  v0.52 checks an adapter against every golden outcome and safety invariant. Passing means contract-compatible for further review, not approved for broker execution.
                </p>
                <div className="capability-table compact">
                  {(openAlgoConformance?.cases ?? []).map((item: any) => (
                    <div key={item.fixture_id}>
                      <b>{item.fixture_id}</b>
                      <span>{item.passed ? "pass" : "fail"}</span>
                      <small>
                        Outcome {item.outcome_matches ? "match" : "mismatch"} | reasons {item.rejection_reasons_match ? "match" : "mismatch"} | safety {item.safety_invariants_match ? "locked" : "failed"}
                      </small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  <div>
                    <b>Conformance Integrity</b>
                    <span>{String(openAlgoConformance?.report_hash ?? "").slice(0, 16) || "pending"}</span>
                    <small>{openAlgoConformance?.signature_algorithm ?? "sha256-canonical-json-integrity-only"}</small>
                  </div>
                  <div>
                    <b>Fixture Coverage</b>
                    <span>{openAlgoConformance?.all_passed ? "complete" : "incomplete"}</span>
                    <small>
                      Missing {(openAlgoConformance?.missing_fixture_ids ?? []).length} | unexpected {(openAlgoConformance?.unexpected_fixture_ids ?? []).length} | duplicate {(openAlgoConformance?.duplicate_fixture_ids ?? []).length}
                    </small>
                  </div>
                </div>
              </Panel>
              <Panel title="OpenAlgo Guarded Transport" span="wide" badge={openAlgoTransportStatus?.live_trading_blocked ? "v0.53 guarded" : "unsafe"}>
                <div className="dna-grid">
                  <Metric label="Adapter" value={openAlgoTransportStatus?.configured ? "configured" : "not configured"} />
                  <Metric label="Service Auth" value={openAlgoTransportStatus?.service_auth_configured ? "configured" : "not configured"} />
                  <Metric label="Circuit" value={openAlgoTransportStatus?.circuit_state ?? "unknown"} />
                  <Metric label="Pending" value={String(openAlgoTransportStatus?.pending_count ?? 0)} />
                  <Metric label="Retry Wait" value={String(openAlgoTransportStatus?.retry_wait_count ?? 0)} />
                  <Metric label="Acknowledged" value={String(openAlgoTransportStatus?.acknowledged_count ?? 0)} />
                  <Metric label="Manual Review" value={String(openAlgoTransportStatus?.manual_review_count ?? 0)} />
                  <Metric label="Dead Letter" value={String(openAlgoTransportStatus?.dead_letter_count ?? 0)} />
                  <Metric label="Cancelled" value={String(openAlgoTransportStatus?.cancelled_count ?? 0)} />
                  <Metric label="Order Routing" value={openAlgoTransportStatus?.order_routing_enabled ? "unsafe" : "disabled"} />
                </div>
                <p>
                  v0.53 persists research intent packages in an idempotent outbox. Delivery is explicit, authenticated between services, timeout-limited, retry-controlled, circuit-broken, and permanently unable to create broker orders.
                </p>
                <div className="capability-table compact">
                  {openAlgoTransportOutbox.length === 0 ? (
                    <div>
                      <b>Outbox</b>
                      <span>empty</span>
                      <small>No package has been queued for external adapter review.</small>
                    </div>
                  ) : openAlgoTransportOutbox.map((record: any) => (
                    <div key={record.delivery_id}>
                      <b>{record.package?.symbol ?? "unknown"} · {record.status}</b>
                      <span>{record.attempt_count}/{record.max_attempts}</span>
                      <small>
                        Idempotency {String(record.idempotency_key).slice(0, 12)} | routing {record.order_routing_enabled ? "unsafe" : "disabled"} | live {record.live_trading_blocked ? "blocked" : "unsafe"}
                      </small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(openAlgoTransportStatus?.notes ?? []).map((note: string) => (
                    <div key={note}>
                      <b>Transport invariant</b>
                      <span>enforced</span>
                      <small>{note}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {openAlgoTransportTraces.slice(0, 8).map((trace: any) => (
                    <div key={trace.trace_id}>
                      <b>{trace.event_type}</b>
                      <span>{trace.status}</span>
                      <small>
                        Attempt {trace.attempt_count} | actor {trace.actor_id}
                        {trace.latency_ms !== null ? ` | ${trace.latency_ms} ms` : ""}
                      </small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Transport Resilience SLO" span="wide" badge={openAlgoResilience?.overall_status ?? "v0.56"}>
                <div className="dna-grid">
                  <Metric label="Availability" value={`${Number(openAlgoResilience?.availability_pct ?? 0).toFixed(2)}%`} />
                  <Metric label="P95 Latency" value={`${Number(openAlgoResilience?.p95_delivery_latency_ms ?? 0).toFixed(1)} ms`} />
                  <Metric label="Retry Rate" value={`${Number(openAlgoResilience?.retry_rate_pct ?? 0).toFixed(2)}%`} />
                  <Metric label="Backlog" value={String(openAlgoResilience?.backlog_count ?? 0)} />
                  <Metric label="Health Samples" value={String(openAlgoResilience?.health_samples ?? 0)} />
                  <Metric label="Incident" value={openAlgoResilience?.incident?.status ?? "none"} />
                  <Metric label="Fault Harness" value={`${openAlgoFaultHarness?.passed_count ?? 0}/${openAlgoFaultHarness?.scenario_count ?? 0}`} />
                  <Metric label="Routing" value={openAlgoResilience?.order_routing_enabled ? "unsafe" : "disabled"} />
                </div>
                <p>
                  v0.56 measures delivery availability, latency, retries, backlog, health, and circuit state. Low sample counts remain explicitly low evidence; dead-letter and circuit failures alert immediately.
                </p>
                <div className="capability-table compact">
                  {(openAlgoResilience?.objectives ?? []).map((objective: any) => (
                    <div key={objective.objective_id}>
                      <b>{objective.name}</b>
                      <span>{objective.status}</span>
                      <small>{objective.reason}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(openAlgoResilience?.alerts ?? []).map((alert: any) => (
                    <div key={alert.alert_id}>
                      <b>{alert.code}</b>
                      <span>{alert.severity}</span>
                      <small>{alert.message} | {alert.runbook}</small>
                    </div>
                  ))}
                  {(openAlgoResilience?.alerts ?? []).length === 0 && (
                    <div>
                      <b>Active Alerts</b>
                      <span>none</span>
                      <small>No resilience alert is active in the current evidence window.</small>
                    </div>
                  )}
                </div>
                <div className="capability-table compact">
                  {(openAlgoFaultHarness?.scenarios ?? []).map((scenario: any) => (
                    <div key={scenario.scenario}>
                      <b>{scenario.scenario}</b>
                      <span>{scenario.passed ? "pass" : "fail"}</span>
                      <small>Expected {scenario.expected_status} | observed {scenario.observed_status}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Transport Security Boundary" span="wide" badge={openAlgoSecurityPosture?.overall_status ?? "v0.57"}>
                <div className="dna-grid">
                  <Metric label="Active Key" value={openAlgoSecurityPosture?.active_key_configured ? "configured" : "missing"} />
                  <Metric label="Rotation Key" value={openAlgoSecurityPosture?.previous_key_configured ? "ready" : "not staged"} />
                  <Metric label="Nonce Guard" value={openAlgoSecurityPosture?.nonce_replay_protection ? "active" : "missing"} />
                  <Metric label="Timestamp Skew" value={`${openAlgoSecurityPosture?.timestamp_skew_seconds ?? 0}s`} />
                  <Metric label="Request Limit" value={`${Math.round((openAlgoSecurityPosture?.max_request_bytes ?? 0) / 1_000_000)} MB`} />
                  <Metric label="Rate Limit" value={`${openAlgoSecurityPosture?.rate_limit_per_minute ?? 0}/min`} />
                  <Metric label="Trace Chain" value={openAlgoSecurityPosture?.trace_integrity?.valid ? "verified" : "failed"} />
                  <Metric label="Threat Tests" value={`${openAlgoSecurityThreatReport?.passed_count ?? 0}/${openAlgoSecurityThreatReport?.threat_count ?? 0}`} />
                </div>
                <p>
                  v0.57 signs each request with a unique nonce, accepts controlled key rotation, restricts network destinations, limits request size/rate, and verifies a chained transport audit trail.
                </p>
                <div className="capability-table compact">
                  {(openAlgoSecurityPosture?.checks ?? []).map((check: any) => (
                    <div key={check.check_id}>
                      <b>{check.name}</b>
                      <span>{check.passed ? "pass" : check.severity}</span>
                      <small>{check.evidence}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(openAlgoSecurityThreatReport?.results ?? []).map((result: any) => (
                    <div key={result.threat}>
                      <b>{result.threat}</b>
                      <span>{result.blocked ? "blocked" : "failed"}</span>
                      <small>{result.expected_control}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Deployment And Recovery Readiness" span="wide" badge={deploymentReadiness?.ready ? "v0.58 ready" : "blocked"}>
                <div className="dna-grid">
                  <Metric label="Target" value={deploymentReadiness?.target ?? "research_mock_stack"} />
                  <Metric label="Readiness" value={deploymentReadiness?.ready ? "ready" : "blocked"} />
                  <Metric label="Checks" value={`${deploymentReadiness?.pass_count ?? 0} pass`} />
                  <Metric label="Warnings" value={String(deploymentReadiness?.warn_count ?? 0)} />
                  <Metric label="Failures" value={String(deploymentReadiness?.fail_count ?? 0)} />
                  <Metric label="Config Drift" value={deploymentReadiness?.configuration?.drift_detected ? "detected" : "clear"} />
                  <Metric label="Smoke" value={`${deploymentSmoke?.passed_count ?? 0}/${deploymentSmoke?.check_count ?? 0}`} />
                  <Metric label="Live Broker" value={deploymentReadiness?.live_broker_deployment_allowed ? "unsafe" : "blocked"} />
                </div>
                <p>
                  v0.58 validates the reproducible research stack, dependency health, database integrity, configuration fingerprint, and brokerless deployment boundary. Backup and restore drills run only through privileged API actions.
                </p>
                <div className="capability-table compact">
                  {(deploymentReadiness?.checks ?? []).map((check: any) => (
                    <div key={check.check_id}>
                      <b>{check.name}</b>
                      <span>{check.status}</span>
                      <small>{check.evidence}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(deploymentSmoke?.checks ?? []).map((check: any) => (
                    <div key={check.check_id}>
                      <b>Smoke · {check.name}</b>
                      <span>{check.status}</span>
                      <small>{check.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Final Research Release Audit" span="wide" badge={finalReleaseAudit?.production_research_release_candidate ? "v0.59 candidate" : "blocked"}>
                <div className="dna-grid">
                  <Metric label="Research Stack" value={finalReleaseAudit?.research_stack_ready ? "ready" : "blocked"} />
                  <Metric label="Release Candidate" value={finalReleaseAudit?.production_research_release_candidate ? "yes" : "no"} />
                  <Metric label="Audit Gates" value={`${finalReleaseAudit?.pass_count ?? 0} pass`} />
                  <Metric label="Warnings" value={String(finalReleaseAudit?.warn_count ?? 0)} />
                  <Metric label="Failures" value={String(finalReleaseAudit?.fail_count ?? 0)} />
                  <Metric label="Resilience" value={finalReleaseAudit?.transport_resilience_status ?? "pending"} />
                  <Metric label="Source Scan" value={finalReleaseAudit?.static_safety_scan?.passed ? "clean" : "finding"} />
                  <Metric label="Artifacts" value={String(finalReleaseAudit?.release_manifest?.artifact_count ?? 0)} />
                  <Metric label="Live Trading" value={finalReleaseAudit?.live_trading_ready ? "unsafe" : "not approved"} />
                </div>
                <p>
                  {finalReleaseAudit?.release_scope ?? "v0.59 consolidates deployment, security, capability, source-safety, and artifact-integrity evidence for the brokerless research release."}
                </p>
                <div className="capability-table compact">
                  {(finalReleaseAudit?.gates ?? []).map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  <div>
                    <b>Static Safety Scan</b>
                    <span>{finalReleaseAudit?.static_safety_scan?.scanned_file_count ?? 0} files</span>
                    <small>{finalReleaseAudit?.static_safety_scan?.findings?.length ?? 0} executable live-route findings</small>
                  </div>
                  <div>
                    <b>Release Manifest</b>
                    <span>{String(finalReleaseAudit?.release_manifest?.manifest_sha256 ?? "").slice(0, 16) || "pending"}</span>
                    <small>{finalReleaseAudit?.release_manifest?.release_id ?? "release id pending"}</small>
                  </div>
                  <div>
                    <b>Operator Sign-off</b>
                    <span>{finalReleaseAudit?.operator_signoff_present ? "present" : "required"}</span>
                    <small>Automated readiness never enables broker routing or live execution.</small>
                  </div>
                </div>
              </Panel>
              <Panel title="Jarvis Final Production Readiness Audit" span="wide" badge={jarvisFinalProductionAudit?.audit_version ?? "v1.32"}>
                <div className="dna-grid">
                  <Metric label="Overall" value={jarvisFinalProductionAudit?.overall_state ?? "pending"} />
                  <Metric label="Research" value={jarvisFinalProductionAudit?.go_no_go?.research_dashboard ?? "NO_GO"} />
                  <Metric label="Paper/Sim" value={jarvisFinalProductionAudit?.go_no_go?.paper_sim_openalgo_inspection ?? "NO_GO"} />
                  <Metric label="Live Broker" value={jarvisFinalProductionAudit?.go_no_go?.live_broker_trading ?? "NO_GO"} />
                  <Metric label="Bot Execution" value={jarvisFinalProductionAudit?.go_no_go?.autonomous_bot_execution ?? "NO_GO"} />
                  <Metric label="Pass" value={String(jarvisFinalProductionAudit?.pass_count ?? 0)} />
                  <Metric label="Fail" value={String(jarvisFinalProductionAudit?.fail_count ?? 0)} />
                  <Metric label="Routing" value={jarvisFinalProductionAudit?.order_routing_enabled ? "unsafe" : "blocked"} />
                </div>
                <p>{jarvisFinalProductionAudit?.operator_message ?? "Jarvis final production audit is loading. Live trading remains blocked."}</p>
                <div className="capability-table compact">
                  {(jarvisFinalProductionAudit?.gates ?? []).map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.gate_id}: {gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.reason}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(jarvisFinalProductionAudit?.live_blockers ?? []).slice(0, 8).map((blocker: any) => (
                    <div key={blocker.blocker_id}>
                      <b>{blocker.blocker_id}</b>
                      <span>live blocked</span>
                      <small>{blocker.required_before_live}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Jarvis Readiness Remediation" span="wide" badge={jarvisReadinessRemediation?.remediation_version ?? "v1.33"}>
                <div className="dna-grid">
                  <Metric label="Current" value={jarvisReadinessRemediation?.current_overall_state ?? "pending"} />
                  <Metric label="Deployment" value={jarvisReadinessRemediation?.deployment_ready ? "ready" : "blocked"} />
                  <Metric label="Release" value={jarvisReadinessRemediation?.release_candidate ? "candidate" : "blocked"} />
                  <Metric label="Jarvis Research" value={jarvisReadinessRemediation?.jarvis_research_ready ? "ready" : "blocked"} />
                  <Metric label="Paper/Sim" value={jarvisReadinessRemediation?.jarvis_paper_sim_ready ? "ready" : "blocked"} />
                  <Metric label="Config Fix" value={jarvisReadinessRemediation?.ready_after_operator_config ? "likely" : "check"} />
                  <Metric label="Safe Apply" value={jarvisReadinessRemediation?.safe_to_apply_without_live_trading ? "yes" : "no"} />
                  <Metric label="Routing" value={jarvisReadinessRemediation?.order_routing_enabled ? "unsafe" : "blocked"} />
                </div>
                <p>{jarvisReadinessRemediation?.operator_message ?? "Readiness remediation is loading."}</p>
                <div className="capability-table compact">
                  {(jarvisReadinessRemediation?.remediation_steps ?? []).map((step: any) => (
                    <div key={step.remediation_id}>
                      <b>{step.title}</b>
                      <span>{step.requires_operator_config ? "operator config" : "review"}</span>
                      <small>{(step.actions ?? []).join(" | ")}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Real OHLCV Import Guard" span="wide" badge={ohlcvImport?.safe_for_research ? "research safe" : "v0.40"}>
                <div className="dna-grid">
                  <Metric label="Rows Parsed" value={String(ohlcvImport?.parsed_bar_count ?? 0)} />
                  <Metric label="Quality" value={`${Math.round((ohlcvImport?.quality?.data_quality_score ?? 0) * 100)}%`} />
                  <Metric label="PIT Guard" value={ohlcvImport?.point_in_time?.passed ? "pass" : "pending"} />
                  <Metric label="Snapshot" value={ohlcvImport?.persisted_snapshot_id ? "stored" : "not stored"} />
                  <Metric label="Trade Allowed" value={ohlcvImport?.trade_allowed ? "yes" : "no"} />
                  <Metric label="Live Trading" value={ohlcvImport?.live_trading_blocked !== false ? "blocked" : "unsafe"} />
                </div>
                <p>
                  v0.40 accepts real candle CSV only as point-in-time research input. It validates OHLC, duplicates, missing volume, timestamp order, split suspects, and future-candle leakage before later Stock DNA/backtest stages can use it.
                </p>
                <div className="capability-table compact">
                  <div>
                    <b>Import Version</b>
                    <span>{ohlcvImport?.import_version ?? "behavior-real-ohlcv-import.v0.40"}</span>
                    <small>Hash {(ohlcvImport?.payload_hash ?? "run import to create hash").slice(0, 16)}</small>
                  </div>
                  <div>
                    <b>Quality Blocks</b>
                    <span>{ohlcvImport?.quality?.blocks_trade ? "blocked" : "clear"}</span>
                    <small>
                      Invalid {ohlcvImport?.quality?.invalid_ohlc_count ?? 0} | Duplicate {ohlcvImport?.quality?.duplicate_timestamp_count ?? 0} | Gaps {ohlcvImport?.quality?.gap_count ?? 0}
                    </small>
                  </div>
                  <div>
                    <b>Point-in-Time</b>
                    <span>{ohlcvImport?.point_in_time?.blocks_trade ? "blocked" : "clear"}</span>
                    <small>
                      Allowed {ohlcvImport?.point_in_time?.allowed_bars ?? 0} | Future {ohlcvImport?.point_in_time?.future_bar_blocked ?? 0} | Incomplete {ohlcvImport?.point_in_time?.incomplete_candle_blocked ?? 0}
                    </small>
                  </div>
                </div>
                {(ohlcvImport?.warnings ?? []).map((warning: string) => (
                  <div className="list-row single" key={warning}><span>{warning}</span></div>
                ))}
              </Panel>
              <Panel title="Downloaded RELIANCE Candle Preview" span="wide" badge={ohlcvImport?.symbol === "RELIANCE" ? "local csv" : "waiting"}>
                <div className="dna-grid">
                  <Metric label="Symbol" value={ohlcvImport?.symbol ?? "none"} />
                  <Metric label="Timeframe" value={ohlcvImport?.timeframe ?? "1m"} />
                  <Metric label="Imported Bars" value={String(ohlcvImport?.parsed_bar_count ?? 0)} />
                  <Metric label="Safe Research" value={ohlcvImport?.safe_for_research ? "yes" : "pending"} />
                  <Metric label="Hash" value={(ohlcvImport?.payload_hash ?? "").slice(0, 12) || "pending"} />
                  <Metric label="Routing" value={ohlcvImport?.order_routing_enabled ? "unsafe" : "blocked"} />
                </div>
                <ImportedOhlcvPreview importResult={ohlcvImport} />
              </Panel>
              <Panel title="Chart Replay Workbench" span="wide" badge={chartReplay?.live_trading_blocked ? "visual only" : "check"}>
                <div className="dna-grid">
                  <Metric label="Candles" value={String(chartReplay?.candle_count ?? 0)} />
                  <Metric label="Selected" value={`#${chartReplay?.selected_sequence_number ?? 0}`} />
                  <Metric label="Overlays" value={String(chartReplay?.overlays?.length ?? 0)} />
                  <Metric label="PIT Evidence" value={chartReplay?.no_future_leakage ? "pass" : "check"} />
                  <Metric label="Trade Allowed" value={chartReplay?.trade_allowed ? "yes" : "no"} />
                  <Metric label="Live Trading" value={chartReplay?.live_trading_blocked ? "blocked" : "unsafe"} />
                </div>
                <ChartReplayWorkbench chart={chartReplay} />
                <div className="capability-table compact">
                  <div>
                    <b>Selected Candle</b>
                    <span>{chartReplay?.selected_candle?.candle_direction ?? "pending"}</span>
                    <small>
                      Body {Math.round((chartReplay?.selected_candle?.body_pct ?? 0) * 100)}% | Upper wick {Math.round((chartReplay?.selected_candle?.upper_wick_pct ?? 0) * 100)}% | Lower wick {Math.round((chartReplay?.selected_candle?.lower_wick_pct ?? 0) * 100)}%
                    </small>
                  </div>
                  <div>
                    <b>Hash / Base</b>
                    <span>{(chartReplay?.output_hash ?? "").slice(0, 12)}</span>
                    <small>Base {(chartReplay?.base_output_hash ?? "").slice(0, 12)} | {chartReplay?.chart_version ?? "behavior-chart-replay-workbench.v0.41"}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {chartReplay?.selected_candle?.evidence_rows?.map((row: string) => (
                    <div key={row}>
                      <b>Evidence</b>
                      <span>{chartReplay?.selected_candle?.marker_tags?.slice(0, 2).join(", ") || "no marker"}</span>
                      <small>{row}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {chartReplay?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Indicator Expansion Workbench" span="wide" badge={`${indicatorExpansion?.promoted_indicator_count ?? 0} promoted`}>
                <div className="dna-grid">
                  <Metric label="Inventory" value={String(indicatorExpansion?.candidate_output_groups ?? 0)} />
                  <Metric label="Base Overlays" value={String(indicatorExpansion?.base_indicator_count ?? 0)} />
                  <Metric label="Matrix Rows" value={String(indicatorExpansion?.matrix_indicator_count ?? 0)} />
                  <Metric label="Promoted" value={String(indicatorExpansion?.promoted_indicator_count ?? 0)} />
                  <Metric label="Proxy" value={String(indicatorExpansion?.proxy_indicator_count ?? 0)} />
                  <Metric label="Live Trading" value={indicatorExpansion?.live_trading_blocked ? "blocked" : "unsafe"} />
                </div>
                <p>
                  v0.42 expands beyond the 6 visual overlays by exposing a governed 32-row indicator matrix. Ready rows are promoted; proxy rows are visible but not falsely treated as complete indicators.
                </p>
                <div className="capability-table compact">
                  {indicatorExpansion?.items?.slice(0, 18).map((item: any) => (
                    <div key={item.row_id}>
                      <b>{item.row_id}</b>
                      <span>{item.status} / {item.signal}</span>
                      <small>
                        {item.family} | score {Number(item.normalized_score ?? 0).toFixed(2)} | {item.contract_name}
                      </small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {indicatorExpansion?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Replay Indicator Chart Validation" span="wide" badge={replayIndicatorChart?.deterministic ? "deterministic" : "check"}>
                <div className="dna-grid">
                  <Metric label="Candles" value={String(replayIndicatorChart?.candle_count ?? 0)} />
                  <Metric label="Indicators" value={String(replayIndicatorChart?.indicator_count ?? 0)} />
                  <Metric label="Chart Points" value={String(replayIndicatorChart?.chart_point_count ?? 0)} />
                  <Metric label="No Future Leakage" value={replayIndicatorChart?.no_future_leakage ? "pass" : "check"} />
                  <Metric label="Live Trading" value={replayIndicatorChart?.live_trading_blocked ? "blocked" : "unsafe"} />
                  <Metric label="Hash" value={(replayIndicatorChart?.output_hash ?? "").slice(0, 12)} />
                </div>
                <div className="capability-table compact">
                  {replayIndicatorChart?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {replayIndicatorChart?.chart_points?.slice(0, 8).map((point: any) => (
                    <div key={point.timestamp_ns}>
                      <b>{point.close.toFixed(2)}</b>
                      <span>VWAP {Number(point.indicator_overlay?.vwap ?? 0).toFixed(2)}</span>
                      <small>{point.markers?.slice(0, 3).join(", ") || "no marker"}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Replay Indicator Matrix" span="wide" badge={`${replayIndicatorMatrix?.matrix_indicator_count ?? 0} rows`}>
                <div className="dna-grid">
                  <Metric label="Matrix Rows" value={String(replayIndicatorMatrix?.matrix_indicator_count ?? 0)} />
                  <Metric label="Ready Rows" value={String(replayIndicatorMatrix?.ready_rows ?? 0)} />
                  <Metric label="Proxy Rows" value={String(replayIndicatorMatrix?.proxy_rows ?? 0)} />
                  <Metric label="Blocked Rows" value={String(replayIndicatorMatrix?.blocked_rows ?? 0)} />
                  <Metric label="Point-in-Time" value={replayIndicatorMatrix?.no_future_leakage ? "pass" : "check"} />
                  <Metric label="Hash" value={(replayIndicatorMatrix?.output_hash ?? "").slice(0, 12)} />
                </div>
                <div className="capability-table compact">
                  {replayIndicatorMatrix?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {replayIndicatorMatrix?.rows?.slice(0, 16).map((row: any) => (
                    <div key={row.row_id}>
                      <b>{row.row_id}</b>
                      <span>{row.signal} / {row.readiness_status}</span>
                      <small>{row.family} score {Number(row.normalized_score ?? 0).toFixed(2)}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Matrix Decision Readiness" span="wide" badge={matrixDecisionReadiness?.readiness_action ?? "pending"}>
                <div className="dna-grid">
                  <Metric label="Action" value={matrixDecisionReadiness?.readiness_action ?? "pending"} />
                  <Metric label="Bias" value={matrixDecisionReadiness?.directional_bias ?? "NEUTRAL"} />
                  <Metric label="Confidence" value={`${Math.round((matrixDecisionReadiness?.confidence_score ?? 0) * 100)}%`} />
                  <Metric label="Agreement" value={`${Math.round((matrixDecisionReadiness?.agreement_score ?? 0) * 100)}%`} />
                  <Metric label="Safety" value={`${Math.round((matrixDecisionReadiness?.safety_score ?? 0) * 100)}%`} />
                  <Metric label="Trade Allowed" value={matrixDecisionReadiness?.trade_allowed ? "yes" : "no"} />
                </div>
                <p>{matrixDecisionReadiness?.reason}</p>
                <div className="capability-table compact">
                  {matrixDecisionReadiness?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {(matrixDecisionReadiness?.blocker_reasons?.length ? matrixDecisionReadiness.blocker_reasons : ["No blocker beyond live-trading safety lock."]).map((reason: string) => (
                    <div key={reason}>
                      <b>Blocker</b>
                      <span>{matrixDecisionReadiness?.live_trading_blocked ? "live blocked" : "check"}</span>
                      <small>{reason}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Trade Lifecycle Simulation" span="wide" badge={tradeLifecycle?.lifecycle_status ?? "pending"}>
                <div className="dna-grid">
                  <Metric label="Lifecycle" value={tradeLifecycle?.lifecycle_status ?? "pending"} />
                  <Metric label="Readiness" value={tradeLifecycle?.readiness_action ?? "pending"} />
                  <Metric label="Outcome" value={tradeLifecycle?.outcome?.outcome_label ?? "pending"} />
                  <Metric label="Fill" value={tradeLifecycle?.execution?.fill_status ?? "pending"} />
                  <Metric label="MFE" value={Number(tradeLifecycle?.expected_MFE ?? 0).toFixed(2)} />
                  <Metric label="MAE" value={Number(tradeLifecycle?.expected_MAE ?? 0).toFixed(2)} />
                  <Metric label="Trade Allowed" value={tradeLifecycle?.trade_allowed ? "yes" : "no"} />
                  <Metric label="Live Blocked" value={tradeLifecycle?.live_trading_blocked ? "yes" : "check"} />
                </div>
                <p>{tradeLifecycle?.reason}</p>
                <div className="capability-table compact">
                  <div>
                    <b>Entry / Wrong</b>
                    <span>{tradeLifecycle?.entry_type ?? "pending"}</span>
                    <small>
                      Entry {Number(tradeLifecycle?.entry_price ?? 0).toFixed(2)} | SL {Number(tradeLifecycle?.stop_loss ?? 0).toFixed(2)} | Target {Number(tradeLifecycle?.target ?? 0).toFixed(2)} | RR {Number(tradeLifecycle?.risk_reward ?? 0).toFixed(2)}
                    </small>
                  </div>
                  <div>
                    <b>Execution Reality</b>
                    <span>{tradeLifecycle?.execution?.fill_quality ?? "pending"}</span>
                    <small>
                      Filled {tradeLifecycle?.execution?.filled_quantity ?? 0}/{tradeLifecycle?.execution?.requested_quantity ?? 0} | Cost {Number(tradeLifecycle?.execution?.costs?.total_cost_pct ?? 0).toFixed(4)}%
                    </small>
                  </div>
                  <div>
                    <b>State Path</b>
                    <span>{tradeLifecycle?.trade_state_path?.join(" -> ") ?? "pending"}</span>
                    <small>Outcome audit {tradeLifecycle?.outcome_run_id ?? "pending"}</small>
                  </div>
                </div>
                <div className="capability-table compact">
                  {tradeLifecycle?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Lifecycle Scenario Comparison" span="wide" badge={`${lifecycleComparison?.scenario_count ?? 0} scenarios`}>
                <div className="dna-grid">
                  <Metric label="Candidates" value={String(lifecycleComparison?.candidate_count ?? 0)} />
                  <Metric label="Blocked" value={String(lifecycleComparison?.blocked_count ?? 0)} />
                  <Metric label="Rejected" value={String(lifecycleComparison?.rejected_count ?? 0)} />
                  <Metric label="Avg MFE" value={Number(lifecycleComparison?.average_MFE ?? 0).toFixed(2)} />
                  <Metric label="Avg MAE" value={Number(lifecycleComparison?.average_MAE ?? 0).toFixed(2)} />
                  <Metric label="Live Blocked" value={lifecycleComparison?.all_live_trading_blocked ? "yes" : "check"} />
                </div>
                <p>
                  Best: {lifecycleComparison?.best_scenario_label ?? "pending"} | Worst: {lifecycleComparison?.worst_scenario_label ?? "pending"} | Hash {(lifecycleComparison?.output_hash ?? "").slice(0, 12)}
                </p>
                <div className="capability-table compact">
                  {lifecycleComparison?.items?.map((item: any) => (
                    <div key={`${item.scenario_id}-${item.seed}`}>
                      <b>{item.label}</b>
                      <span>{item.readiness_action} / {item.lifecycle_status}</span>
                      <small>
                        {item.outcome_label} | {item.fill_status} | MFE {Number(item.expected_MFE ?? 0).toFixed(2)} | MAE {Number(item.expected_MAE ?? 0).toFixed(2)} | live {item.live_trading_blocked ? "blocked" : "check"}
                      </small>
                    </div>
                  ))}
                </div>
                <div className="capability-table compact">
                  {lifecycleComparison?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Lifecycle Evidence Drilldown" span="wide" badge={`${lifecycleEvidence?.scenario_count ?? 0} scenarios`}>
                <div className="dna-grid">
                  <Metric label="Dominant Driver" value={lifecycleEvidence?.dominant_directional_driver ?? "pending"} />
                  <Metric label="Safety Pressure" value={lifecycleEvidence?.dominant_safety_pressure ?? "pending"} />
                  <Metric label="Candidates" value={String(lifecycleEvidence?.candidate_count ?? 0)} />
                  <Metric label="Blocked" value={String(lifecycleEvidence?.blocked_count ?? 0)} />
                  <Metric label="Point-in-Time" value={lifecycleEvidence?.no_future_leakage ? "pass" : "check"} />
                  <Metric label="Live Blocked" value={lifecycleEvidence?.all_live_trading_blocked ? "yes" : "check"} />
                </div>
                <p>
                  Evidence hash {(lifecycleEvidence?.output_hash ?? "").slice(0, 12)} | comparison {(lifecycleEvidence?.comparison_output_hash ?? "").slice(0, 12)}
                </p>
                <div className="capability-table compact">
                  {lifecycleEvidence?.items?.map((item: any) => {
                    const directional = item.top_directional_drivers?.[0];
                    const safety = item.top_safety_pressures?.[0];
                    const counter = item.top_counter_drivers?.[0];
                    return (
                      <div key={`${item.scenario_id}-${item.seed}`}>
                        <b>{item.label}</b>
                        <span>{item.readiness_action} / {item.lifecycle_status}</span>
                        <small>
                          Directional {directional?.row_id ?? "none"} ({Math.round((directional?.contribution_score ?? 0) * 100)}%) | Safety {safety?.row_id ?? "none"} ({Math.round((safety?.contribution_score ?? 0) * 100)}%) | Counter {counter?.row_id ?? "none"} | live {item.live_trading_blocked ? "blocked" : "check"}
                        </small>
                      </div>
                    );
                  })}
                </div>
                <div className="capability-table compact">
                  {lifecycleEvidence?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Tradeability Guidance" span="wide" badge={tradeabilityGuidance?.promotion_allowed ? "unsafe" : "research only"}>
                <div className="dna-grid">
                  <Metric label="Replay Candidates" value={String(tradeabilityGuidance?.replay_candidate_research_only_count ?? 0)} />
                  <Metric label="Research Watch" value={String(tradeabilityGuidance?.research_watch_count ?? 0)} />
                  <Metric label="Blocked" value={String(tradeabilityGuidance?.blocked_count ?? 0)} />
                  <Metric label="Avoid" value={String(tradeabilityGuidance?.avoid_count ?? 0)} />
                  <Metric label="Top Blocker" value={tradeabilityGuidance?.top_global_blocker ?? "pending"} />
                  <Metric label="Promotion" value={tradeabilityGuidance?.promotion_allowed ? "allowed" : "disabled"} />
                </div>
                <p>
                  Safest: {tradeabilityGuidance?.safest_scenario_label ?? "pending"} | Riskiest: {tradeabilityGuidance?.riskiest_scenario_label ?? "pending"} | Hash {(tradeabilityGuidance?.output_hash ?? "").slice(0, 12)}
                </p>
                <div className="capability-table compact">
                  {tradeabilityGuidance?.items?.map((item: any) => {
                    const firstStep = item.improvement_steps?.[0];
                    const safetyStep = item.improvement_steps?.find((step: any) => step.category === "safety_pressure");
                    return (
                      <div key={`${item.scenario_id}-${item.seed}`}>
                        <b>{item.label}</b>
                        <span>{item.tradeability_status} / {item.next_safe_action}</span>
                        <small>
                          Score {Math.round((item.tradeability_score ?? 0) * 100)}% | Driver {item.best_driver_row_id ?? "none"} | Safety {item.worst_safety_row_id ?? "none"} | Step {safetyStep?.action ?? firstStep?.action ?? "review"} | live {item.live_trading_blocked ? "blocked" : "check"}
                        </small>
                      </div>
                    );
                  })}
                </div>
                <div className="capability-table compact">
                  {tradeabilityGuidance?.gates?.map((gate: any) => (
                    <div key={gate.gate_id}>
                      <b>{gate.name}</b>
                      <span>{gate.status}</span>
                      <small>{gate.evidence}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Migrated Indicator Inventory" span="wide" badge={`${readiness?.indicator_groups?.length ?? 0} groups`}>
                <div className="capability-table compact">
                  {readiness?.indicator_groups?.slice(0, 36).map((group: any) => (
                    <div key={group.group_id}>
                      <b>{group.group_id}</b>
                      <span>{group.source}</span>
                      <small>{group.sample_status}</small>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Chart / Research / Replay Readiness" badge={readiness?.safe_mode ? "safe" : "check"}>
                <Metric label="Chart Output" value={readiness?.chart_output_ready ? "ready" : "check"} />
                <Metric label="Research Activity" value={readiness?.research_activity_ready ? "ready" : "check"} />
                <Metric label="Replay" value={readiness?.replay_ready ? "ready" : "check"} />
                <Metric label="Live Trading" value={readiness?.live_trading_blocked ? "blocked" : "unsafe"} />
                <Metric label="Safe Ports" value={(readiness?.browser_recommended_ports ?? []).join(", ")} />
                {readiness?.notes?.map((note: string) => (
                  <div className="list-row single" key={note}><span>{note}</span></div>
                ))}
              </Panel>
              <Panel title="Data Quality">
        <Metric label="Lookback" value={`${dq?.lookback_years ?? 0}Y`} />
        <Metric label="Survivorship Bias" value={dq?.survivorship_bias ? "Risk" : "Clean"} />
        <Metric label="Look-ahead Leakage" value={dq?.look_ahead_leakage ? "Risk" : "Pass"} />
      </Panel>
      <IntegrityPanel data={data.integrity?.data} />
    </div>
  );
}

function Replay({ data }: { data: AppData }) {
  const [seed, setSeed] = useState(42);
  const [session, setSession] = useState<any>(data.replay?.data);
  const replay = session ?? data.replay?.data;
  const firstEventTime = replay?.events?.[0]?.virtual_timestamp_ns ?? replay?.current_timestamp_ns ?? 0;
  const lastEventTime = replay?.events?.[replay.events.length - 1]?.virtual_timestamp_ns ?? replay?.current_timestamp_ns ?? 0;
  async function start() {
    const response = await api.startReplay(seed);
    setSession(response.data);
  }
  async function play() {
    if (!replay?.session_id) return;
    const response = await api.playReplay(replay.session_id);
    setSession(response.data);
  }
  async function pause() {
    if (!replay?.session_id) return;
    const response = await api.pauseReplay(replay.session_id);
    setSession(response.data);
  }
  async function step(steps = 1) {
    if (!replay?.session_id) return;
    const response = await api.stepReplay(replay.session_id, steps);
    setSession(response.data);
  }
  async function seek(timestamp: number) {
    if (!replay?.session_id) return;
    const response = await api.seekReplay(replay.session_id, timestamp);
    setSession(response.data);
  }
  return (
    <div className="workspace">
      <Panel title="Deterministic Replay" span="wide" badge={replay?.state ?? "paused"}>
        <div className="toolbar">
          <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
          <button onClick={start}>Start Seeded Replay</button>
          <button onClick={play}>Play</button>
          <button onClick={pause}>Pause</button>
          <button onClick={() => step(1)}>Step 1</button>
          <button onClick={() => step(5)}>Step 5</button>
          <button onClick={() => seek(firstEventTime)}>Seek Start</button>
          <button onClick={() => seek(lastEventTime)}>Seek End</button>
          <span>Session: {replay?.session_id}</span>
        </div>
        <div className="replay-strip">
          <Metric label="Seed" value={String(replay?.seed ?? seed)} />
          <Metric label="State" value={replay?.state ?? "pending"} />
          <Metric label="Current ns" value={String(replay?.current_timestamp_ns ?? 0)} />
          <Metric label="Events" value={String(replay?.events?.length ?? 0)} />
        </div>
        <div className="event-list">
          {replay?.events.map((event: any) => <div className="event" key={event.event_id}><b>#{event.sequence_number}</b><span>{event.symbol}</span><span>{String(event.payload.price)}</span><small>{event.watermark?.slice(0, 12)}</small></div>)}
        </div>
      </Panel>
      <ReplayEvidencePanels data={data} />
    </div>
  );
}

