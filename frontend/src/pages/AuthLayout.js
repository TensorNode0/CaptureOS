import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { LogoMark } from "../components/Logo";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="liquid liquid-hover w-full max-w-md p-8"
      >
        <Link to="/home" className="mb-6 flex items-center gap-3 text-ink" data-testid="auth-brand-home">
          <LogoMark size={40} ink="#e8eefc" />
          <div>
            <div className="text-base font-bold tracking-tight text-ink">CaptureAgent</div>
            <div className="label-mono">Federal Capture Console</div>
          </div>
        </Link>
        <h1 className="text-xl font-semibold text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-dim">{subtitle}</p>}
        <div className="mt-6">{children}</div>
        {footer && <div className="mt-6 text-center text-sm text-dim">{footer}</div>}
      </motion.div>
    </div>
  );
}
