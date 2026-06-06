import React, { useEffect, useState } from "react";
import { Save, KeyRound, Lock, Settings as SettingsIcon } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, Field } from "../components/ui";

export default function Settings() {
  const { activeOrgId, activeOrg } = useAuth();
  const [org, setOrg] = useState(null);
  const [secrets, setSecrets] = useState(null);
  const [anthropic, setAnthropic] = useState("");
  const [sam, setSam] = useState("");
  const [savingOrg, setSavingOrg] = useState(false);
  const [savingKeys, setSavingKeys] = useState(false);

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}`).then((r) => setOrg(r.data)).catch(() => {});
    api.get(`/orgs/${activeOrgId}/secrets`).then((r) => setSecrets(r.data)).catch(() => {});
  }, [activeOrgId]);

  const saveOrg = async () => {
    setSavingOrg(true);
    try {
      await api.put(`/orgs/${activeOrgId}`, {
        name: org.name,
        naics: (Array.isArray(org.naics) ? org.naics : String(org.naics).split(",")).map((s) => String(s).trim()).filter(Boolean),
        keywords: (Array.isArray(org.keywords) ? org.keywords : String(org.keywords).split(",")).map((s) => String(s).trim()).filter(Boolean),
      });
      toast.success("Organization updated");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSavingOrg(false); }
  };

  const saveKeys = async () => {
    setSavingKeys(true);
    try {
      const { data } = await api.put(`/orgs/${activeOrgId}/secrets`, {
        anthropicKey: anthropic || null, samKey: sam || null,
      });
      setSecrets(data);
      setAnthropic(""); setSam("");
      toast.success("API keys saved (encrypted)", {
        description: `Anthropic: ${data.validation.anthropic} · SAM: ${data.validation.sam}`,
      });
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSavingKeys(false); }
  };

  if (!org || !secrets) return <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>;

  return (
    <PageReveal className="max-w-3xl space-y-5">
      <div><SectionLabel>Settings</SectionLabel><h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-ink"><SettingsIcon size={22} className="text-cyan" /> Organization Settings</h1></div>

      <Card className="p-5">
        <SectionLabel>Organization</SectionLabel>
        <div className="mt-4 space-y-4">
          <Field label="Name"><input className="field" value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} data-testid="settings-org-name" /></Field>
          <Field label="NAICS codes" hint="Comma-separated. Used by SAM/Grants pulls."><input className="field" value={Array.isArray(org.naics) ? org.naics.join(", ") : org.naics} onChange={(e) => setOrg({ ...org, naics: e.target.value })} data-testid="settings-naics" /></Field>
          <Field label="Default keywords" hint="Comma-separated."><input className="field" value={Array.isArray(org.keywords) ? org.keywords.join(", ") : org.keywords} onChange={(e) => setOrg({ ...org, keywords: e.target.value })} data-testid="settings-keywords" /></Field>
          <div className="flex justify-end"><button className="btn btn-primary" onClick={saveOrg} disabled={savingOrg} data-testid="save-org-settings">{savingOrg ? <Spinner /> : <Save size={16} />} Save org</button></div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2"><KeyRound size={16} className="text-cyan" /><SectionLabel>API Keys (server-only secrets)</SectionLabel></div>
        <div className="mt-2 flex items-start gap-2 rounded-lg border border-line bg-white/5 p-3 text-xs text-faint">
          <Lock size={13} className="mt-0.5 shrink-0 text-ok" />
          Keys are encrypted at rest and never returned to the browser in full — only a masked preview. They are used server-side for the AI verify &amp; SAM pull. Validation is currently mocked (Phase 5 wires live calls).
        </div>
        <div className="mt-4 space-y-4">
          <Field label="Anthropic API key" hint={secrets.anthropicSet ? `Currently set: ${secrets.anthropicKey}` : "Not set"}>
            <input className="field mono" value={anthropic} onChange={(e) => setAnthropic(e.target.value)} placeholder={secrets.anthropicSet ? "•••••••• (enter new to replace)" : "sk-ant-…"} data-testid="anthropic-key" />
          </Field>
          <Field label="SAM.gov API key" hint={secrets.samSet ? `Currently set: ${secrets.samKey}` : "Not set"}>
            <input className="field mono" value={sam} onChange={(e) => setSam(e.target.value)} placeholder={secrets.samSet ? "•••••••• (enter new to replace)" : "32-char SAM key"} data-testid="sam-key" />
          </Field>
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Pill tone={secrets.anthropicSet ? "ok" : "neutral"}>Anthropic {secrets.anthropicSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.samSet ? "ok" : "neutral"}>SAM {secrets.samSet ? "set" : "unset"}</Pill>
            </div>
            <button className="btn btn-primary" onClick={saveKeys} disabled={savingKeys || (!anthropic && !sam)} data-testid="save-keys">{savingKeys ? <Spinner /> : <Save size={16} />} Save keys</button>
          </div>
        </div>
      </Card>

      <Card className="p-5 border-warn/20">
        <SectionLabel>Data Sensitivity</SectionLabel>
        <p className="mt-2 text-xs text-faint">This workspace holds <b>unclassified</b> pipeline metadata only. Do not store CUI or ITAR-controlled technical data here — that requires a separate, controlled environment.</p>
      </Card>
    </PageReveal>
  );
}
