import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X, ExternalLink, Star, Save, Sparkles, AlertTriangle, CheckCircle2,
  HelpCircle, MinusCircle,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { Pill, SectionLabel, Spinner } from "./ui";
import AIButton from "./AIButton";
import {
  fmtMoney, fmtDate, fmtDateTime, dueColor, businessDaysUntil,
  ELIG_STATUS, FIT_BAND_CLS, PRIORITY_CFG, PWIN_CLS,
} from "../lib/helpers";

/* Quick-qualification drawer: answer "eligible? fit? winnable? worth it?
   what next?" in 30 seconds without leaving the table. */

const GATE_ICON = {
  pass: <CheckCircle2 size={13} className="text-ok" />,
  fail: <X size={13} className="text-bad" />,
  conditional: <AlertTriangle size={13} className="text-warn" />,
  unknown: <HelpCircle size={13} className="text-faint" />,
};

function Sect({ title, children, testid }) {
  return (
    <div className="border-t border-line/60 px-4 py-3" data-testid={testid}>
      <SectionLabel className="!text-[10px]">{title}</SectionLabel>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function KV({ k, v, mono }) {
  return (
    <div className="flex items-start justify-between gap-3 text-xs">
      <span className="shrink-0 text-faint">{k}</span>
      <span className={`text-right text-dim ${mono ? "mono" : ""}`}>{v ?? <span className="text-faint">Unknown</span>}</span>
    </div>
  );
}

export default function OppDrawer({ opp, orgId, editor, onSaved, onClose }) {
  const navigate = useNavigate();
  const buildForm = (o) => ({
    addressableValue: o?.financials?.addressableValue ?? "",
    valueType: o?.valueType || "",
    pursuitRole: o?.pursuitRole || "",
    vehicleAccess: o?.vehicleAccess || "",
    incumbent: o?.incumbent || "",
    owner: o?.capture?.owner || "",
    nextAction: o?.capture?.nextAction || "",
    nextActionDue: (o?.capture?.nextActionDue || "").slice(0, 10),
    call: o?.decision?.call || "TBD",
    rationale: o?.decision?.rationale || "",
    pwin: o?.pwinView?.pct ?? 0,
    fitOverride: o?.fitComputed?.override?.score ? String(o.fitComputed.override.score) : "",
    fitOverrideNote: o?.fitComputed?.override?.note || "",
  });
  const [form, setForm] = useState(() => buildForm(opp));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(buildForm(opp));
    setDirty(false);
  }, [opp]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!opp) return null;
  const set = (k) => (e) => { setForm((f) => ({ ...f, [k]: e.target.value })); setDirty(true); };

  const save = async () => {
    if (form.fitOverride && !String(form.fitOverrideNote).trim()) {
      toast.error("A manual Fit override requires a rationale.");
      return;
    }
    setSaving(true);
    try {
      const body = {
        addressableValue: form.addressableValue === "" ? null : Number(form.addressableValue),
        valueType: form.valueType, pursuitRole: form.pursuitRole,
        vehicleAccess: form.vehicleAccess, incumbent: form.incumbent,
        pwin: Number(form.pwin) || 0,
        capture: {
          ...(opp.capture || {}),
          owner: form.owner, nextAction: form.nextAction,
          nextActionDue: form.nextActionDue || "",
          fitOverride: form.fitOverride ? Number(form.fitOverride) : null,
          fitOverrideNote: form.fitOverrideNote || "",
        },
        decision: { ...(opp.decision || {}), call: form.call, rationale: form.rationale },
      };
      if (body.addressableValue == null) delete body.addressableValue;
      const { data } = await api.put(`/orgs/${orgId}/opportunities/${opp.id}`, body);
      onSaved(data);
      setDirty(false);
      toast.success("Saved");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  const runEnrich = async ({ engine, model, effort }) => {
    const { data } = await api.post(`/orgs/${orgId}/opportunities/${opp.id}/enrich`,
      { engine, model: model || "", effort: effort || "standard" });
    onSaved(data);
    const n = (data._appliedFields || []).length;
    toast.success("AI Qualify complete", {
      description: n ? `Filled ${n} field(s): ${data._appliedFields.join(", ")}` : "No empty fields could be verified — see requirement matches below.",
    });
    return data;
  };

  const toggleWatch = async () => {
    try {
      const { data } = await api.put(`/orgs/${orgId}/opportunities/${opp.id}`, { watch: !opp.watch });
      onSaved(data);
    } catch (e) { toast.error(errMsg(e)); }
  };

  const f = opp.fitComputed || {};
  const fin = opp.financials || {};
  const elig = opp.eligibility || {};
  const pwin = opp.pwinView || {};
  const enr = opp.aiEnrichment;
  const due = dueColor(opp.dueDate);
  const biz = businessDaysUntil(opp.dueDate);
  const inputCls = "field !py-1 text-xs";

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} data-testid="drawer-backdrop" />
      <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col overflow-hidden border-l border-line bg-panel shadow-2xl"
        data-testid="opp-drawer">
        {/* header */}
        <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`pill ${PRIORITY_CFG[opp.priority?.label]?.cls || ""} font-semibold`} title={opp.priority?.note}>
                {opp.priority?.label}
              </span>
              <span className={`pill ${ELIG_STATUS[elig.status]?.cls || ""}`}>{elig.status}</span>
              <span className={`text-xs font-semibold ${FIT_BAND_CLS[f.band] || "text-dim"}`}>Fit {f.effective}{f.override ? "*" : ""}</span>
              <span className={`text-xs ${PWIN_CLS[pwin.band] || "text-faint"}`}>PWin {pwin.band}{pwin.pct != null ? ` ${pwin.pct}%` : ""}</span>
            </div>
            <h2 className="mt-1 line-clamp-2 text-sm font-semibold text-ink">{opp.title}</h2>
            <div className="mono text-[11px] text-faint">{opp.solNumber || "no sol #"} · {opp.agency || "agency unknown"}</div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <button onClick={toggleWatch} className={opp.watch ? "text-warn" : "text-faint hover:text-warn"}
              title="Watchlist" data-testid="drawer-watch"><Star size={16} fill={opp.watch ? "currentColor" : "none"} /></button>
            <button onClick={onClose} className="text-faint hover:text-ink" data-testid="drawer-close"><X size={17} /></button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* actions */}
          <div className="flex flex-wrap items-center gap-2 px-4 py-3">
            {editor && (
              <AIButton orgId={orgId} compact icon={Sparkles} label="AI Qualify" testid="enrich-button"
                note="Extracts scope, classification, requirement matches & gaps. Anthropic verifies on the live web; other engines review saved data. Fills empty fields only."
                onStart={runEnrich} />
            )}
            <button className="btn btn-ghost !px-2.5 !py-1 text-xs"
              onClick={() => navigate(`/opportunities/${opp.id}`)} data-testid="open-workspace">
              Full workspace <ExternalLink size={12} />
            </button>
            {opp.url && (
              <a href={opp.url} target="_blank" rel="noreferrer" className="btn btn-ghost !px-2.5 !py-1 text-xs"
                data-testid="open-source">Official source <ExternalLink size={12} /></a>
            )}
          </div>

          {/* red flags */}
          {(opp.redFlags || []).length > 0 && (
            <div className="mx-4 mb-2 rounded-lg border border-warn/30 bg-warn/5 p-2.5" data-testid="drawer-flags">
              {(opp.redFlags || []).map((r, i) => (
                <div key={i} className={`flex items-start gap-1.5 text-[11px] ${r.severity === "high" ? "text-bad" : r.severity === "medium" ? "text-warn" : "text-faint"}`}>
                  <AlertTriangle size={11} className="mt-0.5 shrink-0" />{r.flag}
                </div>
              ))}
            </div>
          )}

          {/* A. Overview */}
          <Sect title="Overview" testid="drawer-overview">
            <p className="text-xs text-dim">{opp.scopeSummary || <span className="text-faint">Scope unknown — run AI Qualify or edit in the workspace.</span>}</p>
            {(opp.tags || []).length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {(opp.tags || []).map((t) => <span key={t} className="rounded border border-line bg-white/5 px-1.5 py-0.5 text-[10px] text-faint">{t}</span>)}
              </div>
            )}
            <div className="mt-2 space-y-1">
              <KV k="Customer" v={`${opp.agency || "Unknown"}${opp.office ? " · " + opp.office : ""}`} />
              <KV k="Type / Stage" v={`${opp.oppType || opp.vehicle || "Unknown"} · ${opp.acqStage || "Unknown"}${opp.recompete ? " · " + opp.recompete : ""}`} />
              <KV k="Due" v={opp.dueDate ? <span className={due.cls}>{fmtDate(opp.dueDate)}{opp.dueTime ? ` ${opp.dueTime}` : ""} · {due.label}{biz != null ? ` · ${biz} business days` : ""}</span> : undefined} />
              <KV k="NAICS / PSC" v={`${opp.naics || "?"}${opp.naicsTitle ? ` (${opp.naicsTitle})` : ""}${opp.psc ? " / " + opp.psc : ""}`} mono />
              <KV k="Set-aside" v={`${opp.setAside || "None"}${opp.sizeStandard ? " · Std " + opp.sizeStandard : ""}`} />
              <KV k="Contract" v={`${opp.contractType || "Unknown"}${opp.awardsCount ? " · " + opp.awardsCount : ""}${opp.pop ? " · PoP " + opp.pop : ""}`} />
            </div>
          </Sect>

          {/* B. Fit analysis */}
          <Sect title={`Fit Analysis — ${f.effective}/100 (${f.band}) · confidence ${f.confidence}`} testid="drawer-fit">
            {f.noGo && <div className="mb-2 text-[11px] text-bad">{f.noGo}</div>}
            <table className="w-full text-[11px]">
              <tbody>
                {(f.breakdown || []).map((b) => (
                  <tr key={b.category} className="border-b border-line/40">
                    <td className="py-1 pr-2 text-faint">{b.category} <span className="text-[9px]">({b.weight}%)</span></td>
                    <td className={`mono py-1 pr-2 text-right ${b.score >= 70 ? "text-ok" : b.score >= 45 ? "text-warn" : "text-bad"}`}>{b.score}</td>
                    <td className="py-1 text-faint">{b.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {editor && (
              <div className="mt-2 grid grid-cols-2 gap-2">
                <label className="block text-[10px] text-faint">Manual override (0–100)
                  <input type="number" min={0} max={100} className={inputCls} value={form.fitOverride}
                    onChange={set("fitOverride")} placeholder="none" data-testid="fit-override" />
                </label>
                <label className="block text-[10px] text-faint">Override rationale (required)
                  <input className={inputCls} value={form.fitOverrideNote} onChange={set("fitOverrideNote")}
                    placeholder="why the model is wrong" data-testid="fit-override-note" />
                </label>
              </div>
            )}
          </Sect>

          {/* C. Eligibility gates */}
          <Sect title="Eligibility & Compliance Gates" testid="drawer-gates">
            <div className="space-y-1">
              {(elig.gates || []).map((g, i) => (
                <div key={i} className="flex items-start gap-2 text-[11px]">
                  {GATE_ICON[g.status] || <MinusCircle size={13} className="text-faint" />}
                  <span className="text-dim">{g.gate}</span>
                  <span className="text-faint">— {g.note}</span>
                </div>
              ))}
            </div>
            {editor && (
              <label className="mt-2 block text-[10px] text-faint">Contract-vehicle access
                <select className={inputCls} value={form.vehicleAccess} onChange={set("vehicleAccess")} data-testid="vehicle-access">
                  <option value="">Unknown</option>
                  <option value="have">Have access</option>
                  <option value="open">Open market — no vehicle needed</option>
                  <option value="need">Need access (gate fails)</option>
                </select>
              </label>
            )}
          </Sect>

          {/* D. Requirements (AI) */}
          {enr && (
            <Sect title={`AI Requirement Matches (${enr.confidence} confidence · ${fmtDateTime(enr.generatedAt)})`} testid="drawer-requirements">
              {(enr.requirementMatches || []).length === 0
                ? <p className="text-[11px] text-faint">No requirement matches extracted.</p>
                : (
                  <div className="space-y-1.5">
                    {(enr.requirementMatches || []).map((m, i) => (
                      <div key={i} className="rounded border border-line/60 bg-white/5 p-2 text-[11px]">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-dim">{m.requirement}{m.mandatory && <span className="ml-1 text-[9px] text-warn">MANDATORY</span>}</span>
                          <span className={`mono ${m.score >= 70 ? "text-ok" : m.score >= 45 ? "text-warn" : "text-bad"}`}>{m.score}</span>
                        </div>
                        <div className="text-faint">{m.evidence}{m.source ? ` — ${m.source}` : ""}</div>
                      </div>
                    ))}
                  </div>
                )}
              {(enr.gaps || []).length > 0 && (
                <div className="mt-2 text-[11px] text-warn">Gaps: {(enr.gaps || []).join("; ")}</div>
              )}
            </Sect>
          )}

          {/* E. Competition */}
          <Sect title="Competitive Intelligence" testid="drawer-competition">
            <div className="space-y-1">
              <KV k="Incumbent" v={opp.incumbent || undefined} />
              <KV k="Intensity" v={opp.competition?.intensity} />
              <KV k="Likely bidders" v={opp.competition?.likelyBidders} />
              <KV k="Existing award #" v={opp.competition?.awardNumber} mono />
            </div>
            {editor && (
              <input className={`${inputCls} mt-2`} value={form.incumbent} onChange={set("incumbent")}
                placeholder="Incumbent contractor (if known)" data-testid="incumbent-input" />
            )}
          </Sect>

          {/* F. Financials */}
          <Sect title="Financial Analysis" testid="drawer-financials">
            <div className="space-y-1">
              <KV k="Stated value" v={fin.statedValue ? `${fmtMoney(fin.statedValue)} (${fin.valueType || "type unknown"})` : undefined} mono />
              <KV k="Addressable revenue" v={fin.addressableValue != null ? `${fmtMoney(fin.addressableValue)}${fin.addressableInferred ? " (inferred)" : ""}` : undefined} mono />
              <KV k="Weighted pipeline (× PWin)" v={fin.weightedPipeline != null ? fmtMoney(fin.weightedPipeline) : undefined} mono />
            </div>
            {fin.note && <div className="mt-1.5 text-[11px] text-warn">{fin.note}</div>}
            {editor && (
              <div className="mt-2 grid grid-cols-2 gap-2">
                <label className="block text-[10px] text-faint">Addressable value ($)
                  <input type="number" className={`${inputCls} mono`} value={form.addressableValue}
                    onChange={set("addressableValue")} data-testid="addressable-input" />
                </label>
                <label className="block text-[10px] text-faint">Stated value type
                  <select className={inputCls} value={form.valueType} onChange={set("valueType")} data-testid="value-type">
                    <option value="">Unknown</option>
                    {["Ceiling", "Estimated", "Max individual award", "Task order", "Guaranteed minimum", "Program funding", "Historical"].map((v) => <option key={v}>{v}</option>)}
                  </select>
                </label>
              </div>
            )}
          </Sect>

          {/* G. Capture workspace */}
          <Sect title="Capture" testid="drawer-capture">
            <div className="grid grid-cols-2 gap-2">
              <label className="block text-[10px] text-faint">Capture owner
                <input className={inputCls} disabled={!editor} value={form.owner} onChange={set("owner")} data-testid="capture-owner" />
              </label>
              <label className="block text-[10px] text-faint">Bid decision
                <select className={inputCls} disabled={!editor} value={form.call} onChange={set("call")} data-testid="bid-decision">
                  {["TBD", "Bid", "No-Bid", "Rebuild", "Watch"].map((v) => <option key={v}>{v}</option>)}
                </select>
              </label>
              <label className="block text-[10px] text-faint">Next action
                <input className={inputCls} disabled={!editor} value={form.nextAction} onChange={set("nextAction")} data-testid="next-action" />
              </label>
              <label className="block text-[10px] text-faint">Next action due
                <input type="date" className={`${inputCls} mono`} disabled={!editor} value={form.nextActionDue} onChange={set("nextActionDue")} data-testid="next-action-due" />
              </label>
              <label className="col-span-2 block text-[10px] text-faint">PWin — your judgment ({form.pwin}%)
                <input type="range" min={0} max={100} disabled={!editor} value={form.pwin}
                  onChange={set("pwin")} className="mt-1 w-full accent-violet" data-testid="drawer-pwin" />
              </label>
              <label className="col-span-2 block text-[10px] text-faint">Decision rationale
                <textarea className={`${inputCls} min-h-[50px]`} disabled={!editor} value={form.rationale} onChange={set("rationale")} data-testid="decision-rationale-drawer" />
              </label>
            </div>
          </Sect>

          {/* H. Sources */}
          <Sect title="Sources & Freshness" testid="drawer-sources">
            <div className="space-y-1">
              <KV k="Feed source" v={(opp.source || "manual").toUpperCase()} />
              <KV k="Last verified" v={opp.lastVerified ? fmtDateTime(opp.lastVerified) : "Never"} />
              {enr && <KV k="AI qualified" v={`${fmtDateTime(enr.generatedAt)} (${enr.engine}/${enr.model})`} />}
            </div>
            {(enr?.sources || []).length > 0 && (
              <div className="mt-1.5 space-y-0.5">
                {(enr.sources || []).map((s, i) => (
                  <a key={i} href={s} target="_blank" rel="noreferrer" className="block truncate text-[11px] text-cyan hover:underline">{s}</a>
                ))}
              </div>
            )}
            {(opp.amendments || []).length > 0 && (
              <div className="mt-2 space-y-1">
                {(opp.amendments || []).map((a, i) => (
                  <div key={i} className="text-[11px] text-faint">Amendment {a.number || i + 1} — {fmtDate(a.date)}: {a.summary}</div>
                ))}
              </div>
            )}
          </Sect>
        </div>

        {editor && (
          <div className="border-t border-line px-4 py-3">
            <button className="btn btn-primary w-full !py-1.5 text-sm" onClick={save}
              disabled={!dirty || saving} data-testid="drawer-save">
              {saving ? <Spinner /> : <Save size={14} />} {dirty ? "Save qualification" : "Saved"}
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
