import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Plus, Sparkles, DownloadCloud, ArrowUpDown, Trash2, Inbox,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Skeleton, EmptyState, PageReveal, Modal, Field, Spinner } from "../components/ui";
import AIButton from "../components/AIButton";
import { fmtMoney, fmtDate, fmtDateTime, dueColor, ELIGIBILITY, STAGE_COLORS, canEdit } from "../lib/helpers";

const VEHICLES = ["RFP", "SBIR", "STTR", "BAA", "CSO", "Grant"];
const SETASIDES = ["Total Small Business", "8(a)", "HUBZone", "SDVOSB", "WOSB", "EDWOSB", "VOSB", "None"];
const STAGES = ["Identified", "Qualifying", "Building", "Submitted", "Won", "Lost", "No-Bid"];

function Th({ k, children, className = "", onSort }) {
  return (
    <th className={`cursor-pointer select-none px-3 py-2.5 text-left font-medium hover:text-ink ${className}`}
        onClick={() => onSort(k)} data-testid={`sort-${k}`}>
      <span className="inline-flex items-center gap-1">{children}<ArrowUpDown size={12} className="text-faint" /></span>
    </th>
  );
}

function EligibilityPill({ verdict }) {
  const cfg = ELIGIBILITY[verdict] || ELIGIBILITY.verify;
  return <span className={`pill ${cfg.cls}`} data-testid={`elig-${verdict}`}>{cfg.label}</span>;
}

function CreateModal({ open, onClose, orgId, onCreated }) {
  const [form, setForm] = useState({ title: "", solNumber: "", agency: "", vehicle: "RFP", setAside: "None", ceiling: "", dueDate: "", url: "" });
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post(`/orgs/${orgId}/opportunities`, {
        ...form, ceiling: Number(form.ceiling) || 0, dueDate: form.dueDate || null,
      });
      toast.success("Opportunity created");
      onCreated(data);
      onClose();
      setForm({ title: "", solNumber: "", agency: "", vehicle: "RFP", setAside: "None", ceiling: "", dueDate: "", url: "" });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setLoading(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="New Opportunity">
      <form onSubmit={submit} className="space-y-3" data-testid="create-opp-form">
        <Field label="Title"><input className="field" required value={form.title} onChange={set("title")} data-testid="opp-title" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Solicitation #"><input className="field mono" value={form.solNumber} onChange={set("solNumber")} data-testid="opp-sol" /></Field>
          <Field label="Agency"><input className="field" value={form.agency} onChange={set("agency")} /></Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Vehicle">
            <select className="field" value={form.vehicle} onChange={set("vehicle")}>{VEHICLES.map((v) => <option key={v}>{v}</option>)}</select>
          </Field>
          <Field label="Set-Aside">
            <select className="field" value={form.setAside} onChange={set("setAside")}>{SETASIDES.map((v) => <option key={v}>{v}</option>)}</select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ceiling ($)"><input type="number" className="field mono" value={form.ceiling} onChange={set("ceiling")} /></Field>
          <Field label="Due date"><input type="date" className="field mono" value={form.dueDate} onChange={set("dueDate")} /></Field>
        </div>
        <Field label="Source URL"><input className="field" value={form.url} onChange={set("url")} placeholder="https://sam.gov/opp/..." /></Field>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={loading} data-testid="opp-create-submit">
            {loading ? <Spinner /> : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function Opportunities() {
  const { activeOrgId, activeOrg } = useAuth();
  const navigate = useNavigate();
  const editor = canEdit(activeOrg?.role);
  const [opps, setOpps] = useState(null);
  const [q, setQ] = useState("");
  const [fVehicle, setFVehicle] = useState("");
  const [fSetAside, setFSetAside] = useState("");
  const [fStage, setFStage] = useState("");
  const [fStatus, setFStatus] = useState("active"); // expired hidden by default
  const [fAgency, setFAgency] = useState("");
  const [fAwardMin, setFAwardMin] = useState(0);
  const [fDueWithin, setFDueWithin] = useState(0); // days; 0 = any
  const [hideClosed, setHideClosed] = useState(false);
  const [sort, setSort] = useState({ key: "dueDate", dir: "asc" });
  const [showCreate, setShowCreate] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [scanning, setScanning] = useState(false);

  const load = () => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities`).then((r) => setOpps(r.data)).catch(() => setOpps([]));
  };
  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities`).then((r) => setOpps(r.data)).catch(() => setOpps([]));
  }, [activeOrgId]);

  const runDeepScan = async () => {
    setScanning(true);
    const tid = toast.loading("AI Deep Scan running — searching SAM, SBIR/DSIP, AFWERX, DIU, NASA and the open web…");
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/intel/scan`, { tier: "standard" });
      const jobId = data.jobId;
      for (let i = 0; i < 60; i++) {
        await new Promise((res) => setTimeout(res, 5000));
        const { data: job } = await api.get(`/orgs/${activeOrgId}/intel/jobs/${jobId}`);
        if (job.status === "done") {
          toast.success("Deep scan complete", {
            id: tid, description: job.summary,
            action: { label: "View report", onClick: () => navigate("/intelligence") },
          });
          setScanning(false);
          return;
        }
        if (job.status === "error") {
          toast.error(job.error || "Scan failed", { id: tid });
          setScanning(false);
          return;
        }
      }
      toast.info("Scan is taking a while — check Deep-scan reports shortly", { id: tid });
    } catch (err) {
      toast.error(errMsg(err), { id: tid });
    } finally {
      setScanning(false);
    }
  };

  const runVerify = async ({ engine, model, effort }) => {
    const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/verify`,
      { engine, model: model || "", effort: effort || "standard" });
    toast.success("AI Verify complete", { description: data.summary });
    load();
    return data;
  };

  const runPull = async () => {
    setPulling(true);
    const tid = toast.loading("Pulling from SAM / Grants…");
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/pull`);
      toast.success("Pull complete", { id: tid, description: data.summary });
      load();
    } catch (err) {
      toast.error(errMsg(err), { id: tid });
    } finally {
      setPulling(false);
    }
  };

  const del = async (e, o) => {
    e.stopPropagation();
    if (!window.confirm(`Delete "${o.title}"?`)) return;
    try {
      await api.delete(`/orgs/${activeOrgId}/opportunities/${o.id}`);
      toast.success("Deleted");
      setOpps((prev) => prev.filter((x) => x.id !== o.id));
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  // Notice lifecycle: closed = response deadline has passed; otherwise the
  // source feed's status (pre-release = presolicitation / sources sought).
  const noticeStatusOf = (o) => {
    if (o.dueDate && new Date(o.dueDate) < new Date(new Date().toDateString()))
      return "closed";
    return o.noticeStatus === "pre-release" ? "pre-release" : "open";
  };

  const agencies = useMemo(
    () => [...new Set((opps || []).map((o) => o.agency).filter(Boolean))].sort(),
    [opps]);

  const filtered = useMemo(() => {
    if (!opps) return [];
    let list = opps.filter((o) => {
      if (q && !(`${o.title} ${o.solNumber} ${o.agency} ${o.naics}`.toLowerCase().includes(q.toLowerCase()))) return false;
      if (fVehicle && o.vehicle !== fVehicle) return false;
      if (fSetAside && o.setAside !== fSetAside) return false;
      if (fStage && o.stage !== fStage) return false;
      if (fAgency && o.agency !== fAgency) return false;
      const ns = noticeStatusOf(o);
      if (fStatus === "active" && ns === "closed") return false;
      if (["open", "pre-release", "closed"].includes(fStatus) && ns !== fStatus) return false;
      if (hideClosed && ["Won", "Lost", "No-Bid"].includes(o.stage)) return false;
      if (fAwardMin && (Number(o.ceiling) || 0) < fAwardMin) return false;
      if (fDueWithin) {
        if (!o.dueDate) return false;
        const days = (new Date(o.dueDate).getTime() - Date.now()) / 86400000;
        if (days < 0 || days > fDueWithin) return false;
      }
      return true;
    });
    const { key, dir } = sort;
    list = [...list].sort((a, b) => {
      let av = a[key], bv = b[key];
      if (key === "ceiling") { av = Number(av) || 0; bv = Number(bv) || 0; }
      if (key === "dueDate") { av = av ? new Date(av).getTime() : Infinity; bv = bv ? new Date(bv).getTime() : Infinity; }
      if (typeof av === "string") av = av.toLowerCase();
      if (typeof bv === "string") bv = bv.toLowerCase();
      if (av < bv) return dir === "asc" ? -1 : 1;
      if (av > bv) return dir === "asc" ? 1 : -1;
      return 0;
    });
    return list;
  }, [opps, q, fVehicle, fSetAside, fStage, fStatus, fAgency, fAwardMin, fDueWithin, hideClosed, sort]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSort = (key) =>
    setSort((s) => ({ key, dir: s.key === key && s.dir === "asc" ? "desc" : "asc" }));

  return (
    <PageReveal className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <SectionLabel>Pipeline</SectionLabel>
          <h1 className="mt-1 text-2xl font-semibold text-ink">Federal Opportunities</h1>
          <div className="mt-1 text-xs text-faint">
            FEED as of {fmtDateTime(new Date())} ·{" "}
            <button className="text-cyan hover:underline" onClick={() => navigate("/intelligence")}
              data-testid="scan-reports-link">Deep-scan reports</button>
          </div>
        </div>
        {editor && (
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-violet" onClick={runDeepScan} disabled={scanning} data-testid="deep-scan-button"
              title="AI market scan across SAM, SBIR/DSIP, AFWERX, DIU, DARPA, NASA and the open web — fit-scored against your company profile">
              {scanning ? <Spinner /> : <Sparkles size={16} />} AI Deep Scan
            </button>
            <AIButton orgId={activeOrgId} compact icon={CheckCircle2}
              label="Verify & Refresh with AI" testid="verify-refresh-button"
              note="Anthropic verifies against the live web and discovers new matches; other engines review saved data only."
              onStart={runVerify} onDone={load} />
            <button className="btn btn-ghost" onClick={runPull} disabled={pulling} data-testid="pull-sam-button">
              {pulling ? <Spinner /> : <DownloadCloud size={16} />} Pull from SAM / Grants
            </button>
            <button className="btn btn-primary" onClick={() => setShowCreate(true)} data-testid="new-opp-button">
              <Plus size={16} /> New
            </button>
          </div>
        )}
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[200px] flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
            <input className="field !pl-9" placeholder="Search title, sol #, agency…" value={q}
              onChange={(e) => setQ(e.target.value)} data-testid="opp-search" />
          </div>
          <select className="field !w-auto" value={fStatus} onChange={(e) => setFStatus(e.target.value)} data-testid="filter-status">
            <option value="active">Active (open + pre-release)</option>
            <option value="open">Open</option>
            <option value="pre-release">Pre-release</option>
            <option value="closed">Closed / expired</option>
            <option value="all">All statuses</option>
          </select>
          <select className="field !w-auto" value={fAgency} onChange={(e) => setFAgency(e.target.value)} data-testid="filter-agency">
            <option value="">All agencies</option>{agencies.map((a) => <option key={a}>{a}</option>)}
          </select>
          <select className="field !w-auto" value={fVehicle} onChange={(e) => setFVehicle(e.target.value)} data-testid="filter-vehicle">
            <option value="">All vehicles</option>{VEHICLES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className="field !w-auto" value={fSetAside} onChange={(e) => setFSetAside(e.target.value)} data-testid="filter-setaside">
            <option value="">All set-asides</option>{SETASIDES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className="field !w-auto" value={fStage} onChange={(e) => setFStage(e.target.value)} data-testid="filter-stage">
            <option value="">All stages</option>{STAGES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className="field !w-auto" value={fAwardMin} onChange={(e) => setFAwardMin(Number(e.target.value))} data-testid="filter-award">
            <option value={0}>Any award $</option>
            <option value={100000}>≥ $100K</option>
            <option value={1000000}>≥ $1M</option>
            <option value={5000000}>≥ $5M</option>
            <option value={10000000}>≥ $10M</option>
          </select>
          <select className="field !w-auto" value={fDueWithin} onChange={(e) => setFDueWithin(Number(e.target.value))} data-testid="filter-due">
            <option value={0}>Any due date</option>
            <option value={7}>Due ≤ 7 days</option>
            <option value={30}>Due ≤ 30 days</option>
            <option value={90}>Due ≤ 90 days</option>
          </select>
          <label className="flex items-center gap-2 text-xs text-dim">
            <input type="checkbox" checked={hideClosed} onChange={(e) => setHideClosed(e.target.checked)} data-testid="hide-closed" />
            Hide closed
          </label>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {opps === null ? (
          <div className="space-y-2 p-4">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Inbox} title="No opportunities match"
            subtitle={opps.length === 0 ? "Pull from SAM/Grants or create one manually." : "Try clearing filters."}
            action={editor && opps.length === 0 ? (
              <button className="btn btn-primary" onClick={() => setShowCreate(true)}><Plus size={16} /> New Opportunity</button>
            ) : null} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="opportunities-table">
              <thead className="sticky top-0 z-10 bg-elev/90 text-xs text-dim backdrop-blur">
                <tr className="border-b border-line">
                  <Th k="title" onSort={toggleSort}>Opportunity</Th>
                  <Th k="agency" onSort={toggleSort}>Agency</Th>
                  <Th k="vehicle" onSort={toggleSort}>Vehicle</Th>
                  <Th k="setAside" onSort={toggleSort}>Set-Aside</Th>
                  <Th k="ceiling" className="text-right" onSort={toggleSort}>Ceiling</Th>
                  <Th k="dueDate" onSort={toggleSort}>Due</Th>
                  <Th k="stage" onSort={toggleSort}>Stage</Th>
                  <Th k="lastVerified" onSort={toggleSort}>Last Verified</Th>
                  {editor && <th className="px-3 py-2.5"></th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((o) => {
                  const due = dueColor(o.dueDate);
                  return (
                    <tr key={o.id} onClick={() => navigate(`/opportunities/${o.id}`)}
                      className="cursor-pointer border-b border-line/60 transition-colors hover:bg-white/5"
                      data-testid={`opp-row-${o.id}`}>
                      <td className="px-3 py-3">
                        <div className="font-medium text-ink">{o.title}</div>
                        <div className="mono text-xs text-faint">{o.solNumber || "—"}</div>
                      </td>
                      <td className="px-3 py-3 text-dim">{o.agency || "—"}<div className="text-xs text-faint">{o.office}</div></td>
                      <td className="px-3 py-3"><Pill tone="violet">{o.vehicle}</Pill></td>
                      <td className="px-3 py-3">
                        <div className="flex flex-col gap-1">
                          <EligibilityPill verdict={o.eligibility?.verdict} />
                          <span className="text-xs text-faint">{o.setAside}</span>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-right mono text-ink">{fmtMoney(o.ceiling)}</td>
                      <td className="px-3 py-3">
                        <div className={`mono text-sm ${due.cls}`}>{fmtDate(o.dueDate)}</div>
                        <div className={`text-xs ${due.cls}`}>{due.label}</div>
                      </td>
                      <td className="px-3 py-3">
                        <span className="pill border-line" style={{ color: STAGE_COLORS[o.stage], borderColor: STAGE_COLORS[o.stage] + "66" }}>
                          {o.stage}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        {o.lastVerified ? (
                          <span className="inline-flex items-center gap-1 text-xs text-ok"><CheckCircle2 size={12} />{fmtDate(o.lastVerified)}</span>
                        ) : <span className="text-xs text-faint">Never</span>}
                      </td>
                      {editor && (
                        <td className="px-3 py-3 text-right">
                          <button onClick={(e) => del(e, o)} className="text-faint hover:text-bad" data-testid={`delete-opp-${o.id}`}>
                            <Trash2 size={15} />
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
      </Card>

      <CreateModal open={showCreate} onClose={() => setShowCreate(false)} orgId={activeOrgId}
        onCreated={(d) => setOpps((p) => [d, ...(p || [])])} />
    </PageReveal>
  );
}
