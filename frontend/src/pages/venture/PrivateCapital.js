import React, { useMemo, useState } from "react";
import { Search, ExternalLink, Landmark } from "lucide-react";
import { Card, SectionLabel, Pill, PageReveal, EmptyState } from "../../components/ui";
import { INVESTORS, VENTURE_SOURCES, RESEARCH_TOOLS } from "../../lib/ventureData";

const STAGES = ["Pre-seed", "Seed", "Series A", "Series B", "Growth", "Angel"];
const SECTORS = ["Defense", "Space", "Deep tech", "Dual-use", "Aerospace"];

/* Largest $ figure mentioned in a check-size string, e.g. "$250K–$2M" → 2e6 */
function maxCheckOf(s) {
  let max = 0;
  const re = /\$\s*([\d.]+)\s*([KMB])?/gi;
  let m;
  while ((m = re.exec(s || ""))) {
    const mult = { K: 1e3, M: 1e6, B: 1e9 }[(m[2] || "").toUpperCase()] || 1;
    max = Math.max(max, parseFloat(m[1]) * mult);
  }
  return max;
}

export default function PrivateCapital() {
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("");
  const [sector, setSector] = useState("");
  const [checkMin, setCheckMin] = useState(0);

  const rows = useMemo(() => INVESTORS.filter((r) => {
    const hay = `${r.name} ${r.sectors} ${r.techAreas} ${r.notes}`.toLowerCase();
    if (q && !hay.includes(q.toLowerCase())) return false;
    if (stage && !`${r.stage}`.toLowerCase().includes(stage.toLowerCase())) return false;
    if (sector && !`${r.sectors}`.toLowerCase().includes(sector.toLowerCase())) return false;
    if (checkMin && maxCheckOf(r.checkSize) < checkMin) return false;
    return true;
  }), [q, stage, sector, checkMin]);

  return (
    <PageReveal className="space-y-5">
      <div>
        <SectionLabel>Private Capital</SectionLabel>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Defense & space investors</h1>
        <p className="mt-1 max-w-3xl text-xs text-faint">
          A curated map of the funds, strategics, and government capital writing
          checks into defense and space. Compiled from public sources
          {VENTURE_SOURCES.map((s, i) => (
            <span key={s.href}>{i === 0 ? " — see " : " and "}
              <a href={s.href} target="_blank" rel="noreferrer" className="text-cyan hover:underline">{s.label}</a>
            </span>
          ))}. Check sizes and stages drift — verify on the fund's site before outreach,
          then draft the email in Investment Deals.
        </p>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
            <input className="field !pl-9" placeholder="Search name, sector, tech area…" value={q}
              onChange={(e) => setQ(e.target.value)} data-testid="investor-search" />
          </div>
          <select className="field !w-auto" value={stage} onChange={(e) => setStage(e.target.value)} data-testid="investor-stage">
            <option value="">All stages</option>
            {STAGES.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select className="field !w-auto" value={sector} onChange={(e) => setSector(e.target.value)} data-testid="investor-sector">
            <option value="">All sectors</option>
            {SECTORS.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select className="field !w-auto" value={checkMin} onChange={(e) => setCheckMin(Number(e.target.value))} data-testid="investor-check">
            <option value={0}>Any check size</option>
            <option value={500000}>Writes ≥ $500K</option>
            <option value={2000000}>Writes ≥ $2M</option>
            <option value={10000000}>Writes ≥ $10M</option>
          </select>
          <Pill tone="neutral">{rows.length} investors</Pill>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {rows.length === 0 ? (
          <EmptyState icon={Landmark} title="No investors match" subtitle="Try clearing filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="investors-table">
              <thead className="bg-elev/90 text-xs text-dim">
                <tr className="border-b border-line">
                  <th className="px-3 py-2.5 text-left font-medium">Investor</th>
                  <th className="px-3 py-2.5 text-left font-medium">Check size</th>
                  <th className="px-3 py-2.5 text-left font-medium">Stage</th>
                  <th className="px-3 py-2.5 text-left font-medium">Sectors</th>
                  <th className="px-3 py-2.5 text-left font-medium">Tech areas</th>
                  <th className="px-3 py-2.5 text-left font-medium">Check type</th>
                  <th className="px-3 py-2.5 text-left font-medium">Traction they look for</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} className="border-b border-line/60 align-top hover:bg-white/5">
                    <td className="px-3 py-3">
                      <a href={r.url} target="_blank" rel="noreferrer"
                         className="inline-flex items-center gap-1 font-medium text-ink hover:text-cyan">
                        {r.name} <ExternalLink size={11} className="text-faint" />
                      </a>
                      {r.notes && <div className="mt-0.5 max-w-[260px] text-[11px] leading-snug text-faint">{r.notes}</div>}
                    </td>
                    <td className="px-3 py-3 mono text-xs text-ink">{r.checkSize}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.stage}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.sectors}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.techAreas}</td>
                    <td className="px-3 py-3"><Pill tone="violet">{r.checkType}</Pill></td>
                    <td className="px-3 py-3 max-w-[240px] text-xs leading-snug text-dim">{r.traction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="p-4">
        <div className="text-xs font-medium text-dim">Go deeper (paid research tools)</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {RESEARCH_TOOLS.map((t) => (
            <a key={t.label} href={t.href} target="_blank" rel="noreferrer" title={t.note}
               className="rounded-full border border-line bg-white/5 px-3 py-1 text-xs text-dim hover:border-cyan/40 hover:text-cyan">
              {t.label} <ExternalLink size={10} className="inline" />
            </a>
          ))}
        </div>
      </Card>
    </PageReveal>
  );
}
