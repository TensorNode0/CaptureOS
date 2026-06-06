import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { api, errMsg } from "../lib/api";
import { toast } from "sonner";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      toast.success("Password updated — please sign in.");
      navigate("/login");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Set a new password" footer={<Link to="/login" className="text-cyan hover:underline">Back to sign in</Link>}>
      {!token ? (
        <div className="rounded-lg border border-bad/30 bg-bad/10 p-3 text-sm text-bad">
          Missing or invalid reset token.
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
