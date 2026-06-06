import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function Onboarding() {
  const { user, refreshUser, switchOrg } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [naics, setNaics] = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (user === null) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.organizations && user.organizations.length > 0)
    return <Navigate to="/dashboard" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/orgs", {
        name,
        naics: naics.split(",").map((s) => s.trim()).filter(Boolean),
        keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
      });
      await refreshUser();
      switchOrg(data.id);
      navigate("/dashboard");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Create your organization" subtitle="Every record is scoped to your org. You'll be the Owner.">
      <form onSubmit={submit} className="space-y-4" data-testid="onboarding-form">
        <Field label="Organization name">
          <input className="field" value={name} required
            onChange={(e) => setName(e.target.value)}
            placeholder="Orbital Defense Systems" data-testid="org-name" />
        </Field>
        <Field label="NAICS codes" hint="Comma-separated, e.g. 336412, 541715">
          <input className="field" value={naics}
            onChange={(e) => setNaics(e.target.value)}
            placeholder="336412, 541715" data-testid="org-naics" />
        </Field>
        <Field label="Keywords" hint="Used by SAM/Grants pulls. Comma-separated.">
          <input className="field" value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="UAS, hypersonic, cyber" data-testid="org-keywords" />
        </Field>
        {error && <div className="text-sm text-bad">{error}</div>}
        <button type="submit" className="btn btn-primary w-full" disabled={loading} data-testid="create-org-submit">
          {loading ? <Spinner /> : "Create organization"}
        </button>
      </form>
    </AuthLayout>
  );
}
