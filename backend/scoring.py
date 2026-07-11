"""Deterministic capture-qualification engine.

Eligibility gates, weighted Fit Score, PWin banding, financial derivations and
pursuit Priority are recomputed server-side on every read, so they always
reflect the current org profile and the latest saved/amended opportunity data.
Nothing here fabricates data — missing inputs surface as "Unknown".

Decision variables stay separate on purpose: a failed hard eligibility gate can
never be concealed by a high Fit Score, and PWin is never blended into Fit.
"""
import re
from datetime import datetime, timezone

from domain import compute_eligibility

# Weighted fit model (sums to 100).
FIT_WEIGHTS = [
    ("Capability match", 30),
    ("Past performance", 20),
    ("Customer alignment", 15),
    ("Delivery readiness", 10),
    ("Acquisition model", 10),
    ("Financial attractiveness", 10),
    ("Strategic value", 5),
]

_STOP = {"the", "and", "for", "with", "this", "that", "from", "into", "will",
         "shall", "must", "have", "are", "was", "were", "been", "its", "their",
         "other", "than", "them", "then", "when", "each", "which", "such"}


def _tokens(text):
    return {w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower())} - _STOP


def _days_until(date_str):
    if not date_str:
        return None
    try:
        d = datetime.fromisoformat(str(date_str)[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (d - datetime.now(timezone.utc)).days


# --------------------------- Eligibility gates -------------------------------

def eligibility_gates(o, profile):
    """Hard-gate evaluation. Returns {status, verdict, reason, gates}.
    status ∈ Eligible | Conditional | Ineligible | Unknown."""
    gates = []

    def add(gate, status, note=""):
        gates.append({"gate": gate, "status": status, "note": note})

    verdict, reason = compute_eligibility(o.get("setAside", ""), profile)
    sa_status = {"eligible": "pass", "open": "pass",
                 "not_certified": "fail", "verify": "unknown"}[verdict]
    add("Set-aside certification", sa_status, reason)

    p = profile or {}
    if not profile:
        add("SAM registration", "unknown", "No company profile on file")
    else:
        add("SAM registration", "pass" if p.get("samActive") else "fail",
            "SAM.gov registration active" if p.get("samActive")
            else "SAM.gov registration inactive or expired")
        if sa_status == "pass" and verdict == "eligible" and not p.get("isSmall"):
            add("NAICS size standard", "fail",
                "Org is not small under the assigned NAICS")
        elif p.get("isSmall"):
            std = o.get("sizeStandard") or ""
            add("NAICS size standard", "pass",
                f"Small business{(' — standard: ' + std) if std else ''}")
        else:
            add("NAICS size standard", "unknown", "Size vs. standard not assessed")

    va = (o.get("vehicleAccess") or "").lower()
    if va == "need":
        add("Contract-vehicle access", "fail",
            f"No access to the required vehicle ({o.get('vehicle', '')})")
    elif va in ("have", "open"):
        add("Contract-vehicle access", "pass",
            "Vehicle held" if va == "have" else "Open-market submission")
    else:
        add("Contract-vehicle access", "unknown", "Vehicle access not assessed")

    flags = " ".join(str(t) for t in (o.get("tags") or [])).lower()
    cmmc_req = 3 if "cmmc l3" in flags else 2 if "cmmc l2" in flags else None
    if cmmc_req:
        held = 0
        m = re.search(r"level\s*(\d)", str(p.get("cmmcLevel") or ""), re.I)
        if m:
            held = int(m.group(1))
        if held >= cmmc_req:
            add("CMMC", "pass", f"Requires L{cmmc_req}; org at L{held}")
        else:
            add("CMMC", "conditional",
                f"Requires CMMC L{cmmc_req}; org at L{held or '?'} — remediation needed")
    if any(k in flags for k in ("secret", "ts-sci", "fcl")):
        if (p.get("clearances") or "").strip():
            add("Clearances", "pass", f"On file: {p.get('clearances')}")
        else:
            add("Clearances", "conditional",
                "Clearance requirement flagged; none documented in profile")
    if "itar" in flags or "ear" in flags:
        add("ITAR / export controls", "conditional",
            "ITAR/EAR applies — confirm export-compliance and citizenship posture")

    days = _days_until(o.get("dueDate"))
    if days is not None and days < 0:
        add("Response deadline", "fail", "The response deadline has passed")

    statuses = [g["status"] for g in gates]
    if "fail" in statuses:
        status = "Ineligible"
        reason = next(g["note"] or g["gate"] for g in gates if g["status"] == "fail")
    elif "conditional" in statuses:
        status = "Conditional"
        reason = next(g["note"] or g["gate"] for g in gates if g["status"] == "conditional")
    elif sa_status == "unknown":
        status = "Unknown"
    else:
        status = "Eligible"
    return {"status": status, "verdict": verdict, "reason": reason, "gates": gates}


# ------------------------------- Fit score -----------------------------------

def _cat(name, score, evidence):
    weight = dict(FIT_WEIGHTS)[name]
    return {"category": name, "weight": weight,
            "score": int(max(0, min(100, round(score)))), "evidence": evidence}


def fit_score(o, profile, org=None):
    p = profile or {}
    org = org or {}
    cats = []
    hay = " ".join([o.get("title", ""), o.get("scopeSummary", ""),
                    o.get("naicsTitle", ""), " ".join(str(t) for t in (o.get("tags") or []))])
    hay_t = _tokens(hay)
    cap_t = _tokens(" ".join([p.get("capabilities", "") or "",
                              " ".join(p.get("techFocus") or []),
                              " ".join(org.get("keywords") or [])]))

    ai = ((o.get("aiEnrichment") or {}).get("requirementMatches")) or []
    if ai:
        num = den = 0
        for m in ai:
            w = 2 if m.get("mandatory") else 1
            num += w * (m.get("score") or 0)
            den += w
        s = num / den if den else 0
        mand_gaps = sum(1 for m in ai if m.get("mandatory") and (m.get("score") or 0) <= 25)
        ev = (f"{len(ai)} AI-extracted requirements matched against profile evidence"
              + (f"; {mand_gaps} mandatory gap(s)" if mand_gaps else ""))
        cats.append(_cat("Capability match", s, ev))
    else:
        overlap = hay_t & cap_t
        s = min(100, len(overlap) * 18)
        naics_match = o.get("naics") and o.get("naics") in (org.get("naics") or [])
        if naics_match:
            s = max(s, 40)
        ev = (f"Keyword overlap with profile: {', '.join(sorted(overlap)[:6]) or 'none'}"
              + ("; NAICS match (weak signal alone)" if naics_match else ""))
        cats.append(_cat("Capability match", s, ev))

    pp = (p.get("pastPerformance") or "").strip()
    if not pp:
        cats.append(_cat("Past performance", 10, "No past performance documented in profile"))
    else:
        s = 55
        ag = (o.get("agency") or "").lower()
        if ag and ag.split()[0] in pp.lower():
            s = 90
        cats.append(_cat("Past performance", s,
                         "Documented past performance" + (" incl. this customer" if s == 90 else "")))

    tas = [t.lower() for t in (p.get("targetAgencies") or [])]
    ag = (o.get("agency") or "").lower()
    if ag and tas and any(t in ag or ag in t for t in tas):
        cats.append(_cat("Customer alignment", 95, f"{o.get('agency')} is a target customer"))
    elif not tas:
        cats.append(_cat("Customer alignment", 40, "No target agencies configured in profile"))
    else:
        cats.append(_cat("Customer alignment", 25, f"{o.get('agency') or 'Customer'} not in target list"))

    days = _days_until(o.get("dueDate"))
    if days is None:
        s, ev = 40, "No due date on file"
    elif days < 7:
        s, ev = 15, f"Only {max(days, 0)} day(s) to respond"
    elif days < 14:
        s, ev = 40, f"{days} days to respond — tight"
    elif days < 30:
        s, ev = 65, f"{days} days to respond"
    else:
        s, ev = 85, f"{days} days to respond — adequate runway"
    cats.append(_cat("Delivery readiness", s, ev))

    va = (o.get("vehicleAccess") or "").lower()
    direct = (o.get("oppType") or o.get("vehicle") or "") in ("SBIR", "STTR", "BAA", "Grant", "CSO")
    if va == "need":
        cats.append(_cat("Acquisition model", 15, "Required vehicle not held"))
    elif va in ("have", "open") or direct:
        cats.append(_cat("Acquisition model", 85, "Vehicle held / open submission"))
    else:
        cats.append(_cat("Acquisition model", 50, "Vehicle access unknown"))

    val = o.get("addressableValue") or (o.get("ceiling") or 0)
    if not val:
        cats.append(_cat("Financial attractiveness", 40, "Value unknown"))
    elif val >= 1_000_000:
        cats.append(_cat("Financial attractiveness", 85, "≥ $1M potential"))
    elif val >= 250_000:
        cats.append(_cat("Financial attractiveness", 70, "≥ $250K potential"))
    elif val >= 50_000:
        cats.append(_cat("Financial attractiveness", 55, "≥ $50K potential"))
    else:
        cats.append(_cat("Financial attractiveness", 30, "< $50K potential"))

    tf = _tokens(" ".join(p.get("techFocus") or []))
    strat = 75 if (hay_t & tf) else 50
    cats.append(_cat("Strategic value", strat,
                     "Aligned with declared technology focus" if strat == 75 else "Neutral strategic signal"))

    nogo = _tokens(p.get("noGo") or "")
    nogo_hit = sorted(hay_t & nogo)
    score = round(sum(c["score"] * c["weight"] for c in cats) / 100)
    if nogo_hit:
        score = min(score, 20)

    capture = o.get("capture") or {}
    override = capture.get("fitOverride")
    effective = int(override) if isinstance(override, (int, float)) and override else score
    band = ("Strong" if effective >= 85 else "Good" if effective >= 70
            else "Conditional" if effective >= 55 else "Poor")
    confidence = ("high" if ai and profile else
                  "medium" if profile and (p.get("capabilities") or "").strip() else "low")
    out = {"score": score, "effective": effective, "band": band,
           "confidence": confidence, "breakdown": cats}
    if nogo_hit:
        out["noGo"] = f"Matches profile no-go terms: {', '.join(nogo_hit[:4])}"
    if override:
        out["override"] = {"score": int(override), "note": capture.get("fitOverrideNote") or ""}
    return out


# --------------------------------- PWin ---------------------------------------

def pwin_view(o):
    pct = int(o.get("pwin") or 0)
    if pct <= 0:
        return {"band": "Unknown", "pct": None, "basis": "Not assessed"}
    band = "High" if pct >= 60 else "Medium" if pct >= 35 else "Low"
    return {"band": band, "pct": pct, "basis": "Manual capture assessment"}


# ------------------------------ Financials ------------------------------------

def financial_view(o, pwin):
    stated = float(o.get("ceiling") or 0) or None
    vtype = o.get("valueType") or ("Unknown" if stated else "")
    multi = "multi" in (o.get("awardsCount") or "").lower()
    shared = multi or vtype in ("Ceiling", "Program funding")
    addressable = o.get("addressableValue")
    inferred = False
    note = ""
    if addressable is None and stated:
        if shared:
            note = ("Shared ceiling / program funding — set your realistic "
                    "addressable value; the full figure is NOT expected revenue")
        else:
            addressable, inferred = stated, True
            note = "Assumed full stated value — refine if multi-award or partial workshare"
    weighted = None
    if addressable and pwin.get("pct"):
        weighted = round(addressable * pwin["pct"] / 100)
    return {"statedValue": stated, "valueType": vtype,
            "valueConfidence": o.get("valueConfidence") or ("stated" if stated else ""),
            "addressableValue": addressable, "addressableInferred": inferred,
            "sharedCeiling": shared, "weightedPipeline": weighted, "note": note}


# ------------------------------- Priority -------------------------------------

def priority_view(o, elig, fit, pwin, fin):
    if elig["status"] == "Ineligible":
        failed = next((g for g in elig["gates"] if g["status"] == "fail"), None)
        return {"label": "Pass", "note": f"Failed gate: {failed['gate'] if failed else 'eligibility'}"}
    call = ((o.get("decision") or {}).get("call") or "").lower()
    if call == "no-bid":
        return {"label": "Pass", "note": "Marked No-Bid"}
    if fit.get("noGo"):
        return {"label": "Pass", "note": fit["noGo"]}
    if o.get("watch") and call != "bid":
        return {"label": "Watch", "note": "On watchlist"}
    band, pband = fit["band"], pwin["band"]
    days = _days_until(o.get("dueDate"))
    urgent = days is not None and 0 <= days <= 14
    if band == "Strong" and pband != "Low":
        return {"label": "A", "note": "Strong fit" + (" — due soon, act now" if urgent else "")}
    if band == "Strong" or (band == "Good" and pband == "High"):
        return {"label": "A" if urgent else "B",
                "note": "High potential" + (" — deadline approaching" if urgent else "")}
    if band == "Good":
        return {"label": "B", "note": "Good fit — qualify further"}
    if band == "Conditional":
        return {"label": "C", "note": "Conditional fit — teaming or gap closure needed"}
    return {"label": "Watch", "note": "Poor fit — monitor only"}


# ------------------------------- Red flags ------------------------------------

def red_flags(o, elig, fin):
    flags = []
    for g in elig["gates"]:
        if g["status"] == "fail":
            flags.append({"severity": "high", "flag": g["note"] or g["gate"]})
    for g in elig["gates"]:
        if g["status"] == "conditional":
            flags.append({"severity": "medium", "flag": g["note"] or g["gate"]})
    days = _days_until(o.get("dueDate"))
    if days is None:
        flags.append({"severity": "low", "flag": "No response due date on file"})
    elif days < 0:
        flags.append({"severity": "high", "flag": "Response deadline has passed"})
    elif days <= 7:
        flags.append({"severity": "high", "flag": f"Due in {days} day(s)"})
    if fin["sharedCeiling"] and not o.get("addressableValue"):
        flags.append({"severity": "medium",
                      "flag": "Shared ceiling — addressable value not set"})
    if (o.get("vehicleAccess") or "").lower() == "need":
        flags.append({"severity": "high", "flag": "Required contract vehicle not held"})
    if o.get("incumbent"):
        flags.append({"severity": "medium", "flag": f"Incumbent: {o['incumbent']}"})
    nad = ((o.get("capture") or {}).get("nextActionDue") or "")[:10]
    if nad and _days_until(nad) is not None and _days_until(nad) < 0:
        flags.append({"severity": "medium", "flag": "Next capture action overdue"})
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(flags, key=lambda f: order[f["severity"]])


# ------------------------------- Decorator ------------------------------------

def decorate(o, profile, org=None):
    """Attach all derived qualification views to a serialized opportunity."""
    elig = eligibility_gates(o, profile)
    fit = fit_score(o, profile, org)
    pwin = pwin_view(o)
    fin = financial_view(o, pwin)
    o["eligibility"] = {"verdict": elig["verdict"], "reason": elig["reason"],
                        "status": elig["status"], "gates": elig["gates"]}
    o["fitComputed"] = fit
    o["pwinView"] = pwin
    o["financials"] = fin
    o["priority"] = priority_view(o, elig, fit, pwin, fin)
    o["redFlags"] = red_flags(o, elig, fin)
    days = _days_until(o.get("dueDate"))
    o["daysRemaining"] = days
    return o
