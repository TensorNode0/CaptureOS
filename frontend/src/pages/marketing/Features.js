import React from "react";
import { Link } from "react-router-dom";
import { Radar, Satellite, ClipboardCheck, Sparkles, Package, ShieldCheck,
         Users, ArrowRight, FileText, Crosshair, Landmark } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

const FEATURES = [
  {
    icon: Radar, title: "Pipeline & live pulls",
    points: [
      "One-click pull from SAM.gov (Get Opportunities v2) and Grants.gov, matched to your NAICS and keywords",
      "Deduped by solicitation number — your fit scores and notes survive refreshes",
      "Stage pipeline from Identified through Submitted, Won, Lost, and No-Bid",
      "AI Verify & Refresh checks every record against live sources and flags changed due dates or cancelled notices",
    ],
  },
  {
    icon: Satellite, title: "Opportunity intelligence scans",
    points: [
      "Claude with live web search across SBIR.gov/DSIP, AFWERX, SpaceWERX, DIU, DARPA, NASA, xTech, SOFWERX, MDA, NSIN, and more",
      "Every find fit-scored 1–100 against your capability profile, honestly — low scores included",
      "Executive summary, hot signals, and recommended BD actions in every report",
      "Push any discovered opportunity straight into your pipeline",
    ],
  },
  {
    icon: ClipboardCheck, title: "Compliance & eligibility",
    points: [
      "Set-aside eligibility computed from your certifications — 8(a), HUBZone, SDVOSB, WOSB, EDWOSB, VOSB",
      "Compliance checklist per opportunity with a hard no-bid gate for CMMC requirements",
      "Fit factors, pWin, and proposal-strength scoring kept deliberately separate",
      "Bid/no-bid decision log with rationale — auditable capture discipline",
    ],
  },
  {
    icon: Sparkles, title: "AI capability designer",
    points: [
      "Generates title, abstract, executive summary, and keywords grounded in the solicitation and your profile",
      "Concept rendering (SVG), charts, and requirement-traceability tables",
      "Statement of Work with tasks and deliverables, WBS with a month-by-month schedule",
      "Budget with basis-of-estimate narrative, capped to the ceiling — approve with version history, export to Word",
    ],
  },
  {
    icon: Package, title: "Proposal package builder",
    points: [
      "Volume set adapts to the vehicle: RFP, SBIR/STTR, BAA, CSO, or grant",
      "Draft any volume with Claude or ChatGPT — your choice of engine, your keys",
      "In-app editors: markdown for narratives, structured rows for cost, slides for the briefing deck",
      "Export real .docx, .xlsx, and .pptx files individually or the whole package as a zip",
    ],
  },
  {
    icon: FileText, title: "Proposal hub & AI evaluation",
    points: [
      "Every package your team creates in one Proposals tab — status, volumes drafted, due dates, submission state",
      "AI color-team evaluation: an SSEB-style review scores the drafted package 0–100 across five factors",
      "Strengths, weaknesses, severity-rated risks with mitigations, and compliance gaps — before the government sees it",
      "A prioritized 'do these next' list of the edits that most raise your score; re-evaluate after each pass",
    ],
  },
  {
    icon: Crosshair, title: "Competitive analysis (OSINT)",
    points: [
      "Verified federal award history for any competitor straight from USASpending — totals by year, top agencies, largest contracts with links",
      "AI research across SAM.gov, SBA DSBS, GSA eLibrary, OSDBU forecasts, and the open web — nothing fabricated, sources cited",
      "BLUF up top: who they are, where they win, where they're beatable",
      "Prime/sub/team strategies with specific next steps, plus a recompete watch built from contract end dates",
    ],
  },
  {
    icon: Landmark, title: "Private capital & accelerators",
    points: [
      "Curated directory of defense & space investors — check sizes, stages, sectors, check types, and the traction each looks for",
      "Aerospace/defense accelerator map with terms, cohorts, and application tips (Catalyst, Techstars Space, NSIN, xTech, DIANA...)",
      "Investment Deals workspace: AI-drafted investor emails, pitch decks, business plans, and 3-year financial models — exported to Office",
      "Accelerator Applications workspace: per-question answers with tips on what strong applications do",
    ],
  },
  {
    icon: Users, title: "Team & governance",
    points: [
      "Domain-aware signup: the first user certifies as AOR/Admin; colleagues request access and get roles",
      "Roles that mirror a real capture shop: admin, capture manager, PI, proposal writer, technical writer, editor, viewer",
      "Only the capture manager (or admin) creates and approves; only the admin submits",
      "Entity info locked to the admin, with time-boxed edit grants on request — every action audit-logged",
    ],
  },
  {
    icon: ShieldCheck, title: "Security architecture",
    points: [
      "Bring-your-own API keys, envelope-encrypted per organization — invisible even to the operator",
      "Masked previews only; full keys never reach any browser",
      "Purpose-tagged audit trail for every key use and every admin action",
      "Postgres with row-level security on every table; login lockout; httpOnly cookies",
    ],
  },
];

export default function Features() {
  return (
    <MarketingLayout>
      <section className="mx-auto max-w-6xl px-5 pb-8 pt-16">
        <div className="label-mono mb-3">Features</div>
        <h1 className="max-w-3xl text-4xl font-bold text-ink">
          A complete capture shop, in one console
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-dim">
          Everything between "there's a solicitation somewhere out there" and
          "package submitted" — with a human approving every step.
        </p>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-5 py-6 md:grid-cols-2">
        {FEATURES.map((f) => (
          <div key={f.title} className="glass p-6">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-cyan/40 bg-cyan/10">
              <f.icon size={18} className="text-cyan" />
            </div>
            <h2 className="text-lg font-semibold text-ink">{f.title}</h2>
            <ul className="mt-3 space-y-2">
              {f.points.map((p) => (
                <li key={p} className="flex gap-2 text-sm text-dim">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cyan" />{p}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="mx-auto max-w-3xl px-5 py-14 text-center">
        <h2 className="text-2xl font-semibold text-ink">See it with your own pipeline</h2>
        <p className="mt-3 text-dim">Free to set up. Your keys, your data, your wins.</p>
        <Link to="/register" className="btn btn-primary mt-6 !px-6 !py-3 text-base">
          Create your workspace <ArrowRight size={17} />
        </Link>
      </section>
    </MarketingLayout>
  );
}
