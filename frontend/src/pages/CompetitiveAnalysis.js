import React, { useEffect, useState } from "react";
import { Crosshair, Search, ExternalLink, Trash2, AlertTriangle, Target } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Skeleton, EmptyState, PageReveal, Field } from "../components/ui";
import AIButton from "../components/AIButton";
import { fmtMoney, fmtDateTime, canEdit } from "../lib/helpers";

export default function CompetitiveAnalysis() {
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const [reports, setReports] = useState(null);
  const [report, setReport] = useState(null);
  const [competitor, setCompetitor] = useState("");
  const [naics, setNaics] = useState("");
  const [pendingReportId, setPendingReportId] = useState(null);
  const [reportQ, setReportQ] = useState("");

  const load = async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/competitive`);
    setReports(data);
    return data;
  };
  useEffect(() => {
    if (!activeOrgId) return;
    load().catch(() => setReports([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrgId]);

  const open = async (id) => {
    try {
      const { data } = await api.get(`/orgs/${activeOrgId}/competitive/${id}`);
      setReport(data);
    } catch (e) { toast.error(errMsg(e)); }
  };

  const run = async ({ engine, model, effort }) => {
    if (!competitor || competitor.trim().length < 2) {
      throw new Error("Enter the competitor's registered legal name first");
    }
    const { data } = await api.post(`/orgs/${activeOrgId}/competitive`,
      { competitor, naics, model: model || "", effort: effort || "standard" });
    setPendingReportId(data.reportId);
    return data; // jobId → AIButton streams stage/tokens/cost
  };

  const onRunDone = async () => {
    await load();
    if (pendingReportId) {
      try {
        const { data: rep } = await api.get(`/orgs/${activeOrgId}/competitive/${pendingReportId}`);
        if (rep.status === "done") { setReport(rep); setCompetitor(""); setNaics(""); }
        else if (rep.error) toast.error(rep.error);
      } catch { /* row list already refreshed */ }
      setPendingReportId(null);
    }
  };

  const del = async (e, r) => {
    e.stopPropagation();
    if (!window.confirm(`Delete the ${r.competitor} report?`)) return;
    try {
      await api.delete(`/orgs/${activeOrgId}/competitive/${r.id}`);
      if (report?.id === r.id) setReport(null);
      await load();
    } catch (err) { toast.error(errMsg(err)); }
  };

  const a = report?.analysis || {};
  const u = report?.usaspending || {};

  return (
    <PageReveal className="space-y-5">
      <div>
        <SectionLabel>Capture Intelligence</SectionLabel>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Competitive Analysis</h1>
        <p className="mt-1 max-w-3xl text-xs text-faint">
          Open-source intelligence on any competitor: verified award history straight
          from USASpending (FPDS successor data), plus AI research across SAM.gov, SBA
          DSBS, GSA eLibrary, OSDBU forecasts and the open web — distilled into a BLUF
          with strategies you can act on. Know the customer, know the tech, know the contract.
        </p>
      </div>

      {editor && (
        <Card className="p-4">
          <form onSubmit={(e) => e.preventDefault()} className="flex flex-wrap items-end gap-3" data-testid="competitive-form">
            <div className="min-w-[240px] flex-1">
              <Field label="Competitor (legal name as registered)">
                <input className="field" required minLength={2} value={competitor}
                  onChange={(e) => setCompetitor(e.target.value)}
                  placeholder="e.g. Acme Defense Systems LLC" data-testid="competitor-input" />
              </Field>
            </div>
            <div className="w-40">
              <Field label="NAICS (optional)">
                <input className="field mono" value={naics} onChange={(e) => setNaics(e.target.value)}
                  placeholder="541715" data-testid="competitor-naics" />
              </Field>
            </div>
            <AIButton orgId={activeOrgId} label="Run analysis" icon={Crosshair}
              lockEngine="claude" onStart={run} onDone={onRunDone}
              testid="run-analysis" />
          </form>
        </Card>
      )}

      {report && (
        <div className="space-y-4" data-testid="competitive-report">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-ink">
              {report.competitor}
              {report.naics && <span className="mono ml-2 text-xs text-faint">NAICS {report.naics}</span>}
            </h2>
            <button className="text-xs text-faint hover:text-ink" onClick={() => setReport(null)}>Close report</button>
          </div>

          {report.error && (
            <div className="flex items-start gap-2 rounded-lg border border-warn/40 bg-warn/10 p-3 text-xs text-warn">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {report.error}
            </div>
          )}

          {(a.bluf || []).length > 0 && (
            <Card className="border-cyan/40 p-5">
              <SectionLabel>BLUF — Bottom Line Up Front</SectionLabel>
              <ul className="mt-2 space-y-1.5">
                {a.bluf.map((b, i) => (
                  <li key={i} className="text-sm leading-relaxed text-ink">▸ {b}</li>
                ))}
              </ul>
              {a.profile?.summary && (
                <p className="mt-3 border-t border-line pt-3 text-xs leading-relaxed text-dim">
                  {a.profile.summary}
                  {a.profile.sizeStatus && <Pill tone="violet" className="ml-2">{a.profile.sizeStatus}</Pill>}
                  {(a.profile.certifications || []).map((c) => <Pill key={c} tone="ok" className="ml-1">{c}</Pill>)}
                </p>
              )}
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-5">
              <SectionLabel>Federal obligations by fiscal year (USASpending)</SectionLabel>
              <div className="mt-1 text-xs text-faint">
                Total since FY2020: <span className="mono text-ink">{fmtMoney(u.totalObligated)}</span>
              </div>
              <div className="mt-3 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={u.byYear || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2740" />
                    <XAxis dataKey="fiscalYear" tick={{ fill: "#93a1c0", fontSize: 11 }} />
                    <YAxis tickFormatter={(v) => fmtMoney(v)} tick={{ fill: "#93a1c0", fontSize: 10 }} width={70} />
                    <Tooltip formatter={(v) => fmtMoney(v)}
                      contentStyle={{ background: "#0b1020", border: "1px solid #1c2740" }} />
                    <Bar dataKey="obligated" fill="#38e1ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="p-5">
              <SectionLabel>Top awarding agencies</SectionLabel>
              <table className="mt-3 w-full text-sm">
                <tbody>
                  {(u.byAgency || []).slice(0, 8).map((row) => (
                    <tr key={row.agency} className="border-b border-line/60">
                      <td className="py-2 pr-2 text-dim">{row.agency}</td>
                      <td className="mono py-2 text-right text-ink">{fmtMoney(row.obligated)}</td>
                    </tr>
                  ))}
                  {(u.byAgency || []).length === 0 && (
                    <tr><td className="py-3 text-xs text-faint">No federal awards found under this exact name — try the registered legal name.</td></tr>
                  )}
                </tbody>
              </table>
            </Card>
          </div>

          {(a.insights || []).length > 0 && (
            <Card className="p-5">
              <SectionLabel>Key insights</SectionLabel>
              <div className="mt-3 space-y-2.5">
                {a.insights.map((ins, i) => (
                  <div key={i} className="text-sm leading-relaxed text-dim">
                    <span className="text-ink">{ins.insight}</span>
                    <div className="text-xs text-faint">Evidence: {ins.evidence} {ins.source && <>· {ins.source}</>}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {(a.strategies || []).length > 0 && (
              <Card className="border-ok/30 p-5">
                <SectionLabel>Recommended strategies</SectionLabel>
                <div className="mt-3 space-y-2.5">
                  {a.strategies.map((s, i) => (
                    <div key={i} className="text-sm text-dim">
                      <Pill tone="ok">{s.play}</Pill>
                      <span className="ml-2 text-ink">{s.action}</span>
                      <div className="text-xs text-faint">{s.rationale}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
            {(a.recompetes || []).length > 0 && (
              <Card className="border-warn/30 p-5">
                <SectionLabel>Recompete watch</SectionLabel>
                <div className="mt-3 space-y-2.5">
                  {a.recompetes.map((r, i) => (
                    <div key={i} className="text-sm text-dim">
                      <span className="text-ink">{r.contract}</span> · {r.agency}
                      <Pill tone="warn" className="ml-2">{r.endsBy}</Pill>
                      <div className="text-xs text-faint">{r.angle}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {(u.topAwards || []).length > 0 && (
            <Card className="overflow-hidden">
              <div className="p-4 pb-0"><SectionLabel>Largest contracts (verified, links to USASpending)</SectionLabel></div>
              <div className="overflow-x-auto p-4">
                <table className="w-full text-sm">
                  <thead className="text-xs text-dim">
                    <tr className="border-b border-line">
                      <th className="py-2 pr-3 text-left font-medium">Award</th>
                      <th className="py-2 pr-3 text-left font-medium">Agency</th>
                      <th className="py-2 pr-3 text-right font-medium">Amount</th>
                      <th className="py-2 pr-3 text-left font-medium">Period</th>
                    </tr>
                  </thead>
                  <tbody>
                    {u.topAwards.slice(0, 10).map((aw, i) => (
                      <tr key={i} className="border-b border-line/60 align-top">
                        <td className="max-w-[300px] py-2 pr-3">
                          {aw.url ? (
                            <a href={aw.url} target="_blank" rel="noreferrer"
                               className="inline-flex items-center gap-1 text-cyan hover:underline">
                              <span className="mono text-xs">{aw.awardId}</span> <ExternalLink size={10} />
                            </a>
                          ) : <span className="mono text-xs">{aw.awardId}</span>}
                          <div className="text-[11px] leading-snug text-faint">{aw.description}</div>
                        </td>
                        <td className="py-2 pr-3 text-xs text-dim">{aw.agency}<div className="text-faint">{aw.subAgency}</div></td>
                        <td className="mono py-2 pr-3 text-right text-ink">{fmtMoney(aw.amount)}</td>
                        <td className="mono py-2 pr-3 text-xs text-faint">{aw.startDate} → {aw.endDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {(a.sources || []).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {a.sources.map((s, i) => (
                <a key={i} href={s.url} target="_blank" rel="noreferrer"
                   className="rounded-full border border-line bg-white/5 px-3 py-1 text-xs text-dim hover:border-cyan/40 hover:text-cyan">
                  {s.label} <ExternalLink size={10} className="inline" />
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 p-4 pb-0">
          <SectionLabel>Past reports</SectionLabel>
          <input className="field !w-52 !py-1 text-xs" placeholder="Search competitor…"
            value={reportQ} onChange={(e) => setReportQ(e.target.value)} data-testid="reports-search" />
        </div>
        {reports === null ? (
          <div className="space-y-2 p-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-10" />)}</div>
        ) : reports.length === 0 ? (
          <div className="p-4"><EmptyState icon={Target} title="No analyses yet"
            subtitle="Run your first competitor analysis above — USASpending data works even before you add AI keys." /></div>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {reports.filter((r) => !reportQ || r.competitor.toLowerCase().includes(reportQ.toLowerCase())).map((r) => (
                <tr key={r.id} onClick={() => r.status === "done" && open(r.id)}
                    className={`border-t border-line/60 ${r.status === "done" ? "cursor-pointer hover:bg-white/5" : ""}`}
                    data-testid={`report-row-${r.id}`}>
                  <td className="px-4 py-2.5 font-medium text-ink">{r.competitor}
                    {r.naics && <span className="mono ml-2 text-xs text-faint">{r.naics}</span>}</td>
                  <td className="px-4 py-2.5">
                    <Pill tone={{ done: "ok", running: "cyan", error: "bad" }[r.status]}>{r.status}</Pill>
                  </td>
                  <td className="mono px-4 py-2.5 text-right text-xs text-dim">
                    {r.totalObligated ? fmtMoney(Number(r.totalObligated)) : "—"}
                  </td>
                  <td className="mono px-4 py-2.5 text-xs text-faint">{fmtDateTime(r.createdAt)}</td>
                  {editor && (
                    <td className="px-4 py-2.5 text-right">
                      <button onClick={(e) => del(e, r)} className="text-faint hover:text-bad">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </PageReveal>
  );
}
