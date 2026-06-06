import React, { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Target, Building2, Users, Settings as SettingsIcon,
  Shield, LogOut, ChevronDown, Radar, AlertTriangle, X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { canAdmin } from "../lib/helpers";
import { api } from "../lib/api";
import { toast } from "sonner";

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const utc = now.toISOString().substr(11, 8);
  return (
    <div className="hidden items-center gap-2 md:flex" data-testid="utc-clock">
      <span className="label-mono">UTC</span>
      <span className="mono text-sm text-cyan">{utc}</span>
    </div>
  );
}

function OrgSwitcher() {
  const { user, activeOrg, switchOrg } = useAuth();
  const [open, setOpen] = useState(false);
  const orgs = user?.organizations || [];
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="btn btn-ghost !px-3 !py-2"
        data-testid="org-switcher"
      >
        <Radar size={16} className="text-cyan" />
        <span className="max-w-[160px] truncate text-sm font-medium">
          {activeOrg?.name || "Select org"}
        </span>
        <ChevronDown size={14} className="text-faint" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            className="glass absolute left-0 z-20 mt-2 w-64 overflow-hidden p-1"
            style={{ background: "var(--bg-elev)" }}
            data-testid="org-switcher-menu"
          >
            {orgs.map((o) => (
              <button
                key={o.id}
                onClick={() => { switchOrg(o.id); setOpen(false); }}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-white/5 ${
                  activeOrg?.id === o.id ? "text-cyan" : "text-ink"
                }`}
                data-testid={`org-option-${o.id}`}
              >
                <span className="truncate">{o.name}</span>
                <span className="label-mono">{o.role}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/opportunities", label: "Opportunities", icon: Target, testid: "nav-opportunities" },
  { to: "/profile", label: "Company Profile", icon: Building2, testid: "nav-profile" },
  { to: "/admin", label: "Admin", icon: Users, testid: "nav-admin", admin: true },
  { to: "/settings", label: "Settings", icon: SettingsIcon, testid: "nav-settings", admin: true },
];

function VerifyBanner() {
  const { user, refreshUser } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  if (!user || user.emailVerified || dismissed) return null;
  const resend = async () => {
    try {
      const { data } = await api.post("/auth/resend-verification");
      toast.success("Verification link generated", {
        description: "Email is mocked — open the link to verify.",
        action: { label: "Verify now", onClick: () => (window.location.href = data.verifyUrl) },
      });
    } catch {
      toast.error("Could not generate link");
    }
  };
  return (
    <div
      className="flex items-center justify-between gap-3 border-b border-warn/30 bg-warn/10 px-4 py-2 text-sm text-warn"
      data-testid="verify-email-banner"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle size={15} />
        <span>Your email is not verified yet.</span>
        <button onClick={resend} className="underline hover:text-ink" data-testid="resend-verify-btn">
          Resend verification link
        </button>
      </div>
      <button onClick={() => setDismissed(true)} className="text-warn/70 hover:text-warn">
        <X size={15} />
      </button>
    </div>
  );
}

export default function Shell({ children }) {
  const { user, logout, activeOrg } = useAuth();
  const navigate = useNavigate();
  const role = activeOrg?.role;

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-panel/40 px-3 py-5 lg:flex">
        <div className="mb-8 flex items-center gap-2 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan/40 bg-cyan/10">
            <Shield size={18} className="text-cyan" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-ink">GovCon</div>
            <div className="label-mono">Command Center</div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.filter((n) => !n.admin || canAdmin(role)).map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "border border-cyan/30 bg-cyan/10 text-cyan"
                    : "border border-transparent text-dim hover:bg-white/5 hover:text-ink"
                }`
              }
            >
              <n.icon size={17} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 border-t border-line pt-4">
          <div className="px-2 text-sm font-medium text-ink">{user?.name}</div>
          <div className="px-2 text-xs text-faint">{user?.email}</div>
          <button
            onClick={doLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-dim hover:bg-white/5 hover:text-bad"
            data-testid="logout-btn"
          >
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-deep/70 px-4 py-3 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <OrgSwitcher />
            {role && (
              <span className="pill border-line bg-white/5 text-dim" data-testid="active-role-pill">
                {role.toUpperCase()}
              </span>
            )}
          </div>
          <Clock />
        </header>
        <VerifyBanner />
        <main className="flex-1 px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
