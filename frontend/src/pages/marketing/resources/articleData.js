/* Resource article content. Rendered by Article.js.
   Block types: {h2}, {p}, {note}, {steps:[{t,d,href,hrefLabel}]}, {links:[{label,href,note}]},
   {table:{headers,rows}}, {related:[slugs]} */

export const ARTICLES = {
  /* ─────────────────────────── BYOK ─────────────────────────── */
  "bring-your-own-api-keys": {
    tag: "SETUP · 8 MIN",
    title: "Bring your own API keys",
    summary: "CaptureAgent never resells AI or data access — your organization plugs in its own keys, encrypted per-org so nobody else (including us) can read them. Here is exactly how to get each key.",
    blocks: [
      { h2: "Why bring your own keys" },
      { p: "Your keys mean your rate limits, your costs, your data agreements — and a clean security story: every key is envelope-encrypted with your organization's own data key before it touches the database, only masked previews are ever shown (even to your admin), and every use is written to your audit log." },
      { note: "All keys are entered in the app under Settings → API Keys by an organization admin. Never share keys in email or chat." },

      { h2: "1 · SAM.gov API key (federal opportunity data)" },
      { steps: [
        { t: "Sign in at SAM.gov", d: "use your Login.gov account", href: "https://sam.gov", hrefLabel: "sam.gov" },
        { t: "Open your profile", d: "click your name (top right) → Account Details" },
        { t: "Generate the Public API Key", d: "enter your password to reveal/copy it. This key powers the Get Opportunities API pulls" },
        { t: "Paste into CaptureAgent", d: "Settings → API Keys → SAM.gov" },
      ] },

      { h2: "2 · Anthropic (Claude) API key — the default AI engine" },
      { steps: [
        { t: "Create an account at the Anthropic Console", href: "https://console.anthropic.com", hrefLabel: "console.anthropic.com" },
        { t: "Add billing", d: "Settings → Billing (usage-based; set a monthly limit you're comfortable with)" },
        { t: "Create a key", d: "Settings → API Keys → Create Key. Copy it immediately — it's shown once", href: "https://console.anthropic.com/settings/keys", hrefLabel: "API keys" },
        { t: "Paste into CaptureAgent", d: "Settings → API Keys → Anthropic" },
      ] },

      { h2: "3 · OpenAI (ChatGPT) API key — optional second engine" },
      { steps: [
        { t: "Create an account at the OpenAI platform", href: "https://platform.openai.com", hrefLabel: "platform.openai.com" },
        { t: "Add billing", d: "Settings → Billing" },
        { t: "Create a secret key", href: "https://platform.openai.com/api-keys", hrefLabel: "API keys" },
        { t: "Paste into CaptureAgent", d: "Settings → API Keys → OpenAI. It appears as the ChatGPT option on drafting buttons" },
      ] },

      { h2: "4 · Google Gemini API key — optional, long-context engine" },
      { p: "Gemini 3 Pro / Flash are strong on long-context reasoning and cheap web-grounded search — a good third choice alongside Claude and ChatGPT. In CaptureAgent, Gemini shows up as a drafting engine wherever Claude and OpenAI do." },
      { steps: [
        { t: "Open Google AI Studio", href: "https://aistudio.google.com/apikey", hrefLabel: "aistudio.google.com/apikey" },
        { t: "Create an API key", d: "sign in with your Google account, click Create API key, pick the project (or create one)" },
        { t: "Add billing (for higher rate limits)", d: "the free tier is generous but limits per-minute; add a billing account for production" },
        { t: "Paste into CaptureAgent", d: "Settings → API Keys → Gemini. Available across every drafting/eval button" },
      ] },

      { h2: "5 · Emergent universal LLM key — optional" },
      { p: "If you build or host on Emergent, its universal key gives you one credential that routes to Claude / GPT / Gemini frontier models with a single balance." },
      { steps: [
        { t: "Sign in at Emergent", href: "https://app.emergent.sh", hrefLabel: "app.emergent.sh" },
        { t: "Open your profile menu", d: "look for the key icon / \"Universal Key\" (labeled Emergent LLM Key)" },
        { t: "Copy the key and top up credits", d: "the same balance covers all routed models" },
        { t: "Paste into CaptureAgent", d: "Settings → API Keys → Emergent" },
      ] },

      { h2: "6 · AskSage API key — optional, GovCon-focused AI" },
      { p: "AskSage is a government-focused AI platform (FedRAMP-authorized tiers, GovCloud hosting options) popular with defense teams that want their AI calls inside a compliance boundary." },
      { steps: [
        { t: "Create an AskSage account", href: "https://www.asksage.ai", hrefLabel: "asksage.ai" },
        { t: "Choose a plan with API access", d: "commercial accounts don't require a CAC" },
        { t: "Generate an API key", d: "in the AskSage web app: Account / API settings → generate key (see their docs)", href: "https://docs.asksage.ai", hrefLabel: "docs.asksage.ai" },
        { t: "Paste into CaptureAgent", d: "Settings → API Keys → AskSage" },
      ] },

      { h2: "7 · Overleaf Git integration token — optional, for LaTeX proposals" },
      { p: "Overleaf's Git integration lets CaptureAgent push proposal volumes to your Overleaf project and pull collaborator edits back — bidirectional sync, versioned. You need a paid Overleaf plan (Standard or Professional, personal or group) that includes Git Integration." },
      { steps: [
        { t: "Sign in to Overleaf", href: "https://www.overleaf.com", hrefLabel: "overleaf.com" },
        { t: "Open Account Settings → Git Integration", d: "the section only appears on Standard / Professional plans", href: "https://www.overleaf.com/user/settings", hrefLabel: "Account Settings" },
        { t: "Create an authentication token", d: "click Create Token → copy immediately (Overleaf shows it once)" },
        { t: "Grab your project's Git URL", d: "on the project page → Menu → Sync → Git → copy the HTTPS URL (looks like https://git.overleaf.com/<project-id>)" },
        { t: "Paste into CaptureAgent", d: "on any proposal → Overleaf panel → paste the token + project Git URL. First push seeds the project; subsequent syncs are incremental" },
      ] },
      { note: "The Overleaf token is a Git password with read/write on every project on your account — treat it as sensitive. Rotate from the same Account Settings page any time. Overleaf's docs on git integration authentication: overleaf.com/learn/how-to/Using_Git_and_GitHub." },

      { h2: "What each proposal costs to draft end-to-end" },
      { p: "With your own keys, a full CaptureAgent proposal cycle — scan for the opportunity, draft the volumes, run the AI color-team evaluation, edit, and export — typically costs $5-10 in AI credits per proposal. Compare with $8,000-25,000 for a boutique proposal shop or a fractional capture manager. Effort and model choice (Claude Sonnet vs. Opus, Gemini Flash vs. Pro) move the number within that range; the app shows the running cost on every AI button." },

      { h2: "Where the keys go and who can touch them" },
      { table: { headers: ["Key", "Used for", "Who can manage"],
        rows: [
          ["SAM.gov", "Pulling live federal opportunities", "Org admin"],
          ["Anthropic (Claude)", "Deep scans, verification, capability & proposal drafting (default engine)", "Org admin"],
          ["OpenAI", "Alternate drafting engine", "Org admin"],
          ["Gemini (Google)", "Long-context reasoning, cheap web-grounded search", "Org admin"],
          ["Emergent", "Alternate drafting engine (routed models)", "Org admin"],
          ["AskSage", "Alternate drafting engine inside a Gov compliance boundary", "Org admin"],
          ["Overleaf Git token", "Bidirectional LaTeX sync between CaptureAgent and Overleaf projects", "Per proposal (any editor)"],
        ] } },
      { p: "Members use the keys through the app's buttons without ever seeing them. Admins can rotate the org's encryption key at any time from Settings." },
      { note: "Not on the Small Teams plan? Disk storage, the AI chat assistant, and the drafting engines above require the Small Teams tier. The Starter tier ($49.99/user/mo) still gives you AI-scored opportunities, competitive analysis, and the private-capital + accelerator scans — see /pricing for the full comparison." },
      { related: ["new-contractor-setup", "compliance", "defense-startup-resources"] },
    ],
  },

  /* ─────────────────────── New contractor setup ─────────────────────── */
  "new-contractor-setup": {
    tag: "GETTING STARTED · 12 MIN",
    title: "The new GovCon founder's setup checklist: registrations & certifications",
    summary: "Everything a new venture needs before it can win federal work — SAM.gov and your UEI, CAGE code, D-U-N-S, and your SBA/SBIR identifiers — in the right order, with zero paid middlemen.",
    blocks: [
      { note: "Every registration on this page is FREE. Companies that email offering to \"complete your SAM registration\" for a fee are not the government — you never need them." },

      { h2: "1 · SAM.gov registration (and your UEI)" },
      { p: "SAM.gov is the government's master vendor list. Registering issues your Unique Entity ID (UEI) — the 12-character identifier that replaced the DUNS number for federal awards in April 2022 — and makes you eligible to bid and get paid." },
      { steps: [
        { t: "Gather your info", d: "exact legal business name and physical address (must match your incorporation docs), EIN from the IRS, bank account + routing for EFT, and your NAICS codes" },
        { t: "Create a Login.gov account", href: "https://login.gov", hrefLabel: "login.gov" },
        { t: "Start the entity registration at SAM.gov", d: "choose \"Register Entity\" (full registration — not \"Unique Entity ID only\" — if you want to bid on contracts)", href: "https://sam.gov/content/entity-registration", hrefLabel: "sam.gov entity registration" },
        { t: "Complete Core Data, Assertions, Reps & Certs, and POCs", d: "the Reps & Certs section is where you make your small-business and Section 889 representations" },
        { t: "Validate and wait", d: "entity validation + IRS/CAGE checks typically take days to a few weeks. Renew annually — set a reminder" },
      ] },

      { h2: "2 · CAGE code" },
      { p: "The Commercial and Government Entity (CAGE) code is assigned automatically to U.S. companies during SAM registration — there is no separate application. You'll find it in your SAM entity record once registration is active." },
      { steps: [
        { t: "Complete SAM registration first", d: "CAGE assignment happens during SAM processing (DLA runs the CAGE program)" },
        { t: "Look it up or request changes at the DLA CAGE portal", href: "https://cage.dla.mil", hrefLabel: "cage.dla.mil" },
      ] },

      { h2: "3 · D-U-N-S number" },
      { p: "The federal government no longer uses DUNS — the UEI replaced it. You only need a D-U-N-S number for commercial credit, some state/local governments, some primes' supplier systems, and international work." },
      { steps: [
        { t: "If a customer or prime asks for one, get it free from Dun & Bradstreet", href: "https://www.dnb.com/duns.html", hrefLabel: "dnb.com/duns" },
        { t: "Skip it otherwise", d: "for federal proposals your UEI + CAGE are what matter" },
      ] },

      { h2: "4 · SBA profile and your SBC Control ID (for SBIR/STTR)" },
      { steps: [
        { t: "Confirm your small-business status flows to SBA", d: "your SAM registration feeds the Dynamic Small Business Search (DSBS) profile — complete it; contracting officers actually search it", href: "https://dsbs.sba.gov", hrefLabel: "dsbs.sba.gov" },
        { t: "Create an SBA.gov account for certifications", d: "8(a), HUBZone, WOSB, and VetCert applications run through SBA's certification portals", href: "https://certifications.sba.gov", hrefLabel: "certifications.sba.gov" },
        { t: "Register your company at SBIR.gov", d: "this issues your SBC Control ID (format SBC_123456789) — required on every SBIR/STTR proposal, including DoW DSIP and NASA submissions", href: "https://www.sbir.gov", hrefLabel: "sbir.gov" },
        { t: "Record everything in CaptureAgent", d: "Company Profile → UEI, CAGE, certifications, size status — the AI uses these for eligibility checks on every opportunity" },
      ] },

      { h2: "Suggested order (about 2–4 weeks total)" },
      { table: { headers: ["Week", "Do", "Output"], rows: [
        ["1", "Login.gov + SAM.gov registration", "UEI immediately; registration processing"],
        ["1–3", "SAM validation completes", "Active SAM record + CAGE code"],
        ["2", "SBIR.gov company registry", "SBC Control ID"],
        ["2–4", "DSBS profile + SBA certifications (as applicable)", "Discoverable small-business profile"],
      ] } },
      { related: ["selling-to-the-department-of-war", "bring-your-own-api-keys", "compliance"] },
    ],
  },

  /* ─────────────────────── DoW / DSIP ─────────────────────── */
  "selling-to-the-department-of-war": {
    tag: "GETTING STARTED · 6 MIN",
    title: "Selling to the Department of War: set up your DSIP account",
    summary: "DSIP is the Department of War's one front door for SBIR/STTR — topic search, Q&A, and every proposal submission. Here's how a new firm gets in.",
    blocks: [
      { p: "The DoW SBIR/STTR Innovation Portal (DSIP) is the only place DoW SBIR/STTR proposals are accepted — proposals submitted any other way are disregarded. Army, Air Force/Space Force (AFWERX/SpaceWERX), Navy, DARPA, MDA, SOCOM and the other components all publish their topics through it." },
      { h2: "Before you start" },
      { steps: [
        { t: "Finish the basics", d: "active SAM.gov registration with UEI + CAGE, and your SBC Control ID from SBIR.gov (see the setup checklist below)" },
        { t: "Create a Login.gov account", d: "DSIP authenticates exclusively through Login.gov — use the email you want tied to your firm", href: "https://login.gov", hrefLabel: "login.gov" },
      ] },
      { h2: "Create your DSIP account" },
      { steps: [
        { t: "Go to the DSIP portal and select Submit → Register", href: "https://www.dodsbirsttr.mil", hrefLabel: "dodsbirsttr.mil" },
        { t: "Link your Login.gov identity", d: "first sign-in walks you through it" },
        { t: "Register your firm", d: "enter UEI, CAGE, SBC Control ID, and firm demographics; the first registrant becomes the Firm Admin who can add teammates" },
        { t: "Explore Topic Search and the Q&A window", d: "you can ask the topic authors questions before the close of Q&A — use it" },
        { t: "Study the volume structure before you write", d: "DoW proposals are multi-volume (Coversheet, Technical, Cost, Company Commercialization Report, and topic-specific supporting docs) with hard formatting rules" },
      ] },
      { h2: "Official learning & templates" },
      { links: [
        { label: "DSIP Learning & Support — firm templates", href: "https://www.dodsbirsttr.mil/submissions/learning-support/firm-templates", note: "Official technical-volume and commercialization templates" },
        { label: "DSIP training materials", href: "https://www.dodsbirsttr.mil/submissions/learning-support/training-materials", note: "Walkthroughs of registration and submission" },
        { label: "Solicitation supporting documents", href: "https://www.dodsbirsttr.mil/submissions/solicitation-documents/supporting-documents", note: "Component-specific instructions per BAA cycle" },
      ] },
      { note: "Support: DoDSBIRSupport@reisystems.com. Start your submission days early — DSIP locks at the deadline, and certifications (like the fraud/felony certs and foreign-disclosure questions) take longer than you think." },
      { related: ["new-contractor-setup", "proposal-templates", "compliance-dow-proposal-docs"] },
    ],
  },

  /* ─────────────────── DoW customer discovery / PEO directory ─────────────────── */
  "dow-customer-discovery-peo-directory": {
    tag: "GETTING STARTED · 9 MIN",
    title: "DoW customer discovery: find your PEO before you write a line",
    summary: "The Department of War buys through Program Executive Offices — find the PEO that owns your problem, the program office under it, and the human beings (TPOC, contracting officer) who can actually move your deal.",
    blocks: [
      { p: "Startups lose years pitching the wrong part of the Department of War. The military services don't buy as one customer: money and authority live in Program Executive Offices (PEOs) — portfolio organizations, each run by a general officer or SES, each owning the program offices that actually write requirements and spend budget. Customer discovery in defense means finding which PEO owns your problem, then which program office under it, then the named people: the program manager, the technical point of contact (TPOC), and the contracting officer (KO)." },
      { h2: "Start with the directory, not the org chart" },
      { p: "Stanford's Gordian Knot Center publishes the field's reference document: a directory of every DoW PEO with its portfolio and leadership. Read it the way you'd read a market map — each PEO is a market segment with its own budget line, and the directory tells you who runs it." },
      { links: [
        { label: "Stanford Gordian Knot Center — 2026 Program Executive Offices Directory", href: "https://gordianknot.fsi.stanford.edu/publication/2026-program-executive-offices-directory", note: "The reference document — every DoW PEO, portfolio, and leadership, updated for 2026. The PDF and the newsletter subscription are both on this page" },
        { label: "Silicon Valley Defense Group — DoW Directory", href: "https://www.siliconvalleydefense.org/dow-directory", note: "Community-maintained navigator across DoW innovation orgs and buying commands" },
        { label: "Steve Blank — How to sell to the Dept of Defense: the 2025 PEO directory", href: "https://steveblank.com/2025/09/10/how-to-sell-to-the-dept-of-defense-the-2025-peo-directory/", note: "Why the PEO directory exists and how founders should use it — from the co-creator of Hacking for Defense" },
      ] },
      { note: "Directories age. PEOs get created, merged, and renamed with every reorganization — verify a PEO still exists on the service's own acquisition page before you build your capture plan on it. Inside CaptureAgent, the proposal customer card has an AI currency check that does exactly this." },
      { h2: "The discovery motion, step by step" },
      { steps: [
        { t: "Map your product to 2-3 candidate PEOs", d: "read the portfolio descriptions in the 2026 directory; your tech usually fits fewer places than you think" },
        { t: "Find the program offices under each PEO", d: "PEOs contain program offices (PM shops) — the level where requirements are written and SBIR topics originate" },
        { t: "Trace recent money", d: "search USASpending for awards out of those offices (CaptureAgent's Competitive Analysis tab does this) — who they fund tells you what they actually buy" },
        { t: "Identify the humans", d: "SBIR topics name a TPOC; solicitations name the contracting officer; industry days and program-office pages name the PMs" },
        { t: "Get the meeting through a warm path", d: "an SBIR Phase I, an accelerator demo day (see the Accelerators tab), a Tech Bridge / AFWERX / DIU front door, or your Hacking-for-Defense network" },
        { t: "Validate the problem before proposing", d: "classic customer discovery: does this office have the problem, the budget line, and a transition path? If not, next PEO" },
      ] },
      { h2: "Use it inside CaptureAgent" },
      { p: "When you draft a proposal, the customer card asks for the commercial market you serve and the government customer: sector (civil / defense / intelligence community), then branch, then the PEO from this directory structure, then your TPOC and contracting officer. The AI check button verifies the directory entry is still current before you commit a capture plan to it." },
      { note: "Want directory updates in your inbox? The Gordian Knot Center page includes a newsletter subscription — sign up there for future editions." },
      { related: ["selling-to-the-department-of-war", "new-contractor-setup", "defense-startup-resources"] },
    ],
  },

  /* ─────────────────────── Templates hub + agencies ─────────────────────── */
  "proposal-templates": {
    tag: "TEMPLATES",
    title: "Official proposal templates, by agency",
    summary: "Always draft against the agency's own current templates — evaluators notice. These pages link only to official, current sources.",
    blocks: [
      { links: [
        { label: "NASA — SBIR / STTR / SBIR Ignite templates →", href: "/resources/templates-nasa", note: "Firms Library, EHB templates, PY2026 info hub" },
        { label: "Department of War — DSIP templates →", href: "/resources/templates-dow", note: "Firm templates, per-BAA supporting documents" },
        { label: "Department of Energy — SBIR/STTR application resources →", href: "/resources/templates-doe", note: "Application guide, sample forms, Phase 0 tutorials" },
      ] },
      { note: "Templates change every solicitation cycle. CaptureAgent links to the agencies' live pages instead of hosting copies, so you always land on the current version. The links above open inside this site's resource pages; the pages then link out to the agencies." },
      { related: ["selling-to-the-department-of-war", "compliance"] },
    ],
  },

  "templates-nasa": {
    tag: "TEMPLATES · NASA",
    title: "NASA SBIR / STTR / Ignite proposal templates",
    summary: "NASA maintains a Firms Library with the official Phase I and Phase II proposal forms, plus the PY2026 solicitation hub.",
    blocks: [
      { links: [
        { label: "NASA SBIR/STTR Firms Library", href: "https://www.nasa.gov/sbir_sttr/firms_library/", note: "Official proposal forms: SBIR/STTR Phase I & II, BAA resources" },
        { label: "PY2026 Information Hub", href: "https://www.nasa.gov/sbir_sttr/nasa-sbir-sttr-program-program-year-2026-information-hub/", note: "Current BAA (released Apr 17 2026, valid through Sept 30 2027)" },
        { label: "Firm templates in the Submissions EHB", href: "https://sbir.gsfc.nasa.gov/submissions/firm-templates", note: "Downloadable technical-proposal and forms templates" },
        { label: "Program resources", href: "https://www.nasa.gov/sbir_sttr/program-resources/", note: "Guidance, FAQs, and submission systems (ProSAMS)" },
        { label: "NASA SBIR/STTR home (incl. SBIR Ignite cycles)", href: "https://www.nasa.gov/sbir_sttr/", note: "Ignite is NASA's commercialization-first SBIR track — watch this page for its solicitations" },
      ] },
      { note: "NASA submissions flow through ProSAMS — register early, and confirm your SBC Control ID and SAM registration are active before the deadline week." },
      { related: ["proposal-templates", "new-contractor-setup"] },
    ],
  },

  "templates-dow": {
    tag: "TEMPLATES · DEPT. OF WAR",
    title: "Department of War (DSIP) proposal templates",
    summary: "DoW SBIR/STTR templates live inside DSIP's Learning & Support area, with component-specific instructions attached to each BAA.",
    blocks: [
      { links: [
        { label: "DSIP firm templates", href: "https://www.dodsbirsttr.mil/submissions/learning-support/firm-templates", note: "Official technical volume & commercialization report templates" },
        { label: "Solicitation supporting documents", href: "https://www.dodsbirsttr.mil/submissions/solicitation-documents/supporting-documents", note: "Component instructions (Army, AF/AFWERX, Navy, DARPA…) per cycle" },
        { label: "Example: Phase I Technical Volume (Vol. 2) template", href: "https://media.defense.gov/2022/Jul/07/2003031165/-1/-1/0/PhaseI_Tech_Vol2_Template.DOCX", note: "Representative structure — always use the current cycle's version" },
        { label: "DSIP training materials", href: "https://www.dodsbirsttr.mil/submissions/learning-support/training-materials" },
      ] },
      { note: "Each component adds its own requirements on top of the DoW-wide BAA (page limits, mandatory sections, pitch decks for AFWERX open topics). Read the component instructions for your specific topic before outlining." },
      { related: ["selling-to-the-department-of-war", "compliance-dow-proposal-docs"] },
    ],
  },

  "templates-doe": {
    tag: "TEMPLATES · DOE",
    title: "Department of Energy SBIR/STTR application resources",
    summary: "DOE's Office of Science publishes a step-by-step application guide, sample completed forms, and a free Phase 0 tutorial series.",
    blocks: [
      { links: [
        { label: "DOE grant application resources", href: "https://science.osti.gov/sbir/Applicant-Resources/Grant-Application", note: "Step-by-step instructions, sample documents, and templates per section" },
        { label: "Phase I Application Guide (PDF)", href: "https://science.osti.gov/-/media/sbir/pdf/Application_Resources/2023/DOE-SBIR-STTR-Programs-Phase-I-Application_Guide-8-2023.pdf", note: "Component-by-component walkthrough of the package" },
        { label: "Phase 0 Learning Management System", href: "https://science.osti.gov/SBIRLearning", note: "Free tutorial course on preparing a DOE Phase I proposal" },
        { label: "DOE SBIR funding opportunities", href: "https://science.osti.gov/sbir/Funding-Opportunities" },
      ] },
      { note: "DOE runs on grants (via Grants.gov + PAMS), not contracts — the forms differ from DoW's. Budget justification and the commercialization plan carry heavy weight." },
      { related: ["proposal-templates", "new-contractor-setup"] },
    ],
  },

  /* ─────────────────────── Compliance hub + categories ─────────────────────── */
  "compliance": {
    tag: "COMPLIANCE",
    title: "GovCon compliance, mapped: what you need and when",
    summary: "The compliance stack that unlocks defense work — each category below has its own step-by-step page with the exact forms.",
    blocks: [
      { links: [
        { label: "ITAR / EAR + DD Form 2345 →", href: "/resources/compliance-itar-ear", note: "Export control registration and the JCP certification for controlled technical data" },
        { label: "CMMC & NIST SP 800-171 (with POA&Ms) →", href: "/resources/compliance-cmmc", note: "The cybersecurity bar for handling CUI on DoW contracts" },
        { label: "Facility Clearance (FCL) →", href: "/resources/compliance-fcl", note: "SF-328, DD-441, and DCSA sponsorship for classified work" },
        { label: "Personnel security clearances →", href: "/resources/compliance-clearances", note: "SF-86 / e-QIP and how new companies sponsor people" },
        { label: "Authority to Operate (ATO) →", href: "/resources/compliance-ato", note: "NIST RMF: SSP, assessment, POA&M, authorization" },
        { label: "FedRAMP →", href: "/resources/compliance-fedramp", note: "If you sell cloud software to civilian or defense agencies" },
        { label: "DoW proposal-day documents →", href: "/resources/compliance-dow-proposal-docs", note: "Section 889, data rights, foreign disclosure — the certs every DoW proposal asks for" },
      ] },
      { table: { headers: ["When", "You need"], rows: [
        ["Bidding anything federal", "Active SAM + reps & certs (incl. Section 889)"],
        ["Topic involves export-controlled tech data", "DD 2345 (JCP) — often before you can even read attachments"],
        ["Contract will touch CUI", "NIST 800-171 self-assessment score in SPRS → CMMC Level 2"],
        ["Classified work", "FCL for the company + clearances for the people"],
        ["Your software runs on a government network", "ATO under the agency's RMF"],
        ["You sell SaaS to agencies", "FedRAMP authorization (or an agency sponsor)"],
      ] } },
      { related: ["compliance-cmmc", "compliance-itar-ear", "compliance-dow-proposal-docs"] },
    ],
  },

  "compliance-itar-ear": {
    tag: "COMPLIANCE · EXPORT CONTROL",
    title: "ITAR / EAR and the DD Form 2345",
    summary: "Export control is the first compliance wall most defense startups hit — often just to download topic attachments.",
    blocks: [
      { h2: "ITAR vs. EAR in one minute" },
      { p: "ITAR (State Department / DDTC) governs defense articles and services on the U.S. Munitions List. EAR (Commerce / BIS) governs dual-use items on the Commerce Control List. If you manufacture or export defense articles — even without exporting anything — ITAR registration with DDTC is required." },
      { steps: [
        { t: "Determine jurisdiction", d: "is your tech USML (ITAR) or CCL (EAR)? When unsure, file a Commodity Jurisdiction request with DDTC" },
        { t: "Register with DDTC if ITAR applies", d: "Statement of Registration (DS-2032) through the DECCS portal; annual fee applies", href: "https://www.pmddtc.state.gov", hrefLabel: "pmddtc.state.gov" },
        { t: "Build an export-control program", d: "technology control plan, employee training, foreign-person access controls" },
      ] },
      { h2: "DD Form 2345 — Militarily Critical Technical Data Agreement (JCP)" },
      { p: "The Joint Certification Program (JCP) certification lets a U.S. or Canadian contractor receive export-controlled unclassified technical data from the DoW. Many DSIP topics require it before you can open the technical package." },
      { steps: [
        { t: "Complete DLA's export-control training", d: "\"Introduction to Proper Handling of DoD Export-Controlled Technical Data\" — mandatory prerequisite" },
        { t: "Download the DD 2345", href: "https://www.esd.whs.mil/Portals/54/Documents/DD/forms/dd/dd2345.pdf", hrefLabel: "official form (PDF)" },
        { t: "Fill it out typed, not handwritten", d: "follow DLA's line-by-line instructions", href: "https://www.dla.mil/Portals/104/Documents/J3LogisticOperations/FIC/JCP/J3_DDForm2345Instructions(Oct2022)_221005.pdf", hrefLabel: "DLA instructions (PDF)" },
        { t: "Email the signed PDF to JCP-ADMIN@dla.mil", d: "U.S. firms no longer need supporting legitimacy docs (Canadian firms do)" },
        { t: "Renew every 5 years", d: "send the renewal at least 60 days before expiration" },
      ] },
      { related: ["compliance", "compliance-dow-proposal-docs"] },
    ],
  },

  "compliance-cmmc": {
    tag: "COMPLIANCE · CYBERSECURITY",
    title: "CMMC & NIST SP 800-171: levels, POA&Ms, and your SPRS score",
    summary: "If a DoW contract touches Controlled Unclassified Information, CMMC is the gate. Here's the small-business path through it.",
    blocks: [
      { h2: "The timeline that matters" },
      { p: "Since November 10, 2025, applicable new DoW contracts require at least a CMMC Level 2 self-assessment against NIST SP 800-171 Rev 2. Beginning November 10, 2026, third-party (C3PAO) assessments phase in for applicable contracts. Level 1 (FCI only) stays a 17-practice annual self-assessment." },
      { h2: "Small-business path, step by step" },
      { steps: [
        { t: "Scope your CUI environment", d: "the smaller the enclave that touches CUI, the cheaper everything gets (many startups use a compliant cloud enclave)" },
        { t: "Write your System Security Plan (SSP)", d: "control-by-control statement of how you meet the 110 requirements" },
        { t: "Self-assess with the DoW methodology", d: "score range −203 to +110", href: "https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf", hrefLabel: "Level 2 Assessment Guide (PDF)" },
        { t: "Post your score in SPRS", d: "required by DFARS 252.204-7019/7020 — primes check it before teaming" },
        { t: "Open a POA&M for the gaps", d: "only about one-third of controls are POA&M-eligible under 32 CFR 170, and every POA&M item must close within 180 days" },
        { t: "Prepare for certification", d: "if your contracts will require C3PAO assessment, book early — assessor capacity is tight" },
      ] },
      { h2: "Official references" },
      { links: [
        { label: "CMMC: What Every DoW Contractor Needs to Know (PDF)", href: "https://business.defense.gov/Portals/57/Documents/1%20pagers/CMMC%20What%20Every%20DoD%20Contactor%20Needs%20to%20Know.pdf", note: "The one-pager circulated to small businesses (incl. via AFWERX outreach)" },
        { label: "DoW CIO — CMMC FAQs (PDF)", href: "https://dowcio.war.gov/Portals/0/Documents/CMMC/CMMC-FAQsv5.pdf" },
        { label: "CMMC alignment to NIST standards (PDF)", href: "https://dodcio.defense.gov/Portals/0/Documents/CMMC/CMMC-AlignmentNIST-Standards.pdf" },
      ] },
      { note: "CaptureAgent itself is designed to stay outside your CUI boundary: keep CUI out of the workspace, and it never needs to be in scope." },
      { related: ["compliance", "compliance-ato"] },
    ],
  },

  "compliance-fcl": {
    tag: "COMPLIANCE · CLASSIFIED",
    title: "Facility Clearance (FCL): SF-328, DD-441, and sponsorship",
    summary: "A company can't request its own FCL — a government customer or cleared prime sponsors you. Here's the paperwork that follows.",
    blocks: [
      { steps: [
        { t: "Get sponsored", d: "a contracting officer or a cleared prime submits the sponsorship request to DCSA tied to a classified requirement — you cannot self-sponsor" },
        { t: "Register in NISS", d: "DCSA's National Industrial Security System is where the FCL package and your facility profile live", href: "https://www.dcsa.mil/Industrial-Security/", hrefLabel: "DCSA industrial security" },
        { t: "Submit the SF-328", d: "Certificate Pertaining to Foreign Interests — the FOCI questionnaire; answer precisely, foreign ownership/control drives mitigation requirements" },
        { t: "Execute the DD Form 441", d: "the Security Agreement between your company and the government" },
        { t: "Identify Key Management Personnel (KMP)", d: "officers/owners who must be cleared or excluded; appoint your Facility Security Officer (FSO)" },
        { t: "FSO completes DCSA training", d: "and stands up your insider-threat program" },
      ] },
      { note: "Timeline reality: months, not weeks — and personnel clearances (next article) usually run in parallel once the FCL is in process." },
      { related: ["compliance-clearances", "compliance"] },
    ],
  },

  "compliance-clearances": {
    tag: "COMPLIANCE · CLASSIFIED",
    title: "Personnel security clearances: SF-86 and sponsoring your team",
    summary: "People get clearances only through a sponsoring contract — here's the flow for a small company's first cleared hires.",
    blocks: [
      { steps: [
        { t: "Win or team onto a classified requirement", d: "the contract (DD-254 attachment) authorizes clearance sponsorship" },
        { t: "FSO initiates the investigation", d: "in DISS/NBIS, tied to your FCL" },
        { t: "Employee completes the SF-86", d: "the Questionnaire for National Security Positions, filled out in e-QIP/eApp — thorough and honest beats fast; omissions kill timelines" },
        { t: "Fingerprints + investigation", d: "Tier 3 for Secret, Tier 5 for Top Secret" },
        { t: "Interim eligibility often arrives in weeks", d: "final adjudication can take months; plan staffing around interims" },
        { t: "Maintain it", d: "continuous vetting now replaces most periodic reinvestigations — report foreign travel and reportable events through your FSO" },
      ] },
      { related: ["compliance-fcl", "compliance"] },
    ],
  },

  "compliance-ato": {
    tag: "COMPLIANCE · SYSTEMS",
    title: "Authority to Operate (ATO): the RMF package",
    summary: "If your software runs on a government network or processes government data, an Authorizing Official has to accept the risk — that's the ATO.",
    blocks: [
      { p: "ATOs follow the NIST Risk Management Framework (SP 800-37). The DoW runs it in eMASS; each agency has its own instantiation. Expect the process to be owned by your government program office, with you producing the evidence." },
      { steps: [
        { t: "Categorize the system", d: "FIPS 199 impact levels (confidentiality/integrity/availability)" },
        { t: "Select & tailor controls", d: "NIST SP 800-53 baseline for the category" },
        { t: "Implement and document — the SSP", d: "the System Security Plan is the anchor document" },
        { t: "Assess", d: "an independent assessor produces the Security Assessment Report (SAR)" },
        { t: "POA&M the residual gaps", d: "with dates and owners" },
        { t: "Authorize", d: "the AO signs the ATO letter (often 3-year, increasingly continuous)" },
        { t: "Monitor", d: "continuous monitoring keeps the ATO alive" },
      ] },
      { note: "Startup shortcut: platforms with existing ATOs (e.g., Platform One's cATO environments) let you inherit most controls and ship months faster." },
      { related: ["compliance-fedramp", "compliance-cmmc"] },
    ],
  },

  "compliance-fedramp": {
    tag: "COMPLIANCE · CLOUD",
    title: "FedRAMP: selling cloud software to the government",
    summary: "FedRAMP is the government-wide security authorization for cloud services — one authorization, reusable by every agency.",
    blocks: [
      { steps: [
        { t: "Confirm you actually need it", d: "FedRAMP applies to cloud services holding federal data; on-prem software and pure DoW paths (Impact Levels via DISA) differ" },
        { t: "Pick your path", d: "an agency sponsor authorizes you for their use (most common), or pursue the program's newer streamlined paths (FedRAMP 20x)" },
        { t: "Build to the baseline", d: "Low/Moderate/High per FIPS 199; FIPS-validated crypto everywhere" },
        { t: "Produce the package from official templates", d: "SSP + appendices, policies, incident response, POA&M", href: "https://www.fedramp.gov/documents-templates/", hrefLabel: "fedramp.gov templates" },
        { t: "Third-party assessment (3PAO)", d: "accredited assessor tests and writes the SAR" },
        { t: "Authorization + continuous monitoring", d: "monthly scans, annual assessments, listed in the FedRAMP Marketplace" },
      ] },
      { related: ["compliance-ato", "compliance"] },
    ],
  },

  "compliance-dow-proposal-docs": {
    tag: "COMPLIANCE · PROPOSAL DAY",
    title: "The documents DoW proposals actually ask for",
    summary: "Beyond the technical volume, DoW submissions carry a stack of certifications. Miss one and you're non-compliant regardless of merit.",
    blocks: [
      { table: { headers: ["Document / representation", "What it is", "Where it lives"], rows: [
        ["Section 889 representations", "Certifying you don't use/provide covered Chinese telecom & video-surveillance equipment (Huawei, ZTE, Hikvision, Dahua, Hytera) — FAR 52.204-24/25/26", "SAM Reps & Certs + per-proposal certs"],
        ["Covered-country / foreign disclosure", "Disclosure of foreign ownership, control, funding ties (incl. the DSIP \"Disclosures of Foreign Affiliations\" forms)", "DSIP proposal volumes"],
        ["ITAR/export compliance statement", "Acknowledging export-control obligations for controlled topics", "Proposal cert section"],
        ["DD Form 2345 (JCP)", "Required to access export-controlled technical data topics", "On file with DLA (see ITAR/EAR article)"],
        ["NIST SP 800-171 score (SPRS)", "Current self-assessment posted — DFARS 252.204-7019/7020", "SPRS via PIEE"],
        ["Data rights assertions", "DFARS 252.227-7017 table of noncommercial tech data/software you're restricting", "Proposal cost/admin volume"],
        ["OCI disclosure", "Organizational conflicts of interest statement", "Proposal admin section"],
        ["Fraud/felony & tax certs", "Standard responsibility certifications", "DSIP firm certs"],
        ["Human subjects / animal use", "Extra approvals if research involves either", "Topic-specific attachment"],
      ] } },
      { note: "Every BAA lists its exact set — treat this table as your pre-flight checklist, then reconcile against the current solicitation. CaptureAgent's compliance checklist on each opportunity is built for exactly this reconciliation." },
      { related: ["compliance-itar-ear", "compliance-cmmc", "selling-to-the-department-of-war"] },
    ],
  },

  /* ─────────────────────── Startup fundraising ─────────────────────── */
  "startup-fundraising-defense": {
    tag: "FUNDRAISING · 12 MIN",
    title: "Startup fundraising for defense founders: the playbook",
    summary: "Fundraising for a dual-use defense startup follows the same rules as any startup — with a few defense-specific twists. Here is the compressed playbook, plus the working list of defense-active investors from CaptureAgent's Private Capital tab.",
    blocks: [
      { p: "Fundraising is a distraction from building product. Steve Blank's canonical Raising Money reading list makes the point bluntly — the more of your calendar you spend on fundraising, the less of it you spend on the customers who make you fundable. The point of a round is to raise the LEAST amount of money that gets you to the next milestone that de-risks the business, at the valuation the market will bear, from the investors who will help you win." },
      { note: "Steve Blank's full Raising Money reading list — the definitive founder resource — is at steveblank.com/raising-money/. Read it before you cold-email a VC." },

      { h2: "The defense-startup twist" },
      { p: "Your market has two heads. Investors want to see commercial pull — recurring revenue, dual-use customers, a story that works without a DoW contract. But the DoW is one of the two or three biggest customers in the world, and a warm program of record (SBIR Phase II bridged into a Phase III / OTA production award) is the strongest de-risk you can bring to a Series A. Prove commercial pull, then use SBIR / OTA / DIU prototype awards to layer in defense revenue without diluting the commercial thesis." },

      { h2: "Match the stage to the check" },
      { steps: [
        { t: "Pre-seed / friends & family", d: "funds the customer-discovery motion. Most of the work here is unpaid — the round exists to keep the lights on while you find the PEO that has the problem" },
        { t: "Seed", d: "funds a Phase I → Phase II transition or the first commercial pilots. SAFE or convertible; do NOT overprice this round" },
        { t: "Series A", d: "funds the transition path into a program of record plus repeatable commercial revenue. Priced round with an institutional lead" },
        { t: "Series B+", d: "funds scale-up manufacturing / hiring against a real production award and named commercial customers" },
      ] },
      { p: "If a defense-only pitch is your only pitch, the venture funds that write the big checks won't lead — you'll end up with strategics (Lockheed Ventures, Boeing HorizonX) or the small defense-only funds (Shield Capital, Silent Ventures, Squadra Ventures). That is fine at seed, harder at Series A." },

      { h2: "Steve Blank's rules worth stealing" },
      { steps: [
        { t: "Start long before you send the deck", d: "every coffee, every panel, every customer intro telegraphs signal to the ecosystem — investors buy conviction, then equity" },
        { t: "Pick the partner, not the fund", d: "the term sheet is a ten-year co-pilot; optimize for who picks up when the program office calls asking a reference question" },
        { t: "Minimize round size", d: "raising more than you need at a too-high price prices you out of the next round" },
        { t: "Control the runway math", d: "18 months of runway with 6-9 months of milestone-hitting; anything less turns the next raise into a fire sale" },
      ] },

      { h2: "Defense-active investors (from the Private Capital tab)" },
      { p: "These are the funds actively writing checks into US defense / space / dual-use startups today. Portfolio examples are illustrative — CaptureAgent's Private Capital tab keeps a live, fit-scored version keyed to your company profile." },
      { table: { headers: ["Investor", "Stage", "Portfolio you'll recognize"], rows: [
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
      ] } },

      { h2: "Use it inside CaptureAgent" },
      { p: "The Investment Deals tab drafts investor emails, decks, business plans, and financials against your live opportunity pipeline. The Private Capital tab runs a live AI scan against your company profile to score which investors on the list — plus any new ones on the open web — actually fit your stage and thesis." },
      { links: [
        { label: "Steve Blank — Raising Money reading list", href: "https://steveblank.com/raising-money/", note: "The canonical founder reference on raising money" },
        { label: "Steve Blank — How to sell to the Dept of Defense (2025 PEO directory)", href: "https://steveblank.com/2025/09/10/how-to-sell-to-the-dept-of-defense-the-2025-peo-directory/", note: "Companion reading on the customer side of the pitch" },
        { label: "OpenVC — defense-tech investor list", href: "https://www.openvc.app/investor-lists/defensetech-investors", note: "Community-maintained, larger sweep" },
      ] },
      { related: ["defense-accelerators", "dow-customer-discovery-peo-directory", "defense-startup-resources"] },
    ],
  },

  /* ─────────────────────── Defense accelerators ─────────────────────── */
  "defense-accelerators": {
    tag: "FIELD GUIDE · 10 MIN",
    title: "Defense accelerators: what they are, how they pay, and which ones to shortlist",
    summary: "Non-dilutive funding, warm PEO paths, and DoW sponsor relationships — the accelerator programs every dual-use founder should know, plus the live list from CaptureAgent's Accelerators tab.",
    blocks: [
      { p: "Defense accelerators do three things for a startup that a pure VC round cannot. First, they hand you non-dilutive funding — SBIR, OTA prototype, matching STRATFI dollars — that let you build without giving up equity. Second, they give you a sponsored path into a PEO: a program manager who wants your tech, an OTA vehicle to award through, and the introductions that turn a cold email into a scheduled demo. Third, they train the founder on the acquisition system — the language, the paperwork, and the timing rhythms that separate proposals that get read from proposals that get scored." },

      { h2: "What each type of program optimizes for" },
      { steps: [
        { t: "Non-dilutive, at scale — AFWERX / SpaceWERX / DIU / MDA CSO", d: "annualized SBIR + OTA pipelines. You keep 100% of equity; the trade is compliance overhead and slower velocity" },
        { t: "Equity accelerators — Techstars Defense, MassChallenge DefTech, Catalyst", d: "you give up a few percent; you get a cohort, mentors, demo-day capital, and a running start" },
        { t: "Problem-match programs — NSIN, Hacking-for-Defense, MD5", d: "founder × DoW problem-owner match; the money comes afterward via SBIR / CSO" },
        { t: "Federal-lab commercialization — FedTech, JHU APL Discover", d: "licensable IP + facility access; useful when your tech complements a lab platform" },
        { t: "Strategic ventures — Booz Allen, Lockheed Ventures, Boeing HorizonX", d: "capital plus prime relationships; expect the prime to want a partnership term" },
      ] },

      { h2: "How to pick" },
      { p: "The right accelerator for you depends on stage and customer-path shape. Pre-revenue with novel tech → AFWERX / SpaceWERX SBIR Phase I is the least-cost move ($75-250k open door). Commercial traction, want a defense pilot → DIU's problem set is a straight prototype OTA. First-time founder without a PEO relationship → NSIN Foundry / H4D compresses twelve months of customer discovery into one semester." },
      { note: "Stack accelerators, don't sequence them. A Phase I with AFWERX + a Techstars Defense cohort + an NSIN Foundry problem match in the same quarter is not overreach — the milestones reinforce each other and the diligence stories compound. Primes and defense VCs know the alumni networks by heart." },

      { h2: "The current shortlist (from the Accelerators tab)" },
      { p: "Deadlines and terms change with each cycle — CaptureAgent's Accelerators tab keeps this current with per-program due dates + AI-scored fit against your company profile. Verify on the program's page before you commit." },
      { table: { headers: ["Program", "Focus", "Cadence", "What you get"], rows: [
        ["AFWERX", "Air Force / Space Force SBIR pipeline", "Rolling", "Non-dilutive SBIR + AF contracts"],
        ["SpaceWERX Orbital Prime / STRATFI", "Space Force scaling programs", "Announced BAAs", "Matched Phase II funds"],
        ["DIU (Defense Innovation Unit)", "Commercial dual-use → prototype OTAs", "Rolling problem sets", "OTA prototype awards, production paths"],
        ["Techstars Defense (LA / DC)", "Equity accelerator, defense focus", "Annual cohort", "$120k + demo day"],
        ["Hacking for Defense (H4D)", "University-based problem sourcing", "Semester cadence", "Warm sponsor path"],
        ["MassChallenge DefTech", "New-England defense cohort", "Annual", "Non-dilutive, corporate partners"],
        ["Catalyst Accelerator (Colorado)", "Space & missile-defense focus", "Two cohorts/yr", "Space Force sponsor engagement"],
        ["NSIN Foundry / MD5", "Founder + DoW problem match", "Rolling", "Non-dilutive, DoW partner"],
        ["JHU APL Discover", "Applied physics lab commercialization", "By invite", "APL partnering + facilities"],
        ["FedTech", "Federal-lab tech transfer sprints", "Multiple cohorts/yr", "Lab licenses, corporate access"],
        ["Booz Allen SkillTerra / Ventures", "Booz Allen-partnered ventures", "Rolling", "Prime relationship, pilots"],
        ["Cortado Ventures Defense", "Midwest defense/dual-use", "Annual", "Non-dilutive prep + Series-A intros"],
      ] } },

      { h2: "Use it inside CaptureAgent" },
      { p: "The Accelerators tab lists programs with AI-scored fit and due dates. The Accelerator Applications tab drafts a tailored application per program straight from the program's own page — same fillable-form UX as a proposal, with the AI already having read the sponsor's evaluation criteria." },
      { links: [
        { label: "AFWERX", href: "https://afwerx.com" },
        { label: "SpaceWERX", href: "https://spacewerx.us" },
        { label: "Defense Innovation Unit", href: "https://www.diu.mil" },
        { label: "NSIN (National Security Innovation Network)", href: "https://www.nsin.mil" },
        { label: "Techstars Defense", href: "https://www.techstars.com/accelerators/defense" },
      ] },
      { related: ["startup-fundraising-defense", "defense-startup-resources", "dow-customer-discovery-peo-directory"] },
    ],
  },

  /* ─────────────────────── Startup resources ─────────────────────── */
  "defense-startup-resources": {
    tag: "ECOSYSTEM",
    title: "The defense-tech startup resource map",
    summary: "The programs, accelerators, and free help that shorten a new defense company's path — plus the best community-maintained lists.",
    blocks: [
      { h2: "Start with these" },
      { links: [
        { label: "MIT MIX — Defense Technology Startup Resources", href: "https://mix.mit.edu/defense-technology-startup-resources/", note: "The best single curated map of the defense innovation ecosystem" },
        { label: "APEX Accelerators (formerly PTACs)", href: "https://www.apexaccelerators.us", note: "Free one-on-one government-contracting counseling in every state" },
        { label: "DSIP Learning & Support", href: "https://www.dodsbirsttr.mil/submissions/learning-support/training-materials", note: "Official DoW SBIR/STTR training" },
        { label: "AFWERX", href: "https://afwerx.com", note: "Air Force & Space Force innovation arm — open topics, STRATFI/TACFI scaling funds" },
        { label: "NSIN — National Security Innovation Network", href: "https://www.nsin.mil", note: "Programs connecting startups, academia, and DoW problem owners" },
        { label: "Defense Innovation Unit (DIU)", href: "https://www.diu.mil", note: "Commercial solutions openings (CSOs) for fielding commercial tech fast" },
        { label: "OpenVC — defense-tech investor list", href: "https://www.openvc.app/investor-lists/defensetech-investors", note: "Community-maintained list of VCs writing defense checks" },
      ] },
      { h2: "Use them in this order" },
      { steps: [
        { t: "Registrations first", d: "SAM, UEI, CAGE, SBC ID (see the setup checklist)" },
        { t: "Free counseling", d: "book your APEX Accelerator advisor — they review proposals at no cost" },
        { t: "Non-dilutive money", d: "SBIR/STTR via DSIP, NASA, DOE, NSF — CaptureAgent's Federal Opportunities tab tracks them" },
        { t: "Ecosystem accelerators", d: "AFWERX challenges, NSIN programs, service xTech competitions" },
        { t: "Private capital when traction lands", d: "see the Private Capital tab inside the app for a curated defense/space investor table" },
      ] },
      { related: ["new-contractor-setup", "bring-your-own-api-keys", "proposal-templates"] },
    ],
  },
};

/* Index page ordering */
export const ARTICLE_ORDER = [
  "bring-your-own-api-keys",
  "new-contractor-setup",
  "selling-to-the-department-of-war",
  "dow-customer-discovery-peo-directory",
  "startup-fundraising-defense",
  "defense-accelerators",
  "proposal-templates",
  "compliance",
  "defense-startup-resources",
];
