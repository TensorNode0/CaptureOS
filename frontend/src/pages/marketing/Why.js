import React from "react";
import { Link } from "react-router-dom";
import { XCircle, CheckCircle2, ArrowRight } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

const PAINS = [
  ["BD that burns weeks", "Analysts comb SAM.gov by hand, agency by agency, keyword by keyword — and still miss the SBIR topic or BAA that fit best."],
  ["Proposals that burn weekends", "A single mid-size pursuit consumes hundreds of team hours before you even know if it was worth bidding."],
  ["Generic AI that doesn't know you", "Chatbot drafts read like everyone else's because they aren't grounded in your certifications, past performance, or rates."],
  ["Capture suites priced for primes", "Enterprise tools assume a proposal shop of twenty and a six-figure license. Small businesses get spreadsheets."],
];

const WAYS = [
  ["Capture-first, not document-first", "CaptureAgent starts where wins start: qualification. Fit scores, eligibility verdicts, and compliance gates before you spend a dollar on writing."],
  ["Grounded in your company", "Every output — capability, volumes, budget — is generated from your profile: NAICS, set-aside certs, CMMC posture, past performance, differentiators."],
  ["Human-in-the-loop by design", "The AI proposes; your team disposes. Writers edit, the capture manager approves, the admin submits. Nothing ships itself."],
  ["Priced like a tool, powered by your keys", "Bring your own SAM.gov and LLM keys. Your usage bills at provider cost on your own accounts — no token markup."],
];

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

      <section className="mx-auto grid max-w-6xl gap-8 px-5 py-8 lg:grid-cols-2">
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
