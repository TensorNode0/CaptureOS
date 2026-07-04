// Helpers for the AI Opportunity Intelligence report: badges, aggregation, export.
import { fmtMoney, daysUntil } from "./helpers";

export const SCAN_TIERS = [
  { id: "lean", label: "Lean", hint: "Haiku · ~5 searches · ~12 opps · cheapest" },
  { id: "standard", label: "Standard", hint: "Sonnet · ~8 searches · ~22 opps" },
  { id: "deep", label: "Deep", hint: "Sonnet · ~15 searches · ~30 opps · thorough" },
];

export function fitBadge(score, grade) {
  const s = Number(score) || 0;
  let tone = "neutral";
  if (s >= 90) tone = "ok";
  else if (s >= 75) tone = "cyan";
  else if (s >= 60) tone = "violet";
  else if (s >= 45) tone = "warn";
  else if (s >= 25) tone = "bad";
  const label = grade || (s >= 90 ? "Excellent" : s >= 75 ? "Very Good" : s >= 60 ? "Good"
    : s >= 45 ? "Fair" : s >= 25 ? "Poor" : "No Fit");
  return { tone, label, score: s };
}

export const MONEY_COLORS = {
  "RDT&E": "#34d399", "O&M": "#38bdf8", "Procurement": "#fbbf24",
  "MILCON": "#fb923c", "Multiple/TBD": "#93a1c0",
};
export function moneyColor(c) { return MONEY_COLORS[c] || "#93a1c0"; }

export function complianceTone(flag) {
  const f = (flag || "").toLowerCase();
  if (f.includes("cmmc") || f.includes("secret") || f.includes("ts")) return "bad";
  if (f.includes("itar") || f.includes("ear") || f.includes("fcl") ||
      f.includes("foci") || f.includes("ato") || f.includes("cui")) return "warn";
  if (f.includes("none") || f.includes("commercial")) return "ok";
  return "neutral";
}

export const TEAMING_TONE = {
  Prime: "cyan", Sub: "violet", "JV/Mentor-Protege": "warn", Solo: "neutral",
};

export function countBy(opps, key) {
  const map = {};
  (opps || []).forEach((o) => {
    const v = (o[key] || "TBD").toString().trim() || "TBD";
    map[v] = (map[v] || 0) + 1;
  });
  return Object.entries(map).map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

export function upcoming(opps, days = 14) {
  return (opps || [])
    .map((o) => ({ ...o, _d: daysUntil(o.dueDate) }))
    .filter((o) => o._d != null && o._d >= 0 && o._d <= days)
    .sort((a, b) => a._d - b._d);
}

export function topValue(opps, n = 5) {
  return (opps || [])
    .map((o) => ({ ...o, _a: Number(o.awardAmount) || 0 }))
    .filter((o) => o._a > 0)
    .sort((a, b) => b._a - a._a)
    .slice(0, n);
}

const COLS = [
  ["fitScore", "Fit Score"], ["fitGrade", "Fit Grade"], ["agency", "Agency"],
  ["office", "PEO/Office"], ["dueDate", "Due Date"], ["awardAmount", "Award Amount"],
  ["solNumber", "Solicitation #"], ["solUrl", "Solicitation URL"], ["title", "Topic Title"],
  ["topicUrl", "Topic URL"], ["summary", "Summary"], ["phase", "Phase/Stage"],
  ["colorOfMoney", "Color of Money"], ["vehicle", "Contract Vehicle"],
  ["contractType", "Contract Type"], ["compliance", "Compliance"], ["cta", "CTA"],
  ["techType", "Tech Type"], ["missionCategory", "Mission Category"],
  ["missionSecondary", "Mission (Secondary)"], ["setAside", "Set-Aside"],
  ["teaming", "Teaming"], ["fitRationale", "Fit Rationale"], ["notes", "Notes"],
];

function csvCell(v) {
  if (Array.isArray(v)) v = v.join("; ");
  if (v == null) v = "";
  const s = String(v).replace(/"/g, '""');
  return `"${s}"`;
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

export function exportCSV(report) {
  const opps = report?.opportunities || [];
  const header = COLS.map(([, label]) => csvCell(label)).join(",");
  const rows = opps.map((o) => COLS.map(([k]) => csvCell(o[k])).join(","));
  download(`intel-report-${report?.reportDate || "scan"}.csv`,
    [header, ...rows].join("\n"), "text/csv;charset=utf-8;");
}

export function exportHTML(report) {
  const opps = report?.opportunities || [];
  const es = report?.executiveSummary || {};
  const th = COLS.map(([, l]) => `<th>${l}</th>`).join("");
  const rows = opps.map((o, i) => {
    const d = daysUntil(o.dueDate);
    const cls = d == null || d < 0 ? "" : d <= 7 ? "u7" : d <= 30 ? "u30" : "u30p";
    const tds = COLS.map(([k]) => {
      let v = o[k];
      if (Array.isArray(v)) v = v.join(", ");
      if ((k === "solUrl" || k === "topicUrl") && v && v !== "TBD")
        v = `<a href="${v}" target="_blank" rel="noopener">link</a>`;
      if (k === "awardAmount") v = v ? fmtMoney(v) : "TBD";
      return `<td>${v == null || v === "" ? "TBD" : v}</td>`;
    }).join("");
    return `<tr class="${cls}"><td>${i + 1}</td>${tds}</tr>`;
  }).join("");
  const html = `<!doctype html><html><head><meta charset="utf-8">
<title>CaptureAgent Intelligence Report — ${report?.reportDate || ""}</title>
<style>
:root{--bg:#0a0e1a;--card:#1a2035;--line:#1e293b;--txt:#f1f5f9;--dim:#94a3b8;--cyan:#06b6d4}
body{background:var(--bg);color:var(--txt);font-family:'Segoe UI',system-ui,sans-serif;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--dim);font-size:13px;margin-bottom:20px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:18px}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;min-width:150px}
.kpi b{display:block;font-size:24px}.kpi span{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.08em}
ul{margin:6px 0 0;padding-left:18px;color:var(--dim);font-size:13px}
.tbl{overflow:auto;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:12px}
th{position:sticky;top:0;background:#111827;color:var(--cyan);text-align:left;padding:8px 10px;white-space:nowrap;text-transform:uppercase;font-size:10px;letter-spacing:.06em}
td{padding:8px 10px;border-top:1px solid var(--line);vertical-align:top;max-width:280px}
a{color:var(--cyan)}tr.u7 td:first-child{border-left:3px solid #ef4444}
tr.u30 td:first-child{border-left:3px solid #f59e0b}tr.u30p td:first-child{border-left:3px solid #10b981}
</style></head><body>
<h1>CaptureAgent Opportunity Intelligence Report</h1>
<div class="sub">${report?.reportDate || ""} · ${report?.fiscalYear || ""} · ${opps.length} opportunities · UNCLASSIFIED // FOUO</div>
<div class="kpis">
  <div class="kpi"><span>Total</span><b>${opps.length}</b></div>
  <div class="kpi"><span>Due ≤ 14 days</span><b>${upcoming(opps, 14).length}</b></div>
  <div class="kpi"><span>Excellent fit</span><b>${opps.filter((o) => (Number(o.fitScore) || 0) >= 90).length}</b></div>
</div>
${es.narrative ? `<div class="panel"><b>Executive Read</b><div style="color:var(--dim);font-size:13px;margin-top:6px">${es.narrative}</div></div>` : ""}
${(es.recommendedActions || []).length ? `<div class="panel"><b>Recommended Actions</b><ul>${(es.recommendedActions || []).map((a) => `<li>${a}</li>`).join("")}</ul></div>` : ""}
${(es.hotSignals || []).length ? `<div class="panel"><b>Hot Signals / BD Intel</b><ul>${(es.hotSignals || []).map((s) => `<li>${s.signal || s} ${s.source ? `— <i>${s.source}</i>` : ""}</li>`).join("")}</ul></div>` : ""}
<div class="tbl"><table><thead><tr><th>#</th>${th}</tr></thead><tbody>${rows}</tbody></table></div>
</body></html>`;
  download(`intel-report-${report?.reportDate || "scan"}.html`, html, "text/html;charset=utf-8;");
}
