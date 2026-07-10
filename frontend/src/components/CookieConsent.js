import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cookie } from "lucide-react";

const KEY = "ca-cookie-consent";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(KEY)) setVisible(true);
    } catch { /* storage unavailable — stay hidden */ }
  }, []);

  const choose = (value) => {
    try { localStorage.setItem(KEY, value); } catch { /* ignore */ }
    setVisible(false);
  };

  if (!visible) return null;
  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-3 sm:p-4" data-testid="cookie-banner">
      <div className="mx-auto flex max-w-3xl flex-col gap-3 rounded-xl border border-line bg-elev/95 p-4 shadow-xl backdrop-blur-md sm:flex-row sm:items-center">
        <Cookie size={20} className="hidden shrink-0 text-cyan sm:block" />
        <p className="flex-1 text-xs leading-relaxed text-dim">
          CaptureAgent uses strictly necessary cookies only — encrypted session
          cookies that keep you signed in. No advertising or cross-site tracking.
          See our <Link to="/privacy" className="text-cyan hover:underline">Privacy Policy</Link>.
        </p>
        <div className="flex shrink-0 gap-2">
          <button className="btn btn-ghost !py-1.5 !px-3 text-xs" onClick={() => choose("dismissed")}
                  data-testid="cookie-dismiss">Dismiss</button>
          <button className="btn btn-primary !py-1.5 !px-3 text-xs" onClick={() => choose("accepted")}
                  data-testid="cookie-accept">Got it</button>
        </div>
      </div>
    </div>
  );
}
