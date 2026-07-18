import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Radar, Sparkles, Package, ShieldCheck, ArrowRight, KeyRound,
         Building2, FileSearch, PenTool, Send, Gauge, Rocket, Clock, DollarSign,
         Trophy, Zap } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

// KPIs — grouped in the order (price · time · quality · effort). No "volume of
// artifacts scanned" (not a KPI) and no "keys visible to you" claims here —
// those live in the Security section further down.
const KPIS = [
  {
    icon: DollarSign,
    v: "$5–10", suffix: "per proposal",
    l: "Typical AI-credit cost to scan, draft, edit, evaluate & export a full package. Compare with $8k–25k for a consultant.",
    tint: "cyan",
  },
  {
    icon: Trophy,
    v: "100×", suffix: "cheaper",
    l: "vs. hiring a fractional capture manager ($150–$300/hr) or a proposal shop.",
    tint: "violet",
  },
  {
    icon: Clock,
    v: "< 1 hr", suffix: "solicitation → first draft",
    l: "AI produces a reviewable Technical + Management + Past-Perf + Cost + SF1449 volume-set in minutes, not weeks.",
    tint: "cyan",
  },
  {
    icon: Gauge,
    v: "AI color-team", suffix: "review built-in",
    l: "Every package is scored on all Section-M factors before submission — with the exact edits to raise the score.",
    tint: "violet",
  },
  {
    icon: Zap,
    v: "One profile", suffix: "→ everything auto-fills",
    l: "Enter certs, NAICS, past performance, differentiators once. It fuels every capability, proposal, and application.",
    tint: "cyan",
  },
  {
    icon: Rocket,
    v: "12+", suffix: "federal + private sources",
    l: "SAM.gov, Grants.gov, SBIR/DSIP, AFWERX, DIU, DARPA, NASA + curated investors & accelerators, all fit-scored to your org.",
    tint: "violet",
  },
];

const TRIO = [
  {
    icon: Radar, title: "Opportunity intelligence",
    body: "Pull live solicitations from SAM.gov and Grants.gov, then let the AI scan " +
      "SBIR/DSIP, AFWERX, DIU, DARPA, NASA, and the open web — fit-scored against " +
      "your company profile, with eligibility and compliance flags computed for every record.",
    img: "/marketing/opportunities.png", alt: "Opportunity pipeline screenshot",
  },
  {
    icon: Sparkles, title: "AI capability designer",
    body: "One click turns a solicitation plus your company profile into a proposed " +
      "capability: title, abstract, executive summary, keywords, concept rendering, " +
      "charts, Statement of Work, WBS with schedule, and a budget with basis of estimate. " +
      "Review, edit anything, approve — with version history.",
    img: "/marketing/capability.png", alt: "Capability designer screenshot",
  },
  {
    icon: Package, title: "Proposal package builder",
    body: "The volume set adapts to the vehicle — SBIR gets a commercialization plan, an RFP " +
      "gets technical, management, and past-performance volumes. Draft each with Claude or " +
      "ChatGPT, edit in place, and export real Word, Excel, and PowerPoint files or one zip.",
    img: "/marketing/proposal.png", alt: "Proposal workspace screenshot",
  },
  {
    icon: Gauge, title: "Source-selection-grade evaluation",
    body: "Once every volume is drafted, one click runs an AI color-team review of the " +
      "whole package — scores by factor, strengths, weaknesses, risks, compliance gaps, " +
      "and the edits that raise your score. Every AI button shows live progress, tokens, " +
      "and cost, with a Stop button — pick the provider, model, and effort per call.",
    img: "/marketing/proposal-eval.png", alt: "Proposal evaluation and customer targeting screenshot",
  },
  {
    icon: Radar, title: "Competitive intelligence",
    body: "See who actually wins in your NAICS codes — top primes and top subs straight from " +
      "USASpending — then run a deep OSINT profile on any competitor: verified award history, " +
      "customers, vehicles, headcount, salaries by role, capital raised, and where they're beatable.",
    img: "/marketing/competitive.png", alt: "Competitive analysis screenshot",
  },
  {
    icon: Rocket, title: "Accelerators & private capital",
    body: "Curated tables of defense accelerators (due dates, duration, terms, phase) and the " +
      "investors writing checks into defense and space — click any row for the full profile, " +
      "start an application generated from the program's own page, or let the AI scan the live " +
      "web for programs and investors that fit your company.",
    img: "/marketing/accelerators.png", alt: "Defense accelerators directory screenshot",
  },
];

const STEPS = [
  { icon: Building2, t: "Build your profile", d: "Certs, NAICS, past performance, differentiators — entered once, fueling everything." },
  { icon: FileSearch, t: "Scan & qualify", d: "Pull and discover live opportunities, fit-scored and eligibility-checked in minutes." },
  { icon: PenTool, t: "Design & draft", d: "Approve the AI-designed capability, then draft the full package volume by volume." },
  { icon: Send, t: "Review & submit", d: "Humans edit and approve. The admin marks it submitted. Download everything." },
];

export default function Home() {
  return (
    <MarketingLayout>
      {/* hero */}
      <section className="relative mx-auto max-w-6xl px-5 pb-16 pt-20 text-center">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}>
          <div className="label-mono mb-4 !text-cyan">Streamlining government capture</div>
          <h1 className="mx-auto max-w-4xl text-4xl font-bold leading-[1.08] text-ink md:text-6xl">
            The TurboTax Of GovCon:
            <span className="mt-2 block bg-clip-text text-transparent"
                  style={{ backgroundImage: "linear-gradient(90deg, var(--accent-cyan) 0%, #ffffff 50%, var(--accent-violet) 100%)" }}>
              An AI Capture Manager for Lean Startups &amp; Small Businesses.
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-dim">
            End-to-end GovCon lifecycle in <span className="text-ink font-semibold">minutes, not months</span> —
            at a fraction of the price of a fractional capture manager.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/register"
                  className="btn btn-liquid liquid-cyan !px-7 !py-3 text-base"
                  data-testid="hero-start">
              Start Now <ArrowRight size={17} />
            </Link>
            <Link to="/features"
                  className="btn btn-liquid !px-7 !py-3 text-base"
                  data-testid="hero-see">
              See it in action
            </Link>
          </div>
        </motion.div>

        {/* KPIs — 3 across × 2 rows */}
        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {KPIS.map((k, i) => (
            <motion.div key={k.l}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.05 * i }}
              className="liquid liquid-hover p-5 text-left"
              data-testid={`kpi-${i}`}
            >
              <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl border ${k.tint === "cyan" ? "border-cyan/40 bg-cyan/10 text-cyan" : "border-violet-400/40 bg-violet-400/10 text-violet-300"}`}>
                <k.icon size={17} />
              </div>
              <div className="mono text-2xl font-bold tracking-tight text-ink">
                {k.v}
              </div>
              <div className="mono mt-0.5 text-[11px] uppercase tracking-widest text-faint">
                {k.suffix}
              </div>
              <div className="mt-3 text-sm leading-relaxed text-dim">{k.l}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Value-proposition banner — replaces the "New feature" strip. */}
      <section className="mx-auto max-w-5xl px-5 pb-4 pt-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="liquid liquid-hover liquid-featured relative overflow-hidden px-8 py-10 text-center md:px-12 md:py-14"
          data-testid="value-banner"
        >
          <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-cyan/20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-violet-400/20 blur-3xl" />
          <div className="label-mono !text-cyan">CaptureAgent</div>
          <h2 className="mx-auto mt-4 max-w-4xl text-3xl font-bold leading-tight text-ink md:text-4xl">
            The One-Stop Shop For{" "}
            <span className="bg-clip-text text-transparent"
                  style={{ backgroundImage: "linear-gradient(90deg, var(--accent-cyan) 0%, #ffffff 50%, var(--accent-violet) 100%)" }}>
              Winning Federal Contracts, Raising, and Accelerating.
            </span>
          </h2>
        </motion.div>
      </section>

      {/* product trio with screenshots */}
      <section className="mx-auto max-w-6xl space-y-16 px-5 py-10">
        {TRIO.map((f, i) => (
          <div key={f.title}
               className={`flex flex-col items-center gap-8 lg:flex-row ${i % 2 ? "lg:flex-row-reverse" : ""}`}>
            <div className="flex-1">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-cyan/40 bg-cyan/10">
                <f.icon size={20} className="text-cyan" />
              </div>
              <h2 className="text-2xl font-semibold text-ink">{f.title}</h2>
              <p className="mt-3 leading-relaxed text-dim">{f.body}</p>
            </div>
            <div className="flex-1">
              <img src={f.img} alt={f.alt} loading="lazy"
                   className="w-full rounded-xl border border-line shadow-[0_0_40px_rgba(56,225,255,0.08)]"
                   onError={(e) => { e.currentTarget.style.display = "none"; }} />
            </div>
          </div>
        ))}
      </section>

      {/* how it works */}
      <section className="mx-auto max-w-6xl px-5 py-14">
        <div className="label-mono mb-2 text-center">How it works</div>
        <h2 className="text-center text-3xl font-semibold text-ink">From profile to submitted package</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <div key={s.t} className="liquid liquid-hover p-5">
              <div className="mono text-xs text-faint">0{i + 1}</div>
              <s.icon size={20} className="mt-2 text-cyan" />
              <div className="mt-3 font-semibold text-ink">{s.t}</div>
              <p className="mt-1.5 text-sm text-dim">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* security */}
      <section className="mx-auto max-w-6xl px-5 py-14">
        <div className="liquid liquid-hover p-8 md:p-10">
          <div className="flex flex-col gap-8 md:flex-row">
            <div className="flex-1">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-ok/40 bg-ok/10">
                <ShieldCheck size={20} className="text-ok" />
              </div>
              <h2 className="text-2xl font-semibold text-ink">Your keys. Your data. Nobody else&apos;s.</h2>
              <p className="mt-3 leading-relaxed text-dim">
                Every organization brings its own SAM.gov, Claude, and OpenAI API
                keys — so your usage runs on your accounts, at cost, with no markup
                and no shared quotas. Keys are envelope-encrypted per organization
                and never leave the server: not your teammates, not other
                customers, <span className="text-ink">not even we</span> can read them.
              </p>
            </div>
            <div className="flex-1 space-y-3 text-sm">
              {[
                ["Per-org envelope encryption", "each org has its own data key, wrapped by a master key that never exists in the database"],
                ["Masked everywhere", "admins see sk-…4f2a previews only; full keys are never sent to any browser"],
                ["Audited access", "every key use is logged with its purpose — visible to your admin"],
                ["Role-based governance", "AOR-certified admins, capture managers, writers, viewers — least privilege by default"],
              ].map(([t, d]) => (
                <div key={t} className="flex gap-3 rounded-lg border border-line bg-white/5 p-3">
                  <KeyRound size={15} className="mt-0.5 shrink-0 text-cyan" />
                  <div><span className="text-ink">{t}</span> — <span className="text-dim">{d}</span></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-3xl px-5 py-16 text-center">
        <h2 className="text-3xl font-semibold text-ink">Your next win starts with the next scan</h2>
        <p className="mt-3 text-dim">
          Set up your company profile tonight. Have qualified, fit-scored
          opportunities on your dashboard before your first coffee tomorrow.
        </p>
        <div className="mt-7 flex justify-center gap-3">
          <Link to="/register" className="btn btn-liquid liquid-cyan !px-6 !py-3 text-base">Create your workspace</Link>
          <Link to="/pricing" className="btn btn-liquid !px-6 !py-3 text-base">See pricing</Link>
        </div>
      </section>
    </MarketingLayout>
  );
}
