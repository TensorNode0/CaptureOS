import React, { useEffect, useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { Clock, ShieldCheck } from "lucide-react";
import AuthLayout from "./AuthLayout";
import { Field, Spinner } from "../components/ui";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function Onboarding() {
  const { user, refreshUser, switchOrg } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null); // domain-status payload
  const [name, setName] = useState("");
  const [naics, setNaics] = useState("");
  const [keywords, setKeywords] = useState("");
  const [certify, setCertify] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const hasPending = user?.pendingOrganizations?.length > 0;

  useEffect(() => {
    if (!user || hasPending) return;
    api.get("/orgs/domain-status")
      .then(({ data }) => setStatus(data))
      .catch(() => setStatus({ publicDomain: true, org: null }));
  }, [user, hasPending]);

  if (user === null) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.organizations && user.organizations.length > 0)
    return <Navigate to="/dashboard" replace />;

  // Waiting on an admin to approve a join request
  if (hasPending) {
    const org = user.pendingOrganizations[0];
    return (
      <AuthLayout title="Request pending" subtitle={`Your request to join ${org.name} is with the administrator.`}>
        <div className="flex items-start gap-3 rounded-lg border border-line bg-white/5 p-4 text-sm text-dim"
             data-testid="pending-approval">
          <Clock size={18} className="mt-0.5 shrink-0 text-warn" />
          <div>
            The <span className="text-ink">{org.name}</span> administrator has been
            notified by email. You'll receive an email when your access and role are
            approved — then just sign in again.
          </div>
        </div>
      </AuthLayout>
    );
  }

  if (!status) {
    return (
      <AuthLayout title="Setting up" subtitle="Checking your organization…">
        <div className="flex justify-center py-8"><Spinner size={24} /></div>
      </AuthLayout>
    );
  }

  // Company domain already registered → request to join
  if (status.org) {
    const requestJoin = async () => {
      setError("");
      setLoading(true);
      try {
        await api.post(`/orgs/${status.org.id}/join-request`);
        await refreshUser();
      } catch (err) {
        setError(errMsg(err));
      } finally {
        setLoading(false);
      }
    };
    return (
      <AuthLayout title="Your company is already here"
                  subtitle={`A workspace for @${status.domain} already exists.`}>
        <div className="space-y-4" data-testid="join-existing-org">
          <div className="rounded-lg border border-line bg-white/5 p-4">
            <div className="text-sm font-semibold text-ink">{status.org.name}</div>
            <div className="mt-1 text-xs text-dim">
              Request access and the workspace administrator will approve you and
              assign your role (PI, Proposal Writer, Capture Manager, …).
            </div>
          </div>
          {error && <div className="text-sm text-bad">{error}</div>}
          <button className="btn btn-primary w-full" onClick={requestJoin}
                  disabled={loading} data-testid="request-join-submit">
            {loading ? <Spinner /> : `Request to join ${status.org.name}`}
          </button>
        </div>
      </AuthLayout>
    );
  }

  // No org for this domain → this user must be the AOR / Admin
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!certify) {
      setError("You must certify that you are the AOR / Administrator to continue.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/orgs", {
        name,
        naics: naics.split(",").map((s) => s.trim()).filter(Boolean),
        keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
        certifyAor: certify,
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
    <AuthLayout title="Create your organization"
                subtitle={status.publicDomain
                  ? "You'll be the workspace Administrator."
                  : `You're the first person from @${status.domain} — you'll be the Administrator.`}>
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
        <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-line bg-white/5 p-3"
               data-testid="aor-certify">
          <input type="checkbox" checked={certify} onChange={(e) => setCertify(e.target.checked)}
                 className="mt-1 accent-cyan" data-testid="aor-certify-checkbox" />
          <span className="text-xs leading-relaxed text-dim">
            <ShieldCheck size={13} className="mr-1 inline text-cyan" />
            I certify that I am my organization's <span className="text-ink">Authorized
            Organizational Representative (AOR)</span> and will act as the workspace
            <span className="text-ink"> Administrator</span>, responsible for entity
            information, member roles, and proposal submission.
          </span>
        </label>
        {error && <div className="text-sm text-bad" data-testid="onboarding-error">{error}</div>}
        <button type="submit" className="btn btn-primary w-full" disabled={loading} data-testid="create-org-submit">
          {loading ? <Spinner /> : "Create organization"}
        </button>
      </form>
    </AuthLayout>
  );
}
