import React, { useEffect, useState } from "react";
import { Radar, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { Card, Pill } from "./ui";
import AIButton from "./AIButton";
import SimpleMd from "./SimpleMd";
import { fmtDateTime } from "../lib/helpers";

/* AI web-search scan for a venture page (investor_scan / accelerator_scan):
   one report per org+kind, redrafted in place. Claude-only — the scan uses
   live web search, which runs on the Anthropic engine. */
export default function ScanPanel({ orgId, kind, label, blurb, editor, testid }) {
  const [doc, setDoc] = useState(null);
  const [open, setOpen] = useState(true);

  const load = async () => {
    const { data } = await api.get(`/orgs/${orgId}/venture-docs`, { params: { kind } });
    setDoc(data[0] || null);
    return data[0] || null;
  };
  useEffect(() => {
    if (!orgId) return;
    load().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId, kind]);

  const start = async ({ engine, model, effort }) => {
    let target = doc;
    if (!target) {
      const { data } = await api.post(`/orgs/${orgId}/venture-docs`, { kind, target: "", notes: "" });
      target = data;
      setDoc(data);
    }
    const { data } = await api.post(`/orgs/${orgId}/venture-docs/${target.id}/draft`,
      { engine, model: model || "", effort: effort || "standard" });
    return data; // jobId → AIButton telemetry
  };

  const done = async () => {
    const fresh = await load().catch(() => null);
    if (fresh?.contentMd) { setOpen(true); toast.success("Scan ready"); }
  };

  const remove = async () => {
    if (!doc || !window.confirm("Delete this scan report?")) return;
    try { await api.delete(`/orgs/${orgId}/venture-docs/${doc.id}`); setDoc(null); }
    catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <Card className="p-4" data-testid={`${testid}-panel`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-[220px]">
          <div className="flex items-center gap-2 text-sm font-medium text-ink">
            <Radar size={15} className="text-cyan" /> {label}
          </div>
          <p className="mt-1 max-w-xl text-xs text-faint">{blurb}</p>
        </div>
        {editor && (
          <AIButton orgId={orgId} compact lockEngine="claude" icon={Radar}
            label={doc?.contentMd ? "Re-scan" : "AI scan"}
            onStart={start} onDone={done} testid={testid} />
        )}
      </div>
      {doc?.contentMd && (
        <div className="mt-3 border-t border-line/60 pt-3">
          <div className="flex items-center gap-2">
            <Pill tone="cyan">Latest scan</Pill>
            <span className="text-[11px] text-faint">
              {doc.model ? `${doc.model} · ` : ""}{fmtDateTime(doc.updatedAt)}
            </span>
            <button className="text-xs text-cyan hover:underline" onClick={() => setOpen(!open)}>
              {open ? "Collapse" : "Expand"}
            </button>
            {editor && (
              <button className="ml-auto text-faint hover:text-bad" onClick={remove}
                      aria-label="Delete scan"><Trash2 size={13} /></button>
            )}
          </div>
          {open && <SimpleMd md={doc.contentMd} className="mt-2" />}
        </div>
      )}
    </Card>
  );
}
