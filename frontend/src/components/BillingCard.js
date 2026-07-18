import React, { useState } from "react";
import { Link } from "react-router-dom";
import { CreditCard, ExternalLink, Sparkles, Rocket, Building2, RefreshCcw } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useSubscription } from "../lib/billing";
import { Card, SectionLabel, Pill, Spinner, Field, Modal } from "./ui";

const TIER_LABEL = {
  free: { name: "Free", tone: "neutral", icon: CreditCard,
    desc: "No active plan. Drafting, disk storage, and the AI chat assistant are locked." },
  oi: { name: "Opportunity Intelligence", tone: "cyan", icon: Sparkles,
    desc: "Federal opportunities + competitive analysis + private-capital and accelerator scans. Upgrade to Full for drafting, disk storage, and AI chat." },
  full: { name: "Full Capture & Proposal Generation", tone: "ok", icon: Rocket,
    desc: "Everything is unlocked, including drafting, disk storage, AI chat, and Overleaf sync." },
  enterprise: { name: "Enterprise", tone: "violet", icon: Building2,
    desc: "GovCloud-hosted deployment with CUI/ITAR support and full agentic workflows." },
};

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined,
    { year: "numeric", month: "short", day: "numeric" });
}

export default function BillingCard() {
  const { sub, loading, refresh } = useSubscription();
  const [busy, setBusy] = useState(null);
  const [refundOpen, setRefundOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (loading || !sub) return null;
  const info = TIER_LABEL[sub.tier] || TIER_LABEL.free;
  const Icon = info.icon;

  const goPortal = async () => {
    setBusy("portal");
    try {
      const { data } = await api.post("/payments/portal",
        { returnUrl: `${window.location.origin}/settings` });
      if (data?.url) window.location.href = data.url;
    } catch (e) { toast.error(errMsg(e)); setBusy(null); }
  };

  const submitRefund = async () => {
    setBusy("refund");
    try {
      await api.post("/refund-requests", { reason });
      toast.success("Refund request submitted",
        { description: "CaptureAgent will review and reply by email." });
      setRefundOpen(false); setReason("");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(null); }
  };

  return (
    <Card className="p-5" data-testid="billing-card">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <CreditCard size={16} className="text-cyan" />
          <SectionLabel>Billing</SectionLabel>
        </div>
        <button onClick={refresh} className="btn btn-ghost !py-1 !px-2 text-xs"
                data-testid="billing-refresh"><RefreshCcw size={12} /> Refresh</button>
      </div>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Icon size={18} className="text-cyan" />
            <div className="text-lg font-semibold text-ink" data-testid="billing-tier-name">
              {info.name}
            </div>
            <Pill tone={info.tone}>{sub.status}</Pill>
            {sub.interval && sub.tier !== "free" && (
              <Pill tone="neutral">{sub.interval === "year" ? "Yearly" : "Monthly"}</Pill>
            )}
            {sub.cancelAtPeriodEnd && <Pill tone="warn">cancels at period end</Pill>}
          </div>
          <p className="mt-1 text-xs text-faint">{info.desc}</p>
          {sub.currentPeriodEnd && (
            <p className="mt-1 text-xs text-dim">
              Current period ends: <span className="text-ink">{fmtDate(sub.currentPeriodEnd)}</span>
            </p>
          )}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {sub.tier === "free" && (
          <Link to="/pricing" className="btn btn-primary"
                data-testid="billing-upgrade-btn">
            <Sparkles size={15} /> Choose a plan
          </Link>
        )}
        {sub.tier === "oi" && (
          <Link to="/pricing" className="btn btn-primary"
                data-testid="billing-upgrade-btn">
            <Rocket size={15} /> Upgrade to Full
          </Link>
        )}
        {sub.tier !== "free" && (
          <>
            <button onClick={goPortal} disabled={busy === "portal"}
                    className="btn btn-ghost" data-testid="billing-portal-btn">
              {busy === "portal" ? <Spinner /> : <ExternalLink size={15} />}
              Manage in Stripe
            </button>
            <button onClick={() => setRefundOpen(true)}
                    className="btn btn-ghost" data-testid="billing-refund-btn">
              Request refund
            </button>
          </>
        )}
      </div>

      <Modal open={refundOpen} onClose={() => !busy && setRefundOpen(false)}
             title="Request a refund" maxW="max-w-lg">
        <div className="space-y-3 text-sm" data-testid="refund-modal">
          <p className="text-dim">
            Refunds are reviewed by CaptureAgent (usually within 1 business
            day). Full refunds are honored within the first 14 days; partial
            refunds are considered case-by-case.
          </p>
          <Field label="Reason (optional)">
            <textarea className="field" rows={4} value={reason}
                      maxLength={1000}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="What happened? What would make it right?"
                      data-testid="refund-reason" />
          </Field>
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn btn-ghost" onClick={() => setRefundOpen(false)}
                    disabled={busy === "refund"} data-testid="refund-cancel">
              Cancel
            </button>
            <button className="btn btn-primary" onClick={submitRefund}
                    disabled={busy === "refund"} data-testid="refund-submit">
              {busy === "refund" ? <Spinner /> : "Send request"}
            </button>
          </div>
        </div>
      </Modal>
    </Card>
  );
}
