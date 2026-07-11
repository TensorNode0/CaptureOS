import React, { useMemo, useState } from "react";
import { Search, ExternalLink, Rocket } from "lucide-react";
import { Card, SectionLabel, Pill, PageReveal, EmptyState } from "../../components/ui";
import { ACCELERATORS } from "../../lib/ventureData";

export default function Accelerators() {
  const [q, setQ] = useState("");
  const [fTerms, setFTerms] = useState("");
  const [fLocation, setFLocation] = useState("");

  const rows = useMemo(() => ACCELERATORS.filter((r) => {
    const hay = `${r.name} ${r.focus} ${r.location} ${r.tips}`.toLowerCase();
    if (q && !hay.includes(q.toLowerCase())) return false;
    if (fTerms === "equity-free" && /equity/i.test(r.terms || "") && !/no equity|equity-free|non-dilutive/i.test(r.terms || "")) return false;
    if (fTerms === "equity" && !/equity/i.test(r.terms || "")) return false;
    if (fLocation && !`${r.location}`.toLowerCase().includes(fLocation.toLowerCase())) return false;
    return true;
  }), [q, fTerms, fLocation]);

  return (
    <PageReveal className="space-y-5">
      <div>
        <SectionLabel>Accelerators</SectionLabel>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Aerospace & defense accelerators</h1>
        <p className="mt-1 max-w-3xl text-xs text-faint">
          Cohorts, challenges, and government innovation programs that move defense
          startups fastest — with terms and application tips. Verify current terms on
          each program's site, then draft your application in Accelerator Applications.
        </p>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
            <input className="field !pl-9" placeholder="Search program, focus, location…" value={q}
              onChange={(e) => setQ(e.target.value)} data-testid="accelerator-search" />
          </div>
          <select className="field !w-auto" value={fTerms} onChange={(e) => setFTerms(e.target.value)} data-testid="accel-terms">
            <option value="">All terms</option>
            <option value="equity-free">Equity-free / non-dilutive</option>
            <option value="equity">Takes equity</option>
          </select>
          <input className="field !w-40" placeholder="Location…" value={fLocation}
            onChange={(e) => setFLocation(e.target.value)} data-testid="accel-location" />
          <Pill tone="neutral">{rows.length} programs</Pill>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {rows.length === 0 ? (
          <EmptyState icon={Rocket} title="No programs match" subtitle="Try clearing the search." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="accelerators-table">
              <thead className="bg-elev/90 text-xs text-dim">
                <tr className="border-b border-line">
                  <th className="px-3 py-2.5 text-left font-medium">Program</th>
                  <th className="px-3 py-2.5 text-left font-medium">Focus</th>
                  <th className="px-3 py-2.5 text-left font-medium">Location</th>
                  <th className="px-3 py-2.5 text-left font-medium">Terms</th>
                  <th className="px-3 py-2.5 text-left font-medium">Cohort</th>
                  <th className="px-3 py-2.5 text-left font-medium">Tips</th>
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
                    </td>
                    <td className="px-3 py-3 text-xs text-dim">{r.focus}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.location}</td>
                    <td className="px-3 py-3"><Pill tone="violet">{r.terms}</Pill></td>
                    <td className="px-3 py-3 text-xs text-dim">{r.cohort}</td>
                    <td className="px-3 py-3 max-w-[280px] text-xs leading-snug text-faint">{r.tips}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageReveal>
  );
}
