import React from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

// Simple table renderer for blog posts. Matches Article.js liquid styling.
function BlogTable({ headers, rows }) {
  return (
    <div className="liquid mt-6 overflow-x-auto !rounded-2xl">
      <table className="w-full text-sm">
        <thead className="bg-white/[0.04] text-xs text-dim">
          <tr>{headers.map((h, i) => <th key={i} className="px-3 py-2.5 text-left font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-white/10">
              {r.map((c, j) => <td key={j} className="px-3 py-2.5 align-top text-xs leading-relaxed text-dim">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Curated investor + accelerator tables — mirror the data users see in the
// app (Private Capital and Accelerators tabs) so the blog is a real preview.
const DEFENSE_INVESTORS = [
  ["Andreessen Horowitz (American Dynamism)", "Seed → Growth", "Anduril, Shield AI, Saildrone, Hadrian"],
  ["Founders Fund", "Seed → Growth", "Anduril, Palantir, Varda, ABL Space"],
  ["Lux Capital", "Seed → Series C", "Anduril, Hadrian, Applied Intuition, Vannevar Labs"],
  ["8VC", "Seed → Series C", "Anduril, Epirus, Vannevar Labs, Palantir alumni"],
  ["General Catalyst", "Series A → Growth", "Anduril, Helsing, Rebellion Defense"],
  ["Point72 Ventures", "Seed → Series B", "Rebellion, ThirdWave Automation, Astranis"],
  ["Shield Capital", "Seed → Series B", "Cape, Vannevar Labs, ChaosSearch"],
  ["Razor's Edge Ventures", "Seed → Series B", "HawkEye 360, Reveal Technology, Second Front"],
  ["Booz Allen Ventures", "Seed → Series B", "Latent AI, Reveal, Synthetaic"],
  ["Lockheed Martin Ventures", "Seed → Series B", "Terran Orbital, Fortem, Astroscale"],
  ["Boeing HorizonX / AE Ventures", "Series A → Growth", "Reaction Engines, Isotropic Systems"],
  ["In-Q-Tel (strategic, IC)", "Seed → Series C", "Palantir historical, Databricks, HawkEye 360"],
  ["America's Frontier Fund", "Series A → Growth", "US critical-tech deep-tech focus"],
  ["Alsop Louie Partners", "Seed → Series A", "Vannevar Labs, Chef Robotics"],
  ["Riot Ventures", "Seed → Series A", "Hadrian, Skydio, Anduril early"],
  ["Decisive Point", "Seed → Series A", "National-security AI/software focus"],
  ["Silent Ventures", "Seed → Series A", "Defense/national-security-only fund"],
  ["Squadra Ventures", "Seed → Series A", "National-security software (Baltimore)"],
];

const DEFENSE_ACCELERATORS = [
  ["AFWERX", "Air Force / Space Force SBIR pipeline", "Rolling", "Non-dilutive SBIR funding + AF contracts"],
  ["SpaceWERX Orbital Prime / STRATFI", "Space Force scaling programs", "Announced BAAs", "Matched Phase II funds"],
  ["DIU (Defense Innovation Unit)", "Commercial dual-use → prototype OTAs", "Rolling problem sets", "OTA prototype awards, production paths"],
  ["Techstars Defense (Los Angeles / DC)", "Equity accelerator, defense focus", "Annual cohort", "$120k + demo day"],
  ["Hacking for Defense (H4D)", "University-based problem sourcing", "Semester cadence", "Warm sponsor path"],
  ["Massachusetts DefTech (MassChallenge)", "New-England defense cohort", "Annual", "Non-dilutive, corporate partners"],
  ["Catalyst Accelerator (Colorado / Space Force)", "Space & missile-defense focus", "Two cohorts/yr", "Space Force sponsor engagement"],
  ["MD5 / NSIN Foundry (National Security Innovation Network)", "Founder + DoW problem match", "Rolling", "Non-dilutive, DoW partner"],
  ["JHU APL Discover", "Applied physics lab commercialization", "By invite", "APL partnering + facilities"],
  ["FedTech", "Federal-lab tech transfer sprints", "Multiple cohorts/yr", "Lab licenses, corporate access"],
  ["Booz Allen SkillTerra / Ventures Accelerator", "Booz Allen-partnered ventures", "Rolling", "Prime relationship, pilots"],
  ["Sands Capital Space (SCSA)", "Space startup accelerator", "Annual", "Growth-stage capital connect"],
  ["Blue Bear Capital / Cyber London", "Cyber & industrial control", "Rolling", "European + US network"],
  ["Cortado Ventures Defense", "Midwest defense/dual-use", "Annual", "Non-dilutive prep + Series-A intros"],
];

const POSTS = {
  "dow-customer-discovery-2026-peo-directory": {
    date: "2026-07-11",
    tag: "FIELD GUIDE",
    title: "Selling to the DoW: customer discovery and the 2026 PEO directory",
    summary: "The Department of War is not one customer — it's dozens of Program Executive Offices, each with its own budget and priorities. Here's how to find yours, and the directories that map them all.",
    body: [
      { p: "Ask a first-time defense founder who their customer is and you'll hear \"the DoD\" — now the Department of War. That answer has cost startups years. The department doesn't buy as one entity: acquisition authority and budget live in Program Executive Offices, portfolio organizations that each own a family of programs — Army aviation, Navy submarines, Air Force battle management, Space Force sensing. Each PEO is, for practical purposes, a different customer with its own priorities, budget lines, and people." },
      { p: "Steve Blank (co-creator of Hacking for Defense) put the frame most cleanly in his 2025 essay How to sell to the Dept of Defense: the 2025 PEO directory — you can't do customer discovery if you can't find the customer, and the directory is how you find it. Stanford's Gordian Knot Center publishes the reference edition every year; the 2026 PEO Directory is now out with a downloadable PDF and a newsletter subscription for future editions." },
      { p: "There are two other maps you should keep alongside the Stanford directory. The Silicon Valley Defense Group's DoW Directory rounds out the picture with the innovation organizations — AFWERX, DIU, NavalX, the Tech Bridges — that serve as the front doors into those PEOs. And LookLeft's DoW/DoD PEO tracker at sites.google.com/lookleft.com/index/home publishes rolling updates on reorganizations, renames, and new PEOs faster than the annual directories can print — plus a subscribe-for-updates form worth signing up for." },
      { table: { headers: ["Source", "What it gives you", "Cadence"], rows: [
        ["Stanford Gordian Knot — 2026 PEO Directory", "Every PEO, portfolio, and leadership; the reference for who owns what", "Annual, PDF + newsletter"],
        ["SVDG — DoW Directory", "Innovation orgs and buying commands (AFWERX, DIU, NavalX, Tech Bridges)", "Community-updated"],
        ["LookLeft — DoW/DoD PEO tracker", "Reorg + rename updates between annual editions", "Rolling, subscribe for updates"],
        ["Steve Blank — 2025 PEO directory essay", "The founder's mental model + why this matters", "Blog post, canonical"],
      ] } },
      { p: "The discovery motion looks like commercial customer discovery with different nouns. Map your product to the two or three PEOs whose portfolios actually cover it. Find the program offices under them — that's where requirements are written and SBIR topics originate. Trace recent awards out of those offices to see what they really buy. Then find the named humans: the program manager, the technical point of contact on the SBIR topic, the contracting officer on the solicitation. Warm paths beat cold email: a Phase I award, an accelerator cohort, a Hacking-for-Defense connection." },
      { p: "We built this motion into CaptureAgent. The proposal workspace now has a customer card: pick your commercial market (dual-use matters — to investors and to the department), then the government customer — sector, branch, and the PEO straight from the directory structure, plus your TPOC and contracting officer. On DoW solicitations, an AI reads the solicitation and pre-fills the branch, PEO, and TPOC where they can be inferred. A directory-currency check verifies the entry is still valid against LookLeft + the Gordian Knot directory (PEOs get reorganized more often than directories get reprinted)." },
      { p: "Read the full field guide in Resources (DoW customer discovery: find your PEO before you write a line), then go find your PEO. The customer exists — the directory is how you find their address." },
    ],
    links: [
      { label: "Stanford Gordian Knot Center — 2026 PEO Directory (PDF + subscribe)", href: "https://gordianknot.fsi.stanford.edu/publication/2026-program-executive-offices-directory" },
      { label: "LookLeft — DoW/DoD PEO tracker (subscribe for rolling updates)", href: "https://sites.google.com/lookleft.com/index/home" },
      { label: "Steve Blank — How to sell to the Dept of Defense: the 2025 PEO directory", href: "https://steveblank.com/2025/09/10/how-to-sell-to-the-dept-of-defense-the-2025-peo-directory/" },
      { label: "Silicon Valley Defense Group — DoW Directory", href: "https://www.siliconvalleydefense.org/dow-directory" },
    ],
  },
  "startup-fundraising-defense": {
    date: "2026-07-18",
    tag: "FUNDRAISING",
    title: "Startup fundraising for defense founders: the playbook",
    summary: "Fundraising for a dual-use defense startup follows the same rules as any startup — with a few defense-specific twists. Here's the compressed playbook, plus the investor list from CaptureAgent's Private Capital tab.",
    body: [
      { p: "Fundraising is a distraction from building product. Steve Blank's canonical Raising Money reading list (steveblank.com/raising-money) makes the case bluntly — the more of your calendar you spend on it, the less of it you spend on the customers who will actually make you fundable. The point is to raise the least amount of money that gets you to the next milestone that de-risks the business, at the valuation the market will bear, from the investors who will help you win." },
      { p: "The defense-startup twist is that your \"market\" has two heads. Investors want to see commercial pull — recurring revenue, dual-use customers, a story that works without a DoW contract. But the DoW itself is one of the two or three biggest customers in the world, and a warm program of record (SBIR Phase II bridged into a Phase III / OTA production award) is the strongest de-risk you can bring to a Series A. So your job is: prove commercial pull, then use SBIR / OTA / DIU prototype awards to layer in defense revenue without diluting the commercial thesis." },
      { p: "Match the stage to the check. A pre-seed round funds the customer-discovery motion — most of the work here is unpaid, and the round exists to keep the lights on while you find the PEO that has the problem. A seed round funds a Phase I → Phase II transition or the first commercial pilots. A Series A funds the transition path into a program of record + repeatable commercial revenue. If a defense-only pitch is your only pitch, the venture funds that write the big checks won't lead — you'll end up with strategics (Lockheed Ventures, Boeing HorizonX) or the small defense-only funds (Shield Capital, Silent Ventures, Squadra)." },
      { p: "The mechanics don't change: minimize the amount raised, price the round only when you have leverage, use a SAFE or convertible for the pre-seed, control the runway math. Pick investors on whether they'll pick up when a program office calls asking a reference question, not on the fund size. Below is the working list of defense-active investors from CaptureAgent's Private Capital tab — this is who's actually writing checks at each stage." },
      { table: { headers: ["Investor", "Stage", "Portfolio you'll recognize"], rows: DEFENSE_INVESTORS } },
      { p: "Two more Steve Blank rules worth stealing. First: the fundraising process starts long before you send the deck — every coffee, every panel, every customer intro is you telegraphing signal to the ecosystem. Second: the term sheet you sign is the co-pilot you're going to fly with for a decade. Optimize for the partner, not the valuation." },
      { p: "Inside CaptureAgent, the Investment Deals tab drafts investor emails, decks, business plans, and financials against your live opportunity pipeline; the Private Capital tab is a running roster of these investors with fit-scored intros. Bring your own AI keys, keep your data yours, ship the raise." },
    ],
    links: [
      { label: "Steve Blank — Raising Money (the canonical reading list)", href: "https://steveblank.com/raising-money/" },
      { label: "CaptureAgent — Private Capital tab (in-app)", href: "/private-capital" },
      { label: "CaptureAgent — Investment Deals (in-app)", href: "/investment-deals" },
    ],
  },
  "defense-accelerators-founders-guide": {
    date: "2026-07-18",
    tag: "FIELD GUIDE",
    title: "Defense accelerators: what they are, how they pay, and which ones matter",
    summary: "Non-dilutive funding, warm PEO paths, and DoW sponsor relationships — the accelerator programs every dual-use founder should shortlist, plus the live list from CaptureAgent's Accelerators tab.",
    body: [
      { p: "Defense accelerators do three things for a startup that a pure VC round cannot. First, they hand you non-dilutive funding — SBIR, OTA prototype, matching STRATFI dollars — that let you build without giving up equity. Second, they give you a sponsored path into a PEO: a program manager who wants your tech, an OTA vehicle to award through, and the introductions that turn a cold email into a scheduled demo. Third, they train the founder on the acquisition system itself — the language, the paperwork, and the timing rhythms that separate proposals that get read from proposals that get scored." },
      { p: "The programs vary in what they optimize for. AFWERX and SpaceWERX are non-dilutive at massive scale — the pipeline is annualized around SBIR Phase I → Phase II → STRATFI and now Orbital Prime; you keep 100% of the equity. DIU takes commercial-tech companies straight into prototype OTAs (no SBIR gymnastics) but expects you to have real commercial traction already. Techstars Defense and MassChallenge take equity but hand you a cohort, mentors, and demo-day capital. NSIN / MD5, Hacking-for-Defense, and Catalyst focus on the founder + problem match; the money and awards come afterward. FedTech and JHU APL Discover open doors into federal labs, licensing, and facilities." },
      { p: "The right accelerator for you depends on the stage and the shape of the customer path. If you're pre-revenue with novel tech, AFWERX / SpaceWERX SBIR Phase I is the least-cost move — a $75-250k open door. If you have commercial traction and want a defense pilot, DIU's problem set is a straight prototype OTA. If you're a first-time founder without a PEO relationship, NSIN Foundry / H4D compress twelve months of customer discovery into one semester. Below is the working list from CaptureAgent's Accelerators tab — deadlines and terms change with each cycle, so verify on the program's page before you commit." },
      { table: { headers: ["Program", "Focus", "Cadence", "What you get"], rows: DEFENSE_ACCELERATORS } },
      { p: "One meta-rule: stack accelerators, don't sequence them. A Phase I with AFWERX + a Techstars Defense cohort + an NSIN Foundry problem match in the same quarter is not overreach — the milestones reinforce each other and the diligence stories compound. Every prime and every serious defense VC knows the accelerator alumni networks by heart, and the credibility they confer travels." },
      { p: "In CaptureAgent, the Accelerator Applications tab drafts a tailored application per program from your company profile and the program's own page — same fillable-form UX as a proposal, with the AI already having read the sponsor's evaluation criteria." },
    ],
    links: [
      { label: "CaptureAgent — Accelerators tab (in-app)", href: "/accelerators" },
      { label: "CaptureAgent — Accelerator Applications (in-app)", href: "/accelerator-applications" },
      { label: "AFWERX", href: "https://afwerx.com" },
      { label: "SpaceWERX", href: "https://spacewerx.us" },
      { label: "Defense Innovation Unit", href: "https://www.diu.mil" },
      { label: "NSIN (National Security Innovation Network)", href: "https://www.nsin.mil" },
    ],
  },
  "introducing-captureagent": {
    date: "2026-07-06",
    tag: "ANNOUNCEMENT",
    title: "Introducing CaptureAgent: an AI capture manager for the rest of us",
    summary: "Why we built an AI-native capture and proposal platform for small government contractors — and what it does on day one.",
    body: [
      { p: "Large primes bring proposal shops with dozens of specialists to every pursuit. Small businesses bring nights and weekends. That gap — not technical merit — decides far too many federal awards." },
      { p: "CaptureAgent is our answer: an AI capture manager that scans SAM.gov, Grants.gov, and the SBIR/STTR ecosystem for opportunities that actually fit your company, checks your eligibility against your certifications, designs a proposed capability (title, abstract, executive summary, concept rendering, statement of work, WBS with schedule, and budget), and then drafts the proposal package volume by volume — with a human reviewing, editing, and approving at every step." },
      { p: "Three principles shaped the build. First, bring your own keys: your SAM.gov and AI keys are envelope-encrypted per organization, invisible to everyone including us, with every use audited. Second, evaluator-grade output: every artifact follows the structures source-selection boards actually score. Third, governance that matches how contractors really work: AOR-certified administrators, capture managers who own the pipeline, writers who contribute without holding the keys." },
      { p: "The app is live at captureagent.us — create your workspace, plug in your keys, and pull your first tailored opportunity list in minutes. The Resources section carries our field guides: new-contractor registrations, DSIP setup, official proposal templates by agency, and the compliance stack from ITAR to CMMC." },
      { p: "We're just getting started. On the roadmap: deeper source coverage, proposal evaluation scoring, and tools for the private-capital side of building a defense company. If you win one contract you would have missed, CaptureAgent paid for itself." },
    ],
  },
};

const ORDER = [
  "defense-accelerators-founders-guide",
  "startup-fundraising-defense",
  "dow-customer-discovery-2026-peo-directory",
  "introducing-captureagent",
];

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
                    className="liquid liquid-hover group block p-6">
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
        {p.summary && <p className="mt-3 text-sm leading-relaxed text-faint">{p.summary}</p>}
        {p.body.map((block, i) => {
          if (typeof block === "string") return <p key={i} className="mt-5 text-sm leading-relaxed text-dim">{block}</p>;
          if (block.p) return <p key={i} className="mt-5 text-sm leading-relaxed text-dim">{block.p}</p>;
          if (block.table) return <BlogTable key={i} headers={block.table.headers} rows={block.table.rows} />;
          return null;
        })}
        {p.links && p.links.length > 0 && (
          <div className="mt-8 space-y-2">
            <div className="label-mono mb-1">Sources & further reading</div>
            {p.links.map((l, i) => (
              <a key={i} href={l.href} target={l.href.startsWith("/") ? "_self" : "_blank"} rel="noreferrer"
                 className="liquid liquid-hover flex items-center justify-between px-4 py-3 text-sm text-ink">
                <span>{l.label}</span>
                <ArrowRight size={13} className="text-cyan" />
              </a>
            ))}
          </div>
        )}
        <div className="liquid liquid-hover mt-12 p-5 text-center">
          <div className="text-sm font-medium text-ink">Try CaptureAgent</div>
          <Link to="/register" className="btn btn-liquid liquid-cyan mt-3 !py-2">Start Now</Link>
        </div>
      </article>
    </MarketingLayout>
  );
}
