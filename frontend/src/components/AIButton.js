import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Square, X, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";

/* Shared AI action button: provider / model / effort dropdowns, a Stop button
   while running, and a live telemetry panel (progress, stage, tokens, $ this
   call, org month-to-date spend).

   Props:
     orgId        — org scope (loads /ai/options, polls /ai/jobs)
     label        — button text (e.g. "Generate with AI")
     icon         — lucide icon component (default Sparkles)
     onStart({engine, model, effort}) — MUST call the API and return the
                    response data; if it contains jobId the panel goes live
     onDone()     — called after the job reaches a terminal state (refresh)
     lockEngine   — restrict to one engine id (e.g. "claude" for web-search jobs)
     disabled / disabledReason
     compact      — smaller paddings for card grids
*/

const optionsCache = {};

export default function AIButton({ orgId, label, icon: Icon = Sparkles, onStart, onDone,
                                   lockEngine = "", disabled = false, disabledReason = "",
                                   note = "",
                                   compact = false, className = "", testid = "ai-button" }) {
  const [opts, setOpts] = useState(optionsCache[orgId] || null);
  const [engine, setEngine] = useState(lockEngine || "");
  const [model, setModel] = useState("");
  const [effort, setEffort] = useState("standard");
  const [job, setJob] = useState(null);         // live job row
  const [running, setRunning] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!orgId) return;
    if (optionsCache[orgId]) { setOpts(optionsCache[orgId]); return; }
    api.get(`/orgs/${orgId}/ai/options`).then((r) => {
      optionsCache[orgId] = r.data;
      setOpts(r.data);
    }).catch(() => {});
  }, [orgId]);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const engines = (opts?.engines || []).filter((e) => !lockEngine || e.id === lockEngine);
  const configured = engines.filter((e) => e.configured);
  const activeEngine = engine || (lockEngine || (configured[0]?.id ?? ""));
  const models = engines.find((e) => e.id === activeEngine)?.models || [];
  const noKeys = opts && configured.length === 0;

  const pollJob = (jobId) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/orgs/${orgId}/ai/jobs/${jobId}`);
        setJob(data);
        if (["done", "error", "cancelled"].includes(data.status)) {
          clearInterval(pollRef.current);
          setRunning(false);
          if (optionsCache[orgId]) optionsCache[orgId].monthSpendUsd = data.monthSpendUsd;
          if (data.status === "error") toast.error(data.error || "The AI call failed");
          if (data.status === "cancelled") toast.info("Stopped — no result was saved");
          onDone && onDone(data);
        }
      } catch { /* transient poll errors are fine */ }
    }, 2500);
  };

  const start = async () => {
    setRunning(true);
    setShowPanel(true);
    setJob({ status: "running", stage: "Starting…", progress: 2,
             inputTokens: 0, outputTokens: 0, costUsd: 0,
             monthSpendUsd: opts?.monthSpendUsd });
    try {
      const data = await onStart({ engine: activeEngine, model, effort });
      if (data?.jobId) {
        setJob((j) => ({ ...j, id: data.jobId }));
        pollJob(data.jobId);
      } else {
        // synchronous action — no job to stream
        setRunning(false);
        setJob((j) => ({ ...j, status: "done", stage: "Done", progress: 100 }));
        onDone && onDone(data);
      }
    } catch (e) {
      setRunning(false);
      setJob((j) => ({ ...j, status: "error", stage: "Failed", error: errMsg(e) }));
      toast.error(errMsg(e));
    }
  };

  const stop = async () => {
    if (!job?.id) return;
    try {
      await api.post(`/orgs/${orgId}/ai/jobs/${job.id}/cancel`);
      setJob((j) => ({ ...j, stage: "Stopping after the current step…" }));
    } catch (e) { toast.error(errMsg(e)); }
  };

  const sel = `field !w-auto ${compact ? "!py-0.5 text-[10px]" : "!py-1 text-xs"}`;
  const money = (v) => (v == null ? "—" : `$${Number(v).toFixed(v < 0.1 ? 4 : 2)}`);

  return (
    <div className={`inline-flex flex-col gap-1.5 ${className}`}>
      <div className="flex flex-wrap items-center gap-1.5">
        {lockEngine ? (
          <select className={sel} value={lockEngine} disabled data-testid={`${testid}-engine`}
                  title="This action needs live web search, available on the Anthropic engine">
            <option value={lockEngine}>
              {(opts?.engines || []).find((e) => e.id === lockEngine)?.label || "Anthropic"}
            </option>
          </select>
        ) : (
          <select className={sel} value={activeEngine} data-testid={`${testid}-engine`}
                  onChange={(e) => { setEngine(e.target.value); setModel(""); }}>
            {!activeEngine && <option value="">Select API</option>}
            {engines.map((e) => (
              <option key={e.id} value={e.id} disabled={!e.configured}>
                {e.label}{e.configured ? "" : " (no key)"}
              </option>
            ))}
          </select>
        )}
        <select className={sel} value={model} data-testid={`${testid}-model`}
                onChange={(e) => setModel(e.target.value)}>
          <option value="">Select model (default)</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
        <select className={sel} value={effort} data-testid={`${testid}-effort`}
                onChange={(e) => setEffort(e.target.value)}>
          {(opts?.efforts || [{ id: "standard", label: "Standard" }]).map((ef) => (
            <option key={ef.id} value={ef.id}>Effort: {ef.label.split(" — ")[0]}</option>
          ))}
        </select>
        {running ? (
          <button className={`btn !border-bad/50 !bg-bad/15 !text-bad ${compact ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm"}`}
                  onClick={stop} data-testid={`${testid}-stop`} title="Stop this AI call">
            <Square size={13} fill="currentColor" /> Stop
          </button>
        ) : (
          <button className={`btn btn-primary ${compact ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm"}`}
                  onClick={start} disabled={disabled || noKeys || !activeEngine}
                  data-testid={testid}
                  title={disabled ? disabledReason : noKeys ? "Add API keys in Settings first" : ""}>
            <Icon size={compact ? 13 : 15} /> {label}
          </button>
        )}
      </div>

      {note && !running && (
        <div className="text-[11px] text-faint">{note}</div>
      )}
      {noKeys && (
        <div className="text-[11px] text-warn">
          No AI keys configured — <Link to="/settings" className="underline">add them in Settings</Link>.
        </div>
      )}
      {disabled && disabledReason && !running && (
        <div className="text-[11px] text-faint">{disabledReason}</div>
      )}

      {showPanel && job && (
        <div className="w-full min-w-[260px] max-w-md rounded-lg border border-line bg-white/5 p-3 text-left"
             data-testid={`${testid}-panel`}>
          <div className="flex items-center justify-between gap-2">
            <span className={`text-xs ${job.status === "error" ? "text-bad" : "text-dim"}`}>
              {job.status === "error" ? <AlertTriangle size={12} className="mr-1 inline" /> : null}
              {job.stage}
            </span>
            {!running && (
              <button className="text-faint hover:text-ink" onClick={() => setShowPanel(false)}
                      aria-label="Dismiss"><X size={13} /></button>
            )}
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div className={`h-full rounded-full transition-all duration-500 ${
                   job.status === "error" ? "bg-bad" : job.status === "cancelled" ? "bg-warn" : "bg-cyan"}`}
                 style={{ width: `${job.progress || 0}%` }} />
          </div>
          <div className="mono mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px] text-faint sm:grid-cols-4">
            <span>in: {job.inputTokens ?? 0} tok</span>
            <span>out: {job.outputTokens ?? 0} tok</span>
            <span>this call: {money(job.costUsd)}</span>
            <span title={opts?.spendNote}>month: {money(job.monthSpendUsd)}</span>
          </div>
          {job.model && <div className="mt-1 text-[10px] text-faint">model: {job.model}</div>}
          {job.error && <div className="mt-1 text-[11px] text-bad">{job.error}</div>}
        </div>
      )}
    </div>
  );
}
