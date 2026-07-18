import React, { useEffect, useMemo, useState } from "react";
import { HardDrive, Search, Trash2, Download, FileText } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, PageReveal, EmptyState, Spinner } from "../components/ui";
import { canEdit } from "../lib/helpers";

/* Unified file browser across the org. Shows EVERY file uploaded — both
   org-level assets (7 category folders) and per-item attachments — with
   filters for category, entity type, and full-text filename search. */
const CATEGORY_LABELS = {
  past_performance: "Past Performance",
  commercialization: "Commercialization",
  capability_statements: "Capability Statements",
  quad_charts: "Quad Charts",
  resumes: "Resumes",
  letters_of_support: "Letters of Support",
  pitch_decks: "Pitch Decks",
};

const ENTITY_LABELS = {
  opportunity: "Opportunity attachment",
  proposal: "Proposal attachment",
  venture_doc: "Venture doc attachment",
};

const HUMAN_SIZE = (n) => {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${u[i]}`;
};

const fmtDate = (s) => s ? new Date(s).toLocaleString() : "";

export default function DiskStorage() {
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const [files, setFiles] = useState(null);
  const [q, setQ] = useState("");
  const [scope, setScope] = useState("all");   // all | org | attachments
  const [cat, setCat] = useState("");

  const load = async () => {
    if (!activeOrgId) return;
    try {
      const { data } = await api.get(`/orgs/${activeOrgId}/files`);
      setFiles(data);
    } catch (e) { toast.error(errMsg(e)); setFiles([]); }
  };
  useEffect(() => { load(); }, [activeOrgId]);   // eslint-disable-line react-hooks/exhaustive-deps

  const rows = useMemo(() => (files || []).filter((f) => {
    if (scope === "org" && !f.category) return false;
    if (scope === "attachments" && f.category) return false;
    if (cat && f.category !== cat) return false;
    if (q && !f.filename.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  }), [files, q, scope, cat]);

  const totalBytes = useMemo(() => (files || []).reduce((s, f) => s + (f.sizeBytes || 0), 0), [files]);

  const download = async (id) => {
    try {
      const { data } = await api.get(`/orgs/${activeOrgId}/files/${id}/url`);
      window.open(data.url, "_blank", "noopener");
    } catch (e) { toast.error(errMsg(e)); }
  };
  const remove = async (id, filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try { await api.delete(`/orgs/${activeOrgId}/files/${id}`); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <PageReveal>
      <div>
        <div className="flex items-center gap-2">
          <HardDrive size={22} className="text-cyan" />
          <h1 className="text-2xl font-semibold text-ink">Disk Storage</h1>
        </div>
        <p className="mt-1 text-xs text-faint">
          Every file uploaded across the org — {(files || []).length} file{(files || []).length === 1 ? "" : "s"} · {HUMAN_SIZE(totalBytes)} total.
          Upload files from Company Profile (org assets) or from the drawer on any
          Federal Opportunity, Proposal, Investor Email, or Accelerator Application.
        </p>
      </div>

      <Card className="p-4" data-testid="disk-filters">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-faint" />
            <input className="field pl-7 text-sm"
                   placeholder="Search filename…"
                   value={q} onChange={(e) => setQ(e.target.value)}
                   data-testid="disk-search" />
          </div>
          <select value={scope} onChange={(e) => setScope(e.target.value)}
                  className="field !text-xs" data-testid="disk-scope">
            <option value="all">All files</option>
            <option value="org">Org assets only</option>
            <option value="attachments">Attachments only</option>
          </select>
          <select value={cat} onChange={(e) => setCat(e.target.value)}
                  className="field !text-xs" data-testid="disk-category"
                  disabled={scope === "attachments"}>
            <option value="">All categories</option>
            {Object.entries(CATEGORY_LABELS).map(([k, v]) =>
              <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </Card>

      <Card className="p-0">
        {files === null ? (
          <div className="flex h-40 items-center justify-center"><Spinner /></div>
        ) : rows.length === 0 ? (
          <EmptyState title="No files match" note="Adjust your filters or upload a file from Company Profile." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="disk-table">
              <thead className="border-b border-line bg-white/[0.02] text-left uppercase tracking-widest text-faint">
                <tr>
                  <th className="px-4 py-2.5">File</th>
                  <th className="px-4 py-2.5">Kind</th>
                  <th className="px-4 py-2.5">Size</th>
                  <th className="px-4 py-2.5">Uploaded</th>
                  <th className="px-4 py-2.5 w-24"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((f) => (
                  <tr key={f.id} className="border-b border-line/60 hover:bg-white/5"
                      data-testid={`disk-row-${f.id}`}>
                    <td className="px-4 py-2.5">
                      <button onClick={() => download(f.id)}
                              className="flex items-center gap-1.5 text-left text-ink hover:text-cyan hover:underline">
                        <FileText size={12} className="text-cyan" /> {f.filename}
                      </button>
                    </td>
                    <td className="px-4 py-2.5 text-dim">
                      {f.category
                        ? <Pill tone="cyan" className="!text-[10px]">{CATEGORY_LABELS[f.category] || f.category}</Pill>
                        : <Pill tone="neutral" className="!text-[10px]">{ENTITY_LABELS[f.entityType] || f.entityType}</Pill>}
                    </td>
                    <td className="px-4 py-2.5 mono text-dim">{HUMAN_SIZE(f.sizeBytes)}</td>
                    <td className="px-4 py-2.5 text-faint">{fmtDate(f.createdAt)}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => download(f.id)} className="text-faint hover:text-cyan" aria-label="Download">
                          <Download size={12} />
                        </button>
                        {editor && (
                          <button onClick={() => remove(f.id, f.filename)} className="text-faint hover:text-bad" aria-label="Delete"
                                  data-testid={`disk-delete-${f.id}`}>
                            <Trash2 size={12} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageReveal>
  );
}
