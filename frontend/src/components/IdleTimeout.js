import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TimerReset } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Modal } from "./ui";

const IDLE_MS = 30 * 60 * 1000;   // 30 min of no activity → warn
const WARN_SECONDS = 120;         // visible countdown before sign-out

/* Session inactivity guard: after 30 idle minutes a warning modal counts down
   120s in plain sight. "Stay signed in" refreshes the session; letting it hit
   zero signs the user out. Mounted once inside Shell (authenticated area). */
export default function IdleTimeout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [warning, setWarning] = useState(false);
  const [left, setLeft] = useState(WARN_SECONDS);
  const idleTimer = useRef(null);
  const tick = useRef(null);
  const warningRef = useRef(false);

  const signOut = useCallback(async () => {
    clearInterval(tick.current);
    warningRef.current = false;
    setWarning(false);
    await logout();
    navigate("/login", { state: { reason: "idle" } });
  }, [logout, navigate]);

  const openWarning = useCallback(() => {
    warningRef.current = true;
    setLeft(WARN_SECONDS);
    setWarning(true);
    clearInterval(tick.current);
    tick.current = setInterval(() => {
      setLeft((s) => {
        if (s <= 1) { signOut(); return 0; }
        return s - 1;
      });
    }, 1000);
  }, [signOut]);

  const armIdleTimer = useCallback(() => {
    clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(openWarning, IDLE_MS);
  }, [openWarning]);

  useEffect(() => {
    // Activity resets the idle clock — unless the warning is already up
    // (deciding to stay must be explicit once the countdown starts).
    let last = 0;
    const onActivity = () => {
      if (warningRef.current) return;
      const now = Date.now();
      if (now - last < 5000) return; // throttle
      last = now;
      armIdleTimer();
    };
    const events = ["mousemove", "keydown", "click", "touchstart", "scroll"];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    armIdleTimer();
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
      clearTimeout(idleTimer.current);
      clearInterval(tick.current);
    };
  }, [armIdleTimer]);

  const stay = async () => {
    clearInterval(tick.current);
    warningRef.current = false;
    setWarning(false);
    try { await api.post("/auth/refresh"); } catch { /* next API call re-auths */ }
    armIdleTimer();
  };

  const mm = String(Math.floor(left / 60));
  const ss = String(left % 60).padStart(2, "0");

  return (
    <Modal open={warning} onClose={stay} title="Still there?">
      <div className="space-y-4 text-center" data-testid="idle-warning">
        <p className="text-sm text-dim">
          You have been inactive for 30 minutes. For security you will be signed
          out automatically when the timer reaches zero.
        </p>
        <div className="mono text-5xl font-semibold text-warn" data-testid="idle-countdown">
          {mm}:{ss}
        </div>
        <div className="flex justify-center gap-2">
          <button className="btn btn-ghost" onClick={signOut} data-testid="idle-signout">
            Sign out now
          </button>
          <button className="btn btn-primary" onClick={stay} data-testid="idle-stay">
            <TimerReset size={15} /> Stay signed in
          </button>
        </div>
      </div>
    </Modal>
  );
}
