import React, { useEffect, useState } from "react";
import { UserPlus, Trash2, Crown, ScrollText, Users } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, Modal, Field, EmptyState } from "../components/ui";
import { fmtDateTime, isOwner } from "../lib/helpers";

const ROLES = ["viewer", "editor", "admin"];

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
        <Field label="Role"><select className="field" value={role} onChange={(e) => setRole(e.target.value)} data-testid="invite-role">{ROLES.map((r) => <option key={r} value={r}>{r}</option>)}</select></Field>
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
                      {m.role === "owner" ? <Pill tone="cyan" icon={Crown}>owner</Pill> : (
                        <select className="field !py-1 !w-auto" value={m.role} onChange={(e) => changeRole(m, e.target.value)} data-testid={`role-select-${m.email}`}>
                          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                        </select>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {owner && m.role !== "owner" && m.userId && <button className="btn btn-ghost !py-1 !px-2 text-xs" onClick={() => transfer(m)} data-testid={`transfer-${m.email}`}><Crown size={13} /> Make owner</button>}
                        {m.role !== "owner" && <button onClick={() => remove(m)} className="text-faint hover:text-bad" data-testid={`remove-${m.email}`}><Trash2 size={15} /></button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
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
    </PageReveal>
  );
}
