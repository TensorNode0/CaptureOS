import React, { useMemo, useState } from "react";
import { Search, ExternalLink, Landmark } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { Card, SectionLabel, Pill, PageReveal, EmptyState, Modal } from "../../components/ui";
import ScanPanel from "../../components/ScanPanel";
import { INVESTORS, VENTURE_SOURCES, RESEARCH_TOOLS } from "../../lib/ventureData";
import { canEdit } from "../../lib/helpers";

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
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("");
  const [sector, setSector] = useState("");
  const [checkMin, setCheckMin] = useState(0);
  const [selected, setSelected] = useState(null);

  const rows = useMemo(() => INVESTORS.filter((r) => {
    const hay = `${r.name} ${r.sectors} ${r.techAreas} ${r.notes} ${r.portfolio}`.toLowerCase();
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
          ))}. Click a row for the investor profile; check sizes and stages drift —
          verify on the fund's site before outreach, then draft the email in Investment Deals.
        </p>
      </div>

      <ScanPanel orgId={activeOrgId} kind="investor_scan" editor={editor}
        label="AI deep scan: investors tailored to your company"
        blurb="Searches the live web for active investors matched to your stage, sector,
               and traction — with warm-path ideas and sources. Runs on Claude with web search."
        testid="investor-scan" />

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
            <input className="field !pl-9" placeholder="Search name, sector, portfolio…" value={q}
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
                  <th className="px-3 py-2.5 text-left font-medium">Portfolio highlights</th>
                  <th className="px-3 py-2.5 text-left font-medium">Check type</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} onClick={() => setSelected(r)} data-testid={`investor-row-${r.name}`}
                      className="cursor-pointer border-b border-line/60 align-top hover:bg-white/5">
                    <td className="px-3 py-3">
                      <span className="font-medium text-ink">{r.name}</span>
                      {r.url && (
                        <a href={r.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}
                           className="ml-1.5 inline-flex text-faint hover:text-cyan" aria-label="Investor site">
                          <ExternalLink size={11} />
                        </a>
                      )}
                    </td>
                    <td className="px-3 py-3 mono text-xs text-ink">{r.checkSize}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.stage}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.sectors}</td>
                    <td className="px-3 py-3 max-w-[240px] text-xs leading-snug text-dim">
                      {r.portfolio || <span className="text-faint">—</span>}
                    </td>
                    <td className="px-3 py-3"><Pill tone="violet">{r.checkType}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Investor drawer */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.name || ""} maxW="max-w-2xl">
        {selected && (
          <div className="space-y-3 text-sm" data-testid="investor-drawer">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
              {[["Check size", selected.checkSize], ["Stage", selected.stage],
                ["Sectors", selected.sectors], ["Tech areas", selected.techAreas],
                ["Check type", selected.checkType]]
                .filter(([, v]) => v)
                .map(([label, v]) => (
                  <div key={label}>
                    <div className="text-[10px] uppercase tracking-widest text-faint">{label}</div>
                    <div className="mt-0.5 text-dim">{v}</div>
                  </div>
                ))}
            </div>
            {selected.portfolio && (
              <div>
                <div className="text-[10px] uppercase tracking-widest text-faint">Portfolio / notable bets</div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {selected.portfolio.split(",").map((c) => (
                    <Pill key={c.trim()} tone="cyan">{c.trim()}</Pill>
                  ))}
                </div>
              </div>
            )}
            {selected.traction && (
              <div className="rounded-lg border border-line bg-white/5 p-3 text-xs leading-relaxed text-dim">
                <span className="font-medium text-ink">Traction they look for: </span>{selected.traction}
              </div>
            )}
            {selected.notes && (
              <p className="text-xs leading-relaxed text-dim">{selected.notes}</p>
            )}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {selected.url && (
                <a href={selected.url} target="_blank" rel="noreferrer" className="btn btn-ghost">
                  Investor site <ExternalLink size={12} />
                </a>
              )}
            </div>
            <p className="text-[11px] text-faint">
              Compiled from public sources; portfolio names are notable public examples,
              not the full book. Verify thesis and check size on the fund's site, then
              draft the outreach email in Investment Deals.
            </p>
          </div>
        )}
      </Modal>

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
