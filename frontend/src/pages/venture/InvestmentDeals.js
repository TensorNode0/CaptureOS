import React from "react";
import VentureWorkspace from "./VentureWorkspace";

const KINDS = [
  { kind: "investor_email", label: "Investor outreach email", targetLabel: "Investor / fund",
    targetPlaceholder: "Shield Capital" },
  { kind: "pitch_deck", label: "Pitch deck", targetLabel: "Audience",
    targetPlaceholder: "Seed round — defense VCs" },
  { kind: "business_plan", label: "Business plan", targetLabel: "Purpose",
    targetPlaceholder: "Seed raise / bank / internal" },
  { kind: "financials", label: "Financial model (P&L, cash flow, margins)", targetLabel: "Scenario",
    targetPlaceholder: "3-year base case" },
];

export default function InvestmentDeals() {
  return (
    <VentureWorkspace
      title="Investment Deals"
      sectionLabel="Fundraising"
      blurb="Draft investor outreach, pitch decks, business plans, and financial models
             from your company profile — the AI never invents numbers, it marks [FILL]
             where founder input is needed. Review, edit, finalize, and download as
             Word, PowerPoint, or Excel."
      kinds={KINDS}
      testid="deals"
    />
  );
}
