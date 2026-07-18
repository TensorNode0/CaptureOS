import React, { useState } from "react";
import { toast } from "sonner";
import { Upload, Download, ExternalLink, Link2, Unlink, Save } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { Card, SectionLabel, Pill, Spinner, Field } from "./ui";

/* Bidirectional Overleaf sync for a Federal Proposal. Backend does the git
   heavy lifting (see backend/overleaf.py); this UI just orchestrates:
     1. Link a proposal to an Overleaf project (paste the URL or id).
     2. Push all volumes → Overleaf as .md files + a main.tex wrapper.
     3. Pull the latest revisions from Overleaf back into the volumes.
   Token is set once per org in Settings → API Keys → Overleaf. */
export default function OverleafPanel({ orgId, proposal, onSynced, canEdit }) {
  const linked = !!proposal?.overleafProjectId;
  const [urlInput, setUrlInput] = useState("");
  const [busy, setBusy] = useState("");     // "link" | "push" | "pull" | "unlink" | ""
  const [showLink, setShowLink] = useState(!linked);

  const link = async () => {
    if (!urlInput.trim()) return;
    setBusy("link");
    try {
      const { data } = await api.post(
        `/orgs/${orgId}/proposals/${proposal.id}/overleaf/link`,
        { projectIdOrUrl: urlInput.trim() });
      toast.success("Overleaf project linked", { description: `Project ${data.overleafProjectId.slice(0, 8)}…` });
      setUrlInput("");
      setShowLink(false);
      onSynced?.({ ...proposal, overleafProjectId: data.overleafProjectId });
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const unlink = async () => {
    if (!window.confirm("Unlink this Overleaf project? The Overleaf project itself will not be affected — you can re-link it any time.")) return;
    setBusy("unlink");
    try {
      await api.post(`/orgs/${orgId}/proposals/${proposal.id}/overleaf/unlink`);
      toast.success("Overleaf project unlinked");
      onSynced?.({ ...proposal, overleafProjectId: "", overleafLastSync: null });
      setShowLink(true);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const push = async () => {
    setBusy("push");
    try {
      const { data } = await api.post(`/orgs/${orgId}/proposals/${proposal.id}/overleaf/push`);
      if (data.noChanges) {
        toast.info("Overleaf already up to date");
      } else {
        toast.success(`Pushed to Overleaf`, { description: `${data.filesWritten} file(s) · ${data.commitSha.slice(0, 7)}` });
        onSynced?.({ ...proposal, overleafLastSync: new Date().toISOString() });
      }
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const pull = async () => {
    if (!window.confirm("Pull the latest revision from Overleaf? This overwrites any unsaved edits in the volumes here.")) return;
    setBusy("pull");
    try {
      const { data } = await api.post(`/orgs/${orgId}/proposals/${proposal.id}/overleaf/pull`);
      const n = (data.updated || []).length;
      if (n === 0) {
        toast.info("Nothing changed on Overleaf since the last sync");
      } else {
        toast.success(`Pulled ${n} updated file(s) from Overleaf`,
          { description: (data.updated || []).slice(0, 3).join(", ") + (n > 3 ? `, +${n - 3} more` : "") });
        onSynced?.({ ...proposal, overleafLastSync: new Date().toISOString() });
      }
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const lastSyncLabel = proposal?.overleafLastSync
    ? new Date(proposal.overleafLastSync).toLocaleString()
    : "never";

  return (
    <Card className="p-4" data-testid="overleaf-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-[220px]">
          <SectionLabel>Overleaf sync</SectionLabel>
          <p className="mt-1 max-w-xl text-xs text-faint">
            Edit your proposal in <a className="text-cyan hover:underline" href="https://www.overleaf.com/" target="_blank" rel="noreferrer">Overleaf</a> and
            round-trip changes back here. First, add your Overleaf git auth token in
            Settings → API Keys, then paste your project URL below.
          </p>
        </div>
        {linked && (
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="cyan">
              Linked · <span className="mono">{proposal.overleafProjectId.slice(0, 8)}…</span>
            </Pill>
            <a
              href={`https://www.overleaf.com/project/${proposal.overleafProjectId}`}
              target="_blank" rel="noreferrer"
              className="btn btn-ghost !py-1.5 !px-2 text-xs"
              data-testid="overleaf-open"
              title="Open the project in Overleaf">
              <ExternalLink size={13} /> Open in Overleaf
            </a>
          </div>
        )}
      </div>

      {(!linked || showLink) && canEdit && (
        <div className="mt-3 border-t border-line/60 pt-3">
          <Field label="Overleaf project URL or id"
                 hint="Copy from your browser address bar on overleaf.com — e.g. https://www.overleaf.com/project/aef3…">
            <div className="flex gap-2">
              <input className="field flex-1 mono" value={urlInput}
                     onChange={(e) => setUrlInput(e.target.value)}
                     placeholder="https://www.overleaf.com/project/<project_id>"
                     data-testid="overleaf-url-input" />
              <button className="btn btn-primary" onClick={link}
                      disabled={busy === "link" || !urlInput.trim()}
                      data-testid="overleaf-link-save">
                {busy === "link" ? <Spinner /> : <Save size={14} />} Save
              </button>
              {linked && (
                <button className="btn btn-ghost" onClick={() => setShowLink(false)}>
                  Cancel
                </button>
              )}
            </div>
          </Field>
        </div>
      )}

      {linked && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line/60 pt-3">
          {canEdit && (
            <>
              <button className="btn btn-primary" onClick={push} disabled={!!busy}
                      data-testid="overleaf-push">
                {busy === "push" ? <Spinner /> : <Upload size={14} />}
                Push to Overleaf
              </button>
              <button className="btn btn-ghost" onClick={pull} disabled={!!busy}
                      data-testid="overleaf-pull">
                {busy === "pull" ? <Spinner /> : <Download size={14} />}
                Pull from Overleaf
              </button>
              <button className="btn btn-ghost" onClick={() => setShowLink(true)}
                      disabled={!!busy} title="Change linked project">
                <Link2 size={13} /> Change project
              </button>
              <button className="btn btn-ghost !text-bad" onClick={unlink}
                      disabled={!!busy} data-testid="overleaf-unlink">
                {busy === "unlink" ? <Spinner /> : <Unlink size={13} />} Unlink
              </button>
            </>
          )}
          <span className="ml-auto text-[11px] text-faint">Last synced: {lastSyncLabel}</span>
        </div>
      )}
    </Card>
  );
}
