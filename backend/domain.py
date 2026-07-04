import database as db
from utils import as_uuid


async def write_audit(org_id, user, action, target=None, meta=None):
    await db.execute(
        """insert into audit_log
               (organization_id, user_id, user_email, user_name, action, target, meta)
           values ($1, $2, $3, $4, $5, $6, $7)""",
        as_uuid(org_id), as_uuid(user["id"]), user.get("email"), user.get("name"),
        action, target, meta or {})


# ---- Set-aside eligibility logic (org profile drives eligibility) ----
SETASIDE_CERT_MAP = {
    "8(a)": "eightA",
    "8A": "eightA",
    "HUBZone": "hubzone",
    "HZC": "hubzone",
    "SDVOSB": "sdvosb",
    "SDVOSBC": "sdvosb",
    "WOSB": "wosb",
    "EDWOSB": "edwosb",
    "VOSB": "vosb",
    "Total Small Business": "isSmall",
    "Small Business": "isSmall",
    "SBA": "isSmall",
}


def compute_eligibility(set_aside: str, profile: dict):
    """Returns (verdict, reason). verdict in eligible|not_certified|verify|open.
    `profile` is a serialized (camelCase) org profile dict, or None."""
    if not set_aside or set_aside.lower() in ("none", "full and open", "full & open", "n/a"):
        return ("open", "Full & open — no set-aside restriction")
    if not profile:
        return ("verify", "No org profile on file — verify eligibility")
    cert_key = SETASIDE_CERT_MAP.get(set_aside)
    if cert_key is None:
        return ("verify", f"Unknown set-aside '{set_aside}' — verify manually")
    if cert_key == "isSmall":
        return ("eligible", "Small business") if profile.get("isSmall") else \
               ("not_certified", "Org is not flagged as small business")
    certs = profile.get("certs", {}) or {}
    if certs.get(cert_key):
        return ("eligible", f"Holds required certification ({set_aside})")
    return ("not_certified",
            f"Org does not hold the {set_aside} certification (self-certification not accepted)")


# ---- Default opportunity skeleton ----
FIT_FACTORS = [
    "Mission Alignment", "Technical Capability", "Past Performance",
    "Customer Relationship", "Competitive Position", "Price Competitiveness",
    "Resources / Capacity", "Teaming Strength", "Risk Profile", "Strategic Value",
]


def default_fit():
    return {f: 3 for f in FIT_FACTORS}


def default_compliance():
    return [
        {"item": "SAM.gov active registration", "req": "mandatory", "status": "met", "note": ""},
        {"item": "NAICS size standard met", "req": "mandatory", "status": "met", "note": ""},
        {"item": "CMMC level required", "req": "mandatory", "status": "gap", "note": "Confirm DFARS 252.204-7021/-7025"},
        {"item": "Page/format limits", "req": "mandatory", "status": "partial", "note": ""},
        {"item": "Past performance references", "req": "optional", "status": "partial", "note": ""},
    ]


def default_budget(ceiling=0):
    return {
        "ceiling": ceiling,
        "groups": {
            "Labor": 0, "Burden": 0, "Materials": 0, "Subcontracts": 0,
            "ODC": [],
        },
    }


def default_criteria():
    return [
        {"name": "Technical Merit", "weight": 40, "score": 0, "note": ""},
        {"name": "Management Approach", "weight": 25, "score": 0, "note": ""},
        {"name": "Past Performance", "weight": 20, "score": 0, "note": ""},
        {"name": "Cost / Price", "weight": 15, "score": 0, "note": ""},
    ]
