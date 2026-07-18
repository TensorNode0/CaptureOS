import React from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

const POSTS = {
  "dow-customer-discovery-2026-peo-directory": {
    date: "2026-07-11",
    tag: "FIELD GUIDE",
    title: "Selling to the DoW: customer discovery and the 2026 PEO directory",
    summary: "The Department of War is not one customer — it's dozens of Program Executive Offices, each with its own budget and priorities. Here's how to find yours, and the directory that maps them all.",
    body: [
      "Ask a first-time defense founder who their customer is and you'll hear \"the DoD\" — now the Department of War. That answer has cost startups years. The department doesn't buy as one entity: acquisition authority and budget live in Program Executive Offices, portfolio organizations that each own a family of programs — Army aviation, Navy submarines, Air Force battle management, Space Force sensing. Each PEO is, for practical purposes, a different customer with its own priorities, budget lines, and people.",
      "That's why Stanford's Gordian Knot Center publishes the Program Executive Offices Directory — the 2026 edition is out now at gordianknot.fsi.stanford.edu, with a downloadable PDF and a newsletter subscription for future editions. Steve Blank, who helped create it, frames it exactly right: you can't do customer discovery if you can't find the customer. The Silicon Valley Defense Group's DoW Directory rounds out the map with the innovation organizations — AFWERX, DIU, NavalX, the Tech Bridges — that serve as front doors into those PEOs.",
      "The discovery motion looks like commercial customer discovery with different nouns. Map your product to the two or three PEOs whose portfolios actually cover it. Find the program offices under them — that's where requirements are written and SBIR topics originate. Trace recent awards out of those offices to see what they really buy. Then find the named humans: the program manager, the technical point of contact on the SBIR topic, the contracting officer on the solicitation. Warm paths beat cold email: a Phase I award, an accelerator cohort, a Hacking-for-Defense connection.",
      "We built this motion into CaptureAgent. The proposal workspace now has a customer card: pick your commercial market (dual-use matters — to investors and to the department), then the government customer — sector, branch, and the PEO straight from the directory structure, plus your TPOC and contracting officer. An AI check verifies the directory entry is still current, because PEOs get reorganized more often than directories get reprinted.",
      "Read the full field guide in our Resources section (DoW customer discovery: find your PEO before you write a line), then go find your PEO. The customer exists — the directory is how you find their address.",
    ],
  },
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

const ORDER = ["dow-customer-discovery-2026-peo-directory", "introducing-captureagent"];

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
          <Link to="/register" className="btn btn-liquid liquid-cyan mt-3 !py-2">Start Now</Link>
        </div>
      </article>
    </MarketingLayout>
  );
}
