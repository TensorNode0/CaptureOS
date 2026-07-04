"""Demo-data seeder. Runs at startup only when SEED_DEMO=1 (safe for prod)."""
import os
import random
from datetime import timedelta

import database as db
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


async def _make_opp(org_id, owner_id, i):
    agency, office = random.choice(AGENCIES)
    sa = random.choice(SETASIDES)
    veh = random.choice(VEHICLES)
    stage = random.choice(STAGES)
    ceiling = random.choice([850000, 1800000, 2400000, 4800000, 9500000, 12500000])
    days = random.choice([-10, 3, 6, 14, 22, 40, 65, 120])
    due = (now_utc() + timedelta(days=days)).date().isoformat()
    sol = f"{random.choice(['FA8650', 'N00024', 'W519TC', 'SP4701'])}-26-R-{1000 + i}"
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
    links = [{"label": "Solicitation", "url": f"https://sam.gov/opp/{sol}",
              "status": "live", "checkedAt": iso(now_utc())}]
    await db.execute(
        """insert into opportunities
               (organization_id, title, sol_number, agency, office, vehicle, set_aside,
                naics, ceiling, pop, due_date, stage, url, win_themes, source,
                last_verified, links, fit, pwin, proposal_strength, compliance,
                budget, criteria, created_by)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                   $16, $17, $18, $19, $20, $21, $22, $23, $24)""",
        org_id, random.choice(TITLES) + f" {chr(65 + (i % 6))}", sol, agency, office,
        veh, sa, random.choice(["336412", "541715", "541512", "541611"]), ceiling,
        "12 mo base + 2 option yrs", due, stage, f"https://sam.gov/opp/{sol}",
        "Low-risk, proven team", random.choice(["manual", "sam", "grants"]),
        now_utc() if random.random() > 0.4 else None, links, fit,
        random.randint(15, 75), round(random.uniform(4.5, 9.0), 1),
        default_compliance(), budget, crit, owner_id)


async def _ensure_user(email, name, password):
    u = await db.fetchrow("select * from users where email = $1", email)
    if not u:
        u = await db.fetchrow(
            """insert into users (email, name, password_hash, email_verified)
               values ($1, $2, $3, true) returning *""",
            email, name, hash_password(password))
    return u


async def seed():
    if os.environ.get("SEED_DEMO", "0") != "1":
        return

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@govcon.io").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin#2026")

    admin = await db.fetchrow("select * from users where email = $1", admin_email)
    if not admin:
        admin = await _ensure_user(admin_email, "Mission Commander", admin_password)
    elif not verify_password(admin_password, admin["password_hash"]):
        await db.execute("update users set password_hash = $2 where id = $1",
                         admin["id"], hash_password(admin_password))

    editor = await _ensure_user("editor@govcon.io", "Capture Lead", "Editor#2026")
    viewer = await _ensure_user("viewer@govcon.io", "Proposal Analyst", "Editor#2026")

    org = await db.fetchrow("select * from organizations where name = $1",
                            "Orbital Defense Systems")
    if org:
        return

    org = await db.fetchrow(
        """insert into organizations (name, naics, keywords, owner_id, join_code)
           values ($1, $2, $3, $4, $5) returning *""",
        "Orbital Defense Systems", ["336412", "541715", "541512"],
        ["UAS", "hypersonic", "cyber", "autonomy"], admin["id"], "DEMO2026")
    org_id = org["id"]
    for user, email, role, inviter in (
        (admin, admin_email, "owner", None),
        (editor, "editor@govcon.io", "editor", admin["id"]),
        (viewer, "viewer@govcon.io", "viewer", admin["id"]),
    ):
        await db.execute(
            """insert into memberships (user_id, invited_email, organization_id, role,
                                        invited_by, status)
               values ($1, $2, $3, $4, $5, 'active')""",
            user["id"], email, org_id, role, inviter)
    await db.execute(
        """insert into org_profiles
               (organization_id, uei, cage, sam_active, is_small, certs, cmmc_level,
                sprs_score, size_note, notes)
           values ($1, $2, $3, true, true, $4, 'Level 2', 88, $5, $6)""",
        org_id, "ORB1TALDEF99", "8XQ21",
        {"sba": True, "eightA": False, "hubzone": False, "sdvosb": True,
         "wosb": False, "edwosb": False, "vosb": True},
        "Under 500 employees", "Dual-use aerospace & defense.")
    for i in range(12):
        await _make_opp(org_id, admin["id"], i)
    await db.execute(
        """insert into audit_log (organization_id, user_id, user_email, user_name,
                                  action, target, meta)
           values ($1, $2, $3, $4, 'seed.demo', 'Orbital Defense Systems', '{}')""",
        org_id, admin["id"], admin_email, "Mission Commander")
    print("[seed] demo org 'Orbital Defense Systems' created")
