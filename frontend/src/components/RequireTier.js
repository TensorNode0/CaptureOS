import React from "react";
import { Link } from "react-router-dom";
import { Lock, ArrowRight } from "lucide-react";
import { useSubscription, hasTier } from "../lib/billing";
import { Spinner } from "./ui";

// Route wrapper that renders `children` only when the user's subscription
// tier meets `minTier`. Otherwise it shows an upgrade nudge. Assumes the user
// is already authenticated (Protected/route wrapper handles that).
export default function RequireTier({ minTier = "full", children, feature = "This feature" }) {
  const { sub, loading } = useSubscription();

  if (loading || sub === null) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size={20} className="text-cyan" />
      </div>
    );
  }

  if (hasTier(sub, minTier)) {
    return children;
  }

  return (
    <div className="mx-auto max-w-2xl py-16" data-testid="tier-gate">
      <div className="glass p-8 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan/30 bg-cyan/10 text-cyan">
          <Lock size={22} />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-ink">
          Upgrade to Full Capture to unlock {feature}
        </h1>
        <p className="mx-auto mt-3 max-w-md text-sm text-dim">
          Federal Proposals, Investment Deals, and Accelerator Applications
          are part of the <span className="text-ink font-semibold">Full
          Capture</span> plan. You’re currently on <span className="text-ink font-semibold">
          {sub.tier === "free" ? "Free (no active plan)" : sub.tier === "oi" ? "Opportunity Intelligence" : sub.tier}</span>.
        </p>
        <Link to="/pricing"
              className="btn btn-primary mt-6"
              data-testid="tier-gate-upgrade">
          Compare plans <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
