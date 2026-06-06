import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Spinner } from "../components/ui";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { CheckCircle2, XCircle } from "lucide-react";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState("verifying"); // verifying|ok|fail
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      if (!token) { setStatus("fail"); setError("Missing token"); return; }
      try {
        await api.post("/auth/verify-email", { token });
        setStatus("ok");
        refreshUser();
      } catch (err) {
        setStatus("fail");
        setError(errMsg(err));
      }
    })();
  }, [token, refreshUser]);

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
