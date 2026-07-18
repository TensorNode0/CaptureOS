import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Save, KeyRound, Lock, Settings as SettingsIcon, RotateCw, Trash2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, Field, Modal } from "../components/ui";
import { resetAIOptionsCache } from "../components/AIButton";

export default function Settings() {
  const { activeOrgId, activeOrg, user, logout } = useAuth();
  const navigate = useNavigate();
  const [org, setOrg] = useState(null);
  const [secrets, setSecrets] = useState(null);
  const [anthropic, setAnthropic] = useState("");
  const [sam, setSam] = useState("");
  const [openai, setOpenai] = useState("");
  const [gemini, setGemini] = useState("");
  const [emergent, setEmergent] = useState("");
  const [asksage, setAsksage] = useState("");
  const [overleaf, setOverleaf] = useState("");
  const [savingOrg, setSavingOrg] = useState(false);
  const [savingKeys, setSavingKeys] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteEmail, setDeleteEmail] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);

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
        anthropicKey: anthropic || null, samKey: sam || null, openaiKey: openai || null,
        geminiKey: gemini || null,
        emergentKey: emergent || null, asksageKey: asksage || null,
        overleafKey: overleaf || null,
      });
      setSecrets(data);
      setAnthropic(""); setSam(""); setOpenai(""); setGemini(""); setEmergent(""); setAsksage(""); setOverleaf("");
      resetAIOptionsCache(activeOrgId);
      toast.success("API keys saved (encrypted)", {
        description: `Anthropic: ${data.validation.anthropic} · SAM: ${data.validation.sam} · OpenAI: ${data.validation.openai} · Gemini: ${data.validation.gemini} · Emergent: ${data.validation.emergent} · AskSage: ${data.validation.asksage} · Overleaf: ${data.validation.overleaf}`,
      });
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSavingKeys(false); }
  };

  const rotateKey = async () => {
    if (!window.confirm("Rotate this organization's encryption key? Stored API keys are re-encrypted under a brand-new key. Nothing else changes.")) return;
    setRotating(true);
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/secrets/rotate-key`);
      const fresh = await api.get(`/orgs/${activeOrgId}/secrets`);
      setSecrets(fresh.data);
      resetAIOptionsCache(activeOrgId);
      toast.success(`Encryption key rotated (now v${data.keyVersion})`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setRotating(false); }
  };

  const deleteAccount = async () => {
    if (!user?.email) return;
    if ((deleteEmail || "").trim().toLowerCase() !== user.email.toLowerCase()) {
      toast.error("Type your exact email to confirm.");
      return;
    }
    setDeleting(true);
    try {
      const { data } = await api.delete("/auth/me", {
        data: { confirmEmail: deleteEmail.trim(), reason: deleteReason },
      });
      const summary = [];
      if (data.orgsDeleted) summary.push(`${data.orgsDeleted} organization${data.orgsDeleted === 1 ? "" : "s"} deleted`);
      if (data.membershipsDropped) summary.push(`left ${data.membershipsDropped} organization${data.membershipsDropped === 1 ? "" : "s"}`);
      toast.success("Account deleted", { description: summary.join(" · ") || "All your data has been removed." });
      await logout();
      navigate("/home");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setDeleting(false); }
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
          Keys are encrypted at rest and never returned to the browser in full — only a masked preview. They are used <b>live, server-side</b> for the AI Intelligence scan, “Verify &amp; Refresh with AI”, and the SAM/Grants pull.
        </div>
        <div className="mt-4 space-y-4">
          <Field label="Anthropic API key" hint={secrets.anthropicSet ? `Currently set: ${secrets.anthropicKey}` : "Not set"}>
            <input className="field mono" value={anthropic} onChange={(e) => setAnthropic(e.target.value)} placeholder={secrets.anthropicSet ? "•••••••• (enter new to replace)" : "sk-ant-…"} data-testid="anthropic-key" />
          </Field>
          <Field label="SAM.gov API key" hint={secrets.samSet ? `Currently set: ${secrets.samKey}` : "Not set"}>
            <input className="field mono" value={sam} onChange={(e) => setSam(e.target.value)} placeholder={secrets.samSet ? "•••••••• (enter new to replace)" : "32-char SAM key"} data-testid="sam-key" />
          </Field>
          <Field label="OpenAI API key (optional)" hint={secrets.openaiSet ? `Currently set: ${secrets.openaiKey}` : "Not set — enables the ChatGPT drafting engine"}>
            <input className="field mono" value={openai} onChange={(e) => setOpenai(e.target.value)} placeholder={secrets.openaiSet ? "•••••••• (enter new to replace)" : "sk-…"} data-testid="openai-key" />
          </Field>
          <Field label="Google Gemini API key (optional)" hint={secrets.geminiSet ? `Currently set: ${secrets.geminiKey}` : "Not set — enables the Gemini engine (get one at ai.google.dev/apikey)"}>
            <input className="field mono" value={gemini} onChange={(e) => setGemini(e.target.value)} placeholder={secrets.geminiSet ? "•••••••• (enter new to replace)" : "AIza…"} data-testid="gemini-key" />
          </Field>
          <Field label="Overleaf auth token (optional)" hint={secrets.overleafSet ? `Currently set: ${secrets.overleafKey}` : "Not set — enables push/pull of Federal Proposals to Overleaf. Create at overleaf.com → Account → Git Integration."}>
            <input className="field mono" value={overleaf} onChange={(e) => setOverleaf(e.target.value)} placeholder={secrets.overleafSet ? "•••••••• (enter new to replace)" : "olp_…"} data-testid="overleaf-key" />
          </Field>
          <Field label="Emergent universal LLM key (optional)" hint={secrets.emergentSet ? `Currently set: ${secrets.emergentKey}` : "Not set — enables the Emergent drafting engine (routed models)"}>
            <input className="field mono" value={emergent} onChange={(e) => setEmergent(e.target.value)} placeholder={secrets.emergentSet ? "•••••••• (enter new to replace)" : "sk-emergent-…"} data-testid="emergent-key" />
          </Field>
          <Field label="AskSage API key (optional)" hint={secrets.asksageSet ? `Currently set: ${secrets.asksageKey}` : "Not set — enables the AskSage engine (GovCon compliance boundary)"}>
            <input className="field mono" value={asksage} onChange={(e) => setAsksage(e.target.value)} placeholder={secrets.asksageSet ? "•••••••• (enter new to replace)" : "AskSage access token"} data-testid="asksage-key" />
          </Field>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <Pill tone={secrets.anthropicSet ? "ok" : "neutral"}>Anthropic {secrets.anthropicSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.samSet ? "ok" : "neutral"}>SAM {secrets.samSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.openaiSet ? "ok" : "neutral"}>OpenAI {secrets.openaiSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.geminiSet ? "ok" : "neutral"}>Gemini {secrets.geminiSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.emergentSet ? "ok" : "neutral"}>Emergent {secrets.emergentSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.overleafSet ? "ok" : "neutral"}>Overleaf {secrets.overleafSet ? "set" : "unset"}</Pill>
              <Pill tone={secrets.asksageSet ? "ok" : "neutral"}>AskSage {secrets.asksageSet ? "set" : "unset"}</Pill>
              {secrets.keyVersion && <Pill tone="violet">encryption key v{secrets.keyVersion}</Pill>}
            </div>
            <div className="flex gap-2">
              <button className="btn btn-ghost" onClick={rotateKey} disabled={rotating} data-testid="rotate-key" title="Re-encrypt stored keys under a new per-org encryption key">
                {rotating ? <Spinner /> : <RotateCw size={15} />} Rotate encryption key
              </button>
              <button className="btn btn-primary" onClick={saveKeys} disabled={savingKeys || (!anthropic && !sam && !openai && !gemini && !emergent && !asksage && !overleaf)} data-testid="save-keys">{savingKeys ? <Spinner /> : <Save size={16} />} Save keys</button>
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-5 border-warn/20">
        <SectionLabel>Data Sensitivity</SectionLabel>
        <p className="mt-2 text-xs text-faint">This workspace holds <b>unclassified</b> pipeline metadata only. Do not store CUI or ITAR-controlled technical data here — that requires a separate, controlled environment.</p>
      </Card>

      {/* Danger zone: hard-delete the signed-in user's account. Solo-owned
          orgs and all their data are wiped; multi-member orgs get ownership
          re-assigned. Requires typing the exact account email to guard against
          accidental clicks. Paid subscriptions cancel automatically once
          Stripe (Phase 2) is wired in. */}
      <Card className="p-5" style={{ borderColor: "rgba(239, 68, 68, 0.35)" }} data-testid="danger-zone">
        <div className="flex items-center gap-2">
          <AlertTriangle size={18} className="text-bad" />
          <SectionLabel>Danger zone — delete account</SectionLabel>
        </div>
        <p className="mt-2 max-w-2xl text-xs text-faint">
          Permanently remove your account, your memberships, and any organization you solely own.
          This clears every opportunity, proposal, capability, competitive report, venture doc,
          and file associated with those organizations. Organizations you share with other members
          survive — ownership is transferred to the next active owner or admin.
          <br /><br />
          <b>This cannot be undone.</b> If you have an active paid subscription, your billing is
          also cancelled and no further charges will be made.
        </p>
        <div className="mt-3">
          <button
            className="btn"
            style={{ background: "rgba(239, 68, 68, 0.12)", color: "#fca5a5", borderColor: "rgba(239, 68, 68, 0.35)" }}
            onClick={() => { setDeleteEmail(""); setDeleteReason(""); setDeleteOpen(true); }}
            data-testid="delete-account-open"
          >
            <Trash2 size={15} /> Delete my account
          </button>
        </div>
      </Card>

      <Modal open={deleteOpen} onClose={() => !deleting && setDeleteOpen(false)} title="Delete your CaptureAgent account" maxW="max-w-lg">
        <div className="space-y-3 text-sm" data-testid="delete-account-modal">
          <div className="rounded-md border p-3 text-xs"
               style={{ borderColor: "rgba(239, 68, 68, 0.35)", background: "rgba(239, 68, 68, 0.08)" }}>
            <b className="text-bad">This is permanent.</b>
            <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-dim">
              <li>Organizations you solely own are wiped, along with every record inside.</li>
              <li>Shared organizations survive — ownership passes to the next active member.</li>
              <li>Your Supabase login and email are released for reuse.</li>
              <li>Any active paid subscription is cancelled with no further charges.</li>
            </ul>
          </div>
          <Field label={<>Type <span className="mono text-ink">{user?.email || "your email"}</span> to confirm</>}>
            <input
              className="field mono"
              value={deleteEmail}
              onChange={(e) => setDeleteEmail(e.target.value)}
              placeholder={user?.email || "you@example.com"}
              autoComplete="off"
              data-testid="delete-account-confirm-email"
            />
          </Field>
          <Field label="Why are you leaving? (optional, helps us improve)">
            <textarea
              className="field"
              rows={3}
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              maxLength={500}
              placeholder="Not required."
              data-testid="delete-account-reason"
            />
          </Field>
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn btn-ghost" onClick={() => setDeleteOpen(false)} disabled={deleting} data-testid="delete-account-cancel">
              Cancel
            </button>
            <button
              className="btn"
              style={{ background: "rgba(239, 68, 68, 0.15)", color: "#fca5a5", borderColor: "rgba(239, 68, 68, 0.4)" }}
              onClick={deleteAccount}
              disabled={deleting || !deleteEmail}
              data-testid="delete-account-confirm"
            >
              {deleting ? <Spinner /> : <Trash2 size={15} />}
              Permanently delete my account
            </button>
          </div>
        </div>
      </Modal>
    </PageReveal>
  );
}
