import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, Sparkles, Building2, Rocket, Users } from "lucide-react";
import MarketingLayout from "./MarketingLayout";
import { api, errMsg } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { toast } from "sonner";

// New pricing (Feb 2026):
//   OI     $49.99/user/mo · $479.90/yr (single user)
//   Full   $99.99/user/mo · $2,879.71/yr (bundles up to 3 users)
//   Enterprise  sales-led, no Stripe price
// Yearly discount = 20% off from 12× monthly. Kept out of the JSX so the copy
// is easy to grep + audit against Stripe.
const YEARLY_DISCOUNT_PCT = 20;

const PLANS = [
  {
    tier: "oi",
    name: "Opportunity Intelligence",
    tagline: "Find & qualify — no drafting",
    monthly: 49.99, yearly: 479.90, yearlyBundleSeats: 1,
    monthlyLookup: "oi_monthly", yearlyLookup: "oi_yearly",
    icon: Sparkles,
    features: [
      "AI-scored federal opportunities (SAM.gov + Grants.gov + open web)",
      "Company Profile, NAICS + set-aside eligibility engine",
      "Competitive Analysis — top primes/subs + AI shortlist",
      "Private Capital & Accelerators AI scans",
      "Points-of-Contact & Opportunity Summaries",
    ],
    featuresYearlyExtra: [
      "Single user seat included",
    ],
    notIncluded: [
      "Federal Proposals (full package drafting)",
      "Investment Deals (pitch decks, business plans, financials)",
      "Accelerator Applications (structured fillable forms)",
      "Company disk storage (all seven folders)",
      "AI chat assistant on every page",
    ],
  },
  {
    tier: "full",
    name: "Full Capture & Proposal Generation",
    tagline: "Everything in Opportunity Intelligence — plus drafting",
    monthly: 99.99, yearly: 2879.71, yearlyBundleSeats: 3,
    monthlyLookup: "full_monthly", yearlyLookup: "full_yearly",
    recommended: true,
    icon: Rocket,
    features: [
      "Everything in Opportunity Intelligence",
      "Company disk storage (all seven folders)",
      "AI chat assistant on every page",
      "Federal Proposals — full volume drafting, evaluation & export",
      "Investment Deals — investor emails, pitch decks, business plans, financials",
      "Accelerator Applications — tailored fillable forms per program",
      "Overleaf bidirectional git sync",
      "Bring your own OpenAI · Anthropic · Gemini keys — or use ours",
    ],
    featuresYearlyExtra: [
      "Includes up to 3 users",
    ],
    notIncluded: [],
  },
  {
    tier: "enterprise",
    name: "Enterprise",
    tagline: "For large teams and primes",
    monthly: null, yearly: null,
    icon: Building2,
    features: [
      "Everything in Full Capture",
      "Full Agentic Workflows",
      "AWS GovCloud hosting",
      "Support for CUI and ITAR-controlled data",
      "Enhanced security & encryption (FIPS 140-2, KMS-backed at rest, mTLS in transit)",
      "SSO / SAML (Okta, Azure AD)",
      "Dedicated support & onboarding",
      "Volume seat pricing & custom procurement paperwork",
    ],
    featuresYearlyExtra: [],
    notIncluded: [],
  },
];

function priceLabel(plan, interval) {
  if (plan.monthly === null) return "Contact us";
  if (interval === "year") {
    return `$${plan.yearly.toLocaleString(undefined,
      { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/yr`;
  }
  return `$${plan.monthly.toFixed(2)}/mo`;
}

function perLabel(plan, interval) {
  if (plan.monthly === null) return "";
  if (interval === "year") {
    return plan.yearlyBundleSeats > 1
      ? `${YEARLY_DISCOUNT_PCT}% off · ${plan.yearlyBundleSeats} users included`
      : `${YEARLY_DISCOUNT_PCT}% off · billed annually`;
  }
  return "per user, billed monthly · cancel anytime";
}

function PlanCard({ plan, interval, onSubscribe, busy }) {
  const Icon = plan.icon;
  const highlight = plan.recommended;
  const showsBundle = interval === "year" && plan.yearlyBundleSeats > 1;
  const fullFeatureList = interval === "year"
    ? [...plan.features, ...plan.featuresYearlyExtra]
    : plan.features;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      className={`glass relative flex flex-col p-6 ${highlight ? "border-cyan/60 shadow-[0_0_0_1px_rgba(102,232,255,0.35)]" : ""}`}
      data-testid={`plan-card-${plan.tier}`}
    >
      {highlight && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-cyan px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-deep">
          Recommended
        </div>
      )}
      <div className="flex items-center gap-3">
        <Icon size={22} className="text-cyan" />
        <div>
          <div className="text-lg font-bold text-ink">{plan.name}</div>
          <div className="label-mono text-faint">{plan.tagline}</div>
        </div>
      </div>
      <div className="mt-5">
        <div className="text-3xl font-extrabold tracking-tight text-ink" data-testid={`plan-price-${plan.tier}`}>
          {priceLabel(plan, interval)}
        </div>
        <div className="mt-1 text-xs text-faint">{perLabel(plan, interval)}</div>
        {showsBundle && (
          <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-cyan/30 bg-cyan/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-cyan"
               data-testid={`plan-seat-badge-${plan.tier}`}>
            <Users size={11} /> up to {plan.yearlyBundleSeats} users
          </div>
        )}
      </div>

      <ul className="mt-6 flex-1 space-y-2 text-sm text-dim">
        {fullFeatureList.map((f) => {
          // Give the seat callouts extra emphasis so they read like a badge.
          const isSeatCallout = plan.featuresYearlyExtra.includes(f);
          return (
            <li key={f} className={`flex items-start gap-2 ${isSeatCallout ? "font-semibold text-cyan" : ""}`}
                data-testid={isSeatCallout ? `plan-seat-callout-${plan.tier}` : undefined}>
              {isSeatCallout
                ? <Users size={15} className="mt-0.5 shrink-0 text-cyan" />
                : <Check size={15} className="mt-0.5 shrink-0 text-cyan" />}
              <span>{f}</span>
            </li>
          );
        })}
      </ul>

      {plan.notIncluded.length > 0 && (
        <div className="mt-4 rounded-xl border border-line bg-white/[0.02] p-3 text-xs text-faint">
          <div className="mb-1 uppercase tracking-widest text-[10px] text-warn">Not included</div>
          <ul className="space-y-0.5">
            {plan.notIncluded.map((f) => <li key={f}>· {f}</li>)}
          </ul>
        </div>
      )}

      <div className="mt-6">
        {plan.tier === "enterprise" ? (
          <Link to="/contact"
                className="btn btn-ghost w-full"
                data-testid={`plan-cta-${plan.tier}`}>
            Contact sales
          </Link>
        ) : (
          <button
            onClick={() => onSubscribe(plan, interval)}
            disabled={busy === plan.tier}
            className={`btn w-full ${highlight ? "btn-primary" : "btn-ghost"}`}
            data-testid={`plan-cta-${plan.tier}`}
          >
            {busy === plan.tier ? "Redirecting to Stripe…" : "Start subscription"}
          </button>
        )}
      </div>
    </motion.div>
  );
}

export default function Pricing() {
  const [interval, setBillingInterval] = useState("month");
  const [busy, setBusy] = useState(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  const subscribe = async (plan, ivl) => {
    if (!user) {
      navigate("/register?next=/pricing");
      return;
    }
    setBusy(plan.tier);
    try {
      const lookupKey = ivl === "year" ? plan.yearlyLookup : plan.monthlyLookup;
      const { data } = await api.post("/payments/checkout", {
        lookupKey,
        originUrl: window.location.origin,
      });
      if (data?.url) window.location.href = data.url;
      else throw new Error("Stripe did not return a checkout URL");
    } catch (e) {
      toast.error(errMsg(e));
      setBusy(null);
    }
  };

  const plans = useMemo(() => PLANS, []);

  return (
    <MarketingLayout>
      <section className="mx-auto max-w-6xl px-5 pt-16 pb-4">
        <div className="text-center">
          <div className="label-mono text-cyan">Pricing</div>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            Three plans. Pay for what you use.
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-dim">
            Every plan includes AI-scored federal opportunities, competitive
            analysis, and private-capital + accelerator scans. Move up when
            you need drafting, disk storage, the AI chat assistant, or a
            GovCloud-hosted deployment.
          </p>

          <div className="mt-6 inline-flex items-center gap-1 rounded-full border border-line bg-panel/40 p-1"
               data-testid="pricing-interval-toggle">
            <button
              onClick={() => setBillingInterval("month")}
              className={`rounded-full px-4 py-1.5 text-sm ${interval === "month" ? "bg-cyan text-deep" : "text-dim hover:text-ink"}`}
              data-testid="pricing-interval-month"
            >Monthly</button>
            <button
              onClick={() => setBillingInterval("year")}
              className={`rounded-full px-4 py-1.5 text-sm ${interval === "year" ? "bg-cyan text-deep" : "text-dim hover:text-ink"}`}
              data-testid="pricing-interval-year"
            >
              Yearly <span className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${interval === "year" ? "bg-deep/20 text-deep" : "bg-cyan/15 text-cyan"}`}>Save {YEARLY_DISCOUNT_PCT}%</span>
            </button>
          </div>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {plans.map((p) => (
            <PlanCard key={p.tier} plan={p} interval={interval}
                      onSubscribe={subscribe} busy={busy} />
          ))}
        </div>

        <div className="mx-auto mt-10 max-w-2xl text-center text-xs text-faint">
          Prices in USD. Sales tax added where applicable. Cancel anytime —
          access continues to the end of your billing period. Refunds are
          reviewed by CaptureAgent; request one from{" "}
          <Link to="/login" className="text-cyan hover:underline">Settings → Billing</Link>{" "}
          after signing in. Have a promo code? Enter it on the Stripe
          checkout page.
        </div>
      </section>
    </MarketingLayout>
  );
}
