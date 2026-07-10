import React, { useEffect, useState } from "react";
import { UserPlus, Trash2, Crown, ScrollText, Users, KeyRound, Copy, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, Modal, Field, EmptyState } from "../components/ui";
import { fmtDateTime, isOwner } from "../lib/helpers";

const ROLES = ["viewer", "editor", "technical_writer", "proposal_writer", "pi",
               "capture_manager", "admin", "subcontractor"];
const roleLabel = (r) => r.replace(/_/g, " ");

const CAP_SECTIONS = [
  ["summary", "Title, abstract & executive summary"],
  ["sow", "Statement of Work"],
  ["wbs", "WBS & schedule"],
  ["budget", "Budget"],
];

/* Per-resource access grants for a subcontractor member. */
function AccessModal({ member, orgId, onClose }) {
  const [opps, setOpps] = useState([]);
  const [oppId, setOppId] = useState("");
  const [docs, setDocs] = useState([]);
  const [grants, setGrants] = useState({}); // key `${type}:${id}` -> none|read|write
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!member) return;
    api.get(`/orgs/${orgId}/opportunities`).then((r) => setOpps(r.data)).catch(() => setOpps([]));
    setOppId(""); setDocs([]); setGrants({});
  }, [member, orgId]);

  useEffect(() => {
    if (!member || !oppId) return;
    Promise.all([
      api.get(`/orgs/${orgId}/opportunities/${oppId}/proposal`).catch(() => ({ data: null })),
      api.get(`/orgs/${orgId}/members/${member.id}/grants`).catch(() => ({ data: [] })),
    ]).then(([prop, gr]) => {
      setDocs(prop.data?.documents || []);
      const map = {};
      (gr.data || []).filter((g) => g.opportunityId === oppId).forEach((g) => {
        map[`${g.resourceType}:${g.resourceId}`] = g.access;
      });
      setGrants(map);
    });
  }, [member, oppId, orgId]);

  if (!member) return null;
  const setG = (key, v) => setGrants((g) => ({ ...g, [key]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const list = Object.entries(grants)
        .filter(([, v]) => v === "read" || v === "write")
        .map(([k, v]) => {
          const [resourceType, ...rest] = k.split(":");
          return { resourceType, resourceId: rest.join(":"), access: v };
        });
      await api.put(`/orgs/${orgId}/members/${member.id}/grants`,
        { opportunityId: oppId, grants: list });
      toast.success(`Access updated — ${list.length} item(s) shared with ${member.email}`);
      onClose();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  const Row = ({ k, label }) => (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-line bg-white/5 px-3 py-2">
      <span className="text-sm text-dim">{label}</span>
      <select className="field !w-auto !py-1 text-xs" value={grants[k] || "none"}
              onChange={(e) => setG(k, e.target.value)} data-testid={`grant-${k}`}>
        <option value="none">No access</option>
        <option value="read">Read only</option>
        <option value="write">Read & write</option>
      </select>
    </div>
  );

  return (
    <Modal open={!!member} onClose={onClose} title={`Shared access — ${member.email}`}>
      <p className="mb-3 text-xs text-faint">
        Subcontractors see only what you share here — nothing else in the workspace.
      </p>
      <Field label="Opportunity / proposal">
        <select className="field" value={oppId} onChange={(e) => setOppId(e.target.value)} data-testid="access-opp">
          <option value="">Select an opportunity…</option>
          {opps.map((o) => <option key={o.id} value={o.id}>{o.title}</option>)}
        </select>
      </Field>
      {oppId && (
        <div className="mt-3 space-y-2">
          <div className="label-mono">Capability sections</div>
          {CAP_SECTIONS.map(([k, label]) => (
            <Row key={k} k={`capability_section:${k}`} label={label} />
          ))}
          <div className="label-mono mt-3">Proposal volumes</div>
          {docs.length === 0 && <p className="text-xs text-faint">No proposal package yet for this opportunity.</p>}
          {docs.map((d) => (
            <Row key={d.id} k={`proposal_doc:${d.id}`} label={d.title} />
          ))}
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" onClick={save} disabled={saving} data-testid="save-access">
              {saving ? <Spinner /> : "Save access"}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}

function PendingApproval({ m, orgId, onDone }) {
  const [role, setRole] = useState("proposal_writer");
  const [busy, setBusy] = useState(false);
  const approve = async () => {
    setBusy(true);
    try {
      await api.post(`/orgs/${orgId}/members/${m.id}/approve`, { role });
      toast.success(`${m.email} approved as ${roleLabel(role)}`);
      onDone();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="flex items-center justify-end gap-2">
      <select className="field !py-1 !w-auto" value={role} onChange={(e) => setRole(e.target.value)}
              data-testid={`approve-role-${m.email}`}>
        {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
      </select>
      <button className="btn btn-primary !py-1 !px-3 text-xs" onClick={approve} disabled={busy}
              data-testid={`approve-${m.email}`}>
        {busy ? <Spinner /> : "Approve"}
      </button>
    </div>
  );
}

function EditRequestsCard({ orgId }) {
  const [reqs, setReqs] = useState(null);
  const load = () => api.get(`/orgs/${orgId}/profile/edit-requests`).then((r) => setReqs(r.data)).catch(() => setReqs([]));
  useEffect(() => { if (orgId) load(); }, [orgId]); // eslint-disable-line react-hooks/exhaustive-deps
  const decide = async (r, approve) => {
    try {
      await api.post(`/orgs/${orgId}/profile/edit-requests/${r.id}/decide`, { approve });
      toast.success(approve ? "Edit window granted (24h)" : "Request denied");
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const pending = (reqs || []).filter((r) => r.status === "pending");
  if (!pending.length) return null;
  return (
    <Card className="p-5" data-testid="edit-requests-card">
      <SectionLabel>Entity Info Edit Requests</SectionLabel>
      <p className="mt-1 text-xs text-faint">Capture managers asking for a 24-hour window to edit company/entity info.</p>
      <div className="mt-3 space-y-2">
        {pending.map((r) => (
          <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-white/5 px-3 py-2">
            <div className="text-sm text-ink">{r.requesterName || r.requesterEmail}
              <span className="ml-2 text-xs text-faint">{r.requesterEmail}</span></div>
            <div className="flex gap-2">
              <button className="btn btn-primary !py-1 !px-3 text-xs" onClick={() => decide(r, true)} data-testid={`edit-req-approve-${r.id}`}>Grant 24h</button>
              <button className="btn btn-ghost !py-1 !px-3 text-xs" onClick={() => decide(r, false)} data-testid={`edit-req-deny-${r.id}`}>Deny</button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function JoinCodeCard({ orgId }) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/orgs/${orgId}/join-code`).then((r) => setCode(r.data.joinCode)).catch(() => {}); }, [orgId]);
  const copy = () => { navigator.clipboard?.writeText(code); toast.success("Join code copied"); };
  const rotate = async () => {
    if (!window.confirm("Rotate join code? The old code stops working immediately.")) return;
    setBusy(true);
    try { const { data } = await api.post(`/orgs/${orgId}/join-code/rotate`); setCode(data.joinCode); toast.success("New join code generated"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Card className="p-5" data-testid="join-code-card">
      <div className="flex items-center gap-2"><KeyRound size={16} className="text-cyan" /><SectionLabel>Organization Join Code</SectionLabel></div>
      <p className="mt-1 text-xs text-faint">Share this code so teammates can self-join as Viewer (Org switcher → “Join with code”). Rotate to revoke access.</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <code className="mono rounded-lg border border-line bg-white/5 px-4 py-2 text-lg tracking-[0.3em] text-cyan" data-testid="join-code-value">{code || "—"}</code>
        <button className="btn btn-ghost" onClick={copy} data-testid="join-code-copy"><Copy size={15} /> Copy</button>
        <button className="btn btn-ghost" onClick={rotate} disabled={busy} data-testid="join-code-rotate">{busy ? <Spinner /> : <RefreshCw size={15} />} Rotate</button>
      </div>
    </Card>
  );
}

function InviteModal({ open, onClose, orgId, onDone }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post(`/orgs/${orgId}/members/invite`, { email, role });
      toast.success(`Invited ${email}`, { description: data.status === "invited" ? "Pending — they join on first login." : "Added (existing user)." });
      onDone(); onClose(); setEmail("");
    } catch (err) { toast.error(errMsg(err)); }
    finally { setLoading(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title="Invite member">
      <form onSubmit={submit} className="space-y-4" data-testid="invite-form">
        <Field label="Email"><input type="email" className="field" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teammate@company.com" data-testid="invite-email" /></Field>
        <Field label="Role"><select className="field" value={role} onChange={(e) => setRole(e.target.value)} data-testid="invite-role">{ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}</select></Field>
        <div className="flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={loading} data-testid="invite-submit">{loading ? <Spinner /> : "Send invite"}</button></div>
      </form>
    </Modal>
  );
}

export default function Admin() {
  const { activeOrgId, activeOrg } = useAuth();
  const owner = isOwner(activeOrg?.role);
  const [tab, setTab] = useState("members");
  const [members, setMembers] = useState(null);
  const [audit, setAudit] = useState(null);
  const [showInvite, setShowInvite] = useState(false);
  const [accessMember, setAccessMember] = useState(null);

  const loadMembers = () => api.get(`/orgs/${activeOrgId}/members`).then((r) => setMembers(r.data)).catch(() => setMembers([]));

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/members`).then((r) => setMembers(r.data)).catch(() => setMembers([]));
    api.get(`/orgs/${activeOrgId}/audit`).then((r) => setAudit(r.data)).catch(() => setAudit([]));
  }, [activeOrgId]);

  const changeRole = async (m, role) => {
    try { await api.put(`/orgs/${activeOrgId}/members/${m.id}`, { role }); toast.success("Role updated"); loadMembers(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const remove = async (m) => {
    if (!window.confirm(`Remove ${m.email}?`)) return;
    try { await api.delete(`/orgs/${activeOrgId}/members/${m.id}`); toast.success("Removed"); loadMembers(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const transfer = async (m) => {
    if (!window.confirm(`Transfer ownership to ${m.email}? You become Admin.`)) return;
    try { await api.post(`/orgs/${activeOrgId}/members/transfer-ownership`, { membershipId: m.id }); toast.success("Ownership transferred"); loadMembers(); }
    catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <PageReveal className="space-y-5">
      <div className="flex items-center justify-between">
        <div><SectionLabel>Administration</SectionLabel><h1 className="mt-1 text-2xl font-semibold text-ink">Members & Audit</h1></div>
        {tab === "members" && <button className="btn btn-primary" onClick={() => setShowInvite(true)} data-testid="invite-member-button"><UserPlus size={16} /> Invite member</button>}
      </div>

      <div className="flex gap-1 border-b border-line">
        <button onClick={() => setTab("members")} className={`flex items-center gap-2 px-3 py-2 text-sm ${tab === "members" ? "border-b-2 border-cyan text-cyan" : "text-dim hover:text-ink"}`} data-testid="tab-members"><Users size={15} /> Members</button>
        <button onClick={() => setTab("audit")} className={`flex items-center gap-2 px-3 py-2 text-sm ${tab === "audit" ? "border-b-2 border-cyan text-cyan" : "text-dim hover:text-ink"}`} data-testid="tab-audit"><ScrollText size={15} /> Audit Log</button>
      </div>

      {tab === "members" && (
        <div className="space-y-5">
        <EditRequestsCard orgId={activeOrgId} />
        <JoinCodeCard orgId={activeOrgId} />
        <Card className="overflow-hidden">
          {members === null ? <div className="p-4"><Spinner className="text-cyan" /></div> : (
            <table className="w-full text-sm" data-testid="members-table">
              <thead className="bg-elev/60 text-xs text-dim"><tr className="border-b border-line">
                <th className="px-4 py-2.5 text-left">Member</th><th className="px-4 py-2.5 text-left">Status</th>
                <th className="px-4 py-2.5 text-left">Role</th><th className="px-4 py-2.5 text-right">Actions</th>
              </tr></thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id} className="border-b border-line/60" data-testid={`member-row-${m.email}`}>
                    <td className="px-4 py-3"><div className="font-medium text-ink">{m.name || m.email}</div><div className="text-xs text-faint">{m.email}</div></td>
                    <td className="px-4 py-3"><Pill tone={m.status === "active" ? "ok" : "warn"}>{m.status}</Pill></td>
                    <td className="px-4 py-3">
                      {m.role === "owner" ? <Pill tone="cyan" icon={Crown}>owner</Pill>
                        : m.status === "pending" ? <Pill tone="warn">awaiting approval</Pill> : (
                        <select className="field !py-1 !w-auto" value={m.role} onChange={(e) => changeRole(m, e.target.value)} data-testid={`role-select-${m.email}`}>
                          {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
                        </select>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {m.status === "pending" ? (
                        <PendingApproval m={m} orgId={activeOrgId} onDone={loadMembers} />
                      ) : (
                      <div className="flex justify-end gap-2">
                        {m.role === "subcontractor" && <button className="btn btn-ghost !py-1 !px-2 text-xs" onClick={() => setAccessMember(m)} data-testid={`access-${m.email}`}><KeyRound size={13} /> Access</button>}
                        {owner && m.role !== "owner" && m.userId && <button className="btn btn-ghost !py-1 !px-2 text-xs" onClick={() => transfer(m)} data-testid={`transfer-${m.email}`}><Crown size={13} /> Make owner</button>}
                        {m.role !== "owner" && <button onClick={() => remove(m)} className="text-faint hover:text-bad" data-testid={`remove-${m.email}`}><Trash2 size={15} /></button>}
                      </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
        </div>
      )}

      {tab === "audit" && (
        <Card className="overflow-hidden">
          {audit === null ? <div className="p-4"><Spinner className="text-cyan" /></div> : audit.length === 0 ? (
            <EmptyState icon={ScrollText} title="No audit entries yet" />
          ) : (
            <table className="w-full text-sm" data-testid="audit-table">
              <thead className="bg-elev/60 text-xs text-dim"><tr className="border-b border-line">
                <th className="px-4 py-2.5 text-left">When</th><th className="px-4 py-2.5 text-left">Who</th>
                <th className="px-4 py-2.5 text-left">Action</th><th className="px-4 py-2.5 text-left">Target</th>
              </tr></thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id} className="border-b border-line/60">
                    <td className="px-4 py-2.5 mono text-xs text-faint">{fmtDateTime(a.at)}</td>
                    <td className="px-4 py-2.5 text-dim">{a.userName || a.userEmail}</td>
                    <td className="px-4 py-2.5"><Pill tone="violet">{a.action}</Pill></td>
                    <td className="px-4 py-2.5 text-faint">{a.target || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      <InviteModal open={showInvite} onClose={() => setShowInvite(false)} orgId={activeOrgId} onDone={loadMembers} />
      <AccessModal member={accessMember} orgId={activeOrgId} onClose={() => setAccessMember(null)} />
    </PageReveal>
  );
}
