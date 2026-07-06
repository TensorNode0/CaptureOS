import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

export default function Register() {
  const { register, errMsg } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await register(name, email, password);
      if (data.verifyUrl) {
        toast.success("Account created", {
          description: "Email is in dev mode — verify any time.",
          action: { label: "Verify now", onClick: () => (window.location.href = data.verifyUrl) },
        });
      } else {
        toast.success("Account created", {
          description: "We sent a verification link to your email — check your inbox.",
        });
      }
      navigate(data.organizations?.length ? "/dashboard" : "/onboarding");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Stand up a capture command center in minutes."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="text-cyan hover:underline" data-testid="link-login">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" data-testid="register-form">
        <Field label="Full name">
          <input className="field" value={name} required
            onChange={(e) => setName(e.target.value)}
            placeholder="Jane Capture" data-testid="register-name" />
        </Field>
        <Field label="Email">
          <input type="email" className="field" value={email} required
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com" data-testid="register-email" />
        </Field>
        <Field label="Password" hint="Minimum 8 characters.">
          <input type="password" className="field" value={password} required minLength={8}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••" data-testid="register-password" />
        </Field>
        {error && <div className="text-sm text-bad" data-testid="register-error">{error}</div>}
        <button type="submit" className="btn btn-primary w-full" disabled={loading} data-testid="register-submit">
          {loading ? <Spinner /> : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
