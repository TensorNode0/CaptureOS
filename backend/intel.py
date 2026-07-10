"""AI Opportunity Intelligence Scan.

Uses the org's own Anthropic key (Claude Sonnet + live web search) to discover
REAL open, SB-eligible federal solicitations, fit-score them against the org's
capability profile, and return a structured intelligence report (JSON).

Cost is capped via web-search `max_uses` and a bounded opportunity count.
Keys are never logged or persisted in source.
"""
import json
import re
import asyncio
from datetime import datetime, timezone

# Sonnet-class models, newest first. The SDK passes the string straight through,
# so we try each until one is accepted by the caller's key.
SONNET_MODELS = [
    "claude-sonnet-4-5",
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
]
HAIKU_MODELS = ["claude-3-5-haiku-latest", "claude-3-5-haiku-20241022"]

# Cost/throughput tiers chosen by the org admin.
TIERS = {
    "lean":     {"models": HAIKU_MODELS,  "max_uses": 5,  "max_tokens": 6000,  "target": 12},
    "standard": {"models": SONNET_MODELS, "max_uses": 8,  "max_tokens": 8000,  "target": 22},
    "deep":     {"models": SONNET_MODELS, "max_uses": 15, "max_tokens": 12000, "target": 30},
}

MISSION_CATEGORIES = [
    "Space Logistics / ISAM", "Orbital Warfare / Space Superiority",
    "Space Range / Wargaming / M&S", "Missile Defense / Golden Dome",
    "Space Domain Awareness (SDA/SBM)", "UAS/UAV/Drones", "C-UAS",
    "Sensors", "Robotics / Autonomous Systems", "AI / ML / GenAI",
    "Autonomous Systems (non-UAS)", "BCI / Human-Machine Teaming",
    "Orbital & Lunar Infrastructure / Cislunar", "Space Resources / ISRU",
    "Space Energy / Power Beaming", "Navigation in Denied Environments (Alt-PNT)",
]
CRITICAL_TECH_AREAS = [
    "Trusted AI & Autonomy", "Integrated Network Systems-of-Systems",
    "Microelectronics", "Space Technology", "Renewable Energy Generation & Storage",
    "Advanced Materials", "Advanced Computing & Software", "Human-Machine Interfaces",
    "Directed Energy", "Hypersonics", "Quantum Science", "Biotechnology", "Cybersecurity",
]


def _extract_json(text: str):
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = text[start:end + 1]
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _system_prompt():
    return (
        "You are an expert U.S. Government Contracting Capture Director and Proposal "
        "Strategist with deep knowledge of defense, space and emerging-technology "
        "acquisition. You operate with the precision of a seasoned BD professional and the "
        "rigor of a defense-technology analyst.\n\n"
        "Use the web_search tool to find REAL, currently OPEN / ACTIVE / FORTHCOMING "
        "(within ~90 days) solicitations available to U.S. small businesses. Search "
        "authoritative public sources: SAM.gov, SBIR.gov / DSIP, Grants.gov, AFWERX & "
        "SpaceWERX, DIU, DARPA, NASA SBIR/STTR, Army xTechSearch, SOFWERX, MDA, NSIN. "
        "NEVER fabricate an opportunity, solicitation number, URL or date. If you cannot "
        "verify a field, use \"TBD\". Exclude expired, cancelled, large-business-only, or "
        "foreign-owned opportunities. Prefer awards > $50,000.\n\n"
        "Respond with a SINGLE valid JSON object ONLY — no prose, no markdown fences."
    )


def _user_prompt(ctx, tier_target):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    org = (
        f"ORGANIZATION CAPABILITY PROFILE (use this to compute an honest Fit Score):\n"
        f"- Name: {ctx.get('orgName','')}\n"
        f"- NAICS: {', '.join(ctx.get('naics') or []) or 'n/a'}\n"
        f"- Focus keywords: {', '.join(ctx.get('keywords') or []) or 'n/a'}\n"
        f"- Core capabilities: {ctx.get('capabilities') or 'n/a'}\n"
        f"- Technology focus areas: {', '.join(ctx.get('techFocus') or []) or 'n/a'}\n"
        f"- Past performance: {ctx.get('pastPerformance') or 'n/a'}\n"
        f"- Differentiators: {ctx.get('differentiators') or 'n/a'}\n"
        f"- Commercialization strategy: {ctx.get('commercialization') or 'n/a'}\n"
        f"- Clearances / facility: {ctx.get('clearances') or 'n/a'}\n"
        f"- Target agencies (prioritize these customers): "
        f"{', '.join(ctx.get('targetAgencies') or []) or 'n/a'}\n"
        f"- CMMC level: {ctx.get('cmmcLevel') or 'n/a'}\n"
        f"- Small business: {ctx.get('isSmall')}; SBA certs held: "
        f"{', '.join([k for k, v in (ctx.get('certs') or {}).items() if v]) or 'none'}\n"
    )
    return (
        f"Today is {today}. Conduct a fresh weekly opportunity-intelligence scan.\n\n{org}\n"
        f"Find up to {tier_target} of the BEST-matched real, open opportunities. For EACH, "
        "assign a Fit Score from 1-100 grounded in the org's capabilities, past performance, "
        "tech alignment, defense need, and team expertise (be honest — low scores are fine). "
        "Map fitGrade as: 90-100 Excellent, 75-89 Very Good, 60-74 Good, 45-59 Fair, "
        "25-44 Poor, <25 No Fit.\n\n"
        f"Mission categories taxonomy: {', '.join(MISSION_CATEGORIES)}.\n"
        f"Critical Technology Areas: {', '.join(CRITICAL_TECH_AREAS)}.\n"
        "techType ∈ {H/W, S/W, H/W + S/W, Services, Data}. "
        "colorOfMoney ∈ {RDT&E, O&M, Procurement, MILCON, Multiple/TBD}. "
        "teaming ∈ {Prime, Sub, JV/Mentor-Protege, Solo}. "
        "compliance flags from {CMMC L2, CMMC L3, ITAR/EAR, CUI, ATO Required, FCL, FOCI, "
        "SECRET/TS-SCI, None}.\n\n"
        "Return JSON with EXACTLY this shape (fill every field; use \"TBD\" not empty):\n"
        "{\n"
        '  "reportDate": "YYYY-MM-DD", "fiscalYear": "FYxx (note months remaining)",\n'
        '  "sourceStatus": [{"source": "SAM.gov", "status": "reached|inaccessible", "note": ""}],\n'
        '  "executiveSummary": {\n'
        '    "totalOpportunities": 0, "narrative": "2-3 sentence executive read",\n'
        '    "hotSignals": [{"signal": "BD/market intel item", "source": "url or outlet"}],\n'
        '    "recommendedActions": ["3-5 prioritized BD moves this week"]\n'
        "  },\n"
        '  "opportunities": [{\n'
        '    "fitScore": 0, "fitGrade": "", "fitRationale": "1 sentence",\n'
        '    "agency": "", "office": "", "dueDate": "YYYY-MM-DD or TBD",\n'
        '    "awardAmount": 0, "solNumber": "", "solUrl": "https://...",\n'
        '    "title": "", "topicUrl": "https://...", "summary": "2-3 sentences",\n'
        '    "phase": "", "colorOfMoney": "", "vehicle": "", "contractType": "",\n'
        '    "compliance": ["..."], "cta": ["..."], "techType": "",\n'
        '    "missionCategory": "", "missionSecondary": "", "setAside": "",\n'
        '    "teaming": "", "notes": "intel / nuance"\n'
        "  }]\n"
        "}"
    )


def _call_sync(api_key, system, user, models, max_uses, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}
    last_err = None
    for model in models:
        try:
            msg = client.messages.create(
                model=model, max_tokens=max_tokens, system=system,
                tools=[tool], messages=[{"role": "user", "content": user}],
            )
            text = "".join(
                getattr(b, "text", "") for b in msg.content
                if getattr(b, "type", None) == "text"
            )
            usage = getattr(msg, "usage", None)
            return text, model, usage
        except (anthropic.NotFoundError, anthropic.BadRequestError) as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Anthropic call failed")


async def run_scan(api_key, ctx, tier="standard"):
    """Run the intelligence scan. Returns a parsed report dict (raises on failure)."""
    cfg = TIERS.get(tier, TIERS["standard"])
    system = _system_prompt()
    user = _user_prompt(ctx, cfg["target"])
    text, model, usage = await asyncio.to_thread(
        _call_sync, api_key, system, user,
        cfg["models"], cfg["max_uses"], cfg["max_tokens"],
    )
    data = _extract_json(text)
    if data is None:
        raise ValueError("The AI returned an unparseable response. Try again.")
    # Normalize / guard
    opps = data.get("opportunities") or []
    if not isinstance(opps, list):
        opps = []
    data["opportunities"] = opps
    es = data.get("executiveSummary") or {}
    es["totalOpportunities"] = len(opps)
    data["executiveSummary"] = es
    data["_model"] = model
    if usage is not None:
        si = getattr(usage, "server_tool_use", None)
        searches = getattr(si, "web_search_requests", None) if si else None
        data["_usage"] = {
            "inputTokens": getattr(usage, "input_tokens", None),
            "outputTokens": getattr(usage, "output_tokens", None),
            "webSearches": searches,
        }
    return data
