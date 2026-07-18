import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, Loader2 } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useSubscription } from "../lib/billing";

// Poll /api/payments/status/{sid} until we see 'paid' (or hit our own timeout).
export default function BillingSuccess() {
  const [params] = useSearchParams();
  const sid = params.get("session_id") || "";
  const navigate = useNavigate();
  const { refresh } = useSubscription();
  const [status, setStatus] = useState("polling"); // polling | ok | timeout | error
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!sid) { setStatus("error"); setErr("Missing session id."); return; }
    let attempts = 0;
    let cancelled = false;

    const poll = async () => {
      while (!cancelled && attempts < 15) {
        attempts += 1;
        try {
          const { data } = await api.get(`/payments/status/${sid}`);
          if (data.paymentStatus === "paid") {
            await refresh();
            setStatus("ok");
            return;
          }
        } catch (e) { setErr(errMsg(e)); }
        await new Promise((r) => setTimeout(r, 2000));
      }
      if (!cancelled) setStatus("timeout");
    };
    poll();
    return () => { cancelled = true; };
  }, [sid, refresh]);

  return (
    <div className="mx-auto max-w-xl px-5 pt-20" data-testid="billing-success">
      <div className="glass p-8 text-center">
        {status === "polling" && (
          <>
            <Loader2 size={38} className="mx-auto animate-spin text-cyan" />
            <h1 className="mt-4 text-2xl font-bold text-ink">Finalizing your subscription…</h1>
            <p className="mt-2 text-sm text-dim">
              Stripe is confirming the payment. This usually takes a few
              seconds.
            </p>
          </>
        )}
        {status === "ok" && (
          <>
            <CheckCircle2 size={44} className="mx-auto text-emerald-400" />
            <h1 className="mt-4 text-2xl font-bold text-ink">You’re on the Full plan.</h1>
            <p className="mt-2 text-sm text-dim">
              Federal Proposals, Investment Deals, and Accelerator
              Applications are unlocked. Welcome aboard.
            </p>
            <button className="btn btn-primary mt-6"
                    onClick={() => navigate("/dashboard")}
                    data-testid="billing-success-cta">
              Open the dashboard
            </button>
          </>
        )}
        {status === "timeout" && (
          <>
            <h1 className="mt-4 text-2xl font-bold text-ink">Still processing…</h1>
            <p className="mt-2 text-sm text-dim">
              Stripe hasn’t confirmed the payment yet. You can safely head to
              the dashboard — we’ll update your plan the moment the webhook
              lands. If it doesn’t within a few minutes,{" "}
              <Link to="/contact" className="text-cyan hover:underline">reach out to CaptureAgent</Link>.
            </p>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="mt-4 text-2xl font-bold text-ink">Something went wrong</h1>
            <p className="mt-2 text-sm text-bad">{err || "Unknown error"}</p>
            <Link to="/pricing" className="btn btn-primary mt-6">Back to pricing</Link>
          </>
        )}
      </div>
    </div>
  );
}
