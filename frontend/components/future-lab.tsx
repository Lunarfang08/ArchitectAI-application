"use client";

import { RefObject, useEffect, useRef, useState } from "react";
import { deleteSimulation, FutureResult, FutureSimulation, getSimulations, OperationStep, runSimulation } from "../lib/api";
import styles from "./future-lab.module.css";

function ScoreRadar({ scores }: { scores: Record<string, number> }) {
  const entries = Object.entries(scores);
  const point = (i: number, radius: number) => {
    const angle = i * Math.PI * 2 / entries.length - Math.PI / 2;
    return `${150 + radius * Math.cos(angle)},${130 + radius * Math.sin(angle)}`;
  };
  return <svg viewBox="0 0 300 270" role="img" aria-label={`Resilience profile: ${entries.map(([name, value]) => `${name} ${value} out of 100`).join(", ")}`} style={{ display: "block", maxWidth: 340, width: "100%", margin: "24px auto" }}>
    {[25, 50, 75, 100].map(r => <polygon key={r} points={entries.map((_, i) => point(i, r)).join(" ")} fill="none" stroke="#a8e6cf30" />)}
    {entries.map(([name], i) => <g key={name}><line x1="150" y1="130" x2={point(i, 100).split(",")[0]} y2={point(i, 100).split(",")[1]} stroke="#a8e6cf30" /><text x={point(i, 121).split(",")[0]} y={point(i, 121).split(",")[1]} fill="#b8c9c1" fontSize="10" textAnchor="middle">{name}</text></g>)}
    <polygon points={entries.map(([, value], i) => point(i, value)).join(" ")} fill="#a8e6cf30" stroke="#a8e6cf" strokeWidth="2" />
  </svg>;
}

const presets = [["traffic", "↗", "20× traffic", "Your launch goes viral."], ["database", "◉", "Database outage", "Thirty minutes offline."], ["security", "⌁", "Exposed API key", "A secret escapes."], ["dependency", "◇", "Supply chain", "A dependency is compromised."], ["regions", "◎", "Global expansion", "Cross borders, keep consistency."], ["budget", "↓", "Half the budget", "Same product. Fewer resources."], ["privacy", "⊙", "Privacy shift", "Export and erase personal data."], ["team", "↔", "Team turnover", "Your lead developer leaves."]];
const scenarioLabel = (value: string) => presets.find(([id]) => id === value)?.[2] ?? "Custom scenario";

export function FailureMap({ result, step, selected, onSelect }: { result: FutureResult; step: number; selected: string; onSelect: (id: string) => void }) {
  const positions = result.components.map((_, i) => ({ x: 50 + 36 * Math.cos(i * Math.PI * 2 / result.components.length - Math.PI / 2), y: 50 + 35 * Math.sin(i * Math.PI * 2 / result.components.length - Math.PI / 2) }));
  return <div className={styles.map}><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{result.components.flatMap((c, i) => c.downstream.map(d => { const j = result.components.findIndex(n => n.id === d); return j < 0 ? null : <line key={`${c.id}-${d}`} x1={positions[i].x} y1={positions[i].y} x2={positions[j].x} y2={positions[j].y} />; }))}</svg><div className={styles.mapCore}>SYSTEM<br /><b>MAP</b></div>{result.components.map((c, i) => { const state = result.timeline.slice(0, step + 1).filter(e => e.component_id === c.id).at(-1)?.state ?? "stable"; return <button key={c.id} type="button" aria-pressed={selected === c.id} data-state={state} style={{ left: `${positions[i].x}%`, top: `${positions[i].y}%` }} onClick={() => onSelect(c.id)}><span />{c.name}<small>{state}</small></button>; })}</div>;
}

export function FutureLab({ projectId, ready, onEvent, cancelRef, onOpenArchitecture }: { projectId: string | null; ready: boolean; onEvent: (e: OperationStep) => void; cancelRef: RefObject<(() => void) | null>; onOpenArchitecture?: () => void }) {
  const [runs, setRuns] = useState<FutureSimulation[]>([]);
  const [active, setActive] = useState<FutureSimulation | null>(null);
  const [scenario, setScenario] = useState("traffic");
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState("");
  const [repairs, setRepairs] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const lastEvent = useRef<OperationStep | null>(null);
  function cancel() {
    controller.current?.abort(); setBusy(false); setError("Simulation cancelled.");
    if (lastEvent.current) onEvent({ ...lastEvent.current, event: "cancelled", status: "cancelled", message: "Simulation cancelled" });
  }
  useEffect(() => { cancelRef.current = cancel; return () => { cancelRef.current = null; }; });
  useEffect(() => { let alive = true; if (projectId) getSimulations(projectId).then(r => { if (alive) { setRuns(r); setActive(r[0] ?? null); } }).catch(e => { if (alive) setError(e.message); }); return () => { alive = false; controller.current?.abort(); }; }, [projectId]);
  useEffect(() => { if (!playing || !active) return; const timer = setInterval(() => setStep(s => { if (s >= active.result.timeline.length - 1) { setPlaying(false); return s; } return s + 1; }), 1800); return () => clearInterval(timer); }, [playing, active]);
  async function run() {
    if (!projectId) return;
    const abort = new AbortController(); controller.current = abort; setBusy(true); setError("");
    try { const r = await runSimulation(projectId, scenario, custom, abort.signal, e => { lastEvent.current = e; onEvent(e); }); if (!abort.signal.aborted) { setRuns(old => [r, ...old]); choose(r); } }
    catch (e) { if (!abort.signal.aborted) setError((e as Error).message); }
    finally { if (controller.current === abort) { setBusy(false); controller.current = null; } }
  }
  function choose(r: FutureSimulation) { setActive(r); setStep(0); setSelected(r.result.components[0]?.id ?? ""); setRepairs(false); setPlaying(false); }
  const result = active?.result;
  const component = result?.components.find(c => c.id === selected) ?? result?.components[0];
  return <section className={styles.lab} id="future-lab"><header className={styles.heading}><div><p>SYSTEM RESILIENCE</p><h2>Prepare for what could go wrong.</h2><span>Explore failure scenarios, trace their impact, and consider possible repairs.</span></div></header>
    {!ready && <div className={styles.notice}><p>{projectId ? "This project needs a completed architecture before its future can be explored." : "Select a saved project from the sidebar, or create an architecture to explore its future."}</p><button type="button" onClick={onOpenArchitecture}>Open Architecture studio →</button></div>}
    <div className={styles.presets}>{presets.map(([id, icon, title, copy]) => <button type="button" key={id} aria-pressed={scenario === id} disabled={busy || !ready} onClick={() => setScenario(id)}><i>{icon}</i><strong>{title}</strong><small>{copy}</small></button>)}</div>
    <div className={styles.custom}><label><input type="checkbox" checked={scenario === "custom"} disabled={busy || !ready} onChange={e => setScenario(e.target.checked ? "custom" : "traffic")} /> Write your own future</label>{scenario === "custom" && <textarea aria-label="Custom scenario" maxLength={2000} value={custom} disabled={busy} onChange={e => setCustom(e.target.value)} placeholder="What if our system had to work offline for an entire day?" />}<button type="button" disabled={!ready || !projectId || busy || (scenario === "custom" && custom.trim().length < 10)} onClick={run}>{busy ? "Exploring the future…" : "Run simulation ↗"}</button>{busy && <button type="button" onClick={cancel}>Cancel</button>}</div>
    {error && <p role="alert" className={styles.notice}>{error}</p>}
    {runs.length > 0 && <div className={styles.history}><label>Saved scenarios <select value={active?.id ?? ""} onChange={e => { const r = runs.find(r => r.id === e.target.value); if (r) choose(r); }}>{runs.map(r => <option value={r.id} key={r.id}>{scenarioLabel(r.scenario_type)} · {r.result.survival_score}/100 · {new Date(r.created_at).toLocaleString()}</option>)}</select></label><button type="button" disabled={busy} onClick={async () => { if (!active || !projectId) return; try { await deleteSimulation(projectId, active.id); const next = runs.filter(r => r.id !== active.id); setRuns(next); if (next[0]) choose(next[0]); else setActive(null); } catch (e) { setError((e as Error).message); } }}>Delete selected</button></div>}
    {result && <><div className={styles.summary}><div><p>SCENARIO / {active ? scenarioLabel(active.scenario_type) : ""}</p><h3>{active?.scenario_input}</h3><p>{result.summary}</p><small>Estimate · {result.confidence} confidence · not a guarantee</small></div><div className={styles.survival}><strong>{result.survival_score}</strong><span>/100 SURVIVAL</span></div></div><div className={styles.observatory}><FailureMap result={result} step={step} selected={component?.id ?? ""} onSelect={setSelected} /><aside className={styles.inspector}><p>IMPACT INSPECTOR</p><h3>{component?.name}</h3><p>{component?.cause}</p><h4>Mitigation</h4><p>{component?.mitigation}</p><h4>Affected files</h4>{component?.files.length ? component.files.map(f => <code key={f}>{f}</code>) : <p>No source files available.</p>}<h4>Downstream</h4><p>{component?.downstream.map(id => result.components.find(c => c.id === id)?.name).join(" → ") || "No downstream impact identified"}</p></aside></div><div className={styles.timeline}><div><button type="button" onClick={() => { if (step === result.timeline.length - 1) setStep(0); setPlaying(!playing); }}>{playing ? "Pause" : "Play failure timeline"}</button><input aria-label="Failure timeline" type="range" min={0} max={result.timeline.length - 1} value={step} onChange={e => { setStep(Number(e.target.value)); setPlaying(false); }} /></div><b>{result.timeline[step].time} / {result.timeline[step].state}</b><p>{result.timeline[step].description}</p></div><ScoreRadar scores={result.scores} /><div className={styles.scoreGrid}>{Object.entries(result.scores).map(([name, score]) => <div key={name}><span>{name}</span><strong>{score}<small>/100</small></strong><meter min={0} max={100} value={score} aria-label={name} /></div>)}</div><button className={styles.repairButton} type="button" aria-expanded={repairs} onClick={() => setRepairs(!repairs)}>{repairs ? "Close repair proposal" : "Propose repairs ↗"}</button>{repairs && <div className={styles.repairs}><p>PROPOSAL ONLY · Review before making changes</p>{result.repairs.map((r, i) => <article key={i}><small>{r.priority} priority</small><h3>{r.title}</h3><p>{r.change}</p><p>{r.expected_improvement}</p>{r.files.map(f => <code key={f}>{f}</code>)}</article>)}</div>}{runs.length > 1 && <div className={styles.comparison}><h3>Compare saved futures</h3>{runs.map(r => <div key={r.id}><span>{scenarioLabel(r.scenario_type)}</span><meter min={0} max={100} value={r.result.survival_score} aria-label={`${r.scenario_type} survival`} /><b>{r.result.survival_score}/100</b></div>)}</div>}</>}
  </section>;
}
