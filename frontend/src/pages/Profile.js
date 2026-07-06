import React, { useEffect, useState } from "react";
import { Save, Building2, ShieldCheck, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Spinner, PageReveal, Field } from "../components/ui";
import { canAdmin } from "../lib/helpers";

const CERTS = [
  ["sba", "Small Business (self-cert)"],
  ["eightA", "8(a)"],
  ["hubzone", "HUBZone"],
  ["sdvosb", "SDVOSB"],
  ["wosb", "WOSB"],
  ["edwosb", "EDWOSB"],
  ["vosb", "VOSB"],
];
const CMMC = ["Level 1", "Level 2", "Level 3", "Not assessed"];

export default function Profile() {
  const { activeOrgId, activeOrg } = useAuth();
  const [p, setP] = useState(null);
  const [saving, setSaving] = useState(false);
  const [requesting, setRequesting] = useState(false);
  // Entity info is admin-managed; a capture manager can hold a 24h edit grant
  // (backend computes canEdit accordingly).
  const admin = p?.canEdit ?? canAdmin(activeOrg?.role);
  const isCM = activeOrg?.role === "capture_manager";

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/profile`).then((r) => setP(r.data || {})).catch(() => setP({}));
  }, [activeOrgId]);

  const requestEdit = async () => {
    setRequesting(true);
    try {
      await api.post(`/orgs/${activeOrgId}/profile/edit-request`);
      setP((x) => ({ ...x, editRequestPending: true }));
      toast.success("Request sent", { description: "Your administrator will approve a 24-hour edit window." });
    } catch (e) { toast.error(errMsg(e)); }
    finally { setRequesting(false); }
  };

  const set = (patch) => setP((x) => ({ ...x, ...patch }));
  const setCert = (k, v) => setP((x) => ({ ...x, certs: { ...(x.certs || {}), [k]: v } }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/orgs/${activeOrgId}/profile`, {
        uei: p.uei || "", cage: p.cage || "", samActive: !!p.samActive, isSmall: !!p.isSmall,
        certs: { sba: false, eightA: false, hubzone: false, sdvosb: false, wosb: false, edwosb: false, vosb: false, ...(p.certs || {}) },
        cmmcLevel: p.cmmcLevel || "Level 1", sprsScore: p.sprsScore ? Number(p.sprsScore) : null,
        sizeNote: p.sizeNote || "", notes: p.notes || "",
        capabilities: p.capabilities || "", pastPerformance: p.pastPerformance || "",
        techFocus: (Array.isArray(p.techFocus) ? p.techFocus : String(p.techFocus || "").split(",")).map((s) => String(s).trim()).filter(Boolean),
        differentiators: p.differentiators || "", commercialization: p.commercialization || "",
        clearances: p.clearances || "",
      });
      toast.success("Profile saved — drives eligibility and AI Fit Score.");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  if (!p) return <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>;

  return (
    <PageReveal className="max-w-4xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <SectionLabel>Company Profile</SectionLabel>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-ink"><Building2 size={22} className="text-cyan" /> {activeOrg?.name}</h1>
        </div>
        {admin ? (
          <button className="btn btn-primary" onClick={save} disabled={saving} data-testid="save-profile">{saving ? <Spinner /> : <Save size={16} />} Save</button>
        ) : isCM ? (
          p.editRequestPending ? (
            <span className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn" data-testid="edit-request-pending">Edit request pending admin approval</span>
          ) : (
            <button className="btn btn-ghost" onClick={requestEdit} disabled={requesting} data-testid="request-edit-access">
              {requesting ? <Spinner /> : <ShieldCheck size={16} />} Request edit access
            </button>
          )
        ) : null}
      </div>

      <Card className="p-5">
        <SectionLabel>Identity</SectionLabel>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="UEI"><input className="field mono" disabled={!admin} value={p.uei || ""} onChange={(e) => set({ uei: e.target.value })} data-testid="profile-uei" /></Field>
          <Field label="CAGE Code"><input className="field mono" disabled={!admin} value={p.cage || ""} onChange={(e) => set({ cage: e.target.value })} data-testid="profile-cage" /></Field>
          <label className="flex items-center gap-2 text-sm text-dim"><input type="checkbox" disabled={!admin} checked={!!p.samActive} onChange={(e) => set({ samActive: e.target.checked })} data-testid="profile-sam-active" /> SAM.gov registration active</label>
          <label className="flex items-center gap-2 text-sm text-dim"><input type="checkbox" disabled={!admin} checked={!!p.isSmall} onChange={(e) => set({ isSmall: e.target.checked })} data-testid="profile-is-small" /> Small business</label>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2"><ShieldCheck size={16} className="text-ok" /><SectionLabel>SBA Certifications Held</SectionLabel></div>
        <p className="mt-1 text-xs text-faint">These drive eligibility coloring on the Opportunities table. Self-certification is not accepted for program set-asides.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
          {CERTS.map(([k, label]) => (
            <label key={k} className="flex items-center gap-2 rounded-lg border border-line bg-white/5 p-3 text-sm text-dim" data-testid={`cert-${k}`}>
              <input type="checkbox" disabled={!admin} checked={!!(p.certs && p.certs[k])} onChange={(e) => setCert(k, e.target.checked)} /> {label}
            </label>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2"><Sparkles size={16} className="text-cyan" /><SectionLabel>Capability Profile — drives AI Fit Score</SectionLabel></div>
        <p className="mt-1 text-xs text-faint">The Intelligence scan uses these to honestly score how well each opportunity fits your organization. The more specific, the sharper the scoring.</p>
        <div className="mt-4 space-y-4">
          <Field label="Core capabilities" hint="What you actually build/deliver."><textarea className="field min-h-[70px]" disabled={!admin} value={p.capabilities || ""} onChange={(e) => set({ capabilities: e.target.value })} placeholder="e.g. EO/IR payload design, edge AI for ISR, autonomous flight software…" data-testid="profile-capabilities" /></Field>
          <Field label="Technology focus areas" hint="Comma-separated."><input className="field" disabled={!admin} value={Array.isArray(p.techFocus) ? p.techFocus.join(", ") : (p.techFocus || "")} onChange={(e) => set({ techFocus: e.target.value })} placeholder="Space Technology, Trusted AI & Autonomy, Hypersonics" data-testid="profile-techfocus" /></Field>
          <Field label="Past performance" hint="Notable contracts, agencies, outcomes."><textarea className="field min-h-[70px]" disabled={!admin} value={p.pastPerformance || ""} onChange={(e) => set({ pastPerformance: e.target.value })} placeholder="e.g. AFWERX Phase II (SpaceWERX), prime on $4M AFRL SBIR…" data-testid="profile-pastperf" /></Field>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Differentiators"><textarea className="field min-h-[60px]" disabled={!admin} value={p.differentiators || ""} onChange={(e) => set({ differentiators: e.target.value })} data-testid="profile-diff" /></Field>
            <Field label="Commercialization strategy"><textarea className="field min-h-[60px]" disabled={!admin} value={p.commercialization || ""} onChange={(e) => set({ commercialization: e.target.value })} data-testid="profile-commercial" /></Field>
          </div>
          <Field label="Clearances / facility" hint="e.g. FCL Secret, staff with TS/SCI."><input className="field" disabled={!admin} value={p.clearances || ""} onChange={(e) => set({ clearances: e.target.value })} data-testid="profile-clearances" /></Field>
        </div>
      </Card>

      <Card className="p-5">
        <SectionLabel>CMMC & Other</SectionLabel>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field label="CMMC Level"><select className="field" disabled={!admin} value={p.cmmcLevel || "Level 1"} onChange={(e) => set({ cmmcLevel: e.target.value })} data-testid="profile-cmmc">{CMMC.map((c) => <option key={c}>{c}</option>)}</select></Field>
          <Field label="SPRS Score"><input type="number" className="field mono" disabled={!admin} value={p.sprsScore ?? ""} onChange={(e) => set({ sprsScore: e.target.value })} data-testid="profile-sprs" /></Field>
          <Field label="Size note"><input className="field" disabled={!admin} value={p.sizeNote || ""} onChange={(e) => set({ sizeNote: e.target.value })} /></Field>
        </div>
        <Field label="Notes" ><textarea className="field mt-2 min-h-[80px]" disabled={!admin} value={p.notes || ""} onChange={(e) => set({ notes: e.target.value })} /></Field>
      </Card>
    </PageReveal>
  );
}
