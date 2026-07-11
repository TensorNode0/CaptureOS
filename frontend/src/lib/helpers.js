export function fmtMoney(n) {
  if (n == null || isNaN(n)) return "$0";
  const v = Number(n);
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toLocaleString()}`;
}

export function fmtDate(d) {
  if (!d) return "—";
  try {
    const dt = new Date(d);
    if (isNaN(dt)) return d;
    return dt.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
  } catch {
    return d;
  }
}

export function fmtDateTime(d) {
  if (!d) return "—";
  try {
    const dt = new Date(d);
    if (isNaN(dt)) return d;
    return dt.toLocaleString("en-US", {
      month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return d;
  }
}

export function daysUntil(d) {
  if (!d) return null;
  const dt = new Date(d);
  if (isNaN(dt)) return null;
  const diff = Math.ceil((dt - new Date()) / (1000 * 60 * 60 * 24));
  return diff;
}

// Due-date color: red <=7d, amber <=30d, green >30d, grey undated/closed
export function dueColor(d) {
  const n = daysUntil(d);
  if (n == null) return { key: "grey", cls: "text-faint border-line", label: "Undated" };
  if (n < 0) return { key: "grey", cls: "text-faint border-line", label: "Closed" };
  if (n <= 7) return { key: "red", cls: "text-bad", label: `${n}d` };
  if (n <= 30) return { key: "amber", cls: "text-warn", label: `${n}d` };
  return { key: "green", cls: "text-ok", label: `${n}d` };
}

export const ELIGIBILITY = {
  eligible: { label: "Eligible", cls: "text-ok border-ok/40 bg-ok/10" },
  not_certified: { label: "Not Certified", cls: "text-bad border-bad/40 bg-bad/10" },
  verify: { label: "Verify", cls: "text-warn border-warn/40 bg-warn/10" },
  open: { label: "Full & Open", cls: "text-dim border-line bg-white/5" },
};

// 4-state hard-gate eligibility (scoring engine)
export const ELIG_STATUS = {
  Eligible: { cls: "text-ok border-ok/40 bg-ok/10" },
  Conditional: { cls: "text-warn border-warn/40 bg-warn/10" },
  Ineligible: { cls: "text-bad border-bad/40 bg-bad/10" },
  Unknown: { cls: "text-dim border-line bg-white/5" },
};

export const FIT_BAND_CLS = {
  Strong: "text-ok", Good: "text-cyan", Conditional: "text-warn", Poor: "text-bad",
};

export const PRIORITY_CFG = {
  A: { cls: "text-ok border-ok/50 bg-ok/15" },
  B: { cls: "text-cyan border-cyan/50 bg-cyan/10" },
  C: { cls: "text-warn border-warn/40 bg-warn/10" },
  Watch: { cls: "text-violet border-violet/40 bg-violet/10" },
  Pass: { cls: "text-faint border-line bg-white/5" },
};

export const PWIN_CLS = { High: "text-ok", Medium: "text-warn", Low: "text-bad", Unknown: "text-faint" };

export function businessDaysUntil(d) {
  if (!d) return null;
  const end = new Date(d);
  if (isNaN(end)) return null;
  let cur = new Date();
  cur = new Date(cur.getFullYear(), cur.getMonth(), cur.getDate());
  if (end < cur) return 0;
  let count = 0;
  while (cur < end) {
    cur.setDate(cur.getDate() + 1);
    const day = cur.getDay();
    if (day !== 0 && day !== 6) count++;
  }
  return count;
}

export function exportCsv(filename, header, rows) {
  const esc = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [header.map(esc).join(","), ...rows.map((r) => r.map(esc).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export const STAGE_COLORS = {
  Identified: "#5d6b8a",
  Qualifying: "#38e1ff",
  Building: "#8b7bff",
  Submitted: "#fbbf24",
  Won: "#34d399",
  Lost: "#fb6f70",
  "No-Bid": "#93a1c0",
};

export const CHART_SERIES = ["#38e1ff", "#8b7bff", "#34d399", "#fbbf24", "#ff5cae", "#5d6b8a"];

export const ROLE_RANK = {
  viewer: 1,
  editor: 2, technical_writer: 2, proposal_writer: 2, pi: 2,
  capture_manager: 3,
  admin: 4, owner: 5,
};
export function canEdit(role) { return (ROLE_RANK[role] || 0) >= ROLE_RANK.editor; }
export function canAdmin(role) { return (ROLE_RANK[role] || 0) >= ROLE_RANK.admin; }
export function isOwner(role) { return role === "owner"; }
// Product rules: admins can do anything; capture managers create/approve
// proposal work but only admins submit; dashboards are admin + capture manager.
export function isCaptureManager(role) { return role === "capture_manager"; }
export function canCreateProposal(role) {
  return role === "capture_manager" || role === "admin" || role === "owner";
}
export function canSubmitProposal(role) { return role === "admin" || role === "owner"; }
export function canSeeDashboard(role) {
  return role === "admin" || role === "owner" || role === "capture_manager";
}
