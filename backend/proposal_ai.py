"""AI proposal-package drafting: one button per volume, engine = Claude or OpenAI.

Volume sets adapt to the solicitation vehicle. Narrative volumes are drafted as
markdown (exported to .docx); the cost volume is structured JSON (exported to
.xlsx); the briefing deck is structured JSON (exported to .pptx).
"""
import json
from datetime import datetime, timezone

import genai
from capability_ai import build_context

SYSTEM = (
    "You are a senior U.S. GovCon Proposal Manager writing evaluator-ready proposal "
    "volumes. Compliance first. Short sentences, active voice, present tense. Every "
    "major section opens with a theme statement (Feature → Benefit → Proof). Use the "
    "provided organization facts and approved capability EXACTLY — never invent "
    "certifications, contract numbers, personnel names, or past performance; mark "
    "anything requiring confirmation as [CONFIRM]."
)

# doc_type -> definition
DOC_TYPES = {
    "cover_letter": {
        "title": "Cover Letter", "fmt": "docx", "sort": 0,
        "guidance": (
            "Write a one-page transmittal/cover letter: reference the solicitation "
            "number and title, state the offer, summarize eligibility (set-aside, "
            "UEI/CAGE placeholders as [CONFIRM] if unknown), name a point of contact "
            "placeholder, and close professionally. Markdown."),
    },
    "executive_summary": {
        "title": "Executive Summary", "fmt": "docx", "sort": 1,
        "guidance": (
            "Write a 1-2 page executive summary: the customer's problem, our proposed "
            "capability, three win themes (Feature → Benefit → Proof), key "
            "discriminators, and expected mission outcomes. Markdown with ## headings."),
    },
    "technical_volume": {
        "title": "Technical Volume", "fmt": "docx", "sort": 2,
        "guidance": (
            "Write the technical volume: ## 1 Understanding of the Requirement, "
            "## 2 Technical Approach (respond task-by-task to the SoW), ## 3 "
            "Innovation & Discriminators, ## 4 Schedule & Milestones (reference the "
            "WBS), ## 5 Risk Identification & Mitigation (table), ## 6 Deliverables. "
            "Markdown; use tables where they aid evaluation."),
    },
    "management_volume": {
        "title": "Management Volume", "fmt": "docx", "sort": 3,
        "guidance": (
            "Write the management volume: ## 1 Program Management Approach, ## 2 "
            "Organization & Key Personnel (roles, not invented names), ## 3 Staffing "
            "Plan, ## 4 Quality Assurance, ## 5 Schedule Management & Earned Value, "
            "## 6 Communication & Reporting. Markdown."),
    },
    "past_performance_volume": {
        "title": "Past Performance Volume", "fmt": "docx", "sort": 4,
        "guidance": (
            "Write the past performance volume using ONLY the organization's stated "
            "past performance. For each reference: scope, relevance to this effort, "
            "outcomes. If none is provided, write an honest 'no directly relevant "
            "past performance' narrative leaning on team experience, marked "
            "[CONFIRM]. Markdown."),
    },
    "commercialization_plan": {
        "title": "Commercialization Plan", "fmt": "docx", "sort": 5,
        "guidance": (
            "Write an SBIR/STTR-style commercialization plan: market opportunity "
            "(defense + commercial), transition path (Phase II/III), IP strategy, "
            "revenue model, funding strategy. Ground it in the org's stated "
            "commercialization strategy. Markdown."),
    },
    "project_narrative": {
        "title": "Project Narrative", "fmt": "docx", "sort": 2,
        "guidance": (
            "Write a grant-style project narrative: statement of need, goals & "
            "objectives, project design (aligned to SoW tasks), evaluation plan, "
            "organizational capacity, sustainability. Markdown."),
    },
    "cost_volume": {
        "title": "Cost / Budget Volume", "fmt": "xlsx", "sort": 8,
        "guidance": None,  # structured drafting, see _cost_prompt
    },
    "briefing_deck": {
        "title": "Capability Briefing Deck", "fmt": "pptx", "sort": 9,
        "guidance": None,  # structured drafting, see _deck_prompt
    },
}

# vehicle -> ordered doc types
VOLUME_SETS = {
    "RFP":   ["cover_letter", "executive_summary", "technical_volume",
              "management_volume", "past_performance_volume", "cost_volume",
              "briefing_deck"],
    "SBIR":  ["cover_letter", "technical_volume", "commercialization_plan",
              "cost_volume", "briefing_deck"],
    "STTR":  ["cover_letter", "technical_volume", "commercialization_plan",
              "cost_volume", "briefing_deck"],
    "BAA":   ["cover_letter", "executive_summary", "technical_volume",
              "cost_volume", "briefing_deck"],
    "CSO":   ["cover_letter", "executive_summary", "technical_volume",
              "cost_volume", "briefing_deck"],
    "Grant": ["cover_letter", "project_narrative", "past_performance_volume",
              "cost_volume", "briefing_deck"],
}


def volume_set_for(vehicle):
    return VOLUME_SETS.get(vehicle or "RFP", VOLUME_SETS["RFP"])


def _capability_block(content):
    if not content:
        return "PROPOSED CAPABILITY: none generated yet — derive from the context above."
    cap = {k: v for k, v in content.items() if k != "renderingSvg"}
    return "APPROVED PROPOSED CAPABILITY (use as the single source of truth):\n" + \
        json.dumps(cap, indent=1)[:14000]


def _narrative_prompt(doc_type, ctx_text, cap_content):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d = DOC_TYPES[doc_type]
    return (
        f"Today is {today}.\n\n{ctx_text}\n{_capability_block(cap_content)}\n\n"
        f"DRAFT THE FOLLOWING PROPOSAL DOCUMENT: {d['title']}\n{d['guidance']}\n\n"
        "Evaluators reward structure: include markdown TABLES wherever they carry "
        "the argument better than prose — at minimum a requirements-traceability "
        "or task table, a milestone/schedule table, and (where relevant) a "
        "risk-mitigation table and staffing/LOE table. Tables export directly "
        "into the Word document. Use the capability's WBS/schedule/budget numbers "
        "verbatim — never invent conflicting figures.\n\n"
        "Output the document as clean markdown ONLY (start with a # title line). "
        "No preamble, no closing commentary."
    )


def _cost_prompt(ctx_text, cap_content):
    return (
        f"{ctx_text}\n{_capability_block(cap_content)}\n\n"
        "Build the COST/BUDGET VOLUME as structured data. Expand the capability "
        "budget into line items with a basis of estimate. Return JSON ONLY:\n"
        "{\n"
        '  "currency": "USD",\n'
        '  "rows": [{"category": "Direct Labor", "item": "...", '
        '"basis": "basis of estimate, 1 sentence", "cost": 0}],\n'
        '  "narrative": "cost narrative / BOE summary, 1-2 paragraphs",\n'
        '  "assumptions": ["..."]\n'
        "}\n"
        "Rows must sum to a total consistent with the capability budget/ceiling."
    )


def _deck_prompt(ctx_text, cap_content):
    return (
        f"{ctx_text}\n{_capability_block(cap_content)}\n\n"
        "Design a capability briefing deck (8-12 slides). Return JSON ONLY:\n"
        "{\n"
        '  "slides": [{"title": "...", "bullets": ["3-5 concise bullets"], '
        '"notes": "speaker notes, optional"}]\n'
        "}\n"
        "Slide 1 is the title slide (title + one-line tagline as its only bullet). "
        "Cover: problem, proposed capability, technical approach, schedule, team, "
        "budget summary, discriminators, call to action."
    )


async def draft_document(engine, keys, doc_type, org, profile, opp, cap_content):
    """Draft one document. Returns (content_md, content_json, model_used).
    `keys` is the org_keys.get_keys() dict (all configured engines)."""
    if doc_type not in DOC_TYPES:
        raise ValueError(f"Unknown document type: {doc_type}")
    ctx_text = build_context(org, profile or {}, opp)
    fmt = DOC_TYPES[doc_type]["fmt"]

    if fmt == "docx":
        text, model = await genai.generate(
            engine, keys, SYSTEM,
            _narrative_prompt(doc_type, ctx_text, cap_content), max_tokens=8000)
        md = (text or "").strip()
        if md.startswith("```"):
            md = md.strip("`").lstrip("markdown").strip()
        if not md:
            raise ValueError("The AI returned an empty draft. Try again.")
        return md, {}, model

    prompt = _cost_prompt(ctx_text, cap_content) if doc_type == "cost_volume" \
        else _deck_prompt(ctx_text, cap_content)
    text, model = await genai.generate(engine, keys, SYSTEM, prompt, max_tokens=8000)
    data = genai.extract_json(text)
    if data is None:
        raise ValueError("The AI returned an unparseable draft. Try again.")
    return "", data, model
EVAL_SYSTEM = (
    "You are a Source Selection Evaluation Board (SSEB) chair and color-team lead "
    "with 20+ years evaluating U.S. federal proposals. You score strictly against "
    "what evaluators actually reward: compliance, specificity, evidence, and risk "
    "mitigation — never adjectives. Be tough but constructive; unsupported claims "
    "are weaknesses. Respond with a SINGLE JSON object ONLY — no prose, no fences."
)


def _eval_prompt(ctx_text, docs_digest):
    return (
        f"{ctx_text}\n\n"
        "PROPOSAL PACKAGE UNDER EVALUATION (drafted volumes, truncated):\n"
        f"{docs_digest}\n\n"
        "Run a color-team review of this package as the evaluation board would. "
        "Score each factor 0-100 (be honest: 85+ is rare). Return JSON EXACTLY:\n"
        "{\n"
        '  "overallScore": 0,\n'
        '  "colorReview": "pink|red|gold",  // maturity: pink=storyboard-grade, red=full draft, gold=submit-ready\n'
        '  "verdict": "<one-sentence bottom line an evaluator would write>",\n'
        '  "factors": [{"name": "Technical Merit", "score": 0, "note": "<why>"},\n'
        '               {"name": "Management & Schedule", "score": 0, "note": ""},\n'
        '               {"name": "Compliance & Responsiveness", "score": 0, "note": ""},\n'
        '               {"name": "Past Performance & Team", "score": 0, "note": ""},\n'
        '               {"name": "Cost Realism", "score": 0, "note": ""}],\n'
        '  "strengths": ["<specific, quotable strengths>"],\n'
        '  "weaknesses": ["<specific gaps with the section they live in>"],\n'
        '  "risks": [{"risk": "...", "severity": "high|medium|low", "mitigation": "..."}],\n'
        '  "complianceGaps": ["<missing required elements, page/format concerns>"],\n'
        '  "recommendations": ["<3-7 prioritized edits that most raise score>"]\n'
        "}"
    )


def _docs_digest(docs, limit_each=4000):
    parts = []
    for d in docs:
        body = d.get("content_md") or ""
        if not body and d.get("content_json"):
            import json as _json
            body = _json.dumps(d["content_json"])[:limit_each]
        if not body:
            continue
        parts.append(f"=== {d.get('title')} ({d.get('doc_type')}) ===\n{body[:limit_each]}")
    return "\n\n".join(parts) if parts else "(no drafted content)"


async def evaluate_package(engine, keys, org, profile, opp, docs):
    """AI color-team evaluation of the drafted package. Returns evaluation dict."""
    ctx_text = build_context(org, profile or {}, opp)
    digest = _docs_digest([dict(d) for d in docs])
    text, model = await genai.generate(
        engine, keys, EVAL_SYSTEM, _eval_prompt(ctx_text, digest), max_tokens=6000)
    data = genai.extract_json(text)
    if data is None:
        raise ValueError("The AI returned an unparseable evaluation. Try again.")
    data["_model"] = model
    return data
