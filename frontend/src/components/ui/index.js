import React from "react";
import { motion } from "framer-motion";
import { Loader2, X } from "lucide-react";

export function Card({ className = "", children, hover = false, ...rest }) {
  return (
    <div className={`glass ${hover ? "glass-hover" : ""} ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function SectionLabel({ children, className = "" }) {
  return <div className={`label-mono ${className}`}>{children}</div>;
}

const PILL_TONES = {
  ok: "text-ok border-ok/40 bg-ok/10",
  warn: "text-warn border-warn/40 bg-warn/10",
  bad: "text-bad border-bad/40 bg-bad/10",
  cyan: "text-cyan border-cyan/40 bg-cyan/10",
  violet: "text-violet border-violet/40 bg-violet/10",
  neutral: "text-dim border-line bg-white/5",
};

export function Pill({ tone = "neutral", className = "", children, icon: Icon, ...rest }) {
  return (
    <span className={`pill ${PILL_TONES[tone] || PILL_TONES.neutral} ${className}`} {...rest}>
      {Icon && <Icon size={12} strokeWidth={2.2} />}
      {children}
    </span>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-lg bg-white/5 ${className}`} />;
}

export function Spinner({ size = 16, className = "" }) {
  return <Loader2 size={size} className={`animate-spin ${className}`} />;
}

export function EmptyState({ icon: Icon, title, subtitle, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && (
        <div className="mb-4 rounded-2xl border border-line bg-white/5 p-4">
          <Icon size={28} className="text-faint" />
        </div>
      )}
      <div className="mono text-sm text-dim">{title}</div>
      {subtitle && <div className="mt-1 max-w-sm text-sm text-faint">{subtitle}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Modal({ open, onClose, title, children, maxW = "max-w-lg" }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm"
      onMouseDown={onClose}
      data-testid="modal-overlay"
    >
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.2 }}
        className={`glass mt-16 w-full ${maxW} p-6`}
        style={{ background: "var(--bg-elev)" }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink">{title}</h3>
          <button onClick={onClose} className="text-faint hover:text-ink" data-testid="modal-close">
            <X size={18} />
          </button>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

export function Field({ label, children, hint }) {
  return (
    <label className="block">
      {label && <div className="mb-1.5 text-xs font-medium text-dim">{label}</div>}
      {children}
      {hint && <div className="mt-1 text-xs text-faint">{hint}</div>}
    </label>
  );
}

export function PageReveal({ children, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
