"""AI Proposed-Capability generator.

Given an opportunity + the org's capability profile, produce a structured
proposed capability: title, abstract, executive summary, keywords, charts &
tables, SoW, WBS + schedule, and budget — plus a separate SVG concept
rendering. Grounded in the solicitation via optional web search.
"""
import json
from datetime import datetime, timezone

import genai

SYSTEM = (
    "You are a senior U.S. GovCon Capture Manager and Proposal Strategist with 20+ "
    "years winning DoD, IC, civil-agency and SBIR/STTR awards. You think like a Source "
    "Selection Evaluation Board member: compliance first, then strengths backed by "
    "proof. Write in short, active, present-tense sentences. Features → Benefits → "
    "Proof. Never fabricate certifications, past performance, or solicitation facts "
    "that are not in the provided context; where something must be confirmed, mark it "
    "[CONFIRM]. Respond with a SINGLE valid JSON object ONLY — no prose, no markdown "
    "fences."
)

SVG_SYSTEM = (
    "You are a technical illustrator for aerospace/defense proposals. You produce "
    "clean, self-contained SVG concept diagrams. Output RAW SVG ONLY — a single "
    "<svg> element, no markdown, no explanation. Requirements: viewBox='0 0 800 500'; "
    "dark theme (background #0b1020, lines #1c2740, text #e8eefc, accents #38e1ff "
    "#8b7bff #34d399); every text element legible (font-size >= 12); label the major "
    "components and data flows; no external images, fonts, or scripts."
)


def build_context(org, profile, opp):
    """Assemble the grounding context block from org + profile + opportunity."""
    certs = profile.get("certs") or {}
    return (
        "ORGANIZATION\n"
        f"- Name: {org.get('name', '')}\n"
        f"- NAICS: {', '.join(org.get('naics') or []) or 'n/a'}\n"
        f"- Keywords: {', '.join(org.get('keywords') or []) or 'n/a'}\n"
        f"- Core capabilities: {profile.get('capabilities') or 'n/a'}\n"
        f"- Tech focus: {', '.join(profile.get('techFocus') or []) or 'n/a'}\n"
        f"- Past performance: {profile.get('pastPerformance') or 'n/a'}\n"
        f"- Differentiators: {profile.get('differentiators') or 'n/a'}\n"
        f"- Commercialization: {profile.get('commercialization') or 'n/a'}\n"
        f"- Clearances/facility: {profile.get('clearances') or 'n/a'}\n"
        f"- CMMC: {profile.get('cmmcLevel') or 'n/a'}; small business: {profile.get('isSmall')}\n"
        f"- Certifications held: {', '.join(k for k, v in certs.items() if v) or 'none'}\n"
        f"- Size: {profile.get('employeesCount') or 'n/a'} employees; revenue: {profile.get('annualRevenue') or 'n/a'}\n"
        f"- Locations: {profile.get('locations') or 'n/a'}\n"
        f"- Key personnel: {profile.get('keyPersonnel') or 'n/a'}\n"
        f"- Target agencies: {', '.join(profile.get('targetAgencies') or []) or 'n/a'}\n"
        f"- Website: {profile.get('website') or 'n/a'}\n\n"
        "SOLICITATION / OPPORTUNITY\n"
        f"- Title: {opp.get('title', '')}\n"
        f"- Solicitation #: {opp.get('solNumber') or 'TBD'}\n"
        f"- Agency / office: {opp.get('agency', '')} / {opp.get('office', '')}\n"
        f"- Vehicle: {opp.get('vehicle', 'RFP')}; set-aside: {opp.get('setAside', 'None')}\n"
        f"- NAICS: {opp.get('naics') or 'n/a'}; ceiling: ${opp.get('ceiling') or 'TBD'}\n"
        f"- Period of performance: {opp.get('pop') or 'TBD'}\n"
        f"- Response due: {opp.get('dueDate') or 'TBD'}\n"
        f"- URL: {opp.get('url') or 'n/a'}\n"
        f"- Win themes (user notes): {opp.get('winThemes') or 'n/a'}\n"
    )


def _content_prompt(ctx_text):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"Today is {today}. Using the context below, design the PROPOSED CAPABILITY "
        "this organization should offer for this solicitation. If a solicitation URL is "
        "provided and web search is available, verify scope/requirements against it.\n\n"
        f"{ctx_text}\n"
        "Return JSON with EXACTLY this shape:\n"
        "{\n"
        '  "title": "compelling proposal title, <= 15 words",\n'
        '  "abstract": "150-250 word abstract",\n'
        '  "executiveSummary": "300-500 words, markdown allowed (## headings, **bold**, lists)",\n'
        '  "keywords": ["8-12 keywords"],\n'
        '  "charts": [{"type": "bar|pie", "title": "...", '
        '"data": [{"name": "...", "value": 0}]}],  // 2-3 charts: e.g. budget mix, schedule effort by phase\n'
        '  "tables": [{"title": "...", "headers": ["..."], "rows": [["..."]]}],  '
        "// 1-2 tables: e.g. requirements-to-capability traceability\n"
        '  "sow": {"scope": "1 paragraph", "tasks": [{"number": "1.0", "title": "...", '
        '"description": "2-4 sentences", "deliverables": ["..."]}]},  // 4-8 tasks\n'
        '  "scheduleMonths": 12,  // total period of performance in months\n'
        '  "wbs": [{"code": "1.1", "task": "...", "owner": "role", "startMonth": 1, '
        '"endMonth": 3}],  // 8-16 rows aligned to SoW tasks; months are 1-based\n'
        '  "budget": {"ceiling": 0, "items": [{"category": "Direct Labor|Fringe & Overhead|'
        'Materials|Equipment|Subcontracts|Travel|ODC|Fee", "description": "...", '
        '"cost": 0}], "narrative": "basis-of-estimate narrative, 2-4 sentences"}\n'
        "}\n"
        "Budget items must sum to a realistic total at or under the ceiling (if known). "
        "WBS months must fit within scheduleMonths."
    )


def _svg_prompt(content):
    return (
        "Create a concept rendering (system diagram) of this proposed capability:\n\n"
        f"TITLE: {content.get('title', '')}\n"
        f"ABSTRACT: {content.get('abstract', '')}\n\n"
        "Show the major subsystems/components, how they connect, the data/material "
        "flows, and the operational context. Include a small title block. "
        "Remember: RAW SVG only, viewBox='0 0 800 500'."
    )


def _sanitize_svg(text):
    """Extract the <svg>...</svg> element and reject anything executable."""
    if not text:
        return ""
    start = text.find("<svg")
    end = text.rfind("</svg>")
    if start == -1 or end == -1:
        return ""
    svg = text[start:end + len("</svg>")]
    lowered = svg.lower()
    for banned in ("<script", "javascript:", "onload=", "onclick=", "onerror=",
                   "<foreignobject", "href="):
        if banned in lowered:
            return ""
    return svg


def normalize_content(data):
    """Guard-rail the model output into the shape the app expects."""
    out = {
        "title": str(data.get("title") or "")[:200],
        "abstract": str(data.get("abstract") or ""),
        "executiveSummary": str(data.get("executiveSummary") or ""),
        "keywords": [str(k) for k in (data.get("keywords") or [])][:15],
        "charts": data.get("charts") or [],
        "tables": data.get("tables") or [],
        "sow": data.get("sow") or {"scope": "", "tasks": []},
        "scheduleMonths": int(data.get("scheduleMonths") or 12),
        "wbs": data.get("wbs") or [],
        "budget": data.get("budget") or {"ceiling": 0, "items": [], "narrative": ""},
        "renderingSvg": data.get("renderingSvg") or "",
    }
    if not isinstance(out["charts"], list):
        out["charts"] = []
    if not isinstance(out["tables"], list):
        out["tables"] = []
    if not isinstance(out["wbs"], list):
        out["wbs"] = []
    tasks = out["sow"].get("tasks")
    if not isinstance(tasks, list):
        out["sow"]["tasks"] = []
    items = out["budget"].get("items")
    if not isinstance(items, list):
        out["budget"]["items"] = []
    return out


async def generate_capability(anthropic_key, org, profile, opp,
                              model="", effort="", job_id=None):
    """Two-step generation: structured content JSON, then SVG rendering.
    Returns (content_dict, model_used). Raises on unusable output."""
    import ai_jobs
    ctx_text = build_context(org, profile or {}, opp)
    if job_id:
        await ai_jobs.stage(job_id, "Analyzing the solicitation and your company profile…", 10)
    max_toks = genai.scaled_tokens(12000, effort) if effort else 12000
    text, used_model, usage = await genai.claude_generate(
        anthropic_key, SYSTEM, _content_prompt(ctx_text),
        max_tokens=max_toks, web_search=bool(opp.get("url")), model=model)
    if job_id:
        await ai_jobs.add_usage(job_id, used_model, usage)
        await ai_jobs.stage(job_id, "Capability designed — validating structure…", 60)
    data = genai.extract_json(text)
    if data is None:
        raise ValueError("The AI returned an unparseable capability response. Try again.")
    content = normalize_content(data)

    try:
        if job_id:
            await ai_jobs.stage(job_id, "Drawing the concept rendering…", 75)
        svg_text, svg_model, svg_usage = await genai.claude_generate(
            anthropic_key, SVG_SYSTEM, _svg_prompt(content), max_tokens=4000, model=model)
        if job_id:
            await ai_jobs.add_usage(job_id, svg_model, svg_usage)
        content["renderingSvg"] = _sanitize_svg(svg_text)
    except ai_jobs.JobCancelled:
        raise
    except Exception:
        content["renderingSvg"] = ""  # rendering is best-effort, never fatal

    return content, used_model
