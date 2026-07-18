"""Live integrations: Anthropic (Verify & Refresh) + SAM.gov / Grants.gov pull.
All keys are passed in by the caller (decrypted from org secrets at call time).
Keys are never logged or stored in source."""
import json
import re
import asyncio
from datetime import datetime, timedelta, timezone

import httpx

import genai

# ----------------------------- Anthropic ------------------------------------
HAIKU_MODELS = ["claude-haiku-4-5", "claude-3-5-haiku-latest"]
# Sized so verifying a 25-opportunity batch plus discoveries can never hit the
# output ceiling mid-JSON (the old cause of "unparseable response" failures).
VERIFY_MAX_TOKENS = 16000


async def anthropic_verify(api_key, naics, keywords, opps, capabilities=""):
    """Verify stored opps + discover new ones. Returns parsed dict or raises."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
        "agency sites). Be accurate and never fabricate a title, number, URL, date, or "
        "dollar amount. If you cannot confirm a field, use \"unknown\". "
        "Respond with a SINGLE JSON object ONLY — no prose, no markdown."
    )
    user = (
        f"Today is {today}.\n"
        f"ORGANIZATION FIT PROFILE (discovery must match this, strictly):\n"
        f"- NAICS: {', '.join(naics) or 'n/a'}\n"
        f"- Keywords: {', '.join(keywords) or 'n/a'}\n"
        f"- Core capabilities: {capabilities or 'n/a'}\n\n"
        f"STORED OPPORTUNITIES TO VERIFY (confirm each is still live/active and whether the "
        f"response due date changed):\n{json.dumps(listing, indent=2)}\n\n"
        "Also DISCOVER up to 3 new opportunities, subject to ALL of these hard rules:\n"
        f"- OPEN or forthcoming only: response deadline strictly after {today} (never expired)\n"
        "- Directly relevant: must clearly match the NAICS codes AND at least one keyword or "
        "core capability. A generic services or unrelated-industry notice is NOT a match — "
        "when in doubt, return fewer (or zero) discoveries rather than a weak match\n"
        "- Real and verified via web_search: include the source URL you verified against\n"
        "- Include the award/ceiling dollar amount when the notice states one (a number, "
        "not text); use 0 ONLY when the source truly does not state an amount\n\n"
        "Return JSON with EXACTLY this shape:\n"
        "{\n"
        '  "verifications": [{"id": "<id>", "linkStatus": "live|stale|moved|unknown", '
        '"opportunityStatus": "active|archived|cancelled|unknown", '
        '"currentDueDate": "YYYY-MM-DD or unknown", "dueDateChanged": true|false, '
        '"confidence": "high|medium|low", "sourceUrls": ["..."], "notes": "<short>"}],\n'
        '  "discovered": [{"title": "...", "solNumber": "...", "agency": "...", '
        '"vehicle": "RFP|SBIR|STTR|BAA|CSO|Grant", "setAside": "...", "naics": "...", '
        '"ceiling": 0, "url": "https://...", "dueDate": "YYYY-MM-DD", '
        '"fitRationale": "<one sentence: why this matches the org>"}]\n'
        "}"
    )
    text, model, usage = await asyncio.to_thread(
        genai._anthropic_call_sync, api_key, system, user,
        VERIFY_MAX_TOKENS, True, "", 5, HAIKU_MODELS)
    data = genai.extract_json(text)
    if data is None and text:
        text2, model, usage = await asyncio.to_thread(
            genai.anthropic_json_salvage_sync, api_key, user, text,
            VERIFY_MAX_TOKENS, HAIKU_MODELS)
        data = genai.extract_json(text2)
    if data is None:
        stop = (usage or {}).get("stopReason")
        raise ValueError(
            f"Anthropic's response could not be parsed (stop reason: {stop or 'unknown'}, "
            f"~{(usage or {}).get('outputTokens', 0):,} output tokens). Try again.")
    # Server-side guardrails on discoveries: drop expired or unverifiable rows.
    clean = []
    for rec in (data.get("discovered") or []):
        due = (rec.get("dueDate") or "").strip()
        if not rec.get("title") or not rec.get("url"):
            continue
        if not due or due == "unknown" or due <= today:
            continue
        clean.append(rec)
    data["discovered"] = clean
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
# SAM notice types: p=presolicitation, o=solicitation, k=combined synopsis,
# r=sources sought, g=sale of surplus, s=special notice, a=award notice
PTYPE_STATUS = {"p": "pre-release", "r": "pre-release", "o": "open", "k": "open", "s": "open"}
PTYPE_STAGE = {"p": "Pre-Solicitation", "r": "Sources Sought", "o": "Active RFP/RFQ",
               "k": "Active RFP/RFQ", "s": "Special Notice"}


def _due_time(raw: str) -> str:
    """Preserve the deadline's exact time + UTC offset, e.g. '17:00 (-04:00)'."""
    if not raw or len(raw) < 16:
        return ""
    time_part = raw[11:16]
    tz = raw[19:] if len(raw) > 19 else ""
    return f"{time_part} ({tz})" if tz else time_part


def _mmddyyyy(dt):
    return dt.strftime("%m/%d/%Y")


def _sam_amount(o):
    """Best-effort dollar figure from a SAM notice (award amount or stated ceiling)."""
    award = o.get("award") or {}
    for candidate in (award.get("amount"), o.get("awardCeiling"), o.get("ceiling")):
        try:
            v = float(str(candidate).replace(",", "").replace("$", ""))
            if v > 0:
                return v
        except (TypeError, ValueError):
            continue
    return 0


async def fetch_sam(api_key, naics, keywords, limit=60, psc=None):
    """Pull active SAM.gov opportunities relevant to the org.

    Relevance controls: response deadline must be in the future (rdlfrom),
    queries run per-NAICS (up to 3 codes) plus per-PSC classification code
    (up to 2), and results must match the org's keywords in
    title/description when keywords are configured."""
    posted_to = datetime.now(timezone.utc)
    posted_from = posted_to - timedelta(days=120)
    today = posted_to.strftime("%Y-%m-%d")

    base = {
        "api_key": api_key,
        "postedFrom": _mmddyyyy(posted_from),
        "postedTo": _mmddyyyy(posted_to),
        "rdlfrom": _mmddyyyy(posted_to),  # response deadline >= today: no expired notices
        "rdlto": _mmddyyyy(posted_to + timedelta(days=365)),
        "ptype": "o,p,k,r",               # solicitations & pre-solicitations, not awards/sales
        "limit": str(limit),
        "offset": "0",
    }
    queries = [{**base, "ncode": n} for n in (naics or [])[:3]]
    queries += [{**base, "ccode": c} for c in (psc or [])[:2]]
    queries = queries or [dict(base)]

    raw = []
    async with httpx.AsyncClient(timeout=40) as client:
        for params in queries:
            r = await client.get("https://api.sam.gov/opportunities/v2/search", params=params)
            if r.status_code in (401, 403):
                raise PermissionError("SAM.gov rejected the API key (401/403)")
            r.raise_for_status()
            raw.extend((r.json().get("opportunitiesData") or []))

    kws = [k.lower() for k in (keywords or []) if k.strip()]
    results, seen = [], set()
    for o in raw:
        sol = (o.get("solicitationNumber") or o.get("noticeId") or "").strip()
        if sol in seen:
            continue
        seen.add(sol)
        title = o.get("title", "") or ""
        desc = (o.get("description") or "")[:2000]
        hay = f"{title} {desc}".lower()
        # keyword relevance gate (only when the org has keywords configured)
        if kws and not any(k in hay for k in kws):
            continue
        due_raw = o.get("responseDeadLine") or ""
        due = due_raw[:10] or None
        if due and due < today:
            continue  # belt-and-suspenders: never surface expired notices
        sa_code = o.get("typeOfSetAside") or ""
        ptype = (o.get("type") or "").lower()[:1]
        # Normalize SAM.gov pointOfContact entries into a compact PoC list.
        # SAM returns primary/secondary contacts (contract + technical) — keep
        # the ones with a real name and classify by `type` (primary=PoC,
        # secondary=TPoC) so the UI can render both roles.
        pocs = []
        for pc in (o.get("pointOfContact") or [])[:6]:
            name = (pc.get("fullName") or "").strip()
            email = (pc.get("email") or "").strip()
            phone = (pc.get("phone") or "").strip()
            if not (name or email):
                continue
            ctype = (pc.get("type") or "").lower()
            role = "TPoC" if "secondary" in ctype or "tech" in ctype else "PoC"
            pocs.append({"name": name, "role": role,
                         "title": (pc.get("title") or "").strip(),
                         "email": email, "phone": phone})
        results.append({
            "title": title,
            "solNumber": sol,
            "agency": o.get("fullParentPathName", "").split(".")[0] if o.get("fullParentPathName") else "",
            "office": (o.get("fullParentPathName", "").split(".")[-1] if o.get("fullParentPathName") else ""),
            "vehicle": PTYPE_VEHICLE.get(ptype, "RFP"),
            "noticeStatus": PTYPE_STATUS.get(ptype, "open"),
            "setAside": SETASIDE_LABELS.get(sa_code, sa_code or "None"),
            "naics": o.get("naicsCode") or (naics[0] if naics else ""),
            "ceiling": _sam_amount(o),
            "dueDate": due,
            "dueTime": _due_time(due_raw),
            "psc": o.get("classificationCode") or "",
            "acqStage": PTYPE_STAGE.get(ptype, ""),
            "oppType": "Contract",
            "url": o.get("uiLink") or "",
            "source": "sam",
            "pocs": pocs,
            "description": desc,
        })
    return results


# ----------------------------- Grants.gov -----------------------------------
async def fetch_grants(keywords, rows=25):
    kw = " ".join(keywords or []) or "research"
    body = {"keyword": kw, "oppStatuses": "forecasted|posted", "rows": rows}
    results = []
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post("https://api.grants.gov/v1/api/search2", json=body)
        r.raise_for_status()
        data = r.json()
    hits = (((data or {}).get("data") or {}).get("oppHits")) or []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for h in hits:
        due = (h.get("closeDate") or "")[:10] or None
        if due and due < today:
            continue
        ceiling = 0
        try:
            ceiling = float(str(h.get("awardCeiling") or 0).replace(",", "")) or 0
        except (TypeError, ValueError):
            pass
        results.append({
            "title": h.get("title", ""),
            "solNumber": h.get("number", "") or h.get("id", ""),
            "agency": h.get("agency", "") or h.get("agencyName", ""),
            "office": "",
            "vehicle": "Grant",
            "noticeStatus": "open" if (h.get("oppStatus") or "posted") == "posted" else "pre-release",
            "setAside": "None",
            "naics": "",
            "ceiling": ceiling,
            "dueDate": due,
            "acqStage": "Forecast" if (h.get("oppStatus") or "posted") != "posted" else "Active RFP/RFQ",
            "oppType": "Grant",
            "valueType": "Max individual award" if ceiling else "",
            "url": f"https://www.grants.gov/search-results-detail/{h.get('id', '')}",
            "source": "grants",
        })
    return results
