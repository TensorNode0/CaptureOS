import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Sparkles, Save, Download, FileText, FileSpreadsheet,
  Presentation, Package, CheckCircle2, AlertTriangle, PencilLine, Bot,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, EmptyState, Modal, Field } from "../components/ui";
import { canEdit, canCreateProposal, canSubmitProposal } from "../lib/helpers";

const FMT_META = {
  docx: { icon: FileText, label: "Word", tone: "cyan" },
  xlsx: { icon: FileSpreadsheet, label: "Excel", tone: "ok" },
  pptx: { icon: Presentation, label: "PowerPoint", tone: "violet" },
};

const STATUS_META = {
  empty: { tone: "neutral", label: "Not drafted" },
  drafted: { tone: "cyan", label: "AI draft" },
  edited: { tone: "warn", label: "Edited" },
  final: { tone: "ok", label: "Final" },
};

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

export default function ProposalWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const cm = canCreateProposal(activeOrg?.role);
  const admin = canSubmitProposal(activeOrg?.role);
  const [opp, setOpp] = useState(null);
  const [proposal, setProposal] = useState(undefined);
  const [secrets, setSecrets] = useState(null);
  const [engine, setEngine] = useState("claude");
  const [busy, setBusy] = useState("");
  const [editDoc, setEditDoc] = useState(null);

  const load = useCallback(async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/opportunities/${id}/proposal`);
    setProposal(data);
    return data;
  }, [activeOrgId, id]);

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities/${id}`).then((r) => setOpp(r.data))
      .catch((e) => { toast.error(errMsg(e)); navigate("/opportunities"); });
    load().catch((e) => toast.error(errMsg(e)));
    api.get(`/orgs/${activeOrgId}/secrets/status`).then((r) => setSecrets(r.data)).catch(() => {});
  }, [activeOrgId, id, load, navigate]);

  const anyDrafting = (proposal?.documents || []).some((d) => d.draftStatus === "drafting");

  useEffect(() => {
    if (!anyDrafting) return undefined;
    const timer = setInterval(async () => {
      try {
        const data = await load();
        const still = (data?.documents || []).some((d) => d.draftStatus === "drafting");
        if (!still) {
          const errs = (data?.documents || []).filter((d) => d.draftStatus === "error");
          if (errs.length) toast.error(errs[0].draftError || "A draft failed");
          else toast.success("Draft complete");
        }
      } catch { /* keep polling */ }
    }, 4000);
    return () => clearInterval(timer);
  }, [anyDrafting, load]);

  const createPackage = async () => {
    setBusy("create");
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/${id}/proposal`);
      setProposal(data);
      toast.success("Proposal package created for this solicitation");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const draft = async (doc) => {
    setBusy(`draft-${doc.id}`);
    try {
      await api.post(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/documents/${doc.id}/draft`,
        { engine });
      toast.info(`Drafting ${doc.title} with ${engine === "openai" ? "ChatGPT" : "Claude"}…`);
      await load();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const finalize = async (doc) => {
    setBusy(`final-${doc.id}`);
    try {
      await api.post(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/documents/${doc.id}/finalize`);
      await load();
      toast.success(`${doc.title} marked final`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const download = async (doc) => {
    setBusy(`dl-${doc.id}`);
    try {
      const r = await api.get(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/documents/${doc.id}/download`,
        { responseType: "blob", timeout: 60000 });
      downloadBlob(r.data, `${doc.title.replace(/\s+/g, "_")}.${doc.fmt}`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const downloadZip = async () => {
    setBusy("zip");
    try {
      const r = await api.get(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/download-zip`,
        { responseType: "blob", timeout: 120000 });
      downloadBlob(r.data, `Proposal_Package_${opp?.solNumber || "package"}.zip`);
    } catch (e) {
      // blob error responses need decoding
      try {
        const text = await e.response.data.text();
        toast.error(JSON.parse(text).detail || "Download failed");
      } catch { toast.error(errMsg(e)); }
    }
    finally { setBusy(""); }
  };

  const markSubmitted = async () => {
    if (!window.confirm("Mark this proposal package as submitted to the government? "
        + "This sets the opportunity stage to Submitted.")) return;
    setBusy("submit");
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/${id}/proposal/submit`);
      setProposal(data);
      toast.success("Proposal marked as submitted");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  if (!opp || proposal === undefined) {
    return <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>;
  }

  const docs = proposal?.documents || [];
  const drafted = docs.filter((d) => d.status !== "empty").length;

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
            Proposal Package
            {proposal && <Pill tone="cyan">{drafted}/{docs.length} drafted</Pill>}
            {proposal?.status === "submitted" && <Pill tone="ok">Submitted</Pill>}
          </h1>
          <div className="mt-1 text-sm text-faint">
            <span className="mono">{opp.solNumber || "—"}</span> · {opp.agency} · {opp.vehicle}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn btn-ghost" onClick={() => navigate(`/opportunities/${id}/capability`)}
            data-testid="goto-capability">
            <Sparkles size={15} /> Capability
          </button>
          {editor && proposal && (
            <label className="flex items-center gap-2 text-xs text-dim">
              <Bot size={14} className="text-faint" />
              <select className="field w-auto py-1.5 text-xs" value={engine}
                onChange={(e) => setEngine(e.target.value)} data-testid="engine-select">
                <option value="claude">Claude</option>
                <option value="openai" disabled={!secrets?.openaiSet}>
                  ChatGPT{secrets?.openaiSet ? "" : " (no key)"}
                </option>
                <option value="emergent" disabled={!secrets?.emergentSet}>
                  Emergent{secrets?.emergentSet ? "" : " (no key)"}
                </option>
                <option value="asksage" disabled={!secrets?.asksageSet}>
                  AskSage{secrets?.asksageSet ? "" : " (no key)"}
                </option>
              </select>
            </label>
          )}
          {proposal && drafted > 0 && (
            <button className="btn btn-primary" onClick={downloadZip} disabled={busy === "zip"}
              data-testid="download-zip">
              {busy === "zip" ? <Spinner /> : <Package size={15} />} Download package (.zip)
            </button>
          )}
          {admin && proposal && drafted > 0 && proposal.status !== "submitted" && (
            <button className="btn btn-violet" onClick={markSubmitted} disabled={busy === "submit"}
              data-testid="mark-submitted">
              {busy === "submit" ? <Spinner /> : <CheckCircle2 size={15} />} Mark as Submitted
            </button>
          )}
        </div>
      </div>

      {!proposal && (
        <Card className="p-6">
          <EmptyState icon={Package} title="No proposal package yet"
            subtitle={`Creates the volume set for a ${opp.vehicle} solicitation — each volume gets a one-click AI draft button, human review/editing, and Word/Excel/PowerPoint export.`}
            action={cm ? (
              <button className="btn btn-primary" onClick={createPackage} disabled={busy === "create"}
                data-testid="create-proposal">
                {busy === "create" ? <Spinner /> : <Package size={16} />} Create proposal package
              </button>
            ) : (
              <span className="text-xs text-faint">Your capture manager creates the proposal package.</span>
            )} />
        </Card>
      )}

      {proposal && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {docs.map((doc) => {
            const fmt = FMT_META[doc.fmt] || FMT_META.docx;
            const st = STATUS_META[doc.status] || STATUS_META.empty;
            const drafting = doc.draftStatus === "drafting";
            const FmtIcon = fmt.icon;
            return (
              <Card key={doc.id} hover className="flex flex-col p-5" data-testid={`doc-${doc.docType}`}>
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="rounded-xl border border-line bg-white/5 p-2">
                      <FmtIcon size={18} className="text-cyan" />
                    </div>
                    <div>
                      <div className="font-medium text-ink">{doc.title}</div>
                      <div className="mono text-[10px] uppercase tracking-widest text-faint">
                        {fmt.label} · .{doc.fmt}
                      </div>
                    </div>
                  </div>
                  <Pill tone={st.tone}>{st.label}</Pill>
                </div>

                {doc.draftStatus === "error" && (
                  <div className="mb-2 flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-2 text-xs text-bad">
                    <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {doc.draftError}
                  </div>
                )}
                {doc.model && (
                  <div className="mb-2 text-[11px] text-faint">Last draft: {doc.model}</div>
                )}

                <div className="mt-auto flex flex-wrap gap-1.5 pt-2">
                  {editor && (
                    <button className="btn btn-primary px-3 py-1.5 text-xs" onClick={() => draft(doc)}
                      disabled={drafting || !!busy} data-testid={`draft-${doc.docType}`}>
                      {drafting ? <Spinner size={13} /> : <Sparkles size={13} />}
                      {drafting ? "Drafting…" : doc.status === "empty" ? "Draft with AI" : "Redraft"}
                    </button>
                  )}
                  {editor && doc.status !== "empty" && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => setEditDoc(doc)}
                      data-testid={`edit-${doc.docType}`}>
                      <PencilLine size={13} /> Review & edit
                    </button>
                  )}
                  {doc.status !== "empty" && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => download(doc)}
                      disabled={busy === `dl-${doc.id}`} data-testid={`download-${doc.docType}`}>
                      {busy === `dl-${doc.id}` ? <Spinner size={13} /> : <Download size={13} />} Download
                    </button>
                  )}
                  {editor && (doc.status === "drafted" || doc.status === "edited") && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => finalize(doc)}
                      data-testid={`finalize-${doc.docType}`}>
                      <CheckCircle2 size={13} /> Finalize
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <DocEditor doc={editDoc} onClose={() => setEditDoc(null)} orgId={activeOrgId} oppId={id}
        onSaved={async () => { setEditDoc(null); await load(); }} />
    </PageReveal>
  );
}

function DocEditor({ doc, onClose, orgId, oppId, onSaved }) {
  const [md, setMd] = useState("");
  const [json, setJson] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (doc) {
      setMd(doc.contentMd || "");
      setJson(doc.contentJson || {});
    }
  }, [doc]);

  if (!doc) return null;

  const save = async () => {
    setSaving(true);
    try {
      const body = doc.fmt === "docx" ? { contentMd: md } : { contentJson: json };
      await api.put(`/orgs/${orgId}/opportunities/${oppId}/proposal/documents/${doc.id}`, body);
      toast.success(`${doc.title} saved`);
      await onSaved();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  return (
    <Modal open={!!doc} onClose={onClose} title={`Edit — ${doc.title}`} maxW="max-w-4xl">
      {doc.fmt === "docx" && (
        <Field label="Content (markdown — exported to Word)">
          <textarea className="field mono min-h-[420px] text-[13px]" value={md}
            onChange={(e) => setMd(e.target.value)} data-testid="doc-editor-md" />
        </Field>
      )}
      {doc.fmt === "xlsx" && (
        <CostEditor json={json} setJson={setJson} />
      )}
      {doc.fmt === "pptx" && (
        <DeckEditor json={json} setJson={setJson} />
      )}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={save} disabled={saving} data-testid="doc-editor-save">
          {saving ? <Spinner /> : <Save size={15} />} Save
        </button>
      </div>
    </Modal>
  );
}

function CostEditor({ json, setJson }) {
  const rows = json?.rows || [];
  const total = rows.reduce((s, r) => s + (Number(r.cost) || 0), 0);
  const setRow = (i, patch) => {
    const next = [...rows];
    next[i] = { ...next[i], ...patch };
    setJson({ ...json, rows: next });
  };
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <SectionLabel>Cost lines</SectionLabel>
        <div className="mono text-sm text-ink">Total: ${total.toLocaleString()}</div>
      </div>
      <div className="max-h-[380px] overflow-y-auto rounded-xl border border-line">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-[var(--bg-elev)]">
            <tr className="text-left text-xs text-dim">
              <th className="p-2">Category</th><th className="p-2">Item</th>
              <th className="p-2">Basis</th><th className="p-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-line/50">
                <td className="p-1.5"><input className="field py-1 text-xs" value={r.category || ""}
                  onChange={(e) => setRow(i, { category: e.target.value })} /></td>
                <td className="p-1.5"><input className="field py-1 text-xs" value={r.item || ""}
                  onChange={(e) => setRow(i, { item: e.target.value })} /></td>
                <td className="p-1.5"><input className="field py-1 text-xs" value={r.basis || ""}
                  onChange={(e) => setRow(i, { basis: e.target.value })} /></td>
                <td className="p-1.5"><input type="number" className="field w-28 py-1 text-right text-xs"
                  value={r.cost ?? 0} onChange={(e) => setRow(i, { cost: Number(e.target.value) || 0 })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Field label="Cost narrative">
        <textarea className="field min-h-[90px] text-sm" value={json?.narrative || ""}
          onChange={(e) => setJson({ ...json, narrative: e.target.value })} />
      </Field>
    </div>
  );
}

function DeckEditor({ json, setJson }) {
  const slides = json?.slides || [];
  const setSlide = (i, patch) => {
    const next = [...slides];
    next[i] = { ...next[i], ...patch };
    setJson({ ...json, slides: next });
  };
  return (
    <div className="max-h-[460px] space-y-3 overflow-y-auto pr-1">
      {slides.map((s, i) => (
        <div key={i} className="rounded-xl border border-line bg-white/[0.02] p-3">
          <div className="mb-1.5 flex items-center gap-2">
            <Pill tone="violet">Slide {i + 1}</Pill>
            <input className="field flex-1 py-1 text-sm font-medium" value={s.title || ""}
              onChange={(e) => setSlide(i, { title: e.target.value })} />
          </div>
          <textarea className="field mono min-h-[70px] text-xs"
            value={(s.bullets || []).join("\n")}
            onChange={(e) => setSlide(i, { bullets: e.target.value.split("\n") })}
            placeholder="One bullet per line" />
        </div>
      ))}
    </div>
  );
}
