import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Satellite, Play, Loader2, Download, FileSpreadsheet, Trash2, History,
  KeyRound, Radar, ChevronDown, Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Spinner, PageReveal, EmptyState } from "../components/ui";
import { canEdit as canEditRole, fmtDateTime } from "../lib/helpers";
import { SCAN_TIERS, exportCSV, exportHTML } from "../lib/intel";
import IntelSummary from "../components/IntelSummary";
import IntelTable from "../components/IntelTable";

export default function Intelligence() {
  const { activeOrgId, activeOrg } = useAuth();
  const navigate = useNavigate();
  const editor = canEditRole(activeOrg?.role);
  const [reports, setReports] = useState(null); // metadata list
  const [current, setCurrent] = useState(null);  // full report doc
  const [tier, setTier] = useState("standard");
  const [scanning, setScanning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [addingIdx, setAddingIdx] = useState(null);
  const [histOpen, setHistOpen] = useState(false);
  const pollRef = useRef(null);
  const timerRef = useRef(null);

  const loadReport = useCallback(async (id) => {
    const { data } = await api.get(`/orgs/${activeOrgId}/intel/reports/${id}`);
    setCurrent(data);
  }, [activeOrgId]);

  const loadList = useCallback(async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/intel/reports`);
    setReports(data);
    return data;
  }, [activeOrgId]);

  useEffect(() => {
    if (!activeOrgId) return;
    setCurrent(null); setReports(null);
    loadList().then((list) => { if (list && list.length) loadReport(list[0].id); })
      .catch(() => setReports([]));
    return () => { clearInterval(pollRef.current); clearInterval(timerRef.current); };
  }, [activeOrgId, loadList, loadReport]);

  const stopScan = () => {
    clearInterval(pollRef.current); clearInterval(timerRef.current);
    setScanning(false); setElapsed(0);
  };

  const runScan = async () => {
    setScanning(true); setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/intel/scan`, { tier });
      const jobId = data.jobId;
      pollRef.current = setInterval(async () => {
        try {
          const { data: job } = await api.get(`/orgs/${activeOrgId}/intel/jobs/${jobId}`);
          if (job.status === "done") {
            stopScan();
            const list = await loadList();
            const rid = job.reportId || (list && list[0] && list[0].id);
            if (rid) await loadReport(rid);
            toast.success("Scan complete", { description: job.summary || "" });
          } else if (job.status === "error") {
            stopScan();
            toast.error(job.error || "Scan failed");
          }
        } catch (e) { /* keep polling */ }
      }, 3000);
    } catch (e) {
      stopScan();
      const msg = errMsg(e);
      toast.error(msg, msg.includes("Settings") ? {
        description: "Open Settings → API Keys to add your Anthropic key.",
        action: { label: "Settings", onClick: () => navigate("/settings") },
      } : undefined);
    }
  };

  const del = async () => {
    if (!current) return;
    try {
      await api.delete(`/orgs/${activeOrgId}/intel/reports/${current.id}`);
      const list = await loadList();
      if (list && list.length) await loadReport(list[0].id); else setCurrent(null);
      toast.success("Report deleted");
    } catch (e) { toast.error(errMsg(e)); }
  };

  const addToPipeline = async (idx) => {
    setAddingIdx(idx);
    try {
      await api.post(`/orgs/${activeOrgId}/intel/reports/${current.id}/add/${idx}`);
      toast.success("Added to pipeline", {
        action: { label: "View", onClick: () => navigate("/opportunities") },
      });
    } catch (e) { toast.error(errMsg(e)); }
    finally { setAddingIdx(null); }
  };

  const report = current?.report;
  const isSample = (current?.model || "").toUpperCase().includes("SAMPLE");

  return (
    <PageReveal className="space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <SectionLabel>Opportunity Intelligence</SectionLabel>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-ink">
            <Satellite size={22} className="text-cyan" /> Weekly Intelligence Scan
          </h1>
          <p className="mt-1 text-sm text-faint">Live AI scan of public federal sources — fit-scored against your capability profile.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {reports && reports.length > 0 && (
            <div className="relative">
              <button onClick={() => setHistOpen((o) => !o)} className="btn btn-ghost" data-testid="intel-history-btn">
                <History size={15} /> History <ChevronDown size={13} />
              </button>
              {histOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setHistOpen(false)} />
                  <div className="glass absolute right-0 z-20 mt-2 max-h-72 w-72 overflow-y-auto p-1" style={{ background: "var(--bg-elev)" }} data-testid="intel-history-menu">
                    {reports.map((r) => (
                      <button key={r.id} onClick={() => { loadReport(r.id); setHistOpen(false); }}
                        className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-white/5 ${current?.id === r.id ? "text-cyan" : "text-dim"}`}
                        data-testid={`intel-history-item-${r.id}`}>
                        <span>{fmtDateTime(r.createdAt)}</span>
                        <span className="label-mono">{r.total} · {r.tier}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
          {report && (
            <>
              <button onClick={() => exportCSV(report)} className="btn btn-ghost" data-testid="intel-export-csv"><FileSpreadsheet size={15} /> CSV</button>
              <button onClick={() => exportHTML(report)} className="btn btn-ghost" data-testid="intel-export-html"><Download size={15} /> HTML</button>
              {editor && <button onClick={del} className="btn btn-ghost text-bad hover:text-bad" data-testid="intel-delete"><Trash2 size={15} /></button>}
            </>
          )}
          {editor && (
            <div className="flex items-center gap-2">
              <select className="field !w-auto" value={tier} onChange={(e) => setTier(e.target.value)} disabled={scanning} data-testid="intel-tier">
                {SCAN_TIERS.map((t) => <option key={t.id} value={t.id} title={t.hint}>{t.label}</option>)}
              </select>
              <button onClick={runScan} disabled={scanning} className="btn btn-primary" data-testid="intel-run-scan">
                {scanning ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />} {scanning ? "Scanning…" : "Run Scan"}
              </button>
            </div>
          )}
        </div>
      </div>

      {scanning && (
        <Card className="p-5" data-testid="intel-scanning">
          <div className="flex items-center gap-3">
            <Radar size={18} className="animate-pulse text-cyan" />
            <div className="flex-1">
              <div className="text-sm font-medium text-ink">Scanning live federal sources…</div>
              <div className="text-xs text-faint">Claude is searching SAM.gov, SBIR, AFWERX, DARPA & more, then fit-scoring against your profile. This usually takes 30–120s. Elapsed {elapsed}s.</div>
            </div>
          </div>
          <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/5">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-cyan" style={{ width: `${Math.min(95, elapsed * 1.2)}%` }} />
          </div>
        </Card>
      )}

      {reports === null ? (
        <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>
      ) : !report && !scanning ? (
        <Card className="p-6">
          <EmptyState
            icon={Satellite}
            title="No intelligence reports yet"
            subtitle={editor ? "Run your first AI scan to discover real, open opportunities matched and fit-scored to your organization. Add your Anthropic key in Settings first." : "An editor or admin can run the AI scan to populate intelligence."}
            action={editor ? (
              <div className="flex gap-2">
                <button className="btn btn-primary" onClick={runScan} data-testid="intel-empty-run"><Play size={16} /> Run first scan</button>
                <button className="btn btn-ghost" onClick={() => navigate("/settings")} data-testid="intel-empty-settings"><KeyRound size={15} /> Add API key</button>
              </div>
            ) : null}
          />
        </Card>
      ) : report ? (
        <div className="space-y-5">
          {isSample && (
            <Card className="border-warn/30 bg-warn/5 p-4" data-testid="intel-sample-banner">
              <div className="flex items-center gap-2 text-sm text-warn">
                <Sparkles size={15} className="shrink-0" />
                <span><b>Sample data</b> — shown to preview the report format. Add your Anthropic key in Settings, then click <b>Run Scan</b> to replace this with live, fit-scored opportunities.</span>
              </div>
            </Card>
          )}
          <div className="flex flex-wrap items-center gap-2 text-xs text-faint">
            <span>Report {report.reportDate || fmtDateTime(current.createdAt)}</span>
            {report.fiscalYear && <span>· {report.fiscalYear}</span>}
            {current.model && <span>· {current.model}</span>}
            {current.usage?.webSearches != null && <span>· {current.usage.webSearches} web searches</span>}
          </div>
          <IntelSummary report={report} />
          <IntelTable opps={report.opportunities} canEdit={editor} onAdd={addToPipeline} addingIdx={addingIdx} />
        </div>
      ) : null}
    </PageReveal>
  );
}
