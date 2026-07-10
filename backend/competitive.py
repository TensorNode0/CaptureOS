"""Competitive analysis: hard award data from USASpending (public API, no key)
plus AI OSINT synthesis across public/government sources, producing a BLUF
with insights, strategies, and actionable intel."""
import json
import asyncio
from datetime import datetime, timezone

import httpx

import genai

USASPENDING = "https://api.usaspending.gov/api/v2"
CONTRACT_CODES = ["A", "B", "C", "D"]  # definitive contract award types


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _filters(competitor, naics):
    f = {
        "recipient_search_text": [competitor],
        "award_type_codes": CONTRACT_CODES,
        "time_period": [{"start_date": "2019-10-01", "end_date": _today()}],
    }
    if naics:
        f["naics_codes"] = [naics]
    return f


async def fetch_usaspending(competitor, naics=""):
    """Award history for a recipient: top awards, totals by fiscal year and
    by awarding agency. All figures come straight from USASpending."""
    filters = _filters(competitor, naics)
    out = {"topAwards": [], "byYear": [], "byAgency": [], "totalObligated": 0,
           "awardCount": 0, "queriedAt": _today(), "competitor": competitor,
           "naics": naics}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{USASPENDING}/search/spending_by_award/", json={
            "filters": filters,
            "fields": ["Award ID", "Recipient Name", "Awarding Agency",
                       "Awarding Sub Agency", "Award Amount", "Start Date",
                       "End Date", "Description", "generated_internal_id"],
            "limit": 25, "page": 1, "sort": "Award Amount", "order": "desc",
        })
        r.raise_for_status()
        for a in (r.json().get("results") or []):
            out["topAwards"].append({
                "awardId": a.get("Award ID"),
                "recipient": a.get("Recipient Name"),
                "agency": a.get("Awarding Agency"),
                "subAgency": a.get("Awarding Sub Agency"),
                "amount": a.get("Award Amount") or 0,
                "startDate": a.get("Start Date"),
                "endDate": a.get("End Date"),
                "description": (a.get("Description") or "")[:220],
                "url": f"https://www.usaspending.gov/award/{a.get('generated_internal_id')}"
                       if a.get("generated_internal_id") else "",
            })

        r = await client.post(f"{USASPENDING}/search/spending_over_time/", json={
            "group": "fiscal_year", "filters": filters,
        })
        r.raise_for_status()
        for row in (r.json().get("results") or []):
            out["byYear"].append({
                "fiscalYear": row.get("time_period", {}).get("fiscal_year"),
                "obligated": round(float(row.get("aggregated_amount") or 0)),
            })
        out["totalObligated"] = round(sum(y["obligated"] for y in out["byYear"]))

        r = await client.post(f"{USASPENDING}/search/spending_by_category/awarding_agency", json={
            "filters": filters, "limit": 10, "page": 1,
        })
        r.raise_for_status()
        for row in (r.json().get("results") or []):
            out["byAgency"].append({
                "agency": row.get("name"),
                "obligated": round(float(row.get("amount") or 0)),
            })
    out["awardCount"] = len(out["topAwards"])
    return out


OSINT_SYSTEM = (
    "You are a federal-market competitive-intelligence analyst for a small "
    "government contractor. You work strictly from OPEN sources: SAM.gov entity "
    "records, SBA DSBS, GSA eLibrary schedules, USASpending/FPDS award data, "
    "agency OSDBU forecast pages, subaward listings, company sites, press, and "
    "BLS wage data for labor-rate benchmarks. Use the web_search tool to verify "
    "before asserting; NEVER fabricate a contract, number, or certification. "
    "Anything you cannot verify gets \"unverified\" wording or is omitted. "
    "Respond with a SINGLE JSON object ONLY."
)


def _osint_prompt(competitor, naics, usasp, org_name, org_naics):
    yr = ", ".join(f"FY{y['fiscalYear']}: ${y['obligated']:,}" for y in usasp.get("byYear", []))
    ag = ", ".join(f"{a['agency']}: ${a['obligated']:,}" for a in usasp.get("byAgency", [])[:6])
    return (
        f"COMPETITOR: {competitor}" + (f" (NAICS focus {naics})" if naics else "") + "\n"
        f"OUR COMPANY: {org_name} (NAICS {', '.join(org_naics or []) or 'n/a'})\n\n"
        f"VERIFIED USASPENDING DATA (treat as ground truth):\n"
        f"- Obligations by FY: {yr or 'none found'}\n"
        f"- Top awarding agencies: {ag or 'none found'}\n"
        f"- Total obligated since FY2020: ${usasp.get('totalObligated', 0):,}\n\n"
        "Research this competitor across public sources (SAM entity status, DSBS "
        "profile & certifications, GSA schedules in eLibrary, recompete timing from "
        "the award end dates above, OSDBU forecasts in their agencies, typical "
        "labor rates for the NAICS from BLS OES data, teaming/subcontracting "
        "posture). Then produce actionable capture intelligence. Return JSON:\n"
        "{\n"
        '  "bluf": ["3-5 bottom-line-up-front sentences: who they are, where they win, where they are beatable"],\n'
        '  "profile": {"summary": "2-3 sentences", "sizeStatus": "small|other-than-small|unverified",\n'
        '              "certifications": ["verified certs only"], "vehicles": ["GSA/IDIQ vehicles found"],\n'
        '              "keyCustomers": ["agencies"], "estimatedLaborBenchmarks": "1-2 sentences from BLS OES for this NAICS"},\n'
        '  "insights": [{"insight": "...", "evidence": "what supports it", "source": "url or source name"}],\n'
        '  "strategies": [{"play": "prime|sub|team|counter-position", "rationale": "...", "action": "specific next step"}],\n'
        '  "recompetes": [{"contract": "...", "agency": "...", "endsBy": "YYYY-MM-DD or FY", "angle": "how to position"}],\n'
        '  "sources": [{"label": "...", "url": "https://..."}]\n'
        "}"
    )


async def run_analysis(anthropic_key, competitor, naics, org_name, org_naics):
    """USASpending pull + AI OSINT synthesis. Returns (usaspending, analysis, model)."""
    usasp = await fetch_usaspending(competitor, naics)
    if not anthropic_key:
        return usasp, {}, ""
    text, model = await genai.claude_generate(
        anthropic_key, OSINT_SYSTEM,
        _osint_prompt(competitor, naics, usasp, org_name, org_naics),
        max_tokens=8000, web_search=True)
    analysis = genai.extract_json(text)
    if analysis is None:
        raise ValueError("The AI returned an unparseable analysis. Try again.")
    return usasp, analysis, model
