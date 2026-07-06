import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  PieChart, Pie, Cell, Tooltip,
} from "recharts";
import {
  ArrowLeft, Sparkles, Save, CheckCircle2, Download, RefreshCw,
  AlertTriangle, Package,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, EmptyState } from "../components/ui";
import { fmtMoney, CHART_SERIES, canEdit, canCreateProposal } from "../lib/helpers";

const tooltipStyle = {
  background: "var(--bg-elev)", border: "1px solid var(--line)",
  borderRadius: 10, color: "var(--text)", fontSize: 12,
};

function svgToPngBase64(svgText) {
  return new Promise((resolve) => {
    try {
      const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = 1600;
        canvas.height = 1000;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#0b1020";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL("image/png"));
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
      img.src = url;
    } catch {
      resolve(null);
    }
  });
}

function downloadBlob(data, filename) {
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const STATUS_PILL = {
  draft: { tone: "cyan", label: "Draft" },
  approved: { tone: "ok", label: "Approved" },
};

export default function Capability() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const cm = canCreateProposal(activeOrg?.role);
  const [opp, setOpp] = useState(null);
  const [cap, setCap] = useState(undefined); // undefined = loading, null = none
  const [content, setContent] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/opportunities/${id}/capability`);
    setCap(data);
    if (data && data.generationStatus !== "generating") setContent(data.content || null);
    return data;
  }, [activeOrgId, id]);

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities/${id}`).then((r) => setOpp(r.data))
      .catch((e) => { toast.error(errMsg(e)); navigate("/opportunities"); });
    load().catch((e) => toast.error(errMsg(e)));
  }, [activeOrgId, id, load, navigate]);

  // poll while generating
  useEffect(() => {
    if (cap?.generationStatus !== "generating") return undefined;
    const timer = setInterval(async () => {
      try {
        const data = await load();
        if (data?.generationStatus === "ready") toast.success("Capability generated");
        if (data?.generationStatus === "error") toast.error(data.generationError || "Generation failed");
      } catch { /* keep polling */ }
    }, 4000);
    return () => clearInterval(timer);
  }, [cap?.generationStatus, load]);

  const generate = async () => {
    setBusy("generate");
    try {
      await api.post(`/orgs/${activeOrgId}/opportunities/${id}/capability/generate`);
      toast.info("Generation started — this can take a minute or two.");
      await load();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const patch = (p) => { setContent((c) => ({ ...c, ...p })); setDirty(true); };

  const save = async () => {
    setBusy("save");
    try {
      const { data } = await api.put(`/orgs/${activeOrgId}/opportunities/${id}/capability`,
        { content });
      setCap(data);
      setContent(data.content);
      setDirty(false);
      toast.success("Capability saved");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const approve = async () => {
    setBusy("approve");
    try {
      if (dirty) await api.put(`/orgs/${activeOrgId}/opportunities/${id}/capability`, { content });
      // best-effort: snapshot the SVG rendering as PNG for Word/zip exports
      if (content?.renderingSvg) {
        const png = await svgToPngBase64(content.renderingSvg);
        if (png) {
          await api.post(`/orgs/${activeOrgId}/opportunities/${id}/capability/rendering`,
            { pngBase64: png }).catch(() => {});
        }
      }
      const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/${id}/capability/approve`);
      setCap(data);
      setContent(data.content);
      setDirty(false);
      toast.success(`Version ${data.version} approved`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const exportDocx = async () => {
    setBusy("export");
    try {
      const r = await api.get(
        `/orgs/${activeOrgId}/opportunities/${id}/capability/export/docx`,
        { responseType: "blob", timeout: 60000 });
      downloadBlob(r.data, `Proposed_Capability.docx`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  if (!opp || cap === undefined) {
    return <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>;
  }

  const generating = cap?.generationStatus === "generating";
  const statusPill = STATUS_PILL[cap?.status] || STATUS_PILL.draft;

  return (
    <PageReveal className="space-y-5">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <button onClick={() => navigate(`/opportunities/${id}`)}
            className="mb-2 inline-flex items-center gap-1.5 text-sm text-dim hover:text-cyan"
            data-testid="back-to-opportunity">
            <ArrowLeft size={15} /> {opp.title}
          </button>
          <h1 className="flex flex-wrap items-center gap-3 text-2xl font-semibold text-ink">
            Proposed Capability
            {cap && <Pill tone={statusPill.tone}>{statusPill.label} · v{cap.version}</Pill>}
          </h1>
          <div className="mt-1 text-sm text-faint">
            <span className="mono">{opp.solNumber || "—"}</span> · {opp.agency} · {opp.vehicle}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn btn-ghost" onClick={() => navigate(`/opportunities/${id}/proposal`)}
            data-testid="goto-proposal">
            <Package size={15} /> Proposal Package
          </button>
          {cap?.content?.title && (
            <button className="btn btn-ghost" onClick={exportDocx} disabled={busy === "export"}
              data-testid="export-capability-docx">
              {busy === "export" ? <Spinner /> : <Download size={15} />} Word (.docx)
            </button>
          )}
          {editor && cap?.generationStatus === "ready" && (
            <>
              {cm && (
                <button className="btn btn-ghost" onClick={generate} disabled={!!busy || generating}
                  data-testid="regenerate-capability">
                  <RefreshCw size={15} /> Regenerate
                </button>
              )}
              <button className="btn btn-primary" onClick={save}
                disabled={!dirty || !!busy} data-testid="save-capability">
                {busy === "save" ? <Spinner /> : <Save size={15} />} {dirty ? "Save changes" : "Saved"}
              </button>
              {cm && cap.status !== "approved" && (
                <button className="btn btn-violet" onClick={approve} disabled={!!busy}
                  data-testid="approve-capability">
                  {busy === "approve" ? <Spinner /> : <CheckCircle2 size={15} />} Approve
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* empty / generating / error states */}
      {!cap && (
        <Card className="p-6">
          <EmptyState icon={Sparkles} title="No proposed capability yet"
            subtitle="The AI capture manager will design a capability for this solicitation from your company profile: title, abstract, executive summary, concept rendering, SoW, WBS schedule, and budget."
            action={cm ? (
              <button className="btn btn-primary" onClick={generate} disabled={busy === "generate"}
                data-testid="generate-capability">
                {busy === "generate" ? <Spinner /> : <Sparkles size={16} />} Generate with AI
              </button>
            ) : (
              <span className="text-xs text-faint">Your capture manager creates the proposed capability.</span>
            )} />
        </Card>
      )}
      {generating && (
        <Card className="flex items-center gap-3 p-6" data-testid="capability-generating">
          <Spinner size={20} className="text-cyan" />
          <div>
            <div className="text-sm text-ink">Designing the proposed capability…</div>
            <div className="text-xs text-faint">Claude is analyzing the solicitation and your company profile. This usually takes 1–2 minutes.</div>
          </div>
        </Card>
      )}
      {cap?.generationStatus === "error" && (
        <Card className="flex items-start gap-3 border-bad/40 p-5" data-testid="capability-error">
          <AlertTriangle size={18} className="mt-0.5 text-bad" />
          <div className="min-w-0">
            <div className="text-sm text-ink">Generation failed</div>
            <div className="text-xs text-faint">{cap.generationError}</div>
            {cm && (
              <button className="btn btn-ghost mt-3" onClick={generate} disabled={!!busy}>
                <RefreshCw size={14} /> Try again
              </button>
            )}
          </div>
        </Card>
      )}

      {content && cap?.generationStatus === "ready" && (
        <CapabilityBody content={content} patch={patch} editor={editor} />
      )}
    </PageReveal>
  );
}

function CapabilityBody({ content, patch, editor }) {
  const budgetItems = content.budget?.items || [];
  const budgetTotal = budgetItems.reduce((s, i) => s + (Number(i.cost) || 0), 0);

  const setSow = (sow) => patch({ sow });
  const setWbs = (wbs) => patch({ wbs });
  const setBudget = (budget) => patch({ budget });

  return (
    <div className="space-y-5">
      {/* Title / abstract / summary / keywords */}
      <Card className="space-y-4 p-5">
        <SectionLabel>Title</SectionLabel>
        <input className="field text-lg font-semibold" value={content.title || ""}
          onChange={(e) => patch({ title: e.target.value })} disabled={!editor}
          data-testid="capability-title" />
        <SectionLabel>Abstract</SectionLabel>
        <textarea className="field min-h-[110px]" value={content.abstract || ""}
          onChange={(e) => patch({ abstract: e.target.value })} disabled={!editor}
          data-testid="capability-abstract" />
        <SectionLabel>Executive Summary (markdown)</SectionLabel>
        <textarea className="field mono min-h-[220px] text-[13px]"
          value={content.executiveSummary || ""}
          onChange={(e) => patch({ executiveSummary: e.target.value })} disabled={!editor}
          data-testid="capability-summary" />
        <SectionLabel>Keywords (comma-separated)</SectionLabel>
        <input className="field" value={(content.keywords || []).join(", ")}
          onChange={(e) => patch({ keywords: e.target.value.split(",").map((k) => k.trim()).filter(Boolean) })}
          disabled={!editor} data-testid="capability-keywords" />
        <div className="flex flex-wrap gap-1.5">
          {(content.keywords || []).map((k) => <Pill key={k} tone="cyan">{k}</Pill>)}
        </div>
      </Card>

      {/* Rendering */}
      {content.renderingSvg && (
        <Card className="p-5">
          <SectionLabel className="mb-3">Concept Rendering</SectionLabel>
          <div className="overflow-hidden rounded-xl border border-line"
            data-testid="capability-rendering"
            dangerouslySetInnerHTML={{ __html: content.renderingSvg }} />
        </Card>
      )}

      {/* Charts + tables */}
      {(content.charts?.length > 0 || content.tables?.length > 0) && (
        <div className="grid gap-5 md:grid-cols-2">
          {(content.charts || []).map((chart, ci) => (
            <Card key={ci} className="p-5">
              <SectionLabel className="mb-3">{chart.title || `Chart ${ci + 1}`}</SectionLabel>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  {chart.type === "pie" ? (
                    <PieChart>
                      <Pie data={chart.data || []} dataKey="value" nameKey="name"
                        innerRadius={45} outerRadius={80} paddingAngle={2}>
                        {(chart.data || []).map((_, i) => (
                          <Cell key={i} fill={CHART_SERIES[i % CHART_SERIES.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  ) : (
                    <BarChart data={chart.data || []}>
                      <CartesianGrid stroke="var(--line)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: "var(--text-faint)", fontSize: 11 }} />
                      <YAxis tick={{ fill: "var(--text-faint)", fontSize: 11 }} />
                      <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                      <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                        {(chart.data || []).map((_, i) => (
                          <Cell key={i} fill={CHART_SERIES[i % CHART_SERIES.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            </Card>
          ))}
          {(content.tables || []).map((tbl, ti) => (
            <Card key={`t${ti}`} className="p-5">
              <SectionLabel className="mb-3">{tbl.title || `Table ${ti + 1}`}</SectionLabel>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs text-dim">
                      {(tbl.headers || []).map((h, i) => <th key={i} className="py-2 pr-3">{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {(tbl.rows || []).map((row, ri) => (
                      <tr key={ri} className="border-b border-line/50 hover:bg-white/5">
                        {row.map((c, ci2) => <td key={ci2} className="py-2 pr-3 text-dim">{c}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* SoW */}
      <Card className="space-y-4 p-5">
        <SectionLabel>Statement of Work</SectionLabel>
        <textarea className="field min-h-[70px]" value={content.sow?.scope || ""}
          placeholder="Scope"
          onChange={(e) => setSow({ ...content.sow, scope: e.target.value })} disabled={!editor} />
        {(content.sow?.tasks || []).map((t, i) => (
          <div key={i} className="rounded-xl border border-line bg-white/[0.02] p-4">
            <div className="mb-2 flex items-center gap-2">
              <Pill tone="violet">Task {t.number}</Pill>
              <input className="field flex-1 font-medium" value={t.title || ""}
                onChange={(e) => {
                  const tasks = [...content.sow.tasks];
                  tasks[i] = { ...t, title: e.target.value };
                  setSow({ ...content.sow, tasks });
                }} disabled={!editor} />
            </div>
            <textarea className="field min-h-[60px] text-sm" value={t.description || ""}
              onChange={(e) => {
                const tasks = [...content.sow.tasks];
                tasks[i] = { ...t, description: e.target.value };
                setSow({ ...content.sow, tasks });
              }} disabled={!editor} />
            {(t.deliverables || []).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {t.deliverables.map((d, di) => <Pill key={di}>{d}</Pill>)}
              </div>
            )}
          </div>
        ))}
      </Card>

      {/* WBS + schedule */}
      <Card className="p-5">
        <div className="mb-3 flex items-center justify-between">
          <SectionLabel>Work Breakdown Structure & Schedule</SectionLabel>
          <Pill tone="cyan">{content.scheduleMonths || 12} months</Pill>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="wbs-table">
            <thead>
              <tr className="border-b border-line text-left text-xs text-dim">
                <th className="py-2 pr-3">WBS</th><th className="py-2 pr-3">Task</th>
                <th className="py-2 pr-3">Owner</th><th className="py-2 pr-3">Schedule</th>
              </tr>
            </thead>
            <tbody>
              {(content.wbs || []).map((w, i) => {
                const months = Number(content.scheduleMonths) || 12;
                const start = Math.max(1, Number(w.startMonth) || 1);
                const end = Math.min(months, Math.max(start, Number(w.endMonth) || start));
                return (
                  <tr key={i} className="border-b border-line/50 hover:bg-white/5">
                    <td className="mono py-2 pr-3 text-cyan">{w.code}</td>
                    <td className="py-2 pr-3">
                      <input className="field py-1 text-sm" value={w.task || ""}
                        onChange={(e) => {
                          const wbs = [...content.wbs];
                          wbs[i] = { ...w, task: e.target.value };
                          setWbs(wbs);
                        }} disabled={!editor} />
                    </td>
                    <td className="py-2 pr-3 text-dim">{w.owner}</td>
                    <td className="w-1/3 py-2 pr-3">
                      <div className="relative h-4 rounded bg-white/5">
                        <div className="absolute inset-y-0 rounded"
                          style={{
                            left: `${((start - 1) / months) * 100}%`,
                            width: `${((end - start + 1) / months) * 100}%`,
                            background: CHART_SERIES[i % CHART_SERIES.length],
                            opacity: 0.75,
                          }}
                          title={`M${start}–M${end}`} />
                      </div>
                      <div className="mono mt-0.5 text-[10px] text-faint">M{start}–M{end}</div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Budget */}
      <Card className="p-5">
        <div className="mb-3 flex items-center justify-between">
          <SectionLabel>Budget / Cost Estimate</SectionLabel>
          <div className="mono text-lg text-ink" data-testid="budget-total">{fmtMoney(budgetTotal)}</div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-dim">
                <th className="py-2 pr-3">Category</th>
                <th className="py-2 pr-3">Description</th>
                <th className="py-2 pr-3 text-right">Cost (USD)</th>
              </tr>
            </thead>
            <tbody>
              {budgetItems.map((item, i) => (
                <tr key={i} className="border-b border-line/50 hover:bg-white/5">
                  <td className="py-2 pr-3 text-dim">{item.category}</td>
                  <td className="py-2 pr-3">
                    <input className="field py-1 text-sm" value={item.description || ""}
                      onChange={(e) => {
                        const items = [...budgetItems];
                        items[i] = { ...item, description: e.target.value };
                        setBudget({ ...content.budget, items });
                      }} disabled={!editor} />
                  </td>
                  <td className="py-2 pr-3 text-right">
                    <input type="number" className="field w-32 py-1 text-right text-sm"
                      value={item.cost ?? 0}
                      onChange={(e) => {
                        const items = [...budgetItems];
                        items[i] = { ...item, cost: Number(e.target.value) || 0 };
                        setBudget({ ...content.budget, items });
                      }} disabled={!editor} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <SectionLabel className="mb-1 mt-4">Basis of Estimate</SectionLabel>
        <textarea className="field min-h-[70px] text-sm" value={content.budget?.narrative || ""}
          onChange={(e) => setBudget({ ...content.budget, narrative: e.target.value })}
          disabled={!editor} />
      </Card>
    </div>
  );
}
