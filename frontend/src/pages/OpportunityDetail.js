import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar,
  PieChart, Pie, Cell, Tooltip,
} from "recharts";
import {
  ArrowLeft, Save, Plus, Trash2, ExternalLink, ShieldAlert, Sparkles,
  CheckCircle2, XCircle, AlertTriangle, Gauge, Target,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal } from "../components/ui";
import { fmtMoney, fmtDate, fmtDateTime, ELIGIBILITY, CHART_SERIES, canEdit } from "../lib/helpers";

const TABS = ["Fit & Overview", "Set-Aside", "Compliance", "Budget", "Scorecard", "Decision"];
const STAGES = ["Identified", "Qualifying", "Building", "Submitted", "Won", "Lost", "No-Bid"];
const tooltipStyle = { background: "var(--bg-elev)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--text)", fontSize: 12 };

const PROGRAMS = [
  { code: "8(a)", cert: "eightA", desc: "8(a) Business Development — SBA-certified socially/economically disadvantaged firms." },
  { code: "HUBZone", cert: "hubzone", desc: "Historically Underutilized Business Zone — principal office in a HUBZone, 35% staff residency." },
  { code: "SDVOSB", cert: "sdvosb", desc: "Service-Disabled Veteran-Owned Small Business — VA/SBA certified." },
  { code: "WOSB", cert: "wosb", desc: "Woman-Owned Small Business — SBA certified for designated NAICS." },
  { code: "EDWOSB", cert: "edwosb", desc: "Economically Disadvantaged WOSB." },
  { code: "VOSB", cert: "vosb", desc: "Veteran-Owned Small Business." },
];

function fitPosture(fit) {
  const vals = Object.values(fit || {});
  if (vals.some((v) => v === 1)) return { label: "Escalate", tone: "bad", note: "A factor scored 1 — escalate before proceeding." };
  const greens = vals.filter((v) => v >= 4).length;
  if (greens >= 8) return { label: "Strong", tone: "ok", note: `${greens}/10 factors green.` };
  if (greens >= 6) return { label: "Conditional", tone: "warn", note: `${greens}/10 factors green — conditional pursue.` };
  return { label: "Weak", tone: "bad", note: `${greens}/10 factors green — weak fit.` };
}

export default function OpportunityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const [opp, setOpp] = useState(null);
  const [profile, setProfile] = useState(null);
  const [tab, setTab] = useState(TABS[0]);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities/${id}`).then((r) => setOpp(r.data))
      .catch((e) => { toast.error(errMsg(e)); navigate("/opportunities"); });
    api.get(`/orgs/${activeOrgId}/profile`).then((r) => setProfile(r.data)).catch(() => {});
  }, [activeOrgId, id, navigate]);

  const update = (patch) => { setOpp((o) => ({ ...o, ...patch })); setDirty(true); };

  const save = async () => {
    setSaving(true);
    try {
      const body = {
        title: opp.title, solNumber: opp.solNumber, agency: opp.agency, office: opp.office,
        vehicle: opp.vehicle, setAside: opp.setAside, naics: opp.naics, ceiling: Number(opp.ceiling) || 0,
        pop: opp.pop, dueDate: opp.dueDate || null, stage: opp.stage, url: opp.url, winThemes: opp.winThemes,
        fit: opp.fit, pwin: Number(opp.pwin) || 0, proposalStrength: Number(opp.proposalStrength) || 0,
        compliance: opp.compliance, budget: opp.budget, criteria: opp.criteria, decision: opp.decision,
      };
      const { data } = await api.put(`/orgs/${activeOrgId}/opportunities/${id}`, body);
      setOpp(data);
      setDirty(false);
      toast.success("Saved");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  if (!opp) return <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>;

  const elig = opp.eligibility || { verdict: "verify" };
  const eligCfg = ELIGIBILITY[elig.verdict] || ELIGIBILITY.verify;
  const posture = fitPosture(opp.fit);

  return (
    <PageReveal className="space-y-5">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <button onClick={() => navigate("/opportunities")} className="mb-2 inline-flex items-center gap-1.5 text-sm text-dim hover:text-cyan" data-testid="back-to-pipeline">
            <ArrowLeft size={15} /> Back to Pipeline
          </button>
          <h1 className="text-2xl font-semibold text-ink">{opp.title}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-faint">
            <span className="mono">{opp.solNumber || "—"}</span>
            <span>·</span><span>{opp.agency}</span>
            <Pill tone="violet">{opp.vehicle}</Pill>
            <span className={`pill ${eligCfg.cls}`}>{eligCfg.label}</span>
            {opp.url && <a href={opp.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-cyan hover:underline"><ExternalLink size={12} /> Source</a>}
          </div>
        </div>
        {editor && (
          <button className="btn btn-primary" onClick={save} disabled={!dirty || saving} data-testid="save-opp">
            {saving ? <Spinner /> : <Save size={16} />} {dirty ? "Save changes" : "Saved"}
          </button>
        )}
      </div>

      {/* AI verify report */}
      {opp.verifyReport && <VerifyReport opp={opp} orgId={activeOrgId} editor={editor} onApplied={setOpp} />}

      {/* tabs */}
      <div className="flex flex-wrap gap-1 border-b border-line">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm transition-colors ${tab === t ? "border-b-2 border-cyan text-cyan" : "text-dim hover:text-ink"}`}
            data-testid={`tab-${t.replace(/\W+/g, "-").toLowerCase()}`}>{t}</button>
        ))}
      </div>

      {tab === "Fit & Overview" && <FitTab opp={opp} update={update} editor={editor} posture={posture} />}
      {tab === "Set-Aside" && <SetAsideTab opp={opp} profile={profile} elig={elig} eligCfg={eligCfg} update={update} editor={editor} />}
      {tab === "Compliance" && <ComplianceTab opp={opp} update={update} editor={editor} />}
      {tab === "Budget" && <BudgetTab opp={opp} update={update} editor={editor} />}
      {tab === "Scorecard" && <ScorecardTab opp={opp} update={update} editor={editor} />}
      {tab === "Decision" && <DecisionTab opp={opp} update={update} editor={editor} posture={posture} />}
    </PageReveal>
  );
}

function VerifyReport({ opp, orgId, editor, onApplied }) {
  const r = opp.verifyReport;
  const accept = async (d) => {
    try {
      await api.post(`/orgs/${orgId}/opportunities/${opp.id}/verify/accept`, { field: d.field, value: d.suggested });
      const fresh = await api.get(`/orgs/${orgId}/opportunities/${opp.id}`);
      onApplied(fresh.data); toast.success(`Applied: ${d.field}`);
    } catch (e) { toast.error(errMsg(e)); }
  };
  const dismiss = async (d) => {
    try {
      await api.post(`/orgs/${orgId}/opportunities/${opp.id}/verify/dismiss`, { field: d.field, value: d.suggested });
      const fresh = await api.get(`/orgs/${orgId}/opportunities/${opp.id}`);
      onApplied(fresh.data);
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Card className="border-violet/30 p-4" data-testid="verify-report">
      <div className="flex items-center gap-2"><Sparkles size={16} className="text-violet" /><SectionLabel className="!text-violet">AI Verification Report</SectionLabel>
        <span className="pill border-violet/40 text-violet">{r.confidence} confidence</span></div>
      <p className="mt-2 text-xs text-faint">{r.summary} · {fmtDateTime(r.generatedAt)} · Assistive only — confirm on source.</p>
      {r.diffs?.length > 0 && (
        <div className="mt-3 space-y-2">
          {r.diffs.map((d, i) => (
            <div key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-white/5 p-3" data-testid={`diff-${d.field}`}>
              <div className="text-sm">
                <span className="mono text-cyan">{d.field}</span>{" "}
                <span className="text-faint">{String(d.current)} → </span>
                <span className="text-ink">{String(d.suggested)}</span>
                <div className="text-xs text-faint">{d.note}</div>
              </div>
              {editor && (
                <div className="flex gap-2">
                  <button className="btn btn-ghost !py-1 !px-2 text-xs" onClick={() => accept(d)} data-testid={`accept-${d.field}`}><CheckCircle2 size={13} /> Accept</button>
                  <button className="btn btn-ghost !py-1 !px-2 text-xs" onClick={() => dismiss(d)} data-testid={`dismiss-${d.field}`}><XCircle size={13} /> Dismiss</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {r.linkStatuses?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {r.linkStatuses.map((l, i) => (
            <span key={i} className={`pill ${l.status === "live" ? "text-ok border-ok/40" : "text-warn border-warn/40"}`}>
              {l.label}: {l.status}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}

function FitTab({ opp, update, editor, posture }) {
  const fit = opp.fit || {};
  const setFactor = (k, v) => update({ fit: { ...fit, [k]: Number(v) } });
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <Card className="p-5 lg:col-span-2">
        <SectionLabel>10-Factor Fit Matrix (1–5)</SectionLabel>
        <div className="mt-4 space-y-3">
          {Object.entries(fit).map(([k, v]) => (
            <div key={k} className="flex items-center gap-3" data-testid={`fit-${k.replace(/\W+/g, "-").toLowerCase()}`}>
              <div className="w-44 shrink-0 text-sm text-dim">{k}</div>
              <input type="range" min={1} max={5} value={v} disabled={!editor}
                onChange={(e) => setFactor(k, e.target.value)} className="flex-1 accent-cyan" />
              <span className={`mono w-6 text-center text-sm ${v === 1 ? "text-bad" : v >= 4 ? "text-ok" : "text-warn"}`}>{v}</span>
            </div>
          ))}
        </div>
      </Card>
      <div className="space-y-5">
        <Card className="p-5">
          <SectionLabel>Fit Posture</SectionLabel>
          <div className="mt-3"><Pill tone={posture.tone} className="!text-sm !px-3 !py-1">{posture.label}</Pill></div>
          <p className="mt-2 text-xs text-faint">{posture.note}</p>
        </Card>
        <Card className="p-5">
          <SectionLabel>Snapshot</SectionLabel>
          <dl className="mt-3 space-y-2 text-sm">
            <Row label="Ceiling" value={fmtMoney(opp.ceiling)} />
            <Row label="Due" value={fmtDate(opp.dueDate)} />
            <Row label="PoP" value={opp.pop || "—"} />
            <Row label="NAICS" value={opp.naics || "—"} mono />
            <Row label="Source" value={opp.source} />
          </dl>
        </Card>
        <Card className="p-5">
          <SectionLabel>Win Themes</SectionLabel>
          <textarea className="field mt-3 min-h-[90px]" disabled={!editor} value={opp.winThemes || ""}
            onChange={(e) => update({ winThemes: e.target.value })} placeholder="Discriminators, hot buttons…" data-testid="win-themes" />
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-faint">{label}</dt>
      <dd className={`text-ink ${mono ? "mono" : ""}`}>{value}</dd>
    </div>
  );
}

function SetAsideTab({ opp, profile, elig, eligCfg, update, editor }) {
  return (
    <div className="space-y-5">
      <Card className="p-5">
        <SectionLabel>Eligibility Verdict</SectionLabel>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span className={`pill ${eligCfg.cls} !px-3 !py-1 !text-sm`}>{eligCfg.label}</span>
          <span className="text-sm text-dim">{elig.reason}</span>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="text-sm text-faint">Opportunity set-aside:</span>
          <select className="field !w-auto" disabled={!editor} value={opp.setAside}
            onChange={(e) => update({ setAside: e.target.value })} data-testid="setaside-select">
            {["Total Small Business", "8(a)", "HUBZone", "SDVOSB", "WOSB", "EDWOSB", "VOSB", "None"].map((v) => <option key={v}>{v}</option>)}
          </select>
        </div>
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-warn/30 bg-warn/10 p-3 text-xs text-warn">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          Self-certification is <b>not accepted</b> for program set-asides — your firm must hold the SBA certification at offer and award.
        </div>
      </Card>
      <Card className="p-5">
        <SectionLabel>Program Reference — Your Certifications</SectionLabel>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {PROGRAMS.map((p) => {
            const held = profile?.certs?.[p.cert];
            return (
              <div key={p.code} className="rounded-xl border border-line bg-white/5 p-3" data-testid={`program-${p.cert}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{p.code}</span>
                  <Pill tone={held ? "ok" : "neutral"}>{held ? "Held" : "Not held"}</Pill>
                </div>
                <p className="mt-1 text-xs text-faint">{p.desc}</p>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-faint">Manage certifications on the <b>Company Profile</b> page.</p>
      </Card>
    </div>
  );
}

function ComplianceTab({ opp, update, editor }) {
  const items = opp.compliance || [];
  const noBid = items.some((c) => c.req === "mandatory" && c.status === "gap");
  const setItem = (i, patch) => { const next = items.map((c, idx) => idx === i ? { ...c, ...patch } : c); update({ compliance: next }); };
  const addItem = () => update({ compliance: [...items, { item: "New requirement", req: "mandatory", status: "partial", note: "" }] });
  const removeItem = (i) => update({ compliance: items.filter((_, idx) => idx !== i) });
  return (
    <div className="space-y-5">
      <div className={`flex items-center gap-3 rounded-xl border p-4 ${noBid ? "border-bad/40 bg-bad/10" : "border-ok/30 bg-ok/10"}`} data-testid="cmmc-gate">
        <ShieldAlert size={20} className={noBid ? "text-bad" : "text-ok"} />
        <div>
          <div className={`font-semibold ${noBid ? "text-bad" : "text-ok"}`}>{noBid ? "HARD NO-BID GATE TRIGGERED" : "Compliance gate clear"}</div>
          <div className="text-xs text-faint">{noBid ? "A mandatory requirement is in GAP. Resolve before bidding (incl. CMMC / DFARS 252.204-7021/-7025)." : "No mandatory requirement is in GAP."}</div>
        </div>
      </div>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-elev/60 text-xs text-dim"><tr className="border-b border-line">
            <th className="px-3 py-2.5 text-left">Requirement</th><th className="px-3 py-2.5 text-left">Type</th>
            <th className="px-3 py-2.5 text-left">Status</th><th className="px-3 py-2.5 text-left">Note</th>{editor && <th></th>}
          </tr></thead>
          <tbody>
            {items.map((c, i) => (
              <tr key={i} className="border-b border-line/60" data-testid={`compliance-row-${i}`}>
                <td className="px-3 py-2">
                  <input className="field !py-1" disabled={!editor} value={c.item} onChange={(e) => setItem(i, { item: e.target.value })} />
                </td>
                <td className="px-3 py-2">
                  <select className="field !py-1 !w-auto" disabled={!editor} value={c.req} onChange={(e) => setItem(i, { req: e.target.value })}>
                    <option value="mandatory">Mandatory</option><option value="optional">Optional</option>
                  </select>
                </td>
                <td className="px-3 py-2">
                  <select className={`field !py-1 !w-auto ${c.status === "gap" ? "text-bad" : c.status === "met" ? "text-ok" : "text-warn"}`}
                    disabled={!editor} value={c.status} onChange={(e) => setItem(i, { status: e.target.value })} data-testid={`compliance-status-${i}`}>
                    <option value="met">Met</option><option value="partial">Partial</option><option value="gap">Gap</option>
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input className="field !py-1" disabled={!editor} value={c.note || ""} onChange={(e) => setItem(i, { note: e.target.value })} />
                </td>
                {editor && <td className="px-3 py-2"><button onClick={() => removeItem(i)} className="text-faint hover:text-bad"><Trash2 size={14} /></button></td>}
              </tr>
            ))}
          </tbody>
        </table>
        {editor && <div className="p-3"><button className="btn btn-ghost" onClick={addItem} data-testid="add-compliance"><Plus size={14} /> Add requirement</button></div>}
      </Card>
    </div>
  );
}

function BudgetTab({ opp, update, editor }) {
  const budget = opp.budget || { ceiling: 0, groups: { Labor: 0, Burden: 0, Materials: 0, Subcontracts: 0, ODC: [] } };
  const g = budget.groups;
  const setGroup = (k, v) => update({ budget: { ...budget, groups: { ...g, [k]: Number(v) || 0 } } });
  const odc = g.ODC || [];
  const odcTotal = odc.reduce((s, x) => s + (Number(x.amt) || 0), 0);
  const total = (Number(g.Labor) || 0) + (Number(g.Burden) || 0) + (Number(g.Materials) || 0) + (Number(g.Subcontracts) || 0) + odcTotal;
  const ceiling = Number(opp.ceiling) || 0;
  const margin = ceiling - total;
  const over = total > ceiling && ceiling > 0;
  const data = [
    { name: "Labor", value: Number(g.Labor) || 0 }, { name: "Burden", value: Number(g.Burden) || 0 },
    { name: "Materials", value: Number(g.Materials) || 0 }, { name: "Subcontracts", value: Number(g.Subcontracts) || 0 },
    { name: "ODC", value: odcTotal },
  ].filter((d) => d.value > 0);
  const setOdc = (i, patch) => update({ budget: { ...budget, groups: { ...g, ODC: odc.map((x, idx) => idx === i ? { ...x, ...patch } : x) } } });
  const addOdc = () => update({ budget: { ...budget, groups: { ...g, ODC: [...odc, { label: "ODC item", amt: 0 }] } } });
  const removeOdc = (i) => update({ budget: { ...budget, groups: { ...g, ODC: odc.filter((_, idx) => idx !== i) } } });
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <Card className="p-5 lg:col-span-2">
        <SectionLabel>Cost Build-Up vs Ceiling</SectionLabel>
        <div className="mt-4 grid grid-cols-2 gap-3">
          {["Labor", "Burden", "Materials", "Subcontracts"].map((k) => (
            <label key={k} className="block">
              <div className="mb-1 text-xs text-dim">{k}</div>
              <input type="number" className="field mono" disabled={!editor} value={g[k] || 0} onChange={(e) => setGroup(k, e.target.value)} data-testid={`budget-${k.toLowerCase()}`} />
            </label>
          ))}
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between"><span className="text-xs text-dim">Other Direct Costs (ODC)</span>
            {editor && <button className="btn btn-ghost !py-1 !px-2 text-xs" onClick={addOdc}><Plus size={12} /> Add</button>}</div>
          <div className="mt-2 space-y-2">
            {odc.map((x, i) => (
              <div key={i} className="flex gap-2">
                <input className="field !py-1" disabled={!editor} value={x.label} onChange={(e) => setOdc(i, { label: e.target.value })} />
                <input type="number" className="field mono !py-1 !w-32" disabled={!editor} value={x.amt} onChange={(e) => setOdc(i, { amt: Number(e.target.value) || 0 })} />
                {editor && <button onClick={() => removeOdc(i)} className="text-faint hover:text-bad"><Trash2 size={14} /></button>}
              </div>
            ))}
          </div>
        </div>
      </Card>
      <div className="space-y-4">
        <Card className="p-5">
          <SectionLabel>Totals</SectionLabel>
          <dl className="mt-3 space-y-2 text-sm">
            <Row label="Ceiling" value={fmtMoney(ceiling)} />
            <Row label="Cost total" value={fmtMoney(total)} />
            <div className="flex items-center justify-between border-t border-line pt-2">
              <dt className="text-faint">Margin</dt>
              <dd className={`mono ${over ? "text-bad" : "text-ok"}`}>{fmtMoney(margin)}</dd>
            </div>
          </dl>
          {over && <div className="mt-3 flex items-center gap-2 rounded-lg border border-bad/30 bg-bad/10 p-2 text-xs text-bad"><AlertTriangle size={13} /> Cost exceeds ceiling.</div>}
        </Card>
        <Card className="p-5">
          <SectionLabel>By Group</SectionLabel>
          <div className="mt-2 h-48">
            {data.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70} paddingAngle={2}>
                    {data.map((d, i) => <Cell key={d.name} fill={CHART_SERIES[i % CHART_SERIES.length]} stroke="var(--bg-panel)" />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtMoney(v)} />
                </PieChart>
              </ResponsiveContainer>
            ) : <div className="flex h-full items-center justify-center text-xs text-faint">Enter costs to see breakdown</div>}
          </div>
        </Card>
      </div>
    </div>
  );
}

function ScorecardTab({ opp, update, editor }) {
  const criteria = opp.criteria || [];
  const weightSum = criteria.reduce((s, c) => s + (Number(c.weight) || 0), 0);
  const strength = weightSum > 0 ? criteria.reduce((s, c) => s + (Number(c.score) || 0) * (Number(c.weight) || 0), 0) / weightSum : 0;
  const pwin = Number(opp.pwin) || 0;
  const setCrit = (i, patch) => update({ criteria: criteria.map((c, idx) => idx === i ? { ...c, ...patch } : c) });
  const radar = criteria.map((c) => ({ name: c.name, score: Number(c.score) || 0 }));
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="p-5" data-testid="proposal-strength-card">
          <div className="flex items-center gap-2"><Gauge size={16} className="text-cyan" /><SectionLabel>Proposal Strength</SectionLabel></div>
          <div className="mono mt-3 text-4xl font-semibold text-cyan">{strength.toFixed(1)}<span className="text-lg text-faint">/10</span></div>
          <p className="mt-1 text-xs text-faint">Weighted document quality vs. the verbatim evaluation criteria. {weightSum !== 100 && <span className="text-warn">Weights sum to {weightSum} (should be 100).</span>}</p>
        </Card>
        <Card className="p-5" data-testid="capture-probability-card">
          <div className="flex items-center gap-2"><Target size={16} className="text-violet" /><SectionLabel>Capture Probability (Pwin)</SectionLabel></div>
          <div className="mono mt-3 text-4xl font-semibold text-violet">{pwin}<span className="text-lg text-faint">%</span></div>
          <input type="range" min={0} max={100} value={pwin} disabled={!editor} onChange={(e) => update({ pwin: Number(e.target.value) })} className="mt-3 w-full accent-violet" data-testid="pwin-slider" />
          <p className="mt-1 text-xs text-faint">Your judgment from incumbent, field, relationship, price.</p>
        </Card>
      </div>
      <div className="flex items-start gap-2 rounded-xl border border-line bg-white/5 p-3 text-xs text-dim">
        <AlertTriangle size={14} className="mt-0.5 shrink-0 text-warn" />
        <span><b>Why they are separate:</b> Proposal Strength measures how well your documents answer the criteria. Capture Probability is your odds of winning given the competitive field. We never combine them into a single fabricated win-rate.</span>
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <div className="p-4"><SectionLabel>Evaluation Criteria</SectionLabel></div>
          <table className="w-full text-sm">
            <thead className="bg-elev/60 text-xs text-dim"><tr className="border-b border-line">
              <th className="px-3 py-2 text-left">Criterion</th><th className="px-3 py-2 text-left">Weight</th><th className="px-3 py-2 text-left">Score /10</th>
            </tr></thead>
            <tbody>
              {criteria.map((c, i) => (
                <tr key={i} className="border-b border-line/60" data-testid={`criterion-${i}`}>
                  <td className="px-3 py-2"><input className="field !py-1" disabled={!editor} value={c.name} onChange={(e) => setCrit(i, { name: e.target.value })} /></td>
                  <td className="px-3 py-2"><input type="number" className="field mono !py-1 !w-20" disabled={!editor} value={c.weight} onChange={(e) => setCrit(i, { weight: Number(e.target.value) || 0 })} /></td>
                  <td className="px-3 py-2"><input type="number" min={0} max={10} className="field mono !py-1 !w-20" disabled={!editor} value={c.score} onChange={(e) => setCrit(i, { score: Number(e.target.value) || 0 })} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card className="p-5">
          <SectionLabel>Criteria Radar</SectionLabel>
          <div className="mt-2 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radar} outerRadius="75%">
                <PolarGrid stroke="var(--line)" />
                <PolarAngleAxis dataKey="name" tick={{ fill: "var(--text-dim)", fontSize: 10 }} />
                <Radar dataKey="score" stroke="#38e1ff" fill="#38e1ff" fillOpacity={0.25} />
                <Tooltip contentStyle={tooltipStyle} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}

function DecisionTab({ opp, update, editor, posture }) {
  const items = opp.compliance || [];
  const complianceRed = items.some((c) => c.req === "mandatory" && c.status === "gap");
  const criteria = opp.criteria || [];
  const weightSum = criteria.reduce((s, c) => s + (Number(c.weight) || 0), 0);
  const strength = weightSum > 0 ? criteria.reduce((s, c) => s + (Number(c.score) || 0) * (Number(c.weight) || 0), 0) / weightSum : 0;
  const pwin = Number(opp.pwin) || 0;

  let rec, tone, why;
  if (complianceRed) { rec = "NO-BID"; tone = "bad"; why = "Mandatory compliance requirement in GAP — hard gate."; }
  else if (strength < 6) { rec = "REBUILD"; tone = "warn"; why = `Proposal Strength ${strength.toFixed(1)} < 6 — improve before submitting.`; }
  else if (pwin < 20) { rec = "NO-BID (unless strategic)"; tone = "warn"; why = `Pwin ${pwin}% < 20% — no-bid unless strategically justified.`; }
  else { rec = "BID"; tone = "ok"; why = `Size effort by Strength × Pwin ≈ ${(strength * pwin / 10).toFixed(0)} index.`; }

  const decision = opp.decision || { call: "TBD", rationale: "" };
  return (
    <div className="space-y-5">
      <Card className={`p-5 border-${tone}/40`} data-testid="decision-recommendation">
        <SectionLabel>Recommended Call</SectionLabel>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Pill tone={tone} className="!text-base !px-4 !py-1.5">{rec}</Pill>
          <span className="text-sm text-dim">{why}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg border border-line bg-white/5 p-3"><div className="label-mono">Compliance</div><div className={`mono mt-1 ${complianceRed ? "text-bad" : "text-ok"}`}>{complianceRed ? "RED" : "CLEAR"}</div></div>
          <div className="rounded-lg border border-line bg-white/5 p-3"><div className="label-mono">Strength</div><div className="mono mt-1 text-cyan">{strength.toFixed(1)}/10</div></div>
          <div className="rounded-lg border border-line bg-white/5 p-3"><div className="label-mono">Pwin</div><div className="mono mt-1 text-violet">{pwin}%</div></div>
        </div>
      </Card>
      <Card className="p-5">
        <SectionLabel>Final Decision</SectionLabel>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="block"><div className="mb-1 text-xs text-dim">Call</div>
            <select className="field" disabled={!editor} value={decision.call} onChange={(e) => update({ decision: { ...decision, call: e.target.value } })} data-testid="decision-call">
              {["TBD", "Bid", "No-Bid", "Rebuild", "Watch"].map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
          <label className="block"><div className="mb-1 text-xs text-dim">Move stage</div>
            <select className="field" disabled={!editor} value={opp.stage} onChange={(e) => update({ stage: e.target.value })} data-testid="decision-stage">
              {STAGES.map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
        </div>
        <label className="mt-3 block"><div className="mb-1 text-xs text-dim">Rationale</div>
          <textarea className="field min-h-[90px]" disabled={!editor} value={decision.rationale || ""} onChange={(e) => update({ decision: { ...decision, rationale: e.target.value } })} data-testid="decision-rationale" placeholder="Document the bid/no-bid rationale…" />
        </label>
      </Card>
    </div>
  );
}
