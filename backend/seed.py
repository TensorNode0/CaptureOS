import os
import random
from datetime import timedelta
from bson import ObjectId

from database import db
from utils import now_utc, iso
from auth_utils import hash_password, verify_password
from domain import default_fit, default_compliance, default_budget, default_criteria

SETASIDES = ["Total Small Business", "8(a)", "HUBZone", "SDVOSB", "WOSB", "None"]
VEHICLES = ["RFP", "SBIR", "STTR", "BAA", "CSO", "Grant"]
STAGES = ["Identified", "Qualifying", "Building", "Submitted", "Won", "Lost", "No-Bid"]
AGENCIES = [
    ("Department of the Air Force", "AFRL"),
    ("Department of the Navy", "NAVSEA"),
    ("Department of the Army", "ACC-APG"),
    ("Defense Logistics Agency", "DLA"),
    ("DARPA", "TTO"),
    ("Department of Defense", "DSIP"),
]
TITLES = [
    "Tactical UAS Propulsion Upgrade", "Hypersonic Materials Testbed",
    "Cyber Resiliency Assessment", "AI/ML Mission Autonomy", "Edge ISR Compute Node",
    "Quantum Navigation Sensor", "Directed Energy Cooling System",
    "Secure Tactical Mesh Network", "Additive Mfg for Spares", "Counter-UAS Effectors",
    "Space Domain Awareness Optics", "Predictive Maintenance Platform",
]


async def _make_opp(org_oid, owner_oid, i):
    agency, office = random.choice(AGENCIES)
    sa = random.choice(SETASIDES)
    veh = random.choice(VEHICLES)
    stage = random.choice(STAGES)
    ceiling = random.choice([850000, 1800000, 2400000, 4800000, 9500000, 12500000])
    days = random.choice([-10, 3, 6, 14, 22, 40, 65, 120])
    due = (now_utc() + timedelta(days=days)).date().isoformat()
    sol = f"{random.choice(['FA8650','N00024','W519TC','SP4701'])}-26-R-{1000 + i}"
    fit = default_fit()
    for k in fit:
        fit[k] = random.randint(2, 5)
    budget = default_budget(ceiling)
    budget["groups"]["Labor"] = int(ceiling * 0.5)
    budget["groups"]["Burden"] = int(ceiling * 0.2)
    budget["groups"]["Materials"] = int(ceiling * 0.1)
    budget["groups"]["Subcontracts"] = int(ceiling * 0.1)
    crit = default_criteria()
    for c in crit:
        c["score"] = random.randint(5, 9)
    return {
        "organizationId": org_oid,
        "title": random.choice(TITLES) + f" {chr(65 + (i % 6))}",
        "solNumber": sol,
        "agency": agency, "office": office, "vehicle": veh,
        "setAside": sa, "naics": random.choice(["336412", "541715", "541512", "541611"]),
        "ceiling": ceiling, "pop": "12 mo base + 2 option yrs", "dueDate": due,
        "stage": stage, "url": f"https://sam.gov/opp/{sol}", "winThemes": "Low-risk, proven team",
        "source": random.choice(["manual", "sam", "grants"]),
        "lastVerified": now_utc() if random.random() > 0.4 else None,
        "verifyReport": None,
        "links": [{"label": "Solicitation", "url": f"https://sam.gov/opp/{sol}",
                   "status": "live", "checkedAt": iso(now_utc())}],
        "fit": fit, "pwin": random.randint(15, 75),
        "proposalStrength": round(random.uniform(4.5, 9.0), 1),
        "compliance": default_compliance(), "budget": budget,
        "criteria": crit, "decision": {"call": "TBD", "rationale": ""},
        "createdBy": owner_oid, "createdAt": now_utc(), "updatedAt": now_utc(),
    }


async def seed():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@govcon.io").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin#2026")

    admin = await db.users.find_one({"email": admin_email})
    if not admin:
        res = await db.users.insert_one({
            "email": admin_email, "name": "Mission Commander",
            "password_hash": hash_password(admin_password),
            "emailVerified": True, "created_at": now_utc(),
        })
        admin = await db.users.find_one({"_id": res.inserted_id})
    elif not verify_password(admin_password, admin["password_hash"]):
        await db.users.update_one({"_id": admin["_id"]},
                                  {"$set": {"password_hash": hash_password(admin_password)}})

    admin_oid = admin["_id"]

    # secondary demo users
    async def ensure_user(email, name):
        u = await db.users.find_one({"email": email})
        if not u:
            r = await db.users.insert_one({
                "email": email, "name": name,
                "password_hash": hash_password("Editor#2026"),
                "emailVerified": True, "created_at": now_utc()})
            u = await db.users.find_one({"_id": r.inserted_id})
        return u

    editor = await ensure_user("editor@govcon.io", "Capture Lead")
    viewer = await ensure_user("viewer@govcon.io", "Proposal Analyst")

    # demo org
    org = await db.organizations.find_one({"name": "Orbital Defense Systems"})
    if not org:
        r = await db.organizations.insert_one({
            "name": "Orbital Defense Systems",
            "naics": ["336412", "541715", "541512"],
            "keywords": ["UAS", "hypersonic", "cyber", "autonomy"],
            "ownerId": admin_oid, "createdAt": now_utc(),
        })
        org = await db.organizations.find_one({"_id": r.inserted_id})
        org_oid = org["_id"]
        # memberships
        await db.memberships.insert_many([
            {"userId": admin_oid, "invitedEmail": admin_email, "organizationId": org_oid,
             "role": "owner", "invitedBy": None, "status": "active", "createdAt": now_utc()},
            {"userId": editor["_id"], "invitedEmail": "editor@govcon.io",
             "organizationId": org_oid, "role": "editor", "invitedBy": admin_oid,
             "status": "active", "createdAt": now_utc()},
            {"userId": viewer["_id"], "invitedEmail": "viewer@govcon.io",
             "organizationId": org_oid, "role": "viewer", "invitedBy": admin_oid,
             "status": "active", "createdAt": now_utc()},
        ])
        # profile
        await db.orgProfile.insert_one({
            "organizationId": org_oid, "uei": "ORB1TALDEF99", "cage": "8XQ21",
            "samActive": True, "isSmall": True,
            "certs": {"sba": True, "eightA": False, "hubzone": False,
                      "sdvosb": True, "wosb": False, "edwosb": False, "vosb": True},
            "cmmcLevel": "Level 2", "sprsScore": 88,
            "sizeNote": "Under 500 employees", "notes": "Dual-use aerospace & defense.",
        })
        # opportunities
        opps = [await _make_opp(org_oid, admin_oid, i) for i in range(12)]
        await db.opportunities.insert_many(opps)
        await db.auditLog.insert_one({
            "organizationId": org_oid, "userId": admin_oid, "userEmail": admin_email,
            "userName": "Mission Commander", "action": "seed.demo",
            "target": "Orbital Defense Systems", "meta": {}, "at": now_utc()})

    # write test credentials
    os.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(f"""# Test Credentials — GovCon Command Center

## Admin / Owner
- Email: `{admin_email}`
- Password: `{admin_password}`
- Role in 'Orbital Defense Systems': owner

## Editor
- Email: `editor@govcon.io`
- Password: `Editor#2026`
- Role: editor

## Viewer
- Email: `viewer@govcon.io`
- Password: `Editor#2026`
- Role: viewer

## Notes
- Demo org: **Orbital Defense Systems** (seeded with 12 opportunities + org profile).
- Email verification is MOCKED: register returns a `verifyUrl`; password reset returns `resetUrl`.
- AI 'Verify & Refresh' and 'Pull from SAM/Grants' are MOCKED (Phase 5 wires real keys).

## Auth endpoints
- POST /api/auth/register | /login | /logout | /refresh | /forgot-password | /reset-password | /verify-email
- GET  /api/auth/me
""")
