import React from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

const POSTS = {
  "introducing-captureagent": {
    date: "2026-07-06",
    tag: "ANNOUNCEMENT",
    title: "Introducing CaptureAgent: an AI capture manager for the rest of us",
    summary: "Why we built an AI-native capture and proposal platform for small government contractors — and what it does on day one.",
    body: [
      "Large primes bring proposal shops with dozens of specialists to every pursuit. Small businesses bring nights and weekends. That gap — not technical merit — decides far too many federal awards.",
      "CaptureAgent is our answer: an AI capture manager that scans SAM.gov, Grants.gov, and the SBIR/STTR ecosystem for opportunities that actually fit your company, checks your eligibility against your certifications, designs a proposed capability (title, abstract, executive summary, concept rendering, statement of work, WBS with schedule, and budget), and then drafts the proposal package volume by volume — with a human reviewing, editing, and approving at every step.",
      "Three principles shaped the build. First, bring your own keys: your SAM.gov and AI keys are envelope-encrypted per organization, invisible to everyone including us, with every use audited. Second, evaluator-grade output: every artifact follows the structures source-selection boards actually score. Third, governance that matches how contractors really work: AOR-certified administrators, capture managers who own the pipeline, writers who contribute without holding the keys.",
      "The app is live at captureagent.us — create your workspace, plug in your keys, and pull your first tailored opportunity list in minutes. The Resources section carries our field guides: new-contractor registrations, DSIP setup, official proposal templates by agency, and the compliance stack from ITAR to CMMC.",
      "We're just getting started. On the roadmap: deeper source coverage, proposal evaluation scoring, and tools for the private-capital side of building a defense company. If you win one contract you would have missed, CaptureAgent paid for itself.",
    ],
  },
};

const ORDER = ["introducing-captureagent"];

export function BlogIndex() {
  return (
    <MarketingLayout>
      <div className="mx-auto max-w-3xl px-5 pb-10 pt-14">
        <div className="label-mono">BLOG</div>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Notes from the capture floor</h1>
        <p className="mt-3 text-sm text-dim">Product news and GovCon craft, from the CaptureAgent team.</p>
        <div className="mt-10 space-y-4">
          {ORDER.map((slug) => {
            const p = POSTS[slug];
            return (
              <Link key={slug} to={`/blog/${slug}`} data-testid={`blog-${slug}`}
                    className="group block rounded-xl border border-line bg-white/5 p-6 transition-colors hover:border-cyan/40">
                <div className="label-mono">{p.tag} · {p.date}</div>
                <div className="mt-2 text-xl font-semibold text-ink">{p.title}</div>
                <p className="mt-2 text-sm leading-relaxed text-faint">{p.summary}</p>
                <div className="mt-3 inline-flex items-center gap-1.5 text-xs text-cyan">
                  Read post <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </MarketingLayout>
  );
}

export function BlogPost() {
  const { slug } = useParams();
  const p = POSTS[slug];
  if (!p) return <Navigate to="/blog" replace />;
  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-5 pb-10 pt-12">
        <Link to="/blog" className="inline-flex items-center gap-1.5 text-sm text-dim hover:text-cyan">
          <ArrowLeft size={15} /> All posts
        </Link>
        <div className="label-mono mt-6">{p.tag} · {p.date}</div>
        <h1 className="mt-2 text-3xl font-semibold leading-tight text-ink">{p.title}</h1>
        {p.body.map((para, i) => (
          <p key={i} className="mt-5 text-sm leading-relaxed text-dim">{para}</p>
        ))}
        <div className="mt-12 rounded-xl border border-line bg-white/5 p-5 text-center">
          <div className="text-sm font-medium text-ink">Try CaptureAgent</div>
          <Link to="/register" className="btn btn-primary mt-3 !py-2">Start free</Link>
        </div>
      </article>
    </MarketingLayout>
  );
}
