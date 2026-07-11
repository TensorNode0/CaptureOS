import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Package, FileText, CheckCircle2, Gauge } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Skeleton, EmptyState, PageReveal } from "../components/ui";
import { fmtDate, fmtDateTime, dueColor } from "../lib/helpers";

const COLOR_TONES = { pink: "violet", red: "warn", gold: "ok" };

export default function Proposals() {
  const { activeOrgId } = useAuth();
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fDueWithin, setFDueWithin] = useState(0);

  const visible = (rows || []).filter((p) => {
    if (q && !(`${p.oppTitle} ${p.solNumber} ${p.agency}`.toLowerCase().includes(q.toLowerCase()))) return false;
    if (fStatus && (p.status || "draft") !== fStatus) return false;
    if (fDueWithin) {
      if (!p.dueDate) return false;
      const days = (new Date(p.dueDate).getTime() - Date.now()) / 86400000;
      if (days < 0 || days > fDueWithin) return false;
    }
    return true;
  });

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/proposals`).then((r) => setRows(r.data)).catch(() => setRows([]));
  }, [activeOrgId]);

  return (
    <PageReveal className="space-y-5">
      <div>
        <SectionLabel>Proposal Hub</SectionLabel>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Proposals</h1>
        <p className="mt-1 text-xs text-faint">
          Every package your team has created — open one to keep drafting, run the AI
          evaluation, mark it submitted, or download the documents.
        </p>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <input className="field !w-56" placeholder="Search title, sol#, agency…" value={q}
            onChange={(e) => setQ(e.target.value)} data-testid="proposals-search" />
          <select className="field !w-auto" value={fStatus} onChange={(e) => setFStatus(e.target.value)}
            data-testid="proposals-status">
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
          </select>
          <select className="field !w-auto" value={fDueWithin} onChange={(e) => setFDueWithin(Number(e.target.value))}
            data-testid="proposals-due">
            <option value={0}>Any due date</option>
            <option value={7}>Due ≤ 7 days</option>
            <option value={30}>Due ≤ 30 days</option>
            <option value={90}>Due ≤ 90 days</option>
          </select>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {rows === null ? (
          <div className="space-y-2 p-4">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : visible.length === 0 ? (
          <EmptyState icon={Package} title="No proposals yet"
            subtitle="Open an opportunity in Federal Opportunities and create its proposal package — it will appear here." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="proposals-table">
              <thead className="bg-elev/90 text-xs text-dim">
                <tr className="border-b border-line">
                  <th className="px-3 py-2.5 text-left font-medium">Proposal</th>
                  <th className="px-3 py-2.5 text-left font-medium">Agency</th>
                  <th className="px-3 py-2.5 text-left font-medium">Due</th>
                  <th className="px-3 py-2.5 text-left font-medium">Volumes</th>
                  <th className="px-3 py-2.5 text-left font-medium">AI Evaluation</th>
                  <th className="px-3 py-2.5 text-left font-medium">Status</th>
                  <th className="px-3 py-2.5 text-left font-medium">Updated</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((p) => {
                  const due = dueColor(p.dueDate);
                  return (
                    <tr key={p.id}
                        onClick={() => navigate(`/opportunities/${p.opportunityId}/proposal`)}
                        className="cursor-pointer border-b border-line/60 transition-colors hover:bg-white/5"
                        data-testid={`proposal-row-${p.id}`}>
                      <td className="px-3 py-3">
                        <div className="font-medium text-ink">{p.oppTitle}</div>
                        <div className="mono text-xs text-faint">{p.solNumber || "—"}</div>
                      </td>
                      <td className="px-3 py-3 text-dim">{p.agency || "—"}</td>
                      <td className="px-3 py-3">
                        <span className={`mono text-sm ${due.cls}`}>{fmtDate(p.dueDate)}</span>
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center gap-1.5 text-dim">
                          <FileText size={13} className="text-faint" />
                          {p.drafted}/{p.totalDocs} drafted
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        {p.overallScore != null ? (
                          <span className="inline-flex items-center gap-1.5">
                            <Gauge size={13} className="text-cyan" />
                            <span className="mono text-ink">{p.overallScore}</span>
                            {p.colorReview && (
                              <Pill tone={COLOR_TONES[p.colorReview] || "neutral"}>
                                {p.colorReview} team
                              </Pill>
                            )}
                          </span>
                        ) : <span className="text-xs text-faint">Not evaluated</span>}
                      </td>
                      <td className="px-3 py-3">
                        {p.status === "submitted" ? (
                          <Pill tone="ok"><CheckCircle2 size={11} /> Submitted</Pill>
                        ) : <Pill tone="neutral">{p.status || "draft"}</Pill>}
                      </td>
                      <td className="px-3 py-3 mono text-xs text-faint">{fmtDateTime(p.updatedAt)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageReveal>
  );
}
