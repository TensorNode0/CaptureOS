import React, { useEffect, useRef, useState } from "react";
import { Upload, Trash2, Download, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useSubscription, hasTier } from "../lib/billing";
import { Spinner } from "./ui";

/* Reusable files panel. Two modes controlled by `mode`:
     mode="category"  → org-level asset in one of the 7 curated buckets
                        (Past Performance, Capability Statements, etc.)
     mode="entity"    → per-item attachment for a specific opportunity /
                        proposal / venture_doc (entityType + entityId required)
   Uploads are POST /api/orgs/{orgId}/files as multipart. Downloads mint a
   short-lived signed URL via GET .../files/{id}/url.
*/
const HUMAN_SIZE = (n) => {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${u[i]}`;
};

export default function FilesPanel({
  orgId, mode, category = "", entityType = "", entityId = "",
  label, canEdit = true, testid = "files-panel",
}) {
  const { sub } = useSubscription();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  const params = mode === "category"
    ? { category }
    : { entityType, entityId };

  const load = async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams(params).toString();
      const { data } = await api.get(`/orgs/${orgId}/files?${q}`);
      setFiles(data);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (orgId && hasTier(sub, "full")) load(); }, [orgId, category, entityType, entityId, sub]); // eslint-disable-line react-hooks/exhaustive-deps

  const doUpload = async (fileList) => {
    for (const f of fileList) {
      const form = new FormData();
      form.append("file", f);
      if (mode === "category") form.append("category", category);
      else { form.append("entityType", entityType); form.append("entityId", entityId); }
      setUploading(true);
      try {
        await api.post(`/orgs/${orgId}/files`, form,
          { headers: { "Content-Type": "multipart/form-data" } });
        toast.success(`Uploaded ${f.name}`);
      } catch (e) { toast.error(errMsg(e)); }
      finally { setUploading(false); }
    }
    await load();
  };

  const download = async (id, filename) => {
    try {
      const { data } = await api.get(`/orgs/${orgId}/files/${id}/url`);
      window.open(data.url, "_blank", "noopener");
    } catch (e) { toast.error(errMsg(e)); }
  };

  const remove = async (id, filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/orgs/${orgId}/files/${id}`);
      await load();
    } catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div className="rounded-lg border border-line/60 bg-white/[0.02] p-3" data-testid={testid}>
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-medium text-ink">{label}</div>
        {canEdit && hasTier(sub, "full") && (
          <>
            <input type="file" ref={inputRef} className="hidden" multiple
                   onChange={(e) => { if (e.target.files?.length) doUpload(e.target.files); e.target.value = ""; }} />
            <button className="btn btn-ghost !py-1 !px-2 !text-[11px]"
                    onClick={() => inputRef.current?.click()}
                    disabled={uploading}
                    data-testid={`${testid}-upload`}>
              {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
              Upload
            </button>
          </>
        )}
      </div>
      <div className="mt-2 space-y-1">
        {!hasTier(sub, "full") ? (
          <div className="py-2 text-[11px] text-faint" data-testid={`${testid}-locked`}>
            Disk storage is part of the Full Capture plan.{" "}
            <a href="/pricing" className="text-cyan hover:underline">Upgrade to unlock</a>.
          </div>
        ) : loading ? (
          <div className="flex items-center gap-2 py-2 text-[11px] text-faint"><Spinner size={12} /> Loading…</div>
        ) : files.length === 0 ? (
          <div className="py-2 text-[11px] text-faint">No files yet.</div>
        ) : files.map((f) => (
          <div key={f.id} className="flex items-center justify-between gap-2 rounded border border-line/40 bg-panel/40 px-2 py-1.5"
               data-testid={`${testid}-row-${f.id}`}>
            <div className="flex min-w-0 items-center gap-1.5">
              <FileText size={12} className="shrink-0 text-cyan" />
              <button onClick={() => download(f.id, f.filename)}
                      className="truncate text-left text-[12px] text-dim hover:text-ink hover:underline"
                      title={f.filename}
                      data-testid={`${testid}-download-${f.id}`}>
                {f.filename}
              </button>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="mono text-[10px] text-faint">{HUMAN_SIZE(f.sizeBytes)}</span>
              <button onClick={() => download(f.id, f.filename)}
                      className="text-faint hover:text-cyan" aria-label="Download"
                      title="Download">
                <Download size={11} />
              </button>
              {canEdit && (
                <button onClick={() => remove(f.id, f.filename)}
                        className="text-faint hover:text-bad" aria-label="Delete"
                        title="Delete"
                        data-testid={`${testid}-delete-${f.id}`}>
                  <Trash2 size={11} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
