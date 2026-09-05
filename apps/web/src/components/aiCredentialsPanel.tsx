import { useState } from "react";
import { api } from "../api/client";
import { Metric, Panel } from "./primitives";

export function AiCredentialsPanel({ status }: { status: any }) {
  const [geminiSlot, setGeminiSlot] = useState(1);
  const [geminiKey, setGeminiKey] = useState("");
  const [grokKey, setGrokKey] = useState("");
  const [message, setMessage] = useState("Keys are saved only in the backend vault. Plain secrets are never returned to the browser.");
  const [busy, setBusy] = useState(false);

  const run = async (label: string, task: () => Promise<any>) => {
    setBusy(true);
    try {
      const result = await task();
      setMessage(`${label}: ${result.data?.vault_locked ? "vault locked" : result.data?.status ?? "done"}. Refresh will update masked status.`);
      setGeminiKey("");
      setGrokKey("");
    } catch (error) {
      setMessage(`${label} failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="AI Credential Vault" span="wide" badge={status?.vault_locked ? "locked" : "v1.34"}>
      <div className="dna-grid">
        <Metric label="Vault" value={status?.vault_locked ? "locked" : "unlocked"} />
        <Metric label="Secret Key" value={status?.secret_key_configured ? "configured" : "missing"} />
        <Metric label="Key Source" value={status?.secret_key_source ?? "missing"} />
        <Metric label="Gemini Slots" value={`${status?.gemini?.configured_slots ?? 0}/5`} />
        <Metric label="Active Gemini" value={String(status?.gemini?.active_slot ?? "none")} />
        <Metric label="Grok" value={status?.grok?.configured ? "configured" : "missing"} />
        <Metric label="Live Trading" value={status?.live_trading_blocked ? "blocked" : "unsafe"} />
      </div>
      <p>{message}</p>
      <div className="capability-table compact">
        <div>
          <b>Step 1: Local Vault Unlock File</b>
          <span>{status?.secret_key_path ?? status?.local_secret_key_path ?? "data\\secrets\\tradevision_secret.key"}</span>
          <small>Create this file with one long local secret line, then restart backend. This unlocks encrypted vault saving.</small>
        </div>
        <div>
          <b>Step 2: Encrypted Credential Vault</b>
          <span>{status?.vault_path ?? "data\\secrets\\ai_credentials.enc"}</span>
          <small>Created automatically after you save Gemini slot. Do not manually edit this file.</small>
        </div>
      </div>
      {status?.vault_locked && (
        <div className="list-row single">
          <span>Create the local vault unlock file shown above, or set TRADEVISION_SECRET_KEY, then restart backend before saving keys.</span>
        </div>
      )}
      <div className="capability-table compact">
        {(status?.gemini?.slots ?? []).map((slot: any) => (
          <div key={`gemini-${slot.slot}`}>
            <b>Gemini Slot {slot.slot}</b>
            <span>{slot.display ?? "not configured"}</span>
            <small>Fingerprint {slot.fingerprint ?? "none"} | plaintext returned: {String(slot.secret_returned_to_frontend)}</small>
          </div>
        ))}
        <div>
          <b>Grok / xAI API Key</b>
          <span>{status?.grok?.display ?? "not configured"}</span>
          <small>Fingerprint {status?.grok?.fingerprint ?? "none"} | browser password login: {String(status?.security?.browser_password_login_supported ?? false)}</small>
        </div>
      </div>
      <div className="credential-grid">
        <label>
          Gemini Slot
          <select value={geminiSlot} onChange={(event) => setGeminiSlot(Number(event.target.value))}>
            {[1, 2, 3, 4, 5].map((slot) => <option key={slot} value={slot}>{slot}</option>)}
          </select>
        </label>
        <label>
          Gemini API Key
          <input type="password" value={geminiKey} onChange={(event) => setGeminiKey(event.target.value)} placeholder="paste Gemini API key" autoComplete="off" />
        </label>
        <button disabled={busy || !geminiKey} onClick={() => run("Save Gemini", () => api.saveGeminiCredential(geminiSlot, geminiKey))}>Save Gemini Slot</button>
        <button disabled={busy} onClick={() => run("Test Gemini", () => api.testGeminiCredential(geminiSlot))}>Test Gemini Slot</button>
        <button disabled={busy} onClick={() => run("Clear Gemini", () => api.clearGeminiCredential(geminiSlot))}>Clear Gemini Slot</button>
        <label>
          Grok / xAI API Key
          <input type="password" value={grokKey} onChange={(event) => setGrokKey(event.target.value)} placeholder="paste Grok/xAI API key" autoComplete="off" />
        </label>
        <button disabled={busy || !grokKey} onClick={() => run("Save Grok", () => api.saveGrokCredential(grokKey))}>Save Grok Key</button>
        <button disabled={busy} onClick={() => run("Test Grok", () => api.testGrokCredential())}>Test Grok Key</button>
        <button disabled={busy} onClick={() => run("Clear Grok", () => api.clearGrokCredential())}>Clear Grok Key</button>
      </div>
      <p>v1.34 only proves local vault storage and masked status. v1.35-v1.37 will use these stored credentials for Gemini, Grok, and the side-by-side Jarvis comparison room.</p>
    </Panel>
  );
}
