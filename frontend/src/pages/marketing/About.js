import React from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "./MarketingLayout";
import { LogoMark } from "../../components/Logo";

export default function About() {
  return (
    <MarketingLayout>
      <section className="mx-auto max-w-3xl px-5 pb-10 pt-16">
        <div className="label-mono mb-3">About</div>
        <h1 className="text-4xl font-bold text-ink">Built for the businesses that build for the mission</h1>
        <div className="mt-6 space-y-5 leading-relaxed text-dim">
          <p>
            Federal contracting runs on small businesses — the machine shops,
            software teams, and research labs that deliver most of the
            government's innovation. Yet the capture process is stacked against
            them: the tooling that finds, qualifies, and wins federal work was
            built for primes with dedicated proposal centers.
          </p>
          <p>
            CaptureAgent exists to close that gap. It puts a senior capture
            manager's discipline — qualification before writing, compliance
            before enthusiasm, evaluators before egos — into software any team
            can run, powered by AI that is grounded in <span className="text-ink">your</span> company's
            real certifications, past performance, and differentiators.
          </p>
          <p>
            We are deliberately opinionated about the human's place in the
            loop. The AI designs and drafts; your capture manager approves;
            your Authorized Organizational Representative submits. Every
            artifact is reviewable, editable, and exportable — because the
            signature on the proposal is yours, not the machine's.
          </p>
          <p>
            And we're opinionated about trust: your API keys and pipeline data
            are encrypted per organization, invisible to other customers and to
            us, with every access logged. Your pipeline is your competitive
            advantage. It stays yours.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-5 py-10">
        <div className="glass flex flex-col items-center gap-4 p-8 text-center">
          <LogoMark size={56} ink="#e8eefc" />
          <div className="text-lg font-semibold text-ink">CaptureAgent</div>
          <p className="max-w-md text-sm text-dim">
            Streamlining government capture — from the first scan to the
            submitted package.
          </p>
          <Link to="/register" className="btn btn-primary !px-6 !py-2.5">Join us — start free</Link>
        </div>
      </section>
    </MarketingLayout>
  );
}
