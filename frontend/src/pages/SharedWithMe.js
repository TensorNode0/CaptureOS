import React, { useEffect, useState } from "react";
import { FolderLock, Eye, PencilLine, Save, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Skeleton, EmptyState, PageReveal, Field, Spinner } from "../components/ui";

/* Subcontractor workspace: only the resources the admin explicitly shared. */

function WbsEditor({ value, onChange }) {
  const rows = value?.wbs || [];
  const set = (i, k, v) => {
    const next = rows.map((r, j) => (j === i ? { ...r, [k]: v } : r));
    onChange({ ...value, wbs: next });
  };
  const addRow = () => onChange({ ...value, wbs: [...rows, { code: "", task: "", owner: "", startMonth: 1, endMonth: 1 }] });
  const delRow = (i) => onChange({ ...value, wbs: rows.filter((_, j) => j !== i) });
  return (
    <div>
      <Field label="Schedule length (months)">
        <input type="number" className="field mono !w-28" value={value?.scheduleMonths ?? ""}
          onChange={(e) => onChange({ ...value, scheduleMonths: Number(e.target.value) || 0 })} />
      </Field>
      <table className="mt-3 w-full text-xs">
        <thead className="text-faint">
          <tr><th className="pb-1 text-left">Code</th><th className="pb-1 text-left">Task</th>
              <th className="pb-1 text-left">Owner</th><th className="pb-1 text-left">Start</th>
              <th className="pb-1 text-left">End</th><th></th></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="pr-1 py-0.5"><input className="field mono !py-1 !text-xs" value={r.code || ""} onChange={(e) => set(i, "code", e.target.value)} /></td>
              <td className="pr-1 py-0.5"><input className="field !py-1 !text-xs" value={r.task || ""} onChange={(e) => set(i, "task", e.target.value)} /></td>
              <td className="pr-1 py-0.5"><input className="field !py-1 !text-xs" value={r.owner || ""} onChange={(e) => set(i, "owner", e.target.value)} /></td>
              <td className="pr-1 py-0.5 w-16"><input type="number" className="field mono !py-1 !text-xs" value={r.startMonth ?? ""} onChange={(e) => set(i, "startMonth", Number(e.target.value) || 0)} /></td>
              <td className="pr-1 py-0.5 w-16"><input type="number" className="field mono !py-1 !text-xs" value={r.endMonth ?? ""} onChange={(e) => set(i, "endMonth", Number(e.target.value) || 0)} /></td>
              <td className="py-0.5"><button onClick={() => delRow(i)} className="text-faint hover:text-bad"><Trash2 size={13} /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="btn btn-ghost mt-2 !py-1 !px-2 text-xs" onClick={addRow}><Plus size={13} /> Add row</button>
    </div>
  );
}

function SectionEditor({ grant, draft, setDraft }) {
  const key = grant.sectionKey;
  if (key === "wbs") return <WbsEditor value={draft} onChange={setDraft} />;
  if (key === "summary") return (
    <div className="space-y-3">
      <Field label="Title"><input className="field" value={draft?.title || ""} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></Field>
      <Field label="Abstract"><textarea className="field min-h-[80px]" value={draft?.abstract || ""} onChange={(e) => setDraft({ ...draft, abstract: e.target.value })} /></Field>
      <Field label="Executive summary (markdown)"><textarea className="field mono min-h-[140px] text-xs" value={draft?.executiveSummary || ""} onChange={(e) => setDraft({ ...draft, executiveSummary: e.target.value })} /></Field>
    </div>
  );
  // sow / budget: structured JSON with a guarded editor
  const sub = draft?.[key];
  return (
    <Field label={`${grant.label} (JSON — edit carefully)`}
           hint="Structure must stay valid JSON; the capture team sees your changes live.">
      <textarea className="field mono min-h-[220px] text-xs"
        value={typeof sub === "string" ? sub : JSON.stringify(sub ?? {}, null, 2)}
        onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />
    </Field>
  );
}

function GrantCard({ grant, orgId, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const writable = grant.access === "write";
  const isDoc = grant.resourceType === "proposal_doc";

  const openEdit = () => {
    setDraft(isDoc ? { contentMd: grant.contentMd || "" } : { ...(grant.content || {}) });
    setEditing(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      let payload;
      if (isDoc) payload = { contentMd: draft.contentMd };
      else {
        const content = { ...draft };
        const key = grant.sectionKey;
        if ((key === "sow" || key === "budget") && typeof content[key] === "string") {
          try { content[key] = JSON.parse(content[key]); }
          catch { toast.error("That JSON isn't valid yet — fix it and save again."); setSaving(false); return; }
        }
        payload = { content };
      }
      await api.put(`/orgs/${orgId}/shared/${grant.grantId}`, payload);
      toast.success("Saved — the capture team sees your update");
      setEditing(false);
      onSaved();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  return (
    <Card className="p-5" data-testid={`shared-${grant.grantId}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="font-medium text-ink">{grant.label}</div>
          <div className="text-xs text-faint">{grant.opportunity.title}
            {grant.opportunity.solNumber && <span className="mono ml-2">{grant.opportunity.solNumber}</span>}</div>
        </div>
        <Pill tone={writable ? "cyan" : "neutral"}>
          {writable ? <><PencilLine size={11} /> read & write</> : <><Eye size={11} /> read-only</>}
        </Pill>
      </div>

      {!editing && (
        <div className="mt-3">
          {isDoc ? (
            grant.contentMd
              ? <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-white/5 p-3 text-xs leading-relaxed text-dim">{grant.contentMd}</pre>
              : <pre className="max-h-64 overflow-auto rounded-lg border border-line bg-white/5 p-3 text-xs text-dim">{JSON.stringify(grant.contentJson || {}, null, 2)}</pre>
          ) : (
            <pre className="max-h-64 overflow-auto rounded-lg border border-line bg-white/5 p-3 text-xs text-dim">{JSON.stringify(grant.content || {}, null, 2)}</pre>
          )}
          {writable && (
            <button className="btn btn-primary mt-3 !py-1.5 !px-3 text-xs" onClick={openEdit}
                    data-testid={`edit-shared-${grant.grantId}`}>
              <PencilLine size={13} /> Edit
            </button>
          )}
        </div>
      )}

      {editing && (
        <div className="mt-3 space-y-3">
          {isDoc ? (
            <textarea className="field mono min-h-[260px] w-full text-xs" value={draft.contentMd}
              onChange={(e) => setDraft({ contentMd: e.target.value })} />
          ) : (
            <SectionEditor grant={grant} draft={draft} setDraft={setDraft} />
          )}
          <div className="flex gap-2">
            <button className="btn btn-primary !py-1.5 !px-3 text-xs" onClick={save} disabled={saving}
                    data-testid={`save-shared-${grant.grantId}`}>
              {saving ? <Spinner size={13} /> : <Save size={13} />} Save
            </button>
            <button className="btn btn-ghost !py-1.5 !px-3 text-xs" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function SharedWithMe() {
  const { activeOrgId } = useAuth();
  const [grants, setGrants] = useState(null);

  const load = () => api.get(`/orgs/${activeOrgId}/shared`)
    .then((r) => setGrants(r.data)).catch(() => setGrants([]));
  useEffect(() => { if (activeOrgId) load(); }, [activeOrgId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <PageReveal className="max-w-4xl space-y-5">
      <div>
        <SectionLabel>Subcontractor Workspace</SectionLabel>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Shared with me</h1>
        <p className="mt-1 text-xs text-faint">
          The proposal sections this team has shared with you. Read-only items are
          for your reference; writable items save straight into the live proposal.
        </p>
      </div>
      {grants === null ? (
        <Card className="space-y-2 p-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14" />)}</Card>
      ) : grants.length === 0 ? (
        <Card className="p-6">
          <EmptyState icon={FolderLock} title="Nothing shared yet"
            subtitle="When the team's administrator shares proposal sections with you, they appear here." />
        </Card>
      ) : (
        grants.map((g) => <GrantCard key={g.grantId} grant={g} orgId={activeOrgId} onSaved={load} />)
      )}
    </PageReveal>
  );
}
