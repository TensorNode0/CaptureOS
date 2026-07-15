import React, { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { supabase } from "../lib/supabase";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Supabase emails the recovery link, which returns to /reset-password
      // with a recovery session that supabase-js picks up automatically.
      const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (err) throw err;
      setDone(true);
    } catch (err) {
      setError(err?.message || "Could not send the reset link. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Reset password"
      subtitle="We'll email you a secure reset link."
      footer={<Link to="/login" className="text-cyan hover:underline">Back to sign in</Link>}
    >
      {done ? (
        <div className="space-y-3" data-testid="forgot-done">
          <div className="rounded-lg border border-ok/30 bg-ok/10 p-3 text-sm text-ok">
            If that account exists, a reset link is on its way to your inbox.
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          <Field label="Email">
            <input type="email" className="field" value={email} required
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com" data-testid="forgot-email" />
          </Field>
          {error && <div className="text-sm text-bad">{error}</div>}
          <button type="submit" className="btn btn-primary w-full" disabled={loading} data-testid="forgot-submit">
            {loading ? <Spinner /> : "Send reset link"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
