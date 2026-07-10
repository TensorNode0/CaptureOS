import React from "react";
import VentureWorkspace from "./VentureWorkspace";

const KINDS = [
  { kind: "accelerator_application", label: "Accelerator application", targetLabel: "Program",
    targetPlaceholder: "Catalyst Accelerator — Spring cohort" },
];

export default function AcceleratorApplications() {
  return (
    <VentureWorkspace
      title="Accelerator Applications"
      sectionLabel="Programs"
      blurb="Draft answers for accelerator and government-program applications —
             structured per question with tips on what strong applications do,
             grounded in your company profile. Name the program (from the
             Accelerators tab) and add notes; edit and download when ready."
      kinds={KINDS}
      testid="accel"
    />
  );
}
