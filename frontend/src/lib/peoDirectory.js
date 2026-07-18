/* Curated government-customer directory for proposal targeting.
   Defense/IC entries follow the Program Executive Office structure documented
   in the Stanford Gordian Knot Center's 2026 PEO Directory and the services'
   public acquisition pages. PEO rosters shift with reorganizations — use the
   AI currency check on the proposal customer card, and verify names on the
   source sites before contacting a TPOC. */

export const PEO_SOURCES = [
  { label: "Stanford Gordian Knot Center — 2026 Program Executive Offices Directory",
    href: "https://gordianknot.fsi.stanford.edu/publication/2026-program-executive-offices-directory" },
  { label: "LookLeft — DoW/DoD PEO tracker (rolling updates + subscribe)",
    href: "https://sites.google.com/lookleft.com/index/home" },
  { label: "Silicon Valley Defense Group — DoW Directory",
    href: "https://www.siliconvalleydefense.org/dow-directory" },
  { label: "Steve Blank — How to sell to the Dept of Defense: the 2025 PEO directory",
    href: "https://steveblank.com/2025/09/10/how-to-sell-to-the-dept-of-defense-the-2025-peo-directory/" },
];

// LookLeft is a rolling-update PEO tracker. This is the date we last confirmed
// the tracker was reachable + current — bump when a maintainer reviews the
// site. The AI currency check queries LookLeft live so the user always gets
// the true freshest state; this constant is the fallback signal + display.
export const LOOKLEFT_SOURCE = {
  label: "LookLeft DoW/DoD PEO tracker",
  href: "https://sites.google.com/lookleft.com/index/home",
  lastVerified: "2026-07-18",
};

export const GOV_SECTORS = ["Civil", "Defense", "Intelligence Community"];

/* Civil agencies (no PEO structure — pick the agency, name the program office
   in the TPOC/notes fields). */
export const CIVIL_AGENCIES = [
  "NASA", "Department of Homeland Security (S&T, CBP, TSA, USCG)",
  "Department of Energy (incl. NNSA, ARPA-E)", "Department of Transportation (incl. FAA)",
  "Department of Health & Human Services (incl. NIH, BARDA)", "Department of Commerce (incl. NOAA, NIST)",
  "General Services Administration", "Department of Agriculture",
  "Department of the Interior", "Department of Veterans Affairs",
  "Environmental Protection Agency", "National Science Foundation",
];

/* Defense: branch → program executive offices / buying commands. */
export const DEFENSE_BRANCHES = {
  "Army": [
    "PEO Aviation",
    "PEO Ground Combat Systems",
    "PEO Combat Support & Combat Service Support (CS&CSS)",
    "PEO Command, Control, Communications & Network (C3N)",
    "PEO Intelligence, Electronic Warfare & Sensors (IEW&S)",
    "PEO Missiles & Space",
    "PEO Simulation, Training & Instrumentation (STRI)",
    "PEO Soldier",
    "PEO Enterprise",
    "Joint PEO Armaments & Ammunition (JPEO A&A)",
    "Joint PEO for CBRN Defense (JPEO-CBRND)",
    "Rapid Capabilities & Critical Technologies Office (RCCTO)",
    "Army Applications Laboratory / xTech (entry points)",
  ],
  "Navy & Marine Corps": [
    "PEO Ships",
    "PEO Submarines",
    "PEO Aircraft Carriers",
    "PEO Integrated Warfare Systems (IWS)",
    "PEO Unmanned & Small Combatants (USC)",
    "PEO Attack Submarines (SSN)",
    "PEO Strategic Submarines (SSBN)",
    "PEO Tactical Aircraft Programs (PEO(T))",
    "PEO Air Anti-Submarine Warfare, Assault & Special Mission Programs (PEO(A))",
    "PEO Unmanned Aviation & Strike Weapons (PEO(U&W))",
    "PEO Command, Control, Communications, Computers & Intelligence / Space Systems (C4I)",
    "PEO Digital & Enterprise Services",
    "PEO Manpower, Logistics & Training (MLB)",
    "Marine Corps PEO Land Systems",
    "Marine Corps Systems Command (MCSC)",
    "NavalX / Tech Bridges (entry points)",
  ],
  "Air Force": [
    "PEO Fighters & Advanced Aircraft",
    "PEO Mobility & Training Aircraft",
    "PEO Bombers",
    "PEO Digital",
    "PEO Command, Control, Communications & Battle Management (C3BM)",
    "PEO Weapons",
    "PEO Intelligence, Surveillance, Reconnaissance & Special Operations Forces",
    "PEO Agile Combat Support",
    "PEO Advanced Aircraft (Collaborative Combat Aircraft)",
    "Air Force Nuclear Weapons Center (AFNWC)",
    "AFWERX (entry point)",
  ],
  "Space Force": [
    "SSC PEO Assured Access to Space",
    "SSC PEO Military Communications & Positioning, Navigation and Timing",
    "SSC PEO Space Sensing",
    "SSC PEO Space Domain Awareness & Combat Power",
    "SSC PEO Battle Management, Command, Control & Communications",
    "Space Development Agency (SDA)",
    "SpaceWERX (entry point)",
  ],
  "SOCOM & Defense Agencies": [
    "SOCOM PEO Fixed Wing",
    "SOCOM PEO Rotary Wing",
    "SOCOM PEO Maritime",
    "SOCOM PEO SOF Warrior",
    "SOCOM PEO SOF Digital Applications",
    "Missile Defense Agency (MDA)",
    "Defense Innovation Unit (DIU)",
    "Defense Information Systems Agency (DISA)",
    "Chief Digital & AI Office (CDAO)",
    "Defense Threat Reduction Agency (DTRA)",
    "DARPA (program offices)",
  ],
};

/* Intelligence Community: agency-level (acquisition offices are not public
   PEO structures — route via the listed front doors). */
export const IC_AGENCIES = [
  "Central Intelligence Agency (via In-Q-Tel / CIA Labs)",
  "National Security Agency (via NSA Technology Transfer / OSAs)",
  "National Geospatial-Intelligence Agency (via NGA Ventures)",
  "National Reconnaissance Office (via NRO Director's Innovation Initiative)",
  "Defense Intelligence Agency (via Open Innovation / NeedipeDIA)",
  "Office of the Director of National Intelligence (via IARPA)",
  "Department of Homeland Security Intelligence & Analysis",
];

/* Common commercial markets for the dual-use dropdown (free text allowed). */
export const COMMERCIAL_MARKETS = [
  "Commercial aviation & airlines", "Commercial space & satellite operators",
  "Maritime & shipping", "Energy & utilities", "Critical infrastructure security",
  "Logistics & supply chain", "Manufacturing & industrial automation",
  "Financial services", "Healthcare & life sciences", "Telecommunications",
  "Mining & heavy industry", "Agriculture", "Construction & real estate",
  "Insurance & risk analytics", "State & local government", "Enterprise IT & cybersecurity",
];
