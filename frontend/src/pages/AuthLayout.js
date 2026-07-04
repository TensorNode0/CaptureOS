import React from "react";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="glass w-full max-w-md p-8"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan/40 bg-cyan/10">
            <Shield size={22} className="text-cyan" />
          </div>
          <div>
            <div className="text-base font-semibold text-ink">CaptureAgent</div>
            <div className="label-mono">Federal Capture Console</div>
          </div>
        </div>
        <h1 className="text-xl font-semibold text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-dim">{subtitle}</p>}
        <div className="mt-6">{children}</div>
        {footer && <div className="mt-6 text-center text-sm text-dim">{footer}</div>}
      </motion.div>
    </div>
  );
}
