import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, errMsg } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const invited = new URLSearchParams(location.search).get("invited");
  const [email, setEmail] = useState(invited || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Access your federal pipeline command center."
      footer={
        <>
          No account?{" "}
          <Link to="/register" className="text-cyan hover:underline" data-testid="link-register">
            Create one
          </Link>
        </>
      }
    >
      {invited && (
        <div className="mb-4 rounded-lg border border-cyan/30 bg-cyan/10 p-3 text-sm text-cyan" data-testid="invite-notice">
          You were invited — sign in (or register) with <b>{invited}</b> to join the organization.
        </div>
      )}
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <Field label="Email">
          <input
            type="email" className="field" value={email} required
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com" data-testid="login-email"
          />
        </Field>
        <Field label="Password">
          <input
            type="password" className="field" value={password} required
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••" data-testid="login-password"
          />
        </Field>
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-xs text-dim hover:text-cyan" data-testid="link-forgot">
            Forgot password?
          </Link>
        </div>
        {error && <div className="text-sm text-bad" data-testid="login-error">{error}</div>}
        <button type="submit" className="btn btn-liquid liquid-cyan w-full" disabled={loading} data-testid="login-submit">
          {loading ? <Spinner /> : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}
