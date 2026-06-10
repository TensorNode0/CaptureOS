"""Insert a realistic SAMPLE intel report for UI verification, then it can be deleted."""
import os, sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient
from bson import ObjectId

c = MongoClient(os.environ["MONGO_URL"])
db = c[os.environ["DB_NAME"]]
ORG = ObjectId("6a23e286bc6ad92b27c235f0")
today = datetime.now(timezone.utc)

def d(n):
    return (today + timedelta(days=n)).date().isoformat()

opps = [
    {"fitScore": 94, "fitGrade": "Excellent", "fitRationale": "Direct match to EO/IR payload + edge-AI ISR past performance.",
     "agency": "Department of the Air Force", "office": "AFRL/RYM", "dueDate": d(5), "awardAmount": 1900000,
     "solNumber": "AF254-D012", "solUrl": "https://www.dodsbirsttr.mil/topics-app/", "title": "SBIR: Edge AI for Autonomous ISR Targeting",
     "topicUrl": "https://afwerx.com/", "summary": "Open topic for on-board AI/ML enabling autonomous ISR target recognition at the tactical edge for Group 3 UAS.",
     "phase": "SBIR Phase II", "colorOfMoney": "RDT&E", "vehicle": "SBIR Phase II", "contractType": "FFP",
     "compliance": ["CMMC L2", "ITAR/EAR", "CUI"], "cta": ["Trusted AI & Autonomy", "Space Technology"], "techType": "S/W",
     "missionCategory": "AI / ML / GenAI", "missionSecondary": "UAS/UAV/Drones", "setAside": "Total Small Business",
     "teaming": "Prime", "notes": "Pitch day in 30 days; STRATFI follow-on likely."},
    {"fitScore": 81, "fitGrade": "Very Good", "fitRationale": "Strong space-domain awareness alignment; needs RF sensor partner.",
     "agency": "U.S. Space Force", "office": "SpaceWERX", "dueDate": d(12), "awardAmount": 1250000,
     "solNumber": "SF254-0007", "solUrl": "https://spacewerx.us/", "title": "Space Domain Awareness Sensor Fusion",
     "topicUrl": "https://spacewerx.us/", "summary": "Commercial solutions for multi-source SDA sensor fusion and orbital object custody.",
     "phase": "SBIR Phase I", "colorOfMoney": "RDT&E", "vehicle": "STTR", "contractType": "FFP",
     "compliance": ["CUI", "ATO Required"], "cta": ["Space Technology", "Integrated Network Systems-of-Systems"], "techType": "H/W + S/W",
     "missionCategory": "Space Domain Awareness (SDA/SBM)", "missionSecondary": "Sensors", "setAside": "Total Small Business",
     "teaming": "Sub", "notes": "Teaming with an RF sensor prime recommended."},
    {"fitScore": 67, "fitGrade": "Good", "fitRationale": "Relevant autonomy stack but ground robotics is adjacent to core.",
     "agency": "Department of the Army", "office": "DEVCOM GVSC", "dueDate": d(26), "awardAmount": 3400000,
     "solNumber": "W56HZV-26-R-0042", "solUrl": "https://sam.gov/", "title": "Autonomous Ground Resupply Software",
     "topicUrl": "https://sam.gov/", "summary": "Autonomy software for leader-follower convoy and GPS-denied navigation for tactical resupply vehicles.",
     "phase": "Full RFP", "colorOfMoney": "Procurement", "vehicle": "OTA", "contractType": "CPFF",
     "compliance": ["CMMC L2", "FCL"], "cta": ["Trusted AI & Autonomy"], "techType": "S/W",
     "missionCategory": "Autonomous Systems (non-UAS)", "missionSecondary": "Navigation in Denied Environments (Alt-PNT)", "setAside": "None",
     "teaming": "JV/Mentor-Protege", "notes": "Incumbent is a large prime; pursue as sub or JV."},
    {"fitScore": 88, "fitGrade": "Very Good", "fitRationale": "Cislunar logistics is a named focus area; aligns with ISAM capability.",
     "agency": "DARPA", "office": "TTO", "dueDate": d(40), "awardAmount": 12000000,
     "solNumber": "HR001126S0009", "solUrl": "https://sam.gov/", "title": "BAA: In-Space Servicing & Cislunar Logistics",
     "topicUrl": "https://www.darpa.mil/", "summary": "Broad agency announcement seeking ISAM concepts for cislunar mobility, refueling and assembly.",
     "phase": "BAA (rolling)", "colorOfMoney": "RDT&E", "vehicle": "BAA", "contractType": "CPFF",
     "compliance": ["ITAR/EAR", "SECRET/TS-SCI"], "cta": ["Space Technology", "Advanced Materials"], "techType": "H/W + S/W",
     "missionCategory": "Space Logistics / ISAM", "missionSecondary": "Orbital & Lunar Infrastructure / Cislunar", "setAside": "None",
     "teaming": "Prime", "notes": "White paper stage open now; high ceiling."},
    {"fitScore": 52, "fitGrade": "Fair", "fitRationale": "Directed energy is outside core but adjacent thermal expertise applies.",
     "agency": "Missile Defense Agency", "office": "MDA/DV", "dueDate": d(70), "awardAmount": 5000000,
     "solNumber": "HQ0860-26-R-0003", "solUrl": "https://sam.gov/", "title": "Layered Defense Thermal Management",
     "topicUrl": "https://sam.gov/", "summary": "Advanced thermal management for directed-energy and interceptor subsystems supporting layered missile defense.",
     "phase": "Full RFP", "colorOfMoney": "RDT&E", "vehicle": "IDIQ", "contractType": "T&M",
     "compliance": ["CMMC L3", "SECRET/TS-SCI", "FOCI"], "cta": ["Directed Energy", "Hypersonics"], "techType": "H/W",
     "missionCategory": "Missile Defense / Golden Dome", "missionSecondary": "Space Energy / Power Beaming", "setAside": "None",
     "teaming": "Sub", "notes": "FOCI mitigation required — confirm ownership structure."},
    {"fitScore": 19, "fitGrade": "No Fit", "fitRationale": "Biotechnology scope unrelated to current capabilities.",
     "agency": "Defense Health Agency", "office": "DHA", "dueDate": d(33), "awardAmount": 800000,
     "solNumber": "DHA-26-SBIR-018", "solUrl": "https://sam.gov/", "title": "Wearable Biosensors for Warfighter Readiness",
     "topicUrl": "https://sam.gov/", "summary": "Wearable biosensing for physiological status monitoring of deployed personnel.",
     "phase": "SBIR Phase I", "colorOfMoney": "RDT&E", "vehicle": "SBIR Phase I", "contractType": "FFP",
     "compliance": ["No Special Compliance"], "cta": ["Biotechnology", "Human-Machine Interfaces"], "techType": "H/W + S/W",
     "missionCategory": "BCI / Human-Machine Teaming", "missionSecondary": "Sensors", "setAside": "Total Small Business",
     "teaming": "Solo", "notes": "Listed for completeness; recommend no-bid."},
]

report = {
    "reportDate": today.date().isoformat(),
    "fiscalYear": "FY26 (≈4 months remaining)",
    "sourceStatus": [
        {"source": "SAM.gov", "status": "reached", "note": ""},
        {"source": "SBIR/DSIP", "status": "reached", "note": ""},
        {"source": "SpaceWERX/AFWERX", "status": "reached", "note": ""},
        {"source": "Grants.gov", "status": "reached", "note": ""},
        {"source": "Bloomberg Gov", "status": "inaccessible", "note": "paywalled"},
    ],
    "executiveSummary": {
        "totalOpportunities": len(opps),
        "narrative": "Six SB-eligible opportunities surfaced this cycle, weighted toward space autonomy and SDA. Two are excellent fits with near-term deadlines; prioritize the AFRL edge-AI SBIR and the DARPA cislunar BAA white paper.",
        "hotSignals": [
            {"signal": "SpaceWERX announced a new SDA STRATFI cohort", "source": "spacewerx.us"},
            {"signal": "DARPA TTO increasing cislunar logistics emphasis in FY26", "source": "darpa.mil"},
            {"signal": "Army GVSC moving autonomous resupply to OTA vehicle", "source": "sam.gov"},
        ],
        "recommendedActions": [
            "Submit AFRL edge-AI SBIR Phase II proposal (due in 5 days).",
            "Draft DARPA cislunar BAA white paper; high ceiling, rolling intake.",
            "Initiate teaming talks with an RF sensor prime for the SpaceWERX SDA topic.",
            "Confirm FOCI posture before pursuing the MDA thermal IDIQ.",
        ],
    },
    "opportunities": opps,
    "_model": "claude-sonnet-4-5 (SAMPLE)",
    "_usage": {"inputTokens": 41250, "outputTokens": 5980, "webSearches": 8},
}

doc = {
    "organizationId": ORG,
    "createdBy": ObjectId(),
    "createdAt": today,
    "tier": "standard",
    "model": "claude-sonnet-4-5 (SAMPLE)",
    "usage": report["_usage"],
    "report": report,
    "isSample": True,
}
res = db.intelReports.insert_one(doc)
print("inserted sample report id:", res.inserted_id)
