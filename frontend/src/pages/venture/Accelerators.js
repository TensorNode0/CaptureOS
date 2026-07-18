import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ExternalLink, Rocket, Plus, FileText, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { Card, SectionLabel, Pill, PageReveal, EmptyState, Modal, Field, Spinner } from "../../components/ui";
import ScanPanel from "../../components/ScanPanel";
import { ACCELERATORS } from "../../lib/ventureData";
import { canEdit } from "../../lib/helpers";

const dur = (w) => (w ? (w >= 20 ? `${Math.round(w / 4.3)} months` : `${w} weeks`) : "Varies");

/* Convert an AI-discovered accelerator record into the shape the table
   expects — filling in fields the curated ACCELERATORS list uses. */
const discoveredToRow = (d) => ({
  name: d.name,
  discovered: true,
  url: d.url || d.source || "",
  focus: d.fitReason || "",
  location: "",
  tips: d.fitReason || "",
  phase: d.stage || "",
  terms: d.terms || "",
  attendance: d.attendance || "",
  durationWeeks: null,
  dueDate: d.dueDate || "",
  verified: d.verified !== false,
  sourceDocId: d.sourceDocId,
  discoveredAt: d.discoveredAt,
  _did: d.id,
});

export default function Accelerators() {
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [fTerms, setFTerms] = useState("");
  const [fLocation, setFLocation] = useState("");
  const [fAttend, setFAttend] = useState("");
  const [fPhase, setFPhase] = useState("");
  const [fDurMax, setFDurMax] = useState(0);
  const [custom, setCustom] = useState([]);          // user-added programs (this session)
  const [discovered, setDiscovered] = useState([]);  // AI-discovered programs (persistent)
  const [selected, setSelected] = useState(null);    // drawer row
  const [showAdd, setShowAdd] = useState(false);
  const [starting, setStarting] = useState(false);

  const loadDiscovered = async () => {
    if (!activeOrgId) return;
    try {
      const { data } = await api.get(`/orgs/${activeOrgId}/venture/discovered/accelerator`);
      setDiscovered(data);
    } catch { setDiscovered([]); }
  };
  useEffect(() => { loadDiscovered(); }, [activeOrgId]);   // eslint-disable-line react-hooks/exhaustive-deps

  /* Merge order: user-added first, then AI discoveries (freshest first), then curated. */
  const all = useMemo(() => {
    const dRows = discovered.map(discoveredToRow);
    // Dedupe against curated by lowercased name so AI picks that duplicate the
    // seed list are hidden (curated wins — it has fuller fields).
    const curatedNames = new Set(ACCELERATORS.map((a) => (a.name || "").toLowerCase().trim()));
    const dRowsUnique = dRows.filter((r) => !curatedNames.has((r.name || "").toLowerCase().trim()));
    return [...custom, ...dRowsUnique, ...ACCELERATORS];
  }, [custom, discovered]);

  const rows = useMemo(() => all.filter((r) => {
    const hay = `${r.name} ${r.focus} ${r.location} ${r.tips} ${r.phase}`.toLowerCase();
    if (q && !hay.includes(q.toLowerCase())) return false;
    if (fTerms === "equity-free" && /equity/i.test(r.terms || "") && !/no equity|equity-free|non-dilutive/i.test(r.terms || "")) return false;
    if (fTerms === "equity" && !/equity/i.test(r.terms || "")) return false;
    if (fLocation && !`${r.location}`.toLowerCase().includes(fLocation.toLowerCase())) return false;
    if (fAttend && !`${r.attendance}`.toLowerCase().includes(fAttend.toLowerCase())) return false;
    if (fPhase && !`${r.phase}`.toLowerCase().includes(fPhase.toLowerCase())) return false;
    if (fDurMax && (!r.durationWeeks || r.durationWeeks > fDurMax)) return false;
    return true;
  }), [all, q, fTerms, fLocation, fAttend, fPhase, fDurMax]);

  /* Generate the application form from the program's own page. */
  const startApplication = async (program) => {
    setStarting(true);
    try {
      await api.post(`/orgs/${activeOrgId}/venture-docs/from-program`,
        { name: program.name, url: program.url || "" });
      toast.success("Application form created from the program page");
      setSelected(null);
      navigate("/accelerator-applications");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setStarting(false); }
  };

  return (
    <PageReveal className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <SectionLabel>Accelerators</SectionLabel>
          <h1 className="mt-1 text-2xl font-semibold text-ink">Aerospace & defense accelerators</h1>
          <p className="mt-1 max-w-3xl text-xs text-faint">
            Cohorts, challenges, and government innovation programs that move defense
            startups fastest. Click a row for details and to start an application —
            the form is generated from the program's own page. Logistics drift every cohort;
            verify on the program site.
          </p>
        </div>
        {editor && (
          <button className="btn btn-ghost" onClick={() => setShowAdd(true)} data-testid="accel-add-program">
            <Plus size={15} /> Add your own program
          </button>
        )}
      </div>

      <ScanPanel orgId={activeOrgId} kind="accelerator_scan" editor={editor}
        label="AI deep scan: programs that fit your company"
        blurb="Searches the live web for currently open and upcoming cohorts matched to
               your profile — with due dates, terms, and sources. Runs on Claude with web search.
               Newly discovered programs are added to the table below with an AI tag."
        testid="accel-scan" onDone={loadDiscovered} />

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
          <input className="field !w-36" placeholder="Location…" value={fLocation}
            onChange={(e) => setFLocation(e.target.value)} data-testid="accel-location" />
          <select className="field !w-auto" value={fAttend} onChange={(e) => setFAttend(e.target.value)} data-testid="accel-attend">
            <option value="">Any attendance</option>
            <option value="virtual">Virtual</option>
            <option value="onsite">Onsite</option>
            <option value="hybrid">Hybrid</option>
          </select>
          <select className="field !w-auto" value={fPhase} onChange={(e) => setFPhase(e.target.value)} data-testid="accel-phase">
            <option value="">Any phase</option>
            <option value="idea">Idea</option>
            <option value="pre-seed">Pre-seed</option>
            <option value="seed">Seed</option>
            <option value="series a">Series A+</option>
          </select>
          <select className="field !w-auto" value={fDurMax} onChange={(e) => setFDurMax(Number(e.target.value))} data-testid="accel-duration">
            <option value={0}>Any duration</option>
            <option value={8}>≤ 8 weeks</option>
            <option value={13}>≤ 13 weeks</option>
            <option value={26}>≤ 6 months</option>
          </select>
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
                  <th className="px-3 py-2.5 text-left font-medium">Due</th>
                  <th className="px-3 py-2.5 text-left font-medium">Duration</th>
                  <th className="px-3 py-2.5 text-left font-medium">Attendance</th>
                  <th className="px-3 py-2.5 text-left font-medium">Phase</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} onClick={() => setSelected(r)} data-testid={`accel-row-${r.name}`}
                      className="cursor-pointer border-b border-line/60 align-top hover:bg-white/5">
                    <td className="px-3 py-3">
                      <span className="font-medium text-ink">{r.name}</span>
                      {r.discovered && (
                        <Pill tone="cyan" className="ml-1.5 !py-0 !text-[9px]" title="Discovered by AI scan">
                          <Sparkles size={9} className="mr-0.5" />AI
                        </Pill>
                      )}
                      {r.url && (
                        <a href={r.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}
                           className="ml-1.5 inline-flex text-faint hover:text-cyan" aria-label="Program site">
                          <ExternalLink size={11} />
                        </a>
                      )}
                    </td>
                    <td className="px-3 py-3 text-xs text-dim">{r.focus}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.location}</td>
                    <td className="px-3 py-3"><Pill tone="violet">{r.terms}</Pill></td>
                    <td className="px-3 py-3 text-xs text-dim">{r.dueDate}</td>
                    <td className="px-3 py-3 text-xs text-dim">{dur(r.durationWeeks)}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.attendance}</td>
                    <td className="px-3 py-3 text-xs text-dim">{r.phase}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Program drawer */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.name || ""} maxW="max-w-2xl">
        {selected && (
          <div className="space-y-3 text-sm" data-testid="accel-drawer">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
              {[["Focus", selected.focus], ["Location", selected.location],
                ["Terms", selected.terms], ["Cohort", selected.cohort],
                ["Applications due", selected.dueDate], ["Duration", dur(selected.durationWeeks)],
                ["Attendance", selected.attendance], ["Company phase", selected.phase]]
                .filter(([, v]) => v)
                .map(([label, v]) => (
                  <div key={label}>
                    <div className="text-[10px] uppercase tracking-widest text-faint">{label}</div>
                    <div className="mt-0.5 text-dim">{v}</div>
                  </div>
                ))}
            </div>
            {selected.tips && (
              <div className="rounded-lg border border-line bg-white/5 p-3 text-xs leading-relaxed text-dim">
                <span className="font-medium text-ink">Application tips: </span>{selected.tips}
              </div>
            )}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {editor && (
                <button className="btn btn-primary" onClick={() => startApplication(selected)}
                        disabled={starting} data-testid="accel-start-application">
                  {starting ? <Spinner size={14} /> : <FileText size={14} />} Start application
                </button>
              )}
              {selected.url && (
                <a href={selected.url} target="_blank" rel="noreferrer" className="btn btn-ghost">
                  Program site <ExternalLink size={12} />
                </a>
              )}
            </div>
            <p className="text-[11px] text-faint">
              Start application pulls the program's page and builds its actual questions
              into a form (with tips) in Accelerator Applications — with an Anthropic key
              set, tailored to this program; otherwise a solid generic template.
            </p>
          </div>
        )}
      </Modal>

      <AddProgramModal open={showAdd} onClose={() => setShowAdd(false)}
        onAdd={(p) => { setCustom((c) => [p, ...c]); setSelected(p); }} />
    </PageReveal>
  );
}

function AddProgramModal({ open, onClose, onAdd }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const submit = (e) => {
    e.preventDefault();
    if (name.trim().length < 2) { toast.error("Give the program a name"); return; }
    if (url && !/^https?:\/\//i.test(url.trim())) { toast.error("URL must start with http(s)://"); return; }
    onAdd({ name: name.trim(), url: url.trim(), focus: "Added by you", location: "—",
            terms: "See site", cohort: "", dueDate: "Check site", durationWeeks: null,
            attendance: "Varies", phase: "Any", tips: "" });
    setName(""); setUrl(""); onClose();
  };
  return (
    <Modal open={open} onClose={onClose} title="Add your own program">
      <form onSubmit={submit} className="space-y-3" data-testid="accel-add-form">
        <Field label="Program name">
          <input className="field" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. State defense innovation cohort" />
        </Field>
        <Field label="Program URL" hint="Paste the program page — Start application reads it to build the form.">
          <input className="field" value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="https://…" />
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary">Add program</button>
        </div>
      </form>
    </Modal>
  );
}
