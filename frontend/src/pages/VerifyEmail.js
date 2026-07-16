import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Spinner } from "../components/ui";
import { supabase } from "../lib/supabase";
import { useAuth } from "../context/AuthContext";
import { CheckCircle2, XCircle } from "lucide-react";

export default function VerifyEmail() {
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState("verifying"); // verifying|ok|fail
  const [error, setError] = useState("");

  useEffect(() => {
    // Supabase confirmation links return here with a session in the URL, which
    // supabase-js parses automatically (detectSessionInUrl). A session means
    // the email is confirmed.
    let done = false;
    const finish = (session) => {
      if (done) return;
      done = true;
      if (session) { setStatus("ok"); refreshUser(); }
      else { setStatus("fail"); setError("This confirmation link is invalid or expired."); }
    };
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      if (session) finish(session);
    });
    supabase.auth.getSession().then(({ data }) => {
      if (data?.session) finish(data.session);
      else setTimeout(() => finish(null), 4000); // give the URL parse a moment
    });
    return () => sub?.subscription?.unsubscribe();
  }, [refreshUser]);

  return (
    <AuthLayout title="Email verification">
      <div className="flex flex-col items-center py-4 text-center" data-testid="verify-status">
        {status === "verifying" && <><Spinner size={28} className="text-cyan" /><p className="mt-4 text-sm text-dim">Verifying…</p></>}
        {status === "ok" && (
          <>
            <CheckCircle2 size={40} className="text-ok" />
            <p className="mt-4 text-sm text-ink">Your email is verified.</p>
            <Link to="/dashboard" className="btn btn-primary mt-5">Go to dashboard</Link>
          </>
        )}
        {status === "fail" && (
          <>
            <XCircle size={40} className="text-bad" />
            <p className="mt-4 text-sm text-bad">{error || "Verification failed."}</p>
            <Link to="/login" className="btn btn-ghost mt-5">Back to sign in</Link>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
