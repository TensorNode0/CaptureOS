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
}

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
        engine, keys, SYSTEM, prompt, max_tokens=8000, model=model, effort=effort)
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
