import { useState, type FormEvent } from "react";
import { apiFetch } from "@/api/client";

type Privacy = "local" | "sources" | "redacted" | "open";
interface RunResult {
  run_id: string;
  status: "verified";
  csv: string;
  artifact_name: string;
  artifact_sha256: string;
  receipt_sha256: string;
  receipt_json: string;
  receipt: {
    row_count: number;
    checks: { name: string; passed: boolean }[];
    limitations: string[];
  };
}
const descriptions: Record<Privacy, string> = {
  local: "Keep task content and sources on this device. No sharing permitted.",
  sources: "Allow future tools to request public sources. Your selected source text stays private.",
  redacted: "Allow reviewed, redacted content to be shared by future connected tools.",
  open: "Explicitly allow full task sharing with future connected tools. Provider costs and destinations still need to be shown.",
};
function download(content: string, filename: string, mime: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function Workspace() {
  const [research, setResearch] = useState(false);
  const [privacy, setPrivacy] = useState<Privacy>("local");
  const [task, setTask] = useState("Create a cited CSV from this source.");
  const [title, setTitle] = useState("Synthetic workspace fixture");
  const [passage, setPassage] = useState("This synthetic fixture contains one sample observation.");
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(event: FormEvent) {
    event.preventDefault();
    setError(""); setResult(null); setBusy(true);
    try {
      const response = await apiFetch<RunResult>("/api/workspace/run", {
        method: "POST", body: { task, privacy,
          sources: [{ id: "source-1", title, passage, kind: "unverified" }],
          records: [{ claim: passage, source_id: "source-1", quote: passage }],
        },
      });
      if (response.status !== "verified") throw new Error("The server did not verify this artifact.");
      setResult(response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not complete the task. Try again.");
    } finally { setBusy(false); }
  }
  return <main className="workspace-page">
    <header className="workspace-intro">
      <div><p className="workspace-eyebrow">LOCAL FIRST · EVIDENCE INCLUDED</p><h1>Your work, on your terms.</h1><p>Turn a source into a real file, with an inspectable record of every check.</p></div>
      <div className="workspace-audience" role="group" aria-label="Workspace mode"><button aria-pressed={!research} onClick={() => setResearch(false)}>Simple</button><button aria-pressed={research} onClick={() => setResearch(true)}>Research</button></div>
    </header>
    <div className="workspace-grid">
      <section className="workspace-card">
        <div className="workspace-card-heading"><span className="workspace-step">01</span><h2>Create a sourced artifact</h2></div>
        <p className="workspace-hint">Proof of concept · exact extraction from one source. The sample below is a synthetic fixture; replace it with your own passage.</p>
        <form onSubmit={run}><fieldset disabled={busy}>
          <label htmlFor="workspace-task">Task</label><textarea id="workspace-task" value={task} onChange={e => { setTask(e.target.value); setResult(null); }} required maxLength={500} rows={2} />
          <label htmlFor="workspace-title">Source title</label><input id="workspace-title" value={title} onChange={e => { setTitle(e.target.value); setResult(null); }} required maxLength={500} />
          <label htmlFor="workspace-passage">Source passage</label><textarea id="workspace-passage" value={passage} onChange={e => { setPassage(e.target.value); setResult(null); }} required maxLength={12000} rows={5} />
          <p className="workspace-hint">The CSV copies this entire passage into one cited row. Source quality is unverified; exact extraction does not establish factual truth.</p>
          <label htmlFor="workspace-privacy">Privacy</label><select id="workspace-privacy" value={privacy} onChange={e => { setPrivacy(e.target.value as Privacy); setResult(null); }}><option value="local">Local only (default)</option><option value="sources">Selected sources</option><option value="redacted">Redacted sharing</option><option value="open">Open sharing</option></select>
          <p className="workspace-permission">{descriptions[privacy]}</p><p className="workspace-hint">This prototype records your permission choice. Every mode currently executes offline with no external egress.</p>
          <button className="workspace-primary" type="submit">{busy ? "Verifying artifact…" : "Create verified CSV"}</button>
        </fieldset></form>
        {error && <p className="workspace-error" role="alert">{error}</p>}
      </section>
      <aside className="workspace-results" aria-live="polite" aria-busy={busy}>
        <section className="workspace-card">
          <div className="workspace-card-heading"><span className="workspace-step">02</span><h2>{result ? "Artifact ready" : "Your output lives here"}</h2></div>
          {result ? <>
            <p className="workspace-success">✓ Extraction checks passed · {result.receipt.row_count} row(s)</p>
            <div className="workspace-downloads"><button className="workspace-primary" onClick={() => download(result.csv, result.artifact_name || "evidence.csv", "text/csv;charset=utf-8")}>Download CSV</button><button className="workspace-secondary" onClick={() => download(result.receipt_json, "receipt.json", "application/json")}>Download receipt</button></div>
            <p className="workspace-hint">The receipt includes your source text. Share it only with intended recipients.</p><p className="workspace-run">Run {result.run_id}</p>
            {research ? <div className="workspace-evidence"><h3>Evidence & verification</h3><ul>{result.receipt.checks.map(check => <li key={check.name}>{check.passed ? "✓" : "✕"} <span>{check.name}</span></li>)}</ul>{result.receipt.limitations.map(limitation => <p key={limitation}>{limitation}</p>)}<dl><dt>CSV SHA-256</dt><dd>{result.artifact_sha256}</dd><dt>Receipt SHA-256</dt><dd>{result.receipt_sha256}</dd></dl><details><summary>Inspect receipt</summary><pre>{result.receipt_json}</pre></details></div> : <button className="workspace-text-button" onClick={() => setResearch(true)}>Inspect evidence in Research mode →</button>}
          </> : <div className="workspace-empty"><span aria-hidden="true">▤</span><p>A real CSV and its verification receipt will appear after a successful run.</p></div>}
        </section>
        <section className="workspace-assurance"><span className="workspace-dot" /><div><h3>No model used. No external requests.</h3><p>Deterministic extraction and structural checks. Sources remain unverified. Local storage is not used to save your content.</p></div></section>
      </aside>
    </div>
  </main>;
}
