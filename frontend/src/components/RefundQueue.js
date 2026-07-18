import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Wallet, CheckCircle2, XCircle } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useSubscription } from "../lib/billing";
import { Card, Pill, Spinner, EmptyState, Modal, Field } from "./ui";

function fmt(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined,
    { year: "numeric", month: "short", day: "numeric",
      hour: "numeric", minute: "2-digit" });
}

function money(cents) {
  if (!cents) return "$0.00";
  return `$${(cents / 100).toFixed(2)}`;
}

// Only rendered inside Admin.js for the CaptureAgent platform owner (checked
// server-side via /api/refund-requests). Non-owners hit 403 and we hide the
// table entirely.
export default function RefundQueue() {
  const { sub } = useSubscription();
  const [rows, setRows] = useState(null);
  const [status, setStatus] = useState("pending");
  const [modal, setModal] = useState(null); // { req, action }
  const [amountCents, setAmountCents] = useState("");
  const [adminNotes, setAdminNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    setRows(null);
    api.get(`/refund-requests?status=${status}`)
      .then((r) => setRows(r.data))
      .catch(() => setRows([]));
  };

  useEffect(() => {
    if (!sub?.isPlatformOwner) return;
    load();
  }, [status, sub?.isPlatformOwner]);

  if (!sub || !sub.isPlatformOwner) return null;

  const open = (req, action) => {
    setModal({ req, action });
    setAmountCents(""); setAdminNotes("");
  };

  const submit = async () => {
    if (!modal) return;
    setBusy(true);
    try {
      const path = modal.action === "approve"
        ? `/refund-requests/${modal.req.id}/approve`
        : `/refund-requests/${modal.req.id}/deny`;
      const payload = { adminNotes };
      if (modal.action === "approve" && amountCents.trim()) {
        const n = parseInt(amountCents, 10);
        if (!Number.isFinite(n) || n <= 0) throw new Error("Amount must be a positive integer (in cents)");
        payload.amountCents = n;
      }
      await api.post(path, payload);
      toast.success(modal.action === "approve" ? "Refund approved & issued" : "Refund denied");
      setModal(null);
      load();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };

  return (
    <Card className="overflow-hidden" data-testid="refund-queue">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <Wallet size={16} className="text-cyan" />
          <div className="text-sm font-semibold text-ink">Refund requests</div>
        </div>
        <select
          className="field !py-1 !w-auto text-xs"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          data-testid="refund-status-filter"
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="denied">Denied</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      {rows === null ? (
        <div className="p-4"><Spinner className="text-cyan" /></div>
      ) : rows.length === 0 ? (
        <EmptyState icon={Wallet} title="No refund requests" subtitle={`Nothing in the ${status} queue.`} />
      ) : (
        <table className="w-full text-sm" data-testid="refunds-table">
          <thead className="bg-elev/60 text-xs text-dim">
            <tr className="border-b border-line">
              <th className="px-4 py-2.5 text-left">Requested</th>
              <th className="px-4 py-2.5 text-left">Email</th>
              <th className="px-4 py-2.5 text-left">Reason</th>
              <th className="px-4 py-2.5 text-left">Amount</th>
              <th className="px-4 py-2.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-line/60" data-testid={`refund-row-${r.id}`}>
                <td className="px-4 py-3 mono text-xs text-faint">{fmt(r.requestedAt)}</td>
                <td className="px-4 py-3 text-dim">{r.email}</td>
                <td className="px-4 py-3 text-dim max-w-[280px]"><div className="line-clamp-2">{r.reason || <span className="text-faint">—</span>}</div></td>
                <td className="px-4 py-3">
                  {r.amountCentsRefunded > 0
                    ? <Pill tone="ok">refunded {money(r.amountCentsRefunded)}</Pill>
                    : <Pill tone="neutral">full refund</Pill>}
                </td>
                <td className="px-4 py-3 text-right">
                  {status === "pending" ? (
                    <div className="flex justify-end gap-2">
                      <button className="btn btn-primary !py-1 !px-2 text-xs"
                              onClick={() => open(r, "approve")}
                              data-testid={`refund-approve-${r.id}`}>
                        <CheckCircle2 size={13} /> Approve
                      </button>
                      <button className="btn btn-ghost !py-1 !px-2 text-xs text-bad"
                              onClick={() => open(r, "deny")}
                              data-testid={`refund-deny-${r.id}`}>
                        <XCircle size={13} /> Deny
                      </button>
                    </div>
                  ) : (
                    <span className="text-xs text-faint">{fmt(r.decidedAt)}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal open={!!modal} onClose={() => !busy && setModal(null)}
             title={modal?.action === "approve" ? "Approve refund" : "Deny refund"}>
        <div className="space-y-3 text-sm" data-testid="refund-decision-modal">
          {modal?.action === "approve" ? (
            <>
              <p className="text-dim">
                By default we issue a <b>full refund</b> against the last
                payment on file. Enter an amount in <b>cents</b> to issue a
                partial refund instead.
              </p>
              <Field label="Partial refund amount (in cents) — leave blank for full refund">
                <input className="field mono" value={amountCents}
                       onChange={(e) => setAmountCents(e.target.value)}
                       placeholder="e.g. 4900 for $49.00"
                       inputMode="numeric"
                       data-testid="refund-amount-cents" />
              </Field>
            </>
          ) : (
            <p className="text-dim">Deny this refund. The user will see the note if they contact us.</p>
          )}
          <Field label="Admin note (optional)">
            <textarea className="field" rows={3} value={adminNotes}
                      maxLength={1000}
                      onChange={(e) => setAdminNotes(e.target.value)}
                      data-testid="refund-admin-notes" />
          </Field>
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn btn-ghost" onClick={() => setModal(null)}
                    disabled={busy}>Cancel</button>
            <button className="btn btn-primary" onClick={submit} disabled={busy}
                    data-testid="refund-decision-submit">
              {busy ? <Spinner /> : modal?.action === "approve" ? "Approve & refund" : "Deny"}
            </button>
          </div>
        </div>
      </Modal>
    </Card>
  );
}
