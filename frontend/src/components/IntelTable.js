import React, { useMemo, useState } from "react";
import { Search, ArrowUpDown, ExternalLink, Plus, FileText } from "lucide-react";
import { Card, Pill, EmptyState } from "./ui";
import { fmtMoney, fmtDate, daysUntil, dueColor } from "../lib/helpers";
import { fitBadge, moneyColor, complianceTone, TEAMING_TONE, countBy } from "../lib/intel";

const SORTS = {
  fitScore: (a, b) => (Number(b.fitScore) || 0) - (Number(a.fitScore) || 0),
  awardAmount: (a, b) => (Number(b.awardAmount) || 0) - (Number(a.awardAmount) || 0),
  dueDate: (a, b) => (daysUntil(a.dueDate) ?? 1e9) - (daysUntil(b.dueDate) ?? 1e9),
  agency: (a, b) => (a.agency || "").localeCompare(b.agency || ""),
};

function FlagList({ items, toneFn }) {
  const arr = Array.isArray(items) ? items : (items ? [items] : []);
  if (!arr.length) return <span className="text-faint">TBD</span>;
  return (
    <div className="flex max-w-[200px] flex-wrap gap-1">
      {arr.map((f, i) => <Pill key={i} tone={toneFn ? toneFn(f) : "neutral"} className="!text-[10px]">{f}</Pill>)}
    </div>
  );
}

export default function IntelTable({ opps, canEdit, onAdd, addingIdx }) {
  const indexed = useMemo(() => (opps || []).map((o, i) => ({ ...o, _idx: i })), [opps]);
  const [q, setQ] = useState("");
  const [mission, setMission] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [sort, setSort] = useState("fitScore");

  const missions = useMemo(() => countBy(indexed, "missionCategory").map((d) => d.name), [indexed]);
  const vehicles = useMemo(() => countBy(indexed, "vehicle").map((d) => d.name), [indexed]);

  const rows = useMemo(() => {
    let r = indexed;
    const term = q.trim().toLowerCase();
    if (term) r = r.filter((o) =>
      [o.title, o.agency, o.solNumber, o.office, o.summary].join(" ").toLowerCase().includes(term));
    if (mission) r = r.filter((o) => o.missionCategory === mission);
    if (vehicle) r = r.filter((o) => o.vehicle === vehicle);
    return [...r].sort(SORTS[sort]);
  }, [indexed, q, mission, vehicle, sort]);

  const SortBtn = ({ k, label }) => (
    <button onClick={() => setSort(k)} className={`inline-flex items-center gap-1 ${sort === k ? "text-cyan" : "hover:text-ink"}`}>
      {label} <ArrowUpDown size={11} />
    </button>
  );

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-line p-4 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, agency, sol #…"
            className="field !pl-9" data-testid="intel-search" />
        </div>
        <select className="field md:w-52" value={mission} onChange={(e) => setMission(e.target.value)} data-testid="intel-filter-mission">
          <option value="">All mission categories</option>
          {missions.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <select className="field md:w-44" value={vehicle} onChange={(e) => setVehicle(e.target.value)} data-testid="intel-filter-vehicle">
          <option value="">All vehicles</option>
          {vehicles.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>

      {rows.length === 0 ? (
        <EmptyState icon={FileText} title="No opportunities match" subtitle="Adjust your search or filters." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1500px] text-sm" data-testid="intel-table">
            <thead>
              <tr className="border-b border-line text-left label-mono">
                <th className="px-3 py-3">#</th>
                <th className="px-3 py-3"><SortBtn k="fitScore" label="Fit" /></th>
                <th className="px-3 py-3"><SortBtn k="agency" label="Agency / Office" /></th>
                <th className="px-3 py-3"><SortBtn k="dueDate" label="Due" /></th>
                <th className="px-3 py-3"><SortBtn k="awardAmount" label="Award" /></th>
                <th className="px-3 py-3">Opportunity</th>
                <th className="px-3 py-3">Phase</th>
                <th className="px-3 py-3">$ Money</th>
                <th className="px-3 py-3">Vehicle / Type</th>
                <th className="px-3 py-3">Compliance</th>
                <th className="px-3 py-3">CTA</th>
                <th className="px-3 py-3">Tech</th>
                <th className="px-3 py-3">Mission</th>
                <th className="px-3 py-3">Set-Aside</th>
                <th className="px-3 py-3">Teaming</th>
                {canEdit && <th className="px-3 py-3">Action</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => {
                const fit = fitBadge(o.fitScore, o.fitGrade);
                const dc = dueColor(o.dueDate);
                const border = dc.key === "red" ? "#ef4444" : dc.key === "amber" ? "#f59e0b" : dc.key === "green" ? "#10b981" : "transparent";
                return (
                  <tr key={o._idx} className="border-b border-line/60 align-top hover:bg-white/[0.02]" style={{ borderLeft: `3px solid ${border}` }} data-testid={`intel-row-${o._idx}`}>
                    <td className="px-3 py-3 text-faint">{o._idx + 1}</td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2"><span className="mono text-base text-ink">{fit.score}</span></div>
                      <Pill tone={fit.tone} className="mt-1 !text-[10px]">{fit.label}</Pill>
                      {o.fitRationale && <div className="mt-1 max-w-[160px] text-[11px] leading-snug text-faint">{o.fitRationale}</div>}
                    </td>
                    <td className="px-3 py-3"><div className="max-w-[150px] text-ink">{o.agency || "TBD"}</div><div className="text-xs text-faint">{o.office}</div></td>
                    <td className="px-3 py-3"><div className="text-ink">{fmtDate(o.dueDate)}</div><div className={`text-xs ${dc.cls}`}>{dc.label}</div></td>
                    <td className="px-3 py-3 mono text-violet">{o.awardAmount ? fmtMoney(o.awardAmount) : "TBD"}</td>
                    <td className="px-3 py-3">
                      <div className="max-w-[260px] font-medium text-ink">{o.title}</div>
                      {o.solNumber && o.solNumber !== "TBD" && <div className="mono text-xs text-faint">{o.solNumber}</div>}
                      {o.summary && <div className="mt-1 max-w-[260px] text-xs leading-snug text-dim line-clamp-3">{o.summary}</div>}
                      <div className="mt-1 flex gap-2">
                        {o.solUrl && o.solUrl !== "TBD" && <a href={o.solUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-cyan hover:underline">Sol <ExternalLink size={11} /></a>}
                        {o.topicUrl && o.topicUrl !== "TBD" && o.topicUrl !== o.solUrl && <a href={o.topicUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-cyan hover:underline">Topic <ExternalLink size={11} /></a>}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-dim">{o.phase || "TBD"}</td>
                    <td className="px-3 py-3"><span className="inline-flex items-center gap-1.5 text-xs text-dim"><i className="h-2.5 w-2.5 rounded-full" style={{ background: moneyColor(o.colorOfMoney) }} />{o.colorOfMoney || "TBD"}</span></td>
                    <td className="px-3 py-3"><div className="text-ink">{o.vehicle || "TBD"}</div><div className="text-xs text-faint">{o.contractType}</div></td>
                    <td className="px-3 py-3"><FlagList items={o.compliance} toneFn={complianceTone} /></td>
                    <td className="px-3 py-3"><FlagList items={o.cta} /></td>
                    <td className="px-3 py-3 text-dim">{o.techType || "TBD"}</td>
                    <td className="px-3 py-3"><div className="max-w-[150px] text-dim">{o.missionCategory || "TBD"}</div>{o.missionSecondary && o.missionSecondary !== "TBD" && <div className="text-xs text-faint">{o.missionSecondary}</div>}</td>
                    <td className="px-3 py-3 text-dim">{o.setAside || "TBD"}</td>
                    <td className="px-3 py-3"><Pill tone={TEAMING_TONE[o.teaming] || "neutral"} className="!text-[10px]">{o.teaming || "TBD"}</Pill></td>
                    {canEdit && (
                      <td className="px-3 py-3">
                        <button onClick={() => onAdd(o._idx)} disabled={addingIdx === o._idx} className="btn btn-ghost !px-2 !py-1.5 text-xs" data-testid={`intel-add-${o._idx}`} title="Add to pipeline">
                          <Plus size={13} /> Pipeline
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="border-t border-line px-4 py-2 text-xs text-faint">{rows.length} of {indexed.length} opportunities</div>
    </Card>
  );
}
