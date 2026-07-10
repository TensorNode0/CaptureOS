import React, { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { api, errMsg } from "../lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [resetUrl, setResetUrl] = useState("");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setDone(true);
      if (data.resetUrl) setResetUrl(data.resetUrl);
    } catch (err) {
      setError(errMsg(err));
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
          {resetUrl && (
            <div className="rounded-lg border border-line bg-white/5 p-3 text-xs text-faint">
              <div className="label-mono mb-1">Local development link</div>
              <a href={resetUrl} className="break-all text-cyan hover:underline" data-testid="reset-link">
                {resetUrl}
              </a>
            </div>
          )}
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
