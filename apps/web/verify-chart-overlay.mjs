import { readFileSync } from "node:fs";

const app = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const css = readFileSync(new URL("./src/styles.css", import.meta.url), "utf8");

const requiredAppSnippets = [
  'data-testid="jarvis-decision-chart"',
  'data-testid="jarvis-chart-entry-zone"',
  'data-testid={testId}',
  'jarvis-chart-target-line',
  'jarvis-chart-stop-line',
  'jarvis-chart-invalidation-line',
  'jarvis-chart-vwap-line',
  'data-testid="jarvis-chart-similar-marker"',
  'data-testid="jarvis-chart-blocker-chip"',
  "Chart Overlay QA",
];

const requiredCssSnippets = [
  ".chart-replay .entry-zone",
  ".chart-replay .overlay.target",
  ".chart-replay .overlay.stop",
  ".chart-replay .overlay.invalidation",
  ".chart-replay .overlay-label",
  ".chart-replay .similar-marker",
  ".chart-chip-row",
  ".chart-chip-row .warn-chip",
];

const missing = [];
for (const snippet of requiredAppSnippets) {
  if (!app.includes(snippet)) missing.push(`App.tsx missing ${snippet}`);
}
for (const snippet of requiredCssSnippets) {
  if (!css.includes(snippet)) missing.push(`styles.css missing ${snippet}`);
}

if (missing.length > 0) {
  console.error("Chart overlay verification failed:");
  for (const item of missing) console.error(`- ${item}`);
  process.exit(1);
}

console.log("Chart overlay verification passed.");
