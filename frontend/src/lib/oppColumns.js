import React from "react";
import { Star, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Pill } from "../components/ui";
import {
  fmtMoney, fmtDate, dueColor, businessDaysUntil,
  ELIG_STATUS, FIT_BAND_CLS, PRIORITY_CFG, PWIN_CLS, STAGE_COLORS,
} from "./helpers";

/* Column registry for the capture-qualification table.
   Each column: key, label, minW, sortVal(o) for sorting, csv(o) for export,
   render(o, ctx) for the cell. ctx = { toggleWatch } */

const dash = <span className="text-faint">—</span>;
const sub = (t) => <div className="text-[11px] text-faint">{t}</div>;

export const COLUMNS = [
  {
    key: "priority", label: "Priority", minW: "min-w-[70px]",
    sortVal: (o) => ({ A: 0, B: 1, C: 2, Watch: 3, Pass: 4 }[o.priority?.label] ?? 9),
    csv: (o) => o.priority?.label || "",
    render: (o) => (
      <span className={`pill ${PRIORITY_CFG[o.priority?.label]?.cls || ""} !px-2.5 font-semibold`}
        title={o.priority?.note} data-testid={`priority-${o.id}`}>
        {o.priority?.label || "—"}
      </span>
    ),
  },
  {
    key: "fit", label: "Fit", minW: "min-w-[80px]",
    sortVal: (o) => o.fitComputed?.effective ?? -1,
    csv: (o) => `${o.fitComputed?.effective ?? ""} (${o.fitComputed?.band ?? ""})`,
    render: (o) => {
      const f = o.fitComputed;
      if (!f) return dash;
      const top = (f.breakdown || []).slice(0, 3).map((b) => `${b.category}: ${b.score}`).join(" · ");
      return (
        <div title={`${top}${f.override ? " — MANUAL OVERRIDE" : ""} (confidence: ${f.confidence})`}
          data-testid={`fit-${o.id}`}>
          <span className={`mono font-semibold ${FIT_BAND_CLS[f.band] || "text-dim"}`}>{f.effective}</span>
          <div className={`text-[11px] ${FIT_BAND_CLS[f.band] || "text-faint"}`}>
            {f.band}{f.override ? "*" : ""}
          </div>
        </div>
      );
    },
  },
  {
    key: "eligibility", label: "Eligibility", minW: "min-w-[92px]",
    sortVal: (o) => ({ Eligible: 0, Conditional: 1, Unknown: 2, Ineligible: 3 }[o.eligibility?.status] ?? 9),
    csv: (o) => o.eligibility?.status || "",
    render: (o) => (
      <span className={`pill ${ELIG_STATUS[o.eligibility?.status]?.cls || ""}`}
        title={o.eligibility?.reason} data-testid={`elig-${o.id}`}>
        {o.eligibility?.status || "Unknown"}
      </span>
    ),
  },
  {
    key: "pwin", label: "PWin", minW: "min-w-[64px]",
    sortVal: (o) => o.pwinView?.pct ?? -1,
    csv: (o) => o.pwinView?.pct != null ? `${o.pwinView.pct}% (${o.pwinView.band})` : "Unknown",
    render: (o) => {
      const p = o.pwinView || {};
      return (
        <div title={p.basis} data-testid={`pwin-${o.id}`}>
          <span className={`text-xs font-medium ${PWIN_CLS[p.band] || "text-faint"}`}>{p.band || "Unknown"}</span>
          {p.pct != null && <div className="mono text-[11px] text-faint">{p.pct}%</div>}
        </div>
      );
    },
  },
  {
    key: "opportunity", label: "Opportunity", minW: "min-w-[220px]",
    sortVal: (o) => (o.title || "").toLowerCase(),
    csv: (o) => `${o.title} [${o.solNumber || ""}]`,
    render: (o, ctx) => (
      <div className="flex items-start gap-1.5">
        <button onClick={(e) => { e.stopPropagation(); ctx.toggleWatch(o); }}
          className={o.watch ? "text-warn" : "text-faint hover:text-warn"}
          title={o.watch ? "Remove from watchlist" : "Add to watchlist"}
          data-testid={`watch-${o.id}`}>
          <Star size={14} fill={o.watch ? "currentColor" : "none"} />
        </button>
        <div className="min-w-0">
          <div className="line-clamp-2 font-medium text-ink">{o.title}</div>
          <div className="mono text-xs text-faint">{o.solNumber || "—"}</div>
        </div>
      </div>
    ),
  },
  {
    key: "scope", label: "Scope", minW: "min-w-[220px]",
    sortVal: (o) => (o.scopeSummary || "").toLowerCase(),
    csv: (o) => o.scopeSummary || "Unknown",
    render: (o) => (
      <div>
        <div className="line-clamp-2 text-xs text-dim">{o.scopeSummary || <span className="text-faint">Unknown — run AI Qualify</span>}</div>
        {(o.tags || []).length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {(o.tags || []).slice(0, 3).map((t) => (
              <span key={t} className="rounded border border-line bg-white/5 px-1 py-0.5 text-[10px] text-faint">{t}</span>
            ))}
          </div>
        )}
      </div>
    ),
  },
  {
    key: "customer", label: "Customer", minW: "min-w-[130px]",
    sortVal: (o) => (o.agency || "").toLowerCase(),
    csv: (o) => `${o.agency || ""}${o.office ? " / " + o.office : ""}`,
    render: (o) => (
      <div>
        <div className="text-dim">{o.agency || dash}</div>
        {o.office && sub(o.office)}
      </div>
    ),
  },
  {
    key: "typeStage", label: "Type / Stage", minW: "min-w-[110px]",
    sortVal: (o) => (o.acqStage || "").toLowerCase(),
    csv: (o) => `${o.oppType || o.vehicle || ""} · ${o.acqStage || "Unknown"}${o.recompete ? " · " + o.recompete : ""}`,
    render: (o) => (
      <div>
        <Pill tone="violet">{o.oppType || o.vehicle}</Pill>
        {sub(o.acqStage || "Stage unknown")}
        {o.recompete && sub(o.recompete)}
      </div>
    ),
  },
  {
    key: "due", label: "Due", minW: "min-w-[110px]",
    sortVal: (o) => (o.dueDate ? new Date(o.dueDate).getTime() : Infinity),
    csv: (o) => `${o.dueDate || "Unknown"}${o.dueTime ? " " + o.dueTime : ""}`,
    render: (o) => {
      const due = dueColor(o.dueDate);
      const biz = businessDaysUntil(o.dueDate);
      return (
        <div data-testid={`due-${o.id}`}>
          <div className={`mono text-sm ${due.cls}`}>{fmtDate(o.dueDate)}</div>
          {o.dueTime && <div className="mono text-[10px] text-faint">{o.dueTime}</div>}
          <div className={`text-[11px] ${due.cls}`}>
            {due.label}{biz != null && due.key !== "grey" ? ` · ${biz} biz` : ""}
          </div>
        </div>
      );
    },
  },
  {
    key: "award", label: "Award Value", minW: "min-w-[100px]", right: true,
    sortVal: (o) => Number(o.ceiling) || 0,
    csv: (o) => `${o.ceiling || ""} (${o.financials?.valueType || ""})`,
    render: (o) => {
      const f = o.financials || {};
      return (
        <div className="text-right" data-testid={`award-${o.id}`}>
          <span className="mono text-ink">{f.statedValue ? fmtMoney(f.statedValue) : <span className="text-faint">Unknown</span>}</span>
          {f.valueType && sub(`${f.valueType}${f.valueConfidence === "inferred" ? " (inferred)" : ""}`)}
        </div>
      );
    },
  },
  {
    key: "addressable", label: "Addressable", minW: "min-w-[100px]", right: true,
    sortVal: (o) => o.financials?.addressableValue ?? -1,
    csv: (o) => o.financials?.addressableValue ?? "Unknown",
    render: (o) => {
      const f = o.financials || {};
      if (f.addressableValue == null) {
        return (
          <div className="text-right text-[11px] text-warn" title={f.note}>
            {f.sharedCeiling ? "Set value" : "Unknown"}
          </div>
        );
      }
      return (
        <div className="text-right" title={f.note}>
          <span className="mono text-ink">{fmtMoney(f.addressableValue)}</span>
          {f.weightedPipeline != null && sub(`wtd ${fmtMoney(f.weightedPipeline)}`)}
          {f.addressableInferred && sub("inferred")}
        </div>
      );
    },
  },
  {
    key: "setAside", label: "Set-Aside", minW: "min-w-[110px]",
    sortVal: (o) => (o.setAside || "").toLowerCase(),
    csv: (o) => `${o.setAside || ""}${o.sizeStandard ? " · " + o.sizeStandard : ""}`,
    render: (o) => (
      <div>
        <span className="text-xs text-dim">{o.setAside || "None"}</span>
        {o.sizeStandard && sub(`Std: ${o.sizeStandard}`)}
      </div>
    ),
  },
  {
    key: "naicsPsc", label: "NAICS / PSC", minW: "min-w-[90px]",
    sortVal: (o) => o.naics || "",
    csv: (o) => `${o.naics || ""}${o.psc ? " / " + o.psc : ""}`,
    render: (o) => (
      <div className="mono text-xs text-dim">
        {o.naics || dash}
        {o.naicsTitle && sub(o.naicsTitle)}
        {o.psc && sub(`PSC ${o.psc}`)}
      </div>
    ),
  },
  {
    key: "vehicleRole", label: "Vehicle / Role", minW: "min-w-[100px]",
    sortVal: (o) => (o.vehicle || "").toLowerCase(),
    csv: (o) => `${o.vehicle || ""} · access:${o.vehicleAccess || "unknown"} · ${o.pursuitRole || ""}`,
    render: (o) => (
      <div>
        <span className="text-xs text-dim">{o.vehicle}</span>
        {sub(`Access: ${o.vehicleAccess || "unknown"}`)}
        {o.pursuitRole && sub(o.pursuitRole)}
      </div>
    ),
  },
  {
    key: "contract", label: "Contract", minW: "min-w-[90px]",
    sortVal: (o) => (o.contractType || "").toLowerCase(),
    csv: (o) => `${o.contractType || "Unknown"} · ${o.awardsCount || ""}`,
    render: (o) => (
      <div className="text-xs text-dim">
        {o.contractType || <span className="text-faint">Unknown</span>}
        {o.awardsCount && sub(o.awardsCount)}
        {o.pop && sub(`PoP: ${o.pop}`)}
      </div>
    ),
  },
  {
    key: "competition", label: "Competition", minW: "min-w-[110px]",
    sortVal: (o) => (o.incumbent || "").toLowerCase(),
    csv: (o) => `${o.incumbent || ""} · ${o.competition?.intensity || "Unknown"}`,
    render: (o) => (
      <div className="text-xs text-dim">
        {o.incumbent ? <span title="Incumbent">{o.incumbent}</span> : <span className="text-faint">No incumbent data</span>}
        {o.competition?.intensity && sub(`Intensity: ${o.competition.intensity}`)}
      </div>
    ),
  },
  {
    key: "redFlag", label: "Red Flag", minW: "min-w-[150px]",
    sortVal: (o) => -(o.redFlags || []).filter((f) => f.severity === "high").length,
    csv: (o) => (o.redFlags || [])[0]?.flag || "",
    render: (o) => {
      const top = (o.redFlags || [])[0];
      if (!top) return <CheckCircle2 size={14} className="text-ok" />;
      const cls = top.severity === "high" ? "text-bad" : top.severity === "medium" ? "text-warn" : "text-faint";
      return (
        <div className={`flex items-start gap-1 text-[11px] ${cls}`}
          title={(o.redFlags || []).map((f) => f.flag).join("\n")} data-testid={`flag-${o.id}`}>
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          <span className="line-clamp-2">{top.flag}{o.redFlags.length > 1 ? ` (+${o.redFlags.length - 1})` : ""}</span>
        </div>
      );
    },
  },
  {
    key: "capture", label: "Capture", minW: "min-w-[130px]",
    sortVal: (o) => (o.capture?.owner || "").toLowerCase(),
    csv: (o) => `${o.stage} · ${o.capture?.owner || ""} · ${o.capture?.nextAction || ""} · ${o.decision?.call || ""}`,
    render: (o) => (
      <div data-testid={`capture-${o.id}`}>
        <span className="pill border-line text-[11px]"
          style={{ color: STAGE_COLORS[o.stage], borderColor: (STAGE_COLORS[o.stage] || "#888") + "66" }}>
          {o.stage}
        </span>
        {o.capture?.owner && sub(`Owner: ${o.capture.owner}`)}
        {o.capture?.nextAction && sub(`Next: ${o.capture.nextAction}${o.capture.nextActionDue ? ` (${fmtDate(o.capture.nextActionDue)})` : ""}`)}
        {o.decision?.call && o.decision.call !== "TBD" && sub(`Call: ${o.decision.call}`)}
      </div>
    ),
  },
  {
    key: "source", label: "Source", minW: "min-w-[100px]",
    sortVal: (o) => (o.lastVerified ? new Date(o.lastVerified).getTime() : 0),
    csv: (o) => `${o.source || ""} · verified ${o.lastVerified || "never"}`,
    render: (o) => (
      <div className="text-[11px] text-faint">
        <span className="uppercase">{o.source || "manual"}</span>
        {o.lastVerified
          ? <div className="inline-flex items-center gap-1 text-ok"><CheckCircle2 size={11} />{fmtDate(o.lastVerified)}</div>
          : <div>Never verified</div>}
        {o.aiEnrichment && <div>AI: {o.aiEnrichment.confidence} conf</div>}
      </div>
    ),
  },
];

export const DEFAULT_VISIBLE = [
  "priority", "fit", "eligibility", "pwin", "opportunity", "scope", "customer",
  "due", "award", "addressable", "setAside", "redFlag", "capture", "source",
];

export const COMPACT_VISIBLE = [
  "priority", "fit", "eligibility", "opportunity", "customer", "due", "award", "redFlag",
];
