import React from "react";

/* CaptureAgent brand mark — open C ring, rising A with blue counter, and the
   extended-crossbar arrow capped by a blue dart (vector recreation of the
   brand PNGs). `ink` defaults to currentColor so it adapts to context. */
export const BRAND_BLUE = "#2563eb";

export function LogoMark({ size = 36, ink = "currentColor", accent = BRAND_BLUE }) {
  return (
    <svg viewBox="0 0 120 100" width={size} height={Math.round(size * 100 / 120)}
         role="img" aria-label="CaptureAgent">
      <path d="M 53.8 30.3 A 24 24 0 1 0 58.4 65.4"
            fill="none" stroke={ink} strokeWidth="9" strokeLinecap="butt" />
      <path d="M 44 80 L 68 15 L 92 80" fill="none" stroke={ink}
            strokeWidth="9" strokeLinejoin="miter" strokeLinecap="butt" />
      <path d="M 68 57 L 79 73 L 57 73 Z" fill={accent} />
      <path d="M 18 92 L 90 34.4" fill="none" stroke={ink}
            strokeWidth="7.5" strokeLinecap="butt" />
      <path d="M 102 25 L 96.9 37.8 L 88.4 27.2 Z" fill={accent} />
    </svg>
  );
}

export function LogoLockup({ size = 30, ink = "currentColor", accent = BRAND_BLUE,
                             text = true, className = "" }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark size={size} ink={ink} accent={accent} />
      {text && (
        <span style={{ fontWeight: 700, letterSpacing: "-0.02em", fontSize: size * 0.62 }}>
          CaptureAgent
        </span>
      )}
    </span>
  );
}

export default LogoMark;
