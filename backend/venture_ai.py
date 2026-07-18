"""AI drafting for the venture workspace: investor outreach, pitch decks,
business plans, financial models, and accelerator applications.

Same engine layer and BYOK model as proposal drafting; org context comes
from the company profile so drafts speak with the company's real substance.
"""
import genai

KINDS = {
    "investor_email":          {"title": "Investor outreach email", "fmt": "docx"},
    "pitch_deck":              {"title": "Pitch deck",              "fmt": "pptx"},
    "business_plan":           {"title": "Business plan",           "fmt": "docx"},
    "financials":              {"title": "Financial model",         "fmt": "xlsx"},
    "accelerator_application": {"title": "Accelerator application", "fmt": "docx"},
    "investor_scan":           {"title": "Tailored investor scan",  "fmt": "docx"},
    "accelerator_scan":        {"title": "Tailored accelerator scan", "fmt": "docx"},
}

# Scan kinds research the live web, so they run Claude with web search.
WEB_SEARCH_KINDS = {"investor_scan", "accelerator_scan"}

SYSTEM = (
    "You are a defense-tech founder coach who has raised from top venture firms "
    "and won slots at competitive accelerators. You write tight, specific, "
    "evidence-first materials — no fluff, no buzzwords, no invented numbers. "
    "Where the company context lacks a figure, insert [FILL: what's needed] "
    "rather than fabricating."
)


def _org_context(org, profile):
    p = profile or {}
    return (
        "COMPANY CONTEXT (use faithfully; never invent numbers):\n"
        f"- Name: {org.get('name', '')}\n"
        f"- NAICS: {', '.join(org.get('naics') or [])}\n"
        f"- Keywords/focus: {', '.join(org.get('keywords') or [])}\n"
        f"- Capabilities: {p.get('capabilities') or 'n/a'}\n"
        f"- Tech focus: {', '.join(p.get('techFocus') or []) or 'n/a'}\n"
        f"- Past performance: {p.get('pastPerformance') or 'n/a'}\n"
        f"- Differentiators: {p.get('differentiators') or 'n/a'}\n"
        f"- Commercialization: {p.get('commercialization') or 'n/a'}\n"
        f"- Certifications/clearances: {p.get('clearances') or 'n/a'}\n"
        f"- Team size: {p.get('employeesCount') or 'n/a'}; revenue: {p.get('annualRevenue') or 'n/a'}\n"
        f"- Key personnel: {p.get('keyPersonnel') or 'n/a'}\n"
        f"- Locations: {p.get('locations') or 'n/a'}; website: {p.get('website') or 'n/a'}\n"
    )


def _prompt(kind, ctx_text, target, notes):
    tgt = f"TARGET: {target}\n" if target else ""
    extra = f"FOUNDER NOTES / ASK: {notes}\n" if notes else ""
    if kind == "investor_email":
        return (
            f"{ctx_text}\n{tgt}{extra}\n"
            "Write a cold outreach email to this investor. Rules: subject line first "
            "(SUBJECT: ...), under 180 words, one concrete traction proof point, one "
            "sentence on why THIS investor's thesis fits, a specific low-friction ask "
            "(20-minute call), no attachments mention, no pleasantries padding. "
            "Then add a 3-bullet P.S.-style teaser block. Output clean markdown."
        )
    if kind == "pitch_deck":
        return (
            f"{ctx_text}\n{tgt}{extra}\n"
            "Design a 12-slide investor pitch deck. Return JSON ONLY:\n"
            '{ "slides": [{"title": "...", "bullets": ["3-5 tight bullets"], '
            '"notes": "what the founder says on this slide"}] }\n'
            "Slides: title/one-liner, problem, why now, solution/product, defense+ "
            "commercial market sizing, traction (use [FILL] where unknown), business "
            "model, go-to-market (incl. gov motion: SBIR→program of record), "
            "competition, team, financial ask & use of funds, roadmap."
        )
    if kind == "business_plan":
        return (
            f"{ctx_text}\n{tgt}{extra}\n"
            "Write a concise operating business plan (6-10 pages of markdown): "
            "executive summary; company & mission; market analysis (defense + "
            "commercial, cite assumptions); products/services; go-to-market with a "
            "government-capture motion table (vehicle, agency, timeline); operations "
            "& milestones table (8 quarters); team & hiring plan table; risk table "
            "(risk, likelihood, mitigation); financial summary table (3-year revenue/"
            "costs/margin with [FILL] where data is missing). Markdown ONLY, start "
            "with a # title."
        )
    if kind == "financials":
        return (
            f"{ctx_text}\n{tgt}{extra}\n"
            "Build a 3-year monthly-to-annual financial model summary as structured "
            "data. Return JSON ONLY:\n"
            "{\n"
            '  "currency": "USD",\n'
            '  "rows": [{"category": "Revenue|COGS|OpEx|Financing", "item": "...", '
            '"basis": "assumption, 1 sentence", "cost": 0}],\n'
            '  "narrative": "P&L, cash-flow and gross-margin narrative with the '
            'key assumptions and the runway math",\n'
            '  "assumptions": ["explicit assumptions incl. SBIR/contract revenue timing"]\n'
            "}\n"
            "Rows convention: Revenue items positive, cost items positive under their "
            "category (the sheet computes margins). Use [FILL] basis notes rather than "
            "inventing customer counts."
        )
    if kind == "investor_scan":
        return (
            f"{ctx_text}\n{extra}\n"
            "Use web_search to find CURRENT defense/space/deep-tech investors that "
            "genuinely fit this company's stage, sector, and traction — beyond the "
            "obvious mega-funds. Verify each is actively investing (recent checks). "
            "Output a markdown report: ## Best-fit investors (table: investor | why "
            "this fit | check size | stage | recent relevant investment | source), "
            "## Warm-path ideas (who in their portfolio/network overlaps), "
            "## Outreach order (prioritized 5 with one-line rationale). NEVER invent "
            "an investor or a check size — cite a source URL per row or mark "
            "unverified. Markdown ONLY.\n\n"
            "AFTER the markdown report, append this exact fenced block on a new line "
            "(so the app can index the discoveries into the Private Capital table):\n"
            "```json\n"
            '{ "discovered": [ { "name": "", "checkSize": "", "stage": "", '
            '"sector": "", "recentDeal": "", "url": "", "source": "", '
            '"fitReason": "", "verified": true } ] }\n'
            "```\n"
            "Include every best-fit investor from the report. Preserve names EXACTLY as "
            "in the report."
        )
    if kind == "accelerator_scan":
        return (
            f"{ctx_text}\n{extra}\n"
            "Use web_search to find CURRENTLY OPEN or upcoming accelerator/incubator "
            "cohorts that fit this company (defense/space/dual-use aware). Verify "
            "application windows on the program sites. Output a markdown report: "
            "## Open now (table: program | due date | duration | terms | attendance | "
            "why this fit | source), ## Opening soon, ## Skip and why (programs that "
            "look relevant but aren't for this stage). NEVER invent dates or terms — "
            "cite a source URL per row or mark unverified. Markdown ONLY.\n\n"
            "AFTER the markdown report, append this exact fenced block on a new line "
            "(so the app can index the discoveries into the Accelerators table):\n"
            "```json\n"
            '{ "discovered": [ { "name": "", "dueDate": "", "duration": "", '
            '"terms": "", "attendance": "", "url": "", "source": "", '
            '"fitReason": "", "verified": true } ] }\n'
            "```\n"
            "Include every 'Open now' AND 'Opening soon' program. Do NOT include "
            "programs from the 'Skip' section. Preserve names EXACTLY as in the report."
        )
    # accelerator_application
    return (
        f"{ctx_text}\n{tgt}{extra}\n"
        "Draft answers for this accelerator's application. Structure as markdown "
        "with a ## heading per standard question: What do you do (one-liner + "
        "expanded); Problem & who has it; Solution & demo status; Traction & "
        "letters of support; Team & why-you; Market & competition; What you want "
        "from the program; Milestones for the cohort; Funding status & runway. "
        "Under each answer add a short *Tip:* line with what strong applications "
        "do for that question. Keep answers specific to the company context; use "
        "[FILL] where founder input is required. Markdown ONLY."
    )


async def draft(engine, keys, kind, org, profile, target="", notes="",
                model="", effort="", job_id=None):
    """Returns (content_md, content_json, model)."""
    import ai_jobs
    if kind not in KINDS:
        raise ValueError(f"Unknown document kind: {kind}")
    ctx_text = _org_context(org, profile)
    fmt = KINDS[kind]["fmt"]
    prompt = _prompt(kind, ctx_text, target, notes)
    if job_id:
        await ai_jobs.stage(job_id, f"Writing the {KINDS[kind]['title'].lower()}…", 15)
    text, used_model, usage = await genai.generate(
        engine, keys, SYSTEM, prompt, max_tokens=8000, model=model, effort=effort,
        web_search=(kind in WEB_SEARCH_KINDS))
    if job_id:
        await ai_jobs.add_usage(job_id, used_model, usage)
        await ai_jobs.stage(job_id, "Draft received — validating…", 85)
    if fmt in ("pptx", "xlsx"):
        data = genai.extract_json(text)
        if data is None:
            raise ValueError("The AI returned an unparseable draft. Try again.")
        return "", data, used_model
    md = (text or "").strip()
    if md.startswith("```"):
        md = md.strip("`").lstrip("markdown").strip()
    if not md:
        raise ValueError("The AI returned an empty draft. Try again.")
    return md, {}, used_model


GENERIC_APPLICATION_TEMPLATE = """# {name} — Application draft

*Tip: add your Anthropic API key in Settings and re-run "Generate form from
program page" to get this program's ACTUAL questions with tailored guidance.*

## What does your company do? (one-liner + expanded)
[FILL]
*Tip: lead with the customer problem, not the technology.*

## What problem are you solving, and for whom?
[FILL]

## Describe your solution and current status (demo/prototype/fielded)
[FILL]

## Traction (contracts, pilots, LOIs, revenue)
[FILL]
*Tip: SBIR awards and signed pilot agreements count — cite numbers.*

## Team — who are you and why you?
[FILL]

## What do you want from this program?
[FILL]
*Tip: name specific mentors, customers, or facilities the program offers.*

## Milestones for the cohort period
[FILL]

## Funding status and runway
[FILL]
"""

# Default question set used when we can't fetch/parse the program page. Same
# shape the AI is asked to produce so the form renderer works either way.
GENERIC_QUESTIONS = [
    {"id": "one_liner",     "label": "What does your company do? (one-liner + expanded)", "type": "long",
     "answer": "", "tip": "Lead with the customer problem, not the technology."},
    {"id": "problem",       "label": "What problem are you solving, and for whom?",       "type": "long",
     "answer": "", "tip": ""},
    {"id": "solution",      "label": "Describe your solution and current status.",       "type": "long",
     "answer": "", "tip": "Say whether it's demo, prototype, or fielded."},
    {"id": "traction",      "label": "Traction (contracts, pilots, LOIs, revenue)",      "type": "long",
     "answer": "", "tip": "SBIR awards and signed pilot agreements count — cite numbers."},
    {"id": "team",          "label": "Team — who are you and why you?",                  "type": "long",
     "answer": "", "tip": ""},
    {"id": "ask",           "label": "What do you want from this program?",              "type": "long",
     "answer": "", "tip": "Name specific mentors, customers, or facilities the program offers."},
    {"id": "milestones",    "label": "Milestones for the cohort period",                 "type": "long",
     "answer": "", "tip": ""},
    {"id": "funding",       "label": "Funding status and runway",                        "type": "short",
     "answer": "", "tip": ""},
]


def _questions_to_md(name: str, key_facts: dict, questions: list) -> str:
    """Render a schema back to markdown for exports/downloads/older UIs."""
    parts = [f"# {name} — Application draft\n"]
    if key_facts:
        parts.append("## Key facts")
        for k, v in key_facts.items():
            if v:
                parts.append(f"- **{k}:** {v}")
        parts.append("")
    for q in questions or []:
        parts.append(f"## {q.get('label') or q.get('id', 'Question')}")
        parts.append(str(q.get("answer") or "[FILL]"))
        tip = (q.get("tip") or "").strip()
        if tip:
            parts.append(f"*Tip: {tip}*")
        parts.append("")
    return "\n".join(parts)


async def form_from_program(anthropic_key, name, page_text, org, profile,
                            model="", job_id=None):
    """Extract a program's actual application questions from its page text and
    scaffold answers with tips. Returns (content_md, content_json, used_model)
    where content_json = {"kind": "acceleratorApplication", "keyFacts": {...},
    "questions": [{id, label, type, answer, tip}, ...]}. Falls back to the
    generic template + questions if we don't have a key or a page."""
    import ai_jobs
    if not anthropic_key or not page_text:
        md = GENERIC_APPLICATION_TEMPLATE.format(name=name)
        schema = {"kind": "acceleratorApplication", "programName": name,
                  "keyFacts": {}, "questions": GENERIC_QUESTIONS}
        return md, schema, ""
    if job_id:
        await ai_jobs.stage(job_id, "Reading the program page and extracting questions…", 30)
    ctx_text = _org_context(org, profile)
    prompt = (
        f"{ctx_text}\n"
        f"PROGRAM: {name}\n"
        f"PROGRAM PAGE TEXT (truncated):\n{page_text[:40000]}\n\n"
        "Extract this program's application as a fillable form the founder "
        "will complete inside our app. Respond with a SINGLE JSON object ONLY, "
        "no prose:\n"
        '{ "programName": "",\n'
        '  "keyFacts": { "Deadline": "", "Eligibility": "", "Cohort dates": "", '
        '"Location": "", "Terms": "" },\n'
        '  "questions": [\n'
        '     { "id": "snake_case", "label": "the question as asked on the page", '
        '"type": "short|long|number|url", "answer": "drafted response grounded in '
        'company context; use [FILL] where founder input is needed", '
        '"tip": "one-line coaching for what strong applications do for this question" }\n'
        "  ]\n}\n"
        "Rules:\n"
        "- Include EVERY real application question you can identify on the page.\n"
        "- If the page doesn't list questions, use the standard accelerator "
        "question set (one-liner, problem, solution, traction, team, ask, "
        "milestones, funding).\n"
        "- Populate keyFacts ONLY with values quoted from the page; leave blank strings otherwise.\n"
        "- `answer` should be a draft, not a placeholder — use founder context.\n"
        "- Use `[FILL]` only for numbers/dates the AI can't invent."
    )
    text, used_model, usage = await genai.claude_generate(
        anthropic_key, SYSTEM, prompt, max_tokens=8000, model=model)
    if job_id:
        await ai_jobs.add_usage(job_id, used_model, usage)
    data = genai.extract_json(text) or {}
    questions = data.get("questions") if isinstance(data.get("questions"), list) else []
    key_facts = data.get("keyFacts") if isinstance(data.get("keyFacts"), dict) else {}
    if not questions:
        md = GENERIC_APPLICATION_TEMPLATE.format(name=name)
        schema = {"kind": "acceleratorApplication", "programName": name,
                  "keyFacts": {}, "questions": GENERIC_QUESTIONS}
        return md, schema, used_model
    # Normalize / defensively cap runaway AI output.
    clean_qs = []
    for i, q in enumerate(questions[:40]):
        clean_qs.append({
            "id":     (q.get("id") or f"q_{i}")[:60],
            "label":  (q.get("label") or f"Question {i + 1}")[:400],
            "type":   q.get("type") if q.get("type") in ("short", "long", "number", "url") else "long",
            "answer": (q.get("answer") or "")[:8000],
            "tip":    (q.get("tip") or "")[:400],
        })
    schema = {"kind": "acceleratorApplication",
              "programName": (data.get("programName") or name)[:200],
              "keyFacts": {k: str(v)[:400] for k, v in list(key_facts.items())[:12] if v},
              "questions": clean_qs}
    return _questions_to_md(name, schema["keyFacts"], clean_qs), schema, used_model
