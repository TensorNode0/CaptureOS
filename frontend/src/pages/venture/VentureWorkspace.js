import React, { useEffect, useState } from "react";
import { Plus, Download, PencilLine, Trash2, CheckCircle2, AlertTriangle, Inbox } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { Card, SectionLabel, Pill, Skeleton, EmptyState, PageReveal, Modal, Field, Spinner } from "../../components/ui";
import AIButton from "../../components/AIButton";
import { fmtDateTime, canEdit } from "../../lib/helpers";

function downloadBlob(data, filename) {
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

const FMT_LABEL = { investor_email: "Word", pitch_deck: "PowerPoint", business_plan: "Word",
                    financials: "Excel", accelerator_application: "Word" };

/* Shared venture drafting workspace. `kinds` = [{kind, label, targetLabel}] */
export default function VentureWorkspace({ title, sectionLabel, blurb, kinds, testid }) {
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const [docs, setDocs] = useState(null);


  const [showCreate, setShowCreate] = useState(false);
  const [editDoc, setEditDoc] = useState(null);
  const [busy, setBusy] = useState("");
  const kindSet = kinds.map((k) => k.kind);

  const load = async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/venture-docs`);
    setDocs(data.filter((d) => kindSet.includes(d.kind)));
  };
  useEffect(() => {
    if (!activeOrgId) return;
    load().catch(() => setDocs([]));

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrgId]);

  // poll while any doc is drafting
  useEffect(() => {
    if (!docs?.some((d) => d.draftStatus === "drafting")) return;
    const t = setInterval(() => load().catch(() => {}), 4000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs]);

  const draft = (doc) => async ({ engine: eng, model, effort }) => {
    const { data } = await api.post(`/orgs/${activeOrgId}/venture-docs/${doc.id}/draft`,
      { engine: eng, model: model || "", effort: effort || "standard" });
    await load();
    return data; // jobId powers the telemetry panel
  };

  const del = async (doc) => {
    if (!window.confirm(`Delete "${doc.title}"?`)) return;
    try { await api.delete(`/orgs/${activeOrgId}/venture-docs/${doc.id}`); await load(); }
    catch (e) { toast.error(errMsg(e)); }
  };

  const finalize = async (doc) => {
    try { await api.put(`/orgs/${activeOrgId}/venture-docs/${doc.id}`, { status: "final" }); await load(); }
    catch (e) { toast.error(errMsg(e)); }
  };

  const download = async (doc) => {
    setBusy(`dl-${doc.id}`);
    try {
      const r = await api.get(`/orgs/${activeOrgId}/venture-docs/${doc.id}/download`,
        { responseType: "blob", timeout: 60000 });
      const ext = { Word: "docx", Excel: "xlsx", PowerPoint: "pptx" }[FMT_LABEL[doc.kind]];
      downloadBlob(r.data, `${doc.title}.${ext}`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  return (
    <PageReveal className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <SectionLabel>{sectionLabel}</SectionLabel>
          <h1 className="mt-1 text-2xl font-semibold text-ink">{title}</h1>
          <p className="mt-1 max-w-2xl text-xs text-faint">{blurb}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {editor && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)} data-testid={`${testid}-new`}>
              <Plus size={16} /> New document
            </button>
          )}
        </div>
      </div>

      {docs === null ? (
        <Card className="space-y-2 p-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12" />)}</Card>
      ) : docs.length === 0 ? (
        <Card className="p-6">
          <EmptyState icon={Inbox} title="Nothing here yet"
            subtitle="Create a document and let the AI draft the first version from your company profile."
            action={editor ? (
              <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
                <Plus size={16} /> New document
              </button>) : null} />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {docs.map((doc) => {
            const drafting = doc.draftStatus === "drafting";
            const hasContent = !!(doc.contentMd || (doc.contentJson && Object.keys(doc.contentJson).length));
            return (
              <Card key={doc.id} hover className="flex flex-col p-5" data-testid={`vdoc-${doc.id}`}>
                <div className="mb-1 flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-ink">{doc.title}</div>
                    <div className="mono text-[10px] uppercase tracking-widest text-faint">
                      {kinds.find((k) => k.kind === doc.kind)?.label} · {FMT_LABEL[doc.kind]}
                    </div>
                  </div>
                  <Pill tone={doc.status === "final" ? "ok" : hasContent ? "cyan" : "neutral"}>
                    {doc.status === "final" ? "Final" : hasContent ? "Drafted" : "Empty"}
                  </Pill>
                </div>
                {doc.target && <div className="text-xs text-dim">→ {doc.target}</div>}
                {doc.draftStatus === "error" && (
                  <div className="mt-2 flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-2 text-xs text-bad">
                    <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {doc.draftError}
                  </div>
                )}
                <div className="mt-1 text-[11px] text-faint">
                  {doc.model ? `Engine: ${doc.model} · ` : ""}Updated {fmtDateTime(doc.updatedAt)}
                </div>
                <div className="mt-auto flex flex-wrap gap-1.5 pt-3">
                  {editor && (
                    <AIButton orgId={activeOrgId} compact
                      label={drafting ? "Drafting…" : hasContent ? "Redraft" : "Draft with AI"}
                      onStart={draft(doc)} onDone={load}
                      disabled={drafting} testid={`vdraft-${doc.id}`} />
                  )}
                  {editor && hasContent && !drafting && doc.contentMd !== undefined && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => setEditDoc(doc)}>
                      <PencilLine size={13} /> Edit
                    </button>
                  )}
                  {hasContent && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => download(doc)}
                      disabled={busy === `dl-${doc.id}`}>
                      {busy === `dl-${doc.id}` ? <Spinner size={13} /> : <Download size={13} />} Download
                    </button>
                  )}
                  {editor && hasContent && doc.status !== "final" && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => finalize(doc)}>
                      <CheckCircle2 size={13} /> Finalize
                    </button>
                  )}
                  {editor && (
                    <button className="ml-auto text-faint hover:text-bad" onClick={() => del(doc)}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <CreateModal open={showCreate} onClose={() => setShowCreate(false)}
        orgId={activeOrgId} kinds={kinds} onCreated={load} testid={testid} />
      <EditModal doc={editDoc} onClose={() => setEditDoc(null)} orgId={activeOrgId} onSaved={load} />
    </PageReveal>
  );
}

function CreateModal({ open, onClose, orgId, kinds, onCreated, testid }) {
  const [kind, setKind] = useState(kinds[0].kind);
  const [target, setTarget] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const meta = kinds.find((k) => k.kind === kind) || kinds[0];
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post(`/orgs/${orgId}/venture-docs`, { kind, target, notes });
      toast.success("Document created — hit Draft with AI when ready");
      onCreated(); onClose(); setTarget(""); setNotes("");
    } catch (err) { toast.error(errMsg(err)); }
    finally { setLoading(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title="New document">
      <form onSubmit={submit} className="space-y-3" data-testid={`${testid}-create-form`}>
        <Field label="Type">
          <select className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
            {kinds.map((k) => <option key={k.kind} value={k.kind}>{k.label}</option>)}
          </select>
        </Field>
        <Field label={meta.targetLabel} hint="Used to tailor the draft.">
          <input className="field" value={target} onChange={(e) => setTarget(e.target.value)}
            placeholder={meta.targetPlaceholder}
            list={meta.targetOptions ? `${testid}-target-options` : undefined} />
          {meta.targetOptions && (
            <datalist id={`${testid}-target-options`}>
              {meta.targetOptions.map((o) => <option key={o} value={o} />)}
            </datalist>
          )}
        </Field>
        <Field label="Notes for the AI (optional)" hint="Your ask, stage, numbers you want used.">
          <textarea className="field min-h-[70px]" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <Spinner /> : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EditModal({ doc, onClose, orgId, onSaved }) {
  const [md, setMd] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { setMd(doc?.contentMd || ""); }, [doc]);
  if (!doc) return null;
  const isJson = !doc.contentMd && doc.contentJson && Object.keys(doc.contentJson).length;
  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/orgs/${orgId}/venture-docs/${doc.id}`, { contentMd: md });
      toast.success("Saved");
      onSaved(); onClose();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };
  return (
    <Modal open={!!doc} onClose={onClose} title={`Edit — ${doc.title}`} wide>
      {isJson ? (
        <p className="text-sm text-dim">
          This document is structured data (slides / financial rows). Redraft it with
          different notes, or download and edit in Office.
        </p>
      ) : (
        <>
          <textarea className="field mono min-h-[380px] w-full text-xs" value={md}
            onChange={(e) => setMd(e.target.value)} data-testid="venture-edit-md" />
          <div className="mt-3 flex justify-end gap-2">
            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? <Spinner /> : "Save"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
