"""Live integrations: Anthropic (Verify & Refresh) + SAM.gov / Grants.gov pull.
All keys are passed in by the caller (decrypted from org secrets at call time).
Keys are never logged or stored in source."""
import json
import re
import asyncio
from datetime import datetime, timedelta, timezone

import httpx

# ----------------------------- Anthropic ------------------------------------
HAIKU_MODELS = ["claude-3-5-haiku-latest", "claude-haiku-4-5"]
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


def _extract_json(text: str):
    """Pull the first JSON object out of a model response (handles code fences)."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
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


def _anthropic_call_sync(api_key: str, system: str, user: str, max_tokens: int = 2200):
    """Blocking Anthropic call with web search. Returns (text, model_used)."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    last_err = None
    for model in HAIKU_MODELS:
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=[WEB_SEARCH_TOOL],
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(
                getattr(b, "text", "") for b in msg.content
                if getattr(b, "type", None) == "text"
            )
            return text, model
        except anthropic.NotFoundError as e:
            last_err = e
            continue
        except anthropic.BadRequestError as e:
            # model/tool not available for this key -> try next model
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Anthropic call failed")


async def anthropic_verify(api_key, naics, keywords, opps):
    """Verify stored opps + discover new ones. Returns parsed dict or raises."""
    listing = []
    for o in opps:
        listing.append({
            "id": o["id"], "title": o.get("title", ""),
            "solNumber": o.get("solNumber", ""), "url": o.get("url", ""),
            "dueDate": o.get("dueDate", ""),
        })
    system = (
        "You are a U.S. federal contracting (GovCon) research analyst. Use the web_search "
        "tool to verify opportunities against authoritative sources (SAM.gov, Grants.gov, "
        "agency sites). Be accurate and never fabricate. If you cannot confirm a field, use "
        "\"unknown\". Respond with a SINGLE JSON object ONLY — no prose, no markdown."
    )
    user = (
        f"Organization NAICS: {', '.join(naics) or 'n/a'}. Keywords: {', '.join(keywords) or 'n/a'}.\n\n"
        f"STORED OPPORTUNITIES TO VERIFY (confirm each is still live/active and whether the "
        f"response due date changed):\n{json.dumps(listing, indent=2)}\n\n"
        "Also DISCOVER up to 3 current or upcoming opportunities matching the NAICS/keywords "
        "that are not already in the list.\n\n"
        "Return JSON with EXACTLY this shape:\n"
        "{\n"
        '  "verifications": [{"id": "<id>", "linkStatus": "live|stale|moved|unknown", '
        '"opportunityStatus": "active|archived|cancelled|unknown", '
        '"currentDueDate": "YYYY-MM-DD or unknown", "dueDateChanged": true|false, '
        '"confidence": "high|medium|low", "sourceUrls": ["..."], "notes": "<short>"}],\n'
        '  "discovered": [{"title": "...", "solNumber": "...", "agency": "...", '
        '"vehicle": "RFP|SBIR|STTR|BAA|CSO|Grant", "setAside": "...", "naics": "...", '
        '"url": "https://...", "dueDate": "YYYY-MM-DD or unknown"}]\n'
        "}"
    )
    text, model = await asyncio.to_thread(_anthropic_call_sync, api_key, system, user)
    data = _extract_json(text)
    if data is None:
        raise ValueError("Anthropic returned an unparseable response")
    data["_model"] = model
    return data


# ----------------------------- SAM.gov --------------------------------------
SETASIDE_LABELS = {
    "SBA": "Total Small Business", "SBP": "Partial Small Business",
    "8A": "8(a)", "8AN": "8(a)", "HZC": "HUBZone", "HZS": "HUBZone",
    "SDVOSBC": "SDVOSB", "SDVOSBS": "SDVOSB", "WOSB": "WOSB", "WOSBSS": "WOSB",
    "EDWOSB": "EDWOSB", "EDWOSBSS": "EDWOSB", "VOSB": "VOSB",
}
PTYPE_VEHICLE = {"o": "RFP", "p": "RFP", "k": "RFP", "r": "RFP", "g": "Grant", "s": "RFP"}


def _mmddyyyy(dt):
    return dt.strftime("%m/%d/%Y")


async def fetch_sam(api_key, naics, keywords, limit=40):
    """Pull recent SAM.gov opportunities. Returns normalized list."""
    posted_to = datetime.now(timezone.utc)
    posted_from = posted_to - timedelta(days=90)
    params = {
        "api_key": api_key,
        "postedFrom": _mmddyyyy(posted_from),
        "postedTo": _mmddyyyy(posted_to),
        "limit": str(limit),
        "offset": "0",
    }
    if naics:
        params["ncode"] = naics[0]
    results = []
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.get("https://api.sam.gov/opportunities/v2/search", params=params)
        if r.status_code == 401 or r.status_code == 403:
            raise PermissionError("SAM.gov rejected the API key (401/403)")
        r.raise_for_status()
        data = r.json()
    kws = [k.lower() for k in (keywords or [])]
    for o in (data.get("opportunitiesData") or []):
        title = o.get("title", "") or ""
        if kws and not any(k in title.lower() for k in kws):
            # keep NAICS-matched even if keyword miss, but prefer keyword hits
            pass
        sa_code = o.get("typeOfSetAside") or ""
        results.append({
            "title": title,
            "solNumber": o.get("solicitationNumber") or o.get("noticeId") or "",
            "agency": o.get("fullParentPathName", "").split(".")[0] if o.get("fullParentPathName") else "",
            "office": (o.get("fullParentPathName", "").split(".")[-1] if o.get("fullParentPathName") else ""),
            "vehicle": PTYPE_VEHICLE.get((o.get("type") or "").lower()[:1], "RFP"),
            "setAside": SETASIDE_LABELS.get(sa_code, sa_code or "None"),
            "naics": o.get("naicsCode") or (naics[0] if naics else ""),
            "ceiling": 0,
            "dueDate": (o.get("responseDeadLine") or "")[:10] or None,
            "url": o.get("uiLink") or "",
            "source": "sam",
        })
    return results


# ----------------------------- Grants.gov -----------------------------------
async def fetch_grants(keywords, rows=20):
    kw = " ".join(keywords or []) or "research"
    body = {"keyword": kw, "oppStatuses": "forecasted|posted", "rows": rows}
    results = []
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post("https://api.grants.gov/v1/api/search2", json=body)
        r.raise_for_status()
        data = r.json()
    hits = (((data or {}).get("data") or {}).get("oppHits")) or []
    for h in hits:
        results.append({
            "title": h.get("title", ""),
            "solNumber": h.get("number", "") or h.get("id", ""),
            "agency": h.get("agency", "") or h.get("agencyName", ""),
            "office": "",
            "vehicle": "Grant",
            "setAside": "None",
            "naics": "",
            "ceiling": 0,
            "dueDate": (h.get("closeDate") or "")[:10] or None,
            "url": f"https://www.grants.gov/search-results-detail/{h.get('id', '')}",
            "source": "grants",
        })
    return results
