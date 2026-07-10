import React from "react";
import { Link } from "react-router-dom";
import { XCircle, CheckCircle2, MinusCircle, ArrowRight, Check, X, Minus } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

const PAINS = [
  ["BD that burns weeks", "Analysts comb SAM.gov by hand, agency by agency — and still miss the SBIR topic or BAA that fit best."],
  ["Proposals that burn weekends", "A single mid-size pursuit consumes hundreds of team hours before you even know if it was worth bidding."],
  ["Generic AI that doesn't know you", "Chatbot drafts read like everyone else's because they aren't grounded in your certifications, past performance, or rates."],
  ["Capture suites priced for primes", "Enterprise tools assume a proposal shop of twenty and a six-figure license. Small businesses get spreadsheets."],
];

const COMPETITION = [
  ["Per-seat pricing that stacks up", "AI-GovCon tools typically run hundreds of dollars per seat per month — thousands a year before your first win, with AI usage bundled at a markup."],
  ["Half the workflow", "Most tools do opportunity matching or proposal drafting — rarely qualification, capability design, drafting, and evaluation in one flow."],
  ["Their keys, their models, your data", "AI calls usually run on the vendor's own accounts. You can't choose the model, audit the usage, or point it at a compliance boundary you control."],
  ["GovCon only", "Winning contracts is half of building a defense company. Raising capital and landing accelerators live in other tools — or nowhere."],
];

const WAYS = [
  ["Capture-first, end to end", "Qualification, capability design, volume drafting, AI color-team evaluation, and submission tracking — one pipeline, one workspace."],
  ["Grounded in your company", "Every output is generated from your profile: NAICS, set-aside certs, CMMC posture, past performance, differentiators."],
  ["Your keys, your models, your audit log", "Bring your own SAM.gov, Claude, ChatGPT, Emergent, or AskSage keys — envelope-encrypted, operator-blind, every use logged."],
  ["The whole company, not just contracts", "Competitive OSINT, defense-investor scouting, pitch materials, and accelerator applications in the same workspace."],
];

const TABLE = [
  { metric: "Price", sq: "Free (costly labor & loss of focus)", comp: "Typically $300–$1,000+ per seat / month, hidden behind a contact form", ca: "Free for a limited time (always transparent pricing that makes sense) — your usage bills at AI provider cost on your own keys" },
  { metric: "Time to a qualified pipeline", sq: "Days of manual search per week", comp: "Minutes–hours (matching only)", ca: "Minutes — pulled, fit-scored, eligibility-checked" },
  { metric: "First reviewable draft package", sq: "Weeks of team writing, endless meetings with subs, countless email threads, personal sacrifices, losing focus, disappearing runway, increasing burn rate, and staring at the abyss eating glass while crossing “the valley”", comp: "Days (single volumes, human assembly)", ca: "Under an hour: capability + volumes + cost + deck" },
  { metric: "Proposal evaluation", sq: "Color teams you have to staff", comp: "Rarely offered", ca: "AI SSEB-style review with scores, risks, and fix list" },
  { metric: "Competitive intelligence", sq: "Hours on USASpending + FPDS", comp: "Rarely offered", ca: "One click: verified award data + OSINT BLUF" },
  { metric: "Bring your own AI keys", sq: "—", comp: "Typically no", ca: "Yes — 4 engines, envelope-encrypted, audited" },
  { metric: "Investor & accelerator tooling", sq: "Interviewing cohort companies and cold-calling investors “asking for advice”", comp: "No", ca: "Directories + AI drafting workspaces included" },
  { metric: "Governance for real capture shops", sq: "Tribal knowledge", comp: "Basic seats/roles", ca: "AOR certification, 8 functional roles, audit trail" },
];

function Cell({ v }) {
  if (v === "—") return <Minus size={14} className="text-faint" />;
  return <span>{v}</span>;
}

export default function Why() {
  return (
    <MarketingLayout>
      <section className="mx-auto max-w-6xl px-5 pb-10 pt-16">
        <div className="label-mono mb-3">Why CaptureAgent</div>
        <h1 className="max-w-3xl text-4xl font-bold text-ink">
          Small teams lose federal work on process, not merit
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-dim">
          The best-fit vendor rarely loses on capability. They lose because the
          opportunity surfaced too late, the compliance gate got missed, or the
          proposal machine ran out of nights and weekends.
        </p>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-3">
        <div className="space-y-3">
          <div className="label-mono !text-bad">The status quo</div>
          {PAINS.map(([t, d]) => (
            <div key={t} className="flex gap-3 rounded-xl border border-line bg-white/5 p-4">
              <XCircle size={18} className="mt-0.5 shrink-0 text-bad" />
              <div><div className="font-semibold text-ink">{t}</div>
                <p className="mt-1 text-sm text-dim">{d}</p></div>
            </div>
          ))}
        </div>
        <div className="space-y-3">
          <div className="label-mono !text-warn">The competition</div>
          {COMPETITION.map(([t, d]) => (
            <div key={t} className="flex gap-3 rounded-xl border border-warn/25 bg-warn/5 p-4">
              <MinusCircle size={18} className="mt-0.5 shrink-0 text-warn" />
              <div><div className="font-semibold text-ink">{t}</div>
                <p className="mt-1 text-sm text-dim">{d}</p></div>
            </div>
          ))}
        </div>
        <div className="space-y-3">
          <div className="label-mono !text-ok">The CaptureAgent way</div>
          {WAYS.map(([t, d]) => (
            <div key={t} className="flex gap-3 rounded-xl border border-cyan/25 bg-cyan/5 p-4">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-ok" />
              <div><div className="font-semibold text-ink">{t}</div>
                <p className="mt-1 text-sm text-dim">{d}</p></div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-10">
        <div className="label-mono mb-3">Head to head</div>
        <h2 className="text-2xl font-semibold text-ink">Price, features, and what your week looks like</h2>
        <p className="mt-2 max-w-2xl text-sm text-faint">
          "The competition" reflects typical AI-GovCon tools on the market today; specifics
          vary by vendor — always compare current pricing pages.
        </p>
        <div className="mt-5 overflow-x-auto rounded-xl border border-line">
          <table className="w-full text-sm" data-testid="comparison-table">
            <thead className="bg-elev/80 text-xs text-dim">
              <tr className="border-b border-line">
                <th className="px-4 py-3 text-left font-medium"></th>
                <th className="px-4 py-3 text-left font-medium">Winging it</th>
                <th className="px-4 py-3 text-left font-medium">The competition</th>
                <th className="px-4 py-3 text-left font-medium text-cyan">CaptureAgent</th>
              </tr>
            </thead>
            <tbody>
              {TABLE.map((r) => (
                <tr key={r.metric} className="border-b border-line/60 align-top">
                  <td className="px-4 py-3 font-medium text-ink">{r.metric}</td>
                  <td className="px-4 py-3 text-xs leading-relaxed text-dim"><Cell v={r.sq} /></td>
                  <td className="px-4 py-3 text-xs leading-relaxed text-dim"><Cell v={r.comp} /></td>
                  <td className="bg-cyan/5 px-4 py-3 text-xs leading-relaxed text-ink"><Cell v={r.ca} /></td>
                </tr>
              ))}
              <tr className="align-top">
                <td className="px-4 py-3 font-medium text-ink">Bottom line</td>
                <td className="px-4 py-3 text-xs text-dim"><X size={14} className="inline text-bad" /> Weeks of labor per pursuit</td>
                <td className="px-4 py-3 text-xs text-dim"><Minus size={14} className="inline text-warn" /> Faster, but partial and pricey</td>
                <td className="bg-cyan/5 px-4 py-3 text-xs text-ink"><Check size={14} className="inline text-ok" /> Save weeks and $$$$ — and never miss a relevant opportunity</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-5 py-14 text-center">
        <h2 className="text-2xl font-semibold text-ink">
          Bid fewer. Win more. Sleep occasionally.
        </h2>
        <p className="mt-3 text-dim">
          The most expensive proposal is the one you were never going to win.
          CaptureAgent makes qualification cheap, so the pursuits you do fund
          get your team's best work.
        </p>
        <Link to="/register" className="btn btn-primary mt-6 !px-6 !py-3 text-base">
          Start qualifying smarter <ArrowRight size={17} />
        </Link>
      </section>
    </MarketingLayout>
  );
}
