import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Radar, Sparkles, Package, ShieldCheck, ArrowRight, KeyRound,
         Building2, FileSearch, PenTool, Send } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

const STATS = [
  { v: "12+", l: "federal sources scanned per intelligence run" },
  { v: "<1 hr", l: "from solicitation to a reviewable first-draft package" },
  { v: "5", l: "proposal volumes exported in a single zip" },
  { v: "0", l: "API keys visible to anyone — even us" },
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
      <section className="mx-auto max-w-6xl px-5 pb-16 pt-20 text-center">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}>
          <div className="label-mono mb-4 !text-cyan">Streamlining government capture</div>
          <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight text-ink md:text-5xl">
            Win federal work with an AI capture manager on your team
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-dim">
            Find and qualify opportunities closely tailored to your business in
            <span className="text-ink"> minutes, not days</span>. Prepare and submit
            proposal packages in <span className="text-ink">days, not weeks</span>.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/register" className="btn btn-primary !px-6 !py-3 text-base" data-testid="hero-start">
              Start free — bring your own keys <ArrowRight size={17} />
            </Link>
            <Link to="/features" className="btn btn-ghost !px-6 !py-3 text-base">See it in action</Link>
          </div>
        </motion.div>
        <div className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.l} className="glass p-4 text-left">
              <div className="mono text-2xl text-cyan">{s.v}</div>
              <div className="mt-1 text-xs text-dim">{s.l}</div>
            </div>
          ))}
        </div>
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
            <div key={s.t} className="glass p-5">
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
        <div className="glass p-8 md:p-10">
          <div className="flex flex-col gap-8 md:flex-row">
            <div className="flex-1">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-ok/40 bg-ok/10">
                <ShieldCheck size={20} className="text-ok" />
              </div>
              <h2 className="text-2xl font-semibold text-ink">Your keys. Your data. Nobody else's.</h2>
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
          <Link to="/register" className="btn btn-primary !px-6 !py-3 text-base">Create your workspace</Link>
          <Link to="/resources" className="btn btn-ghost !px-6 !py-3 text-base">Get your API keys</Link>
        </div>
      </section>
    </MarketingLayout>
  );
}
