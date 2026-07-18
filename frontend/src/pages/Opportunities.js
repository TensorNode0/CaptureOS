import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Plus, Sparkles, DownloadCloud, ArrowUpDown, Trash2, Inbox,
  CheckCircle2, Columns3, Download, Star, ChevronUp, ChevronDown, X,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Skeleton, EmptyState, PageReveal, Modal, Field, Spinner } from "../components/ui";
import AIButton from "../components/AIButton";
import AIChatButton from "../components/AIChatButton";
import OppDrawer from "../components/OppDrawer";
import { COLUMNS, DEFAULT_VISIBLE, COMPACT_VISIBLE } from "../lib/oppColumns";
import { fmtDateTime, exportCsv, canEdit } from "../lib/helpers";

const VEHICLES = ["RFP", "SBIR", "STTR", "BAA", "CSO", "Grant"];
const SETASIDES = ["Total Small Business", "8(a)", "HUBZone", "SDVOSB", "WOSB", "EDWOSB", "VOSB", "None"];
const STAGES = ["Identified", "Qualifying", "Building", "Submitted", "Won", "Lost", "No-Bid"];
const COL_BY_KEY = Object.fromEntries(COLUMNS.map((c) => [c.key, c]));

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

function ColumnChooser({ visible, setVisible, views, onSaveView, onApplyView, onClose }) {
  const move = (key, dir) => {
    const i = visible.indexOf(key);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= visible.length) return;
    const next = [...visible];
    [next[i], next[j]] = [next[j], next[i]];
    setVisible(next);
  };
  const toggle = (key) =>
    setVisible(visible.includes(key)
      ? visible.filter((k) => k !== key)
      : [...visible, key]);
  const ordered = [...visible.map((k) => COL_BY_KEY[k]),
    ...COLUMNS.filter((c) => !visible.includes(c.key))].filter(Boolean);
  return (
    <div className="absolute right-0 top-full z-30 mt-1 w-72 rounded-xl border border-line bg-panel p-3 shadow-2xl" data-testid="column-chooser">
      <div className="flex items-center justify-between">
        <SectionLabel className="!text-[10px]">Columns & views</SectionLabel>
        <button onClick={onClose} className="text-faint hover:text-ink"><X size={13} /></button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <button className="btn btn-ghost !px-2 !py-0.5 text-[11px]" onClick={() => onApplyView(DEFAULT_VISIBLE)} data-testid="view-default">Capture view</button>
        <button className="btn btn-ghost !px-2 !py-0.5 text-[11px]" onClick={() => onApplyView(COMPACT_VISIBLE)} data-testid="view-compact">Compact</button>
        {Object.keys(views).map((name) => (
          <button key={name} className="btn btn-ghost !px-2 !py-0.5 text-[11px] !text-cyan" onClick={() => onApplyView(views[name])}>{name}</button>
        ))}
        <button className="btn btn-ghost !px-2 !py-0.5 text-[11px]" onClick={onSaveView} data-testid="save-view">+ Save view</button>
      </div>
      <div className="mt-2 max-h-72 space-y-0.5 overflow-y-auto">
        {ordered.map((c) => {
          const on = visible.includes(c.key);
          return (
            <div key={c.key} className="flex items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-white/5">
              <input type="checkbox" checked={on} onChange={() => toggle(c.key)} data-testid={`col-toggle-${c.key}`} />
              <span className={on ? "text-dim" : "text-faint"}>{c.label}</span>
              {on && (
                <span className="ml-auto flex gap-0.5">
                  <button onClick={() => move(c.key, -1)} className="text-faint hover:text-ink"><ChevronUp size={12} /></button>
                  <button onClick={() => move(c.key, 1)} className="text-faint hover:text-ink"><ChevronDown size={12} /></button>
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
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
  const [fStatus, setFStatus] = useState("active");
  const [fAgency, setFAgency] = useState("");
  const [fAwardMin, setFAwardMin] = useState(0);
  const [fDueWithin, setFDueWithin] = useState(0);
  const [fElig, setFElig] = useState("");
  const [fPriority, setFPriority] = useState("");
  const [fFit, setFFit] = useState("");
  const [fPwin, setFPwin] = useState("");
  const [fDecision, setFDecision] = useState("");
  const [watchOnly, setWatchOnly] = useState(false);
  const [hideClosed, setHideClosed] = useState(false);
  const [sortStack, setSortStack] = useState([{ key: "priority", dir: "asc" }]);
  const [visible, setVisibleRaw] = useState(DEFAULT_VISIBLE);
  const [views, setViews] = useState({});
  const [showCols, setShowCols] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [drawerId, setDrawerId] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [scanning, setScanning] = useState(false);

  const setVisible = (cols) => {
    setVisibleRaw(cols);
    try { localStorage.setItem(`oppCols:${activeOrgId}`, JSON.stringify(cols)); } catch {}
  };

  useEffect(() => {
    if (!activeOrgId) return;
    try {
      const saved = JSON.parse(localStorage.getItem(`oppCols:${activeOrgId}`) || "null");
      if (Array.isArray(saved) && saved.length) setVisibleRaw(saved.filter((k) => COL_BY_KEY[k]));
      const v = JSON.parse(localStorage.getItem(`oppViews:${activeOrgId}`) || "{}");
      setViews(v && typeof v === "object" ? v : {});
    } catch {}
    api.get(`/orgs/${activeOrgId}/opportunities`).then((r) => setOpps(r.data)).catch(() => setOpps([]));
  }, [activeOrgId]);

  const load = () => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities`).then((r) => setOpps(r.data)).catch(() => setOpps([]));
  };

  const patchRow = (data) => setOpps((prev) => (prev || []).map((x) => (x.id === data.id ? data : x)));

  const saveView = () => {
    const name = window.prompt("Name this view:");
    if (!name) return;
    const next = { ...views, [name.trim()]: visible };
    setViews(next);
    try { localStorage.setItem(`oppViews:${activeOrgId}`, JSON.stringify(next)); } catch {}
    toast.success(`View "${name.trim()}" saved`);
  };

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

  const toggleWatch = async (o) => {
    try {
      const { data } = await api.put(`/orgs/${activeOrgId}/opportunities/${o.id}`, { watch: !o.watch });
      patchRow(data);
    } catch (err) { toast.error(errMsg(err)); }
  };

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
      const hay = `${o.title} ${o.solNumber} ${o.agency} ${o.naics} ${o.psc || ""} ${o.scopeSummary || ""} ${(o.capture?.owner) || ""} ${(o.tags || []).join(" ")}`.toLowerCase();
      if (q && !hay.includes(q.toLowerCase())) return false;
      if (fVehicle && o.vehicle !== fVehicle) return false;
      if (fSetAside && o.setAside !== fSetAside) return false;
      if (fStage && o.stage !== fStage) return false;
      if (fAgency && o.agency !== fAgency) return false;
      if (fElig && o.eligibility?.status !== fElig) return false;
      if (fPriority && o.priority?.label !== fPriority) return false;
      if (fFit && o.fitComputed?.band !== fFit) return false;
      if (fPwin && o.pwinView?.band !== fPwin) return false;
      if (fDecision && (o.decision?.call || "TBD") !== fDecision) return false;
      if (watchOnly && !o.watch) return false;
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
    list = [...list].sort((a, b) => {
      for (const { key, dir } of sortStack) {
        const col = COL_BY_KEY[key];
        if (!col) continue;
        let av = col.sortVal(a), bv = col.sortVal(b);
        if (typeof av === "string") av = av.toLowerCase();
        if (typeof bv === "string") bv = bv.toLowerCase();
        if (av < bv) return dir === "asc" ? -1 : 1;
        if (av > bv) return dir === "asc" ? 1 : -1;
      }
      return 0;
    });
    return list;
  }, [opps, q, fVehicle, fSetAside, fStage, fStatus, fAgency, fAwardMin, fDueWithin,
      fElig, fPriority, fFit, fPwin, fDecision, watchOnly, hideClosed, sortStack]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSort = (key, additive) => {
    setSortStack((stack) => {
      const existing = stack.find((s) => s.key === key);
      if (additive) {
        if (existing) {
          return stack.map((s) => (s.key === key ? { ...s, dir: s.dir === "asc" ? "desc" : "asc" } : s));
        }
        return [...stack, { key, dir: "asc" }];
      }
      if (existing && stack.length === 1) {
        return [{ key, dir: existing.dir === "asc" ? "desc" : "asc" }];
      }
      return [{ key, dir: "asc" }];
    });
  };

  const toggleSelect = (id) => setSelected((s) => {
    const next = new Set(s);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const allSelected = filtered.length > 0 && filtered.every((o) => selected.has(o.id));
  const toggleSelectAll = () =>
    setSelected(allSelected ? new Set() : new Set(filtered.map((o) => o.id)));

  const bulk = async (fn, label) => {
    const ids = [...selected];
    try {
      await Promise.all(ids.map(fn));
      toast.success(`${label} — ${ids.length} opportunit${ids.length === 1 ? "y" : "ies"}`);
      setSelected(new Set());
      load();
    } catch (err) { toast.error(errMsg(err)); }
  };
  const bulkStage = (stage) => bulk((id) => api.put(`/orgs/${activeOrgId}/opportunities/${id}`, { stage }), `Stage → ${stage}`);
  const bulkOwner = () => {
    const owner = window.prompt("Assign capture owner (name):");
    if (owner == null) return;
    bulk(async (id) => {
      const o = (opps || []).find((x) => x.id === id);
      await api.put(`/orgs/${activeOrgId}/opportunities/${id}`, { capture: { ...(o?.capture || {}), owner } });
    }, `Owner → ${owner || "cleared"}`);
  };
  const bulkWatch = (watch) => bulk((id) => api.put(`/orgs/${activeOrgId}/opportunities/${id}`, { watch }), watch ? "Watchlisted" : "Unwatched");
  const bulkDelete = () => {
    if (!window.confirm(`Delete ${selected.size} selected opportunit${selected.size === 1 ? "y" : "ies"}?`)) return;
    bulk((id) => api.delete(`/orgs/${activeOrgId}/opportunities/${id}`), "Deleted");
  };

  const doExport = (rows) => {
    const cols = visible.map((k) => COL_BY_KEY[k]).filter(Boolean);
    exportCsv(`opportunities-${new Date().toISOString().slice(0, 10)}.csv`,
      cols.map((c) => c.label), rows.map((o) => cols.map((c) => c.csv(o))));
    toast.success(`Exported ${rows.length} rows`);
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

  const visCols = visible.map((k) => COL_BY_KEY[k]).filter(Boolean);
  const drawerOpp = drawerId ? (opps || []).find((o) => o.id === drawerId) : null;
  const selCls = "field !w-auto !py-1 text-xs";

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
          <div className="relative min-w-[180px] flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
            <input className="field !pl-9" placeholder="Search title, sol #, scope, tags, owner…" value={q}
              onChange={(e) => setQ(e.target.value)} data-testid="opp-search" />
          </div>
          <select className={selCls} value={fPriority} onChange={(e) => setFPriority(e.target.value)} data-testid="filter-priority">
            <option value="">Priority: all</option>
            {["A", "B", "C", "Watch", "Pass"].map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fElig} onChange={(e) => setFElig(e.target.value)} data-testid="filter-eligibility">
            <option value="">Eligibility: all</option>
            {["Eligible", "Conditional", "Ineligible", "Unknown"].map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fFit} onChange={(e) => setFFit(e.target.value)} data-testid="filter-fit">
            <option value="">Fit: all</option>
            {["Strong", "Good", "Conditional", "Poor"].map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fPwin} onChange={(e) => setFPwin(e.target.value)} data-testid="filter-pwin">
            <option value="">PWin: all</option>
            {["High", "Medium", "Low", "Unknown"].map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fDecision} onChange={(e) => setFDecision(e.target.value)} data-testid="filter-decision">
            <option value="">Decision: all</option>
            {["TBD", "Bid", "No-Bid", "Rebuild", "Watch"].map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fStatus} onChange={(e) => setFStatus(e.target.value)} data-testid="filter-status">
            <option value="active">Active (open + pre-release)</option>
            <option value="open">Open</option>
            <option value="pre-release">Pre-release</option>
            <option value="closed">Closed / expired</option>
            <option value="all">All statuses</option>
          </select>
          <select className={selCls} value={fAgency} onChange={(e) => setFAgency(e.target.value)} data-testid="filter-agency">
            <option value="">All agencies</option>{agencies.map((a) => <option key={a}>{a}</option>)}
          </select>
          <select className={selCls} value={fVehicle} onChange={(e) => setFVehicle(e.target.value)} data-testid="filter-vehicle">
            <option value="">All vehicles</option>{VEHICLES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fSetAside} onChange={(e) => setFSetAside(e.target.value)} data-testid="filter-setaside">
            <option value="">All set-asides</option>{SETASIDES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fStage} onChange={(e) => setFStage(e.target.value)} data-testid="filter-stage">
            <option value="">All stages</option>{STAGES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select className={selCls} value={fAwardMin} onChange={(e) => setFAwardMin(Number(e.target.value))} data-testid="filter-award">
            <option value={0}>Any award $</option>
            <option value={100000}>≥ $100K</option>
            <option value={1000000}>≥ $1M</option>
            <option value={5000000}>≥ $5M</option>
            <option value={10000000}>≥ $10M</option>
          </select>
          <select className={selCls} value={fDueWithin} onChange={(e) => setFDueWithin(Number(e.target.value))} data-testid="filter-due">
            <option value={0}>Any due date</option>
            <option value={7}>Due ≤ 7 days</option>
            <option value={30}>Due ≤ 30 days</option>
            <option value={90}>Due ≤ 90 days</option>
          </select>
          <label className="flex items-center gap-1.5 text-xs text-dim">
            <input type="checkbox" checked={watchOnly} onChange={(e) => setWatchOnly(e.target.checked)} data-testid="watch-only" />
            <Star size={11} className="text-warn" /> Watchlist
          </label>
          <label className="flex items-center gap-2 text-xs text-dim">
            <input type="checkbox" checked={hideClosed} onChange={(e) => setHideClosed(e.target.checked)} data-testid="hide-closed" />
            Hide closed
          </label>
          <div className="relative ml-auto flex gap-2">
            <button className="btn btn-ghost !px-2.5 !py-1 text-xs" onClick={() => doExport(filtered)} data-testid="export-csv">
              <Download size={13} /> CSV
            </button>
            <button className="btn btn-ghost !px-2.5 !py-1 text-xs" onClick={() => setShowCols((s) => !s)} data-testid="columns-button">
              <Columns3 size={13} /> Columns
            </button>
            {showCols && (
              <ColumnChooser visible={visible} setVisible={setVisible} views={views}
                onSaveView={saveView} onApplyView={setVisible} onClose={() => setShowCols(false)} />
            )}
          </div>
        </div>
        <div className="mt-2 text-[11px] text-faint">
          {filtered.length} of {(opps || []).length} opportunities · click a row for 30-second qualification · shift-click headers for multi-sort
        </div>
      </Card>

      {editor && selected.size > 0 && (
        <Card className="flex flex-wrap items-center gap-2 border-cyan/40 p-3" data-testid="bulk-bar">
          <span className="text-xs text-cyan">{selected.size} selected</span>
          <select className={selCls} defaultValue="" onChange={(e) => { if (e.target.value) bulkStage(e.target.value); e.target.value = ""; }} data-testid="bulk-stage">
            <option value="" disabled>Set stage…</option>
            {STAGES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <button className="btn btn-ghost !px-2.5 !py-1 text-xs" onClick={bulkOwner} data-testid="bulk-owner">Assign owner</button>
          <button className="btn btn-ghost !px-2.5 !py-1 text-xs" onClick={() => bulkWatch(true)} data-testid="bulk-watch"><Star size={12} /> Watch</button>
          <button className="btn btn-ghost !px-2.5 !py-1 text-xs" onClick={() => doExport(filtered.filter((o) => selected.has(o.id)))} data-testid="bulk-export"><Download size={12} /> Export</button>
          <button className="btn btn-ghost !px-2.5 !py-1 text-xs !text-bad" onClick={bulkDelete} data-testid="bulk-delete"><Trash2 size={12} /> Delete</button>
          <button className="ml-auto text-xs text-faint hover:text-ink" onClick={() => setSelected(new Set())}>Clear</button>
        </Card>
      )}

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
                  {editor && (
                    <th className="w-8 px-2 py-2.5">
                      <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} data-testid="select-all" />
                    </th>
                  )}
                  {visCols.map((c) => {
                    const si = sortStack.findIndex((s) => s.key === c.key);
                    return (
                      <th key={c.key}
                        className={`cursor-pointer select-none px-3 py-2.5 text-left font-medium hover:text-ink ${c.minW} ${c.right ? "text-right" : ""}`}
                        onClick={(e) => toggleSort(c.key, e.shiftKey)} data-testid={`sort-${c.key}`}
                        title="Click to sort · shift-click to add secondary sort">
                        <span className="inline-flex items-center gap-1">
                          {c.label}
                          <ArrowUpDown size={11} className={si >= 0 ? "text-cyan" : "text-faint"} />
                          {si >= 0 && sortStack.length > 1 && <span className="text-[9px] text-cyan">{si + 1}</span>}
                        </span>
                      </th>
                    );
                  })}
                  {editor && <th className="px-2 py-2.5"></th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((o) => (
                  <tr key={o.id} onClick={() => setDrawerId(o.id)}
                    className={`cursor-pointer border-b border-line/60 align-top transition-colors hover:bg-white/5 ${drawerId === o.id ? "bg-white/5" : ""}`}
                    data-testid={`opp-row-${o.id}`}>
                    {editor && (
                      <td className="px-2 py-3" onClick={(e) => e.stopPropagation()}>
                        <input type="checkbox" checked={selected.has(o.id)} onChange={() => toggleSelect(o.id)}
                          data-testid={`select-${o.id}`} />
                      </td>
                    )}
                    {visCols.map((c) => (
                      <td key={c.key} className={`px-3 py-3 ${c.right ? "text-right" : ""}`}>
                        {c.render(o, { toggleWatch })}
                      </td>
                    ))}
                    {editor && (
                      <td className="px-2 py-3 text-right">
                        <button onClick={(e) => del(e, o)} className="text-faint hover:text-bad" data-testid={`delete-opp-${o.id}`}>
                          <Trash2 size={15} />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {drawerOpp && (
        <OppDrawer opp={drawerOpp} orgId={activeOrgId} editor={editor}
          onSaved={patchRow} onClose={() => setDrawerId(null)} />
      )}

      <CreateModal open={showCreate} onClose={() => setShowCreate(false)} orgId={activeOrgId}
        onCreated={(d) => setOpps((p) => [d, ...(p || [])])} />

      <AIChatButton
        contextTitle="Federal Opportunities pipeline"
        contextText={(opps || []).slice(0, 30).map((o) =>
          `- ${o.title} · ${o.solNumber || "no-sol"} · ${o.agency || "?"} · fit=${o.fit?.overall ?? "—"} · due ${o.dueDate || "?"}`
        ).join("\n")}
        suggestions={[
          "Which of these has the strongest fit for us right now?",
          "Group these by agency and rank by pWin.",
          "Draft a go/no-go rationale for the top 3.",
        ]}
      />
    </PageReveal>
  );
}
