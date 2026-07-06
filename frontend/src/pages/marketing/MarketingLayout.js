import React, { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { LogoMark } from "../../components/Logo";

const NAV = [
  { to: "/home", label: "Home" },
  { to: "/why", label: "Why CaptureAgent" },
  { to: "/features", label: "Features" },
  { to: "/resources", label: "Resources" },
  { to: "/about", label: "About" },
];

export function Wordmark({ size = 34 }) {
  return (
    <span className="inline-flex items-center gap-2.5 text-ink">
      <LogoMark size={size} ink="#e8eefc" />
      <span className="text-lg font-bold tracking-tight">CaptureAgent</span>
    </span>
  );
}

export default function MarketingLayout({ children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-line bg-deep/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <Link to="/home" data-testid="mk-brand"><Wordmark /></Link>
          <nav className="hidden items-center gap-6 md:flex">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to}
                className={({ isActive }) =>
                  `text-sm transition-colors ${isActive ? "text-cyan" : "text-dim hover:text-ink"}`}>
                {n.label}
              </NavLink>
            ))}
            <Link to="/login" className="text-sm text-ink hover:text-cyan" data-testid="mk-signin">Sign in</Link>
            <Link to="/register" className="btn btn-primary !py-2" data-testid="mk-start">Start free</Link>
          </nav>
          <button className="text-ink md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
        {open && (
          <nav className="flex flex-col gap-1 border-t border-line px-5 py-3 md:hidden">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} onClick={() => setOpen(false)}
                className="rounded-lg px-2 py-2 text-sm text-dim hover:bg-white/5 hover:text-ink">
                {n.label}
              </NavLink>
            ))}
            <div className="mt-2 flex gap-2">
              <Link to="/login" className="btn btn-ghost flex-1">Sign in</Link>
              <Link to="/register" className="btn btn-primary flex-1">Start free</Link>
            </div>
          </nav>
        )}
      </header>

      <main>{children}</main>

      <footer className="mt-20 border-t border-line">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 py-10 md:grid-cols-3">
          <div>
            <Wordmark size={28} />
            <p className="mt-3 max-w-xs text-xs leading-relaxed text-faint">
              Streamlining government capture. Find, qualify, and win federal
              work with an AI capture manager on your team.
            </p>
          </div>
          <div className="text-sm">
            <div className="label-mono mb-2">Product</div>
            <div className="flex flex-col gap-1.5">
              {NAV.slice(1).map((n) => (
                <Link key={n.to} to={n.to} className="text-dim hover:text-cyan">{n.label}</Link>
              ))}
              <Link to="/register" className="text-dim hover:text-cyan">Create an account</Link>
            </div>
          </div>
          <div className="text-sm">
            <div className="label-mono mb-2">Trust</div>
            <p className="text-xs leading-relaxed text-faint">
              Bring your own API keys — encrypted per organization, never
              visible to anyone else, with every access audited. CaptureAgent
              workspaces are for unclassified pipeline data; do not store CUI
              or ITAR-controlled technical data.
            </p>
          </div>
        </div>
        <div className="border-t border-line py-4 text-center text-xs text-faint">
          © {new Date().getFullYear()} CaptureAgent · captureagent.us
        </div>
      </footer>
    </div>
  );
}
