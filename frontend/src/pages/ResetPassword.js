import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { supabase } from "../lib/supabase";
import { toast } from "sonner";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false); // recovery session established?
  const [error, setError] = useState("");

  useEffect(() => {
    // The recovery link opens here with a recovery session in the URL; supabase-js
    // parses it and fires PASSWORD_RECOVERY. Either signal means we can reset.
    supabase.auth.getSession().then(({ data }) => { if (data?.session) setReady(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" || session) setReady(true);
    });
    return () => sub?.subscription?.unsubscribe();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { error: err } = await supabase.auth.updateUser({ password });
      if (err) throw err;
      await supabase.auth.signOut();
      toast.success("Password updated — please sign in.");
      navigate("/login");
    } catch (err) {
      setError(err?.message || "Could not update the password. Request a new link.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Set a new password" footer={<Link to="/login" className="text-cyan hover:underline">Back to sign in</Link>}>
      {!ready ? (
        <div className="rounded-lg border border-bad/30 bg-bad/10 p-3 text-sm text-bad">
          Open this page from the reset link in your email. The link may have expired —
          request a new one from “Forgot password”.
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
          <Field label="New password" hint="Minimum 8 characters.">
            <input type="password" className="field" value={password} required minLength={8}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••" data-testid="reset-password" />
          </Field>
          {error && <div className="text-sm text-bad">{error}</div>}
          <button type="submit" className="btn btn-primary w-full" disabled={loading} data-testid="reset-submit">
            {loading ? <Spinner /> : "Update password"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
