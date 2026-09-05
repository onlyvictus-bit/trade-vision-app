import { readFileSync } from "node:fs";

const app = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const client = readFileSync(new URL("./src/api/client.ts", import.meta.url), "utf8");
const spec = readFileSync(new URL("../../SPEC.md", import.meta.url), "utf8");
const architecture = readFileSync(new URL("../../ARCHITECTURE.md", import.meta.url), "utf8");
const testPlan = readFileSync(new URL("../../TEST_PLAN.md", import.meta.url), "utf8");

const requiredAppSnippets = [
  "const FRONTEND_API_LOAD_CONCURRENCY = 4",
  "async function runBounded(",
  "onTaskError?: (error: unknown, index: number) => void",
  "refreshInFlight.current",
  "const criticalTvProdRed001 = await api.tvProdRed001().catch",
  "setData((current) => ({ ...current, tvProdRed001: criticalTvProdRed001 }))",
  "() => Promise.resolve(criticalTvProdRed001)",
  "Partial Evidence Load",
  "TV-PROD-RED-001 Manipulated-Wick Safety Proof",
  "hasTvProdRed001 ? (tvProdRed001?.passed ? \"red-team pass\" : \"release blocked\") : \"loading\"",
  "tvProdRed001?.passed ? \"PASS\" : \"BLOCK\"",
  "tvProdRed001?.paper_candidate_allowed ? \"unsafe\" : \"blocked\"",
  "tvProdRed001?.trade_allowed ? \"unsafe\" : \"blocked\"",
  "tvProdRed001?.order_routing_enabled ? \"unsafe\" : \"blocked\"",
  "hasTvProdRed001 && tvProdRed001?.live_trading_blocked === false ? \"unsafe\" : \"blocked\"",
  "tvProdRed001?.release_blocking ? \"blocked\" : \"gate clear\"",
  "tvProdRed001?.cache_status ?? \"pending\"",
  "tvProdRed001?.arbiter?.consulted_flags",
  "tvProdRed001?.volatility_status?.volatility_bucket",
];

const requiredClientSnippets = [
  "tvProdRed001: (symbol = \"RELIANCE\", timeframe = \"1m\")",
  "/api/v1/behavior/red-team/tv-prod-red-001",
  "encodeURIComponent(symbol)",
  "encodeURIComponent(timeframe)",
];

const requiredDocSnippets = [
  [spec, "Critical release-safety evidence, including TV-PROD-RED-001, must be fetched before bulk evidence hydration"],
  [spec, "Scheduled refreshes must not overlap"],
  [spec, "TV-PROD-RED-001 can hydrate even while slower non-critical evidence endpoints are still pending"],
  [architecture, "refresh in-flight guard"],
  [architecture, "critical safety evidence fetch"],
  [architecture, "Failed slots remain visibly pending/blocked"],
  [testPlan, "npm.cmd run verify:jarvis-redteam"],
  [testPlan, "TV-PROD-RED-001 hydrates before slower non-critical evidence panels"],
];

const missing = [];
for (const snippet of requiredAppSnippets) {
  if (!app.includes(snippet)) missing.push(`App.tsx missing ${snippet}`);
}
for (const snippet of requiredClientSnippets) {
  if (!client.includes(snippet)) missing.push(`client.ts missing ${snippet}`);
}
for (const [documentText, snippet] of requiredDocSnippets) {
  if (!documentText.includes(snippet)) missing.push(`docs missing ${snippet}`);
}

if (app.includes("api.tvProdRed001(),")) {
  missing.push("App.tsx must not fetch tvProdRed001 as an ordinary bulk eager endpoint");
}

if (missing.length > 0) {
  console.error("Jarvis red-team verification failed:");
  for (const item of missing) console.error(`- ${item}`);
  process.exit(1);
}

console.log("Jarvis red-team verification passed.");
