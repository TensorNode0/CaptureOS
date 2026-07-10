import React, { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Target, Building2, Users, Settings as SettingsIcon,
  Shield, LogOut, ChevronDown, Radar, AlertTriangle, X, Menu, FileText,
  Plus, KeyRound, Landmark, Handshake, Rocket, ClipboardList, Crosshair, FolderLock,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { canAdmin, canSeeDashboard } from "../lib/helpers";
import { LogoMark } from "./Logo";
import { api, errMsg } from "../lib/api";
import { toast } from "sonner";
import { Modal, Field, Spinner } from "./ui";

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
  const { user, activeOrg, switchOrg, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState(null); // "create" | "join" | null
  const [name, setName] = useState("");
  const [naics, setNaics] = useState("");
  const [keywords, setKeywords] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const orgs = user?.organizations || [];

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post("/orgs", {
        name,
        naics: naics.split(",").map((s) => s.trim()).filter(Boolean),
        keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
      });
      await refreshUser();
      switchOrg(data.id);
      toast.success(`Organization "${data.name}" created`);
      setModal(null); setName(""); setNaics(""); setKeywords("");
      navigate("/dashboard");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };

  const join = async () => {
    if (!code.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post("/orgs/join", { code: code.trim() });
      await refreshUser();
      switchOrg(data.id);
      toast.success(`Joined "${data.name}"`);
      setModal(null); setCode("");
      navigate("/dashboard");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="btn btn-ghost !px-3 !py-2" data-testid="org-switcher">
        <Radar size={16} className="text-cyan" />
        <span className="max-w-[160px] truncate text-sm font-medium">{activeOrg?.name || "Select org"}</span>
        <ChevronDown size={14} className="text-faint" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="glass absolute left-0 z-20 mt-2 w-64 overflow-hidden p-1" style={{ background: "var(--bg-elev)" }} data-testid="org-switcher-menu">
            <div className="max-h-64 overflow-y-auto">
              {orgs.map((o) => (
                <button key={o.id} onClick={() => { switchOrg(o.id); setOpen(false); }}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-white/5 ${activeOrg?.id === o.id ? "text-cyan" : "text-ink"}`}
                  data-testid={`org-option-${o.id}`}>
                  <span className="truncate">{o.name}</span>
                  <span className="label-mono">{o.role}</span>
                </button>
              ))}
            </div>
            <div className="mt-1 border-t border-line pt-1">
              <button onClick={() => { setOpen(false); setModal("create"); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-dim hover:bg-white/5 hover:text-ink" data-testid="org-create-btn">
                <Plus size={14} className="text-cyan" /> Create organization
              </button>
              <button onClick={() => { setOpen(false); setModal("join"); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-dim hover:bg-white/5 hover:text-ink" data-testid="org-join-btn">
                <KeyRound size={14} className="text-cyan" /> Join with code
              </button>
            </div>
          </div>
        </>
      )}

      <Modal open={modal === "create"} onClose={() => setModal(null)} title="Create organization">
        <div className="space-y-4" data-testid="create-org-modal">
          <Field label="Organization name"><input className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Orbital Defense Systems" data-testid="create-org-name" /></Field>
          <Field label="NAICS codes" hint="Comma-separated, e.g. 336412, 541715"><input className="field" value={naics} onChange={(e) => setNaics(e.target.value)} placeholder="336412, 541715" data-testid="create-org-naics" /></Field>
          <Field label="Focus keywords" hint="Drives AI scans & pulls. Comma-separated."><input className="field" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="UAS, hypersonic, space" data-testid="create-org-keywords" /></Field>
          <button className="btn btn-primary w-full" onClick={create} disabled={busy || !name.trim()} data-testid="create-org-confirm">{busy ? <Spinner /> : <Plus size={16} />} Create</button>
        </div>
      </Modal>

      <Modal open={modal === "join"} onClose={() => setModal(null)} title="Join an organization">
        <div className="space-y-4" data-testid="join-org-modal">
          <p className="text-sm text-faint">Ask an admin of that organization for its 8-character join code (Admin → Members).</p>
          <Field label="Join code"><input className="field mono uppercase" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="A1B2C3D4" maxLength={12} data-testid="join-org-code" /></Field>
          <button className="btn btn-primary w-full" onClick={join} disabled={busy || !code.trim()} data-testid="join-org-confirm">{busy ? <Spinner /> : <KeyRound size={16} />} Join</button>
        </div>
      </Modal>
    </div>
  );
}

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard", dashboard: true },
  { to: "/opportunities", label: "Federal Opportunities", icon: Target, testid: "nav-opportunities" },
  { to: "/proposals", label: "Proposals", icon: FileText, testid: "nav-proposals" },
  { to: "/competitive-analysis", label: "Competitive Analysis", icon: Crosshair, testid: "nav-competitive" },
  { to: "/private-capital", label: "Private Capital", icon: Landmark, testid: "nav-capital" },
  { to: "/investment-deals", label: "Investment Deals", icon: Handshake, testid: "nav-deals" },
  { to: "/accelerators", label: "Accelerators", icon: Rocket, testid: "nav-accelerators" },
  { to: "/accelerator-applications", label: "Accelerator Applications", icon: ClipboardList, testid: "nav-accel-apps" },
  { to: "/profile", label: "Company Profile", icon: Building2, testid: "nav-profile" },
  { to: "/admin", label: "Admin", icon: Users, testid: "nav-admin", admin: true },
  { to: "/settings", label: "Settings", icon: SettingsIcon, testid: "nav-settings", admin: true },
];

const SUB_NAV = [
  { to: "/shared", label: "Shared With Me", icon: FolderLock, testid: "nav-shared" },
];

function NavList({ role, onNavigate }) {
  const items = role === "subcontractor"
    ? SUB_NAV
    : NAV.filter((n) => (!n.admin || canAdmin(role)) && (!n.dashboard || canSeeDashboard(role)));
  return (
    <nav className="flex flex-1 flex-col gap-1">
      {items.map((n) => (
        <NavLink key={n.to} to={n.to} data-testid={n.testid} onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
              isActive ? "border border-cyan/30 bg-cyan/10 text-cyan"
                       : "border border-transparent text-dim hover:bg-white/5 hover:text-ink"}`}>
          <n.icon size={17} />
          {n.label}
        </NavLink>
      ))}
    </nav>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-2 text-ink">
      <LogoMark size={34} ink="#e8eefc" />
      <div className="leading-tight">
        <div className="text-sm font-bold tracking-tight text-ink">CaptureAgent</div>
        <div className="label-mono">captureagent.us</div>
      </div>
    </div>
  );
}

function VerifyBanner() {
  const { user } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  if (!user || user.emailVerified || dismissed) return null;
  const resend = async () => {
    try {
      const { data } = await api.post("/auth/resend-verification");
      if (data.verifyUrl) {
        toast.success("Verification link ready", {
          action: { label: "Verify now", onClick: () => (window.location.href = data.verifyUrl) },
        });
      } else {
        toast.success("Verification email sent", { description: "Check your inbox." });
      }
    } catch { toast.error("Could not send the email. Try again.") ; }
  };
  return (
    <div className="flex items-center justify-between gap-3 border-b border-warn/30 bg-warn/10 px-4 py-2 text-sm text-warn" data-testid="verify-email-banner">
      <div className="flex items-center gap-2">
        <AlertTriangle size={15} />
        <span>Your email is not verified yet.</span>
        <button onClick={resend} className="underline hover:text-ink" data-testid="resend-verify-btn">Resend verification link</button>
      </div>
      <button onClick={() => setDismissed(true)} className="text-warn/70 hover:text-warn"><X size={15} /></button>
    </div>
  );
}

function UserFooter({ user, onLogout }) {
  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="px-2 text-sm font-medium text-ink">{user?.name}</div>
      <div className="px-2 text-xs text-faint">{user?.email}</div>
      <button onClick={onLogout} className="mt-3 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-dim hover:bg-white/5 hover:text-bad" data-testid="logout-btn">
        <LogOut size={16} /> Sign out
      </button>
    </div>
  );
}

export default function Shell({ children }) {
  const { user, logout, activeOrg } = useAuth();
  const navigate = useNavigate();
  const role = activeOrg?.role;
  const [drawer, setDrawer] = useState(false);

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-panel/40 px-3 py-5 lg:flex">
        <div className="mb-8"><Brand /></div>
        <NavList role={role} />
        <UserFooter user={user} onLogout={doLogout} />
      </aside>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden" data-testid="mobile-drawer">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col border-r border-line bg-panel px-3 py-5" style={{ background: "var(--bg-elev)" }}>
            <div className="mb-6 flex items-center justify-between">
              <Brand />
              <button onClick={() => setDrawer(false)} className="text-faint hover:text-ink" data-testid="drawer-close"><X size={18} /></button>
            </div>
            <NavList role={role} onNavigate={() => setDrawer(false)} />
            <UserFooter user={user} onLogout={doLogout} />
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-deep/70 px-4 py-3 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <button onClick={() => setDrawer(true)} className="btn btn-ghost !px-2 !py-2 lg:hidden" data-testid="mobile-menu-btn" aria-label="Open menu">
              <Menu size={18} />
            </button>
            <OrgSwitcher />
            {role && <span className="pill border-line bg-white/5 text-dim" data-testid="active-role-pill">{role.toUpperCase()}</span>}
          </div>
          <Clock />
        </header>
        <VerifyBanner />
        <main className="flex-1 px-4 py-6 md:px-8">
          {children}
          <p className="mt-10 border-t border-line pt-4 text-center text-[10px] font-semibold leading-relaxed tracking-wide text-warn/80"
             data-testid="app-disclaimer">
            CAPTUREAGENT DOES NOT SUPPORT CUI, ITAR, OR CLASSIFIED DATA YET. PLEASE DO
            NOT CREATE OR STORE ANY CUI, ITAR, OR CLASSIFIED MATERIALS.
          </p>
        </main>
      </div>
    </div>
  );
}
