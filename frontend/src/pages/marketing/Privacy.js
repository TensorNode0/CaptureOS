import React from "react";
import MarketingLayout from "./MarketingLayout";

const EFFECTIVE = "July 6, 2026";

function H({ children }) {
  return <h2 className="mt-10 text-lg font-semibold text-ink">{children}</h2>;
}
function P({ children }) {
  return <p className="mt-3 text-sm leading-relaxed text-dim">{children}</p>;
}
function LI({ children }) {
  return <li className="mt-1.5 text-sm leading-relaxed text-dim">• {children}</li>;
}

export default function Privacy() {
  return (
    <MarketingLayout>
      <div className="mx-auto max-w-3xl px-5 pb-10 pt-14">
        <div className="label-mono">LEGAL</div>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Privacy Policy</h1>
        <p className="mt-2 text-xs text-faint">Effective date: {EFFECTIVE}</p>

        <P>
          CaptureAgent ("we," "us") provides an AI-assisted capture and proposal
          management platform for government contractors at captureagent.us (the
          "Service"). This policy explains what we collect, how we use it, and the
          choices you have. It is written to comply with applicable U.S. privacy
          laws, including the California Consumer Privacy Act as amended by the
          CPRA ("CCPA") and similar state privacy statutes.
        </P>

        <H>Information we collect</H>
        <ul>
          <LI><span className="text-ink">Account data</span> — name, work email, password (stored only as a salted bcrypt hash).</LI>
          <LI><span className="text-ink">Organization data you enter</span> — company profile details (UEI, CAGE, certifications, capabilities, past performance), opportunities you track, and proposal content you create.</LI>
          <LI><span className="text-ink">API keys you bring</span> — encrypted with per-organization envelope encryption before storage; displayed only as masked previews; every use is written to your organization's audit log. We do not use your keys for anything except the actions you trigger.</LI>
          <LI><span className="text-ink">Usage and log data</span> — authentication events, IP-based login-attempt throttling records, and audit-log entries of actions inside your workspace.</LI>
          <LI><span className="text-ink">Cookies</span> — see "Cookies" below.</LI>
        </ul>

        <H>How we use information</H>
        <ul>
          <LI>To provide the Service: storing your pipeline, generating AI drafts you request, sending transactional email (verification, password reset, invitations, approval notices).</LI>
          <LI>To secure the Service: login throttling, audit trails, role-based access control.</LI>
          <LI>We do <span className="text-ink">not</span> sell or share your personal information for cross-context behavioral advertising, and we do not use your proposal content to train AI models.</LI>
        </ul>

        <H>AI processing</H>
        <P>
          When you press an AI action, relevant workspace content (for example, an
          opportunity description and your company profile) is sent to the AI
          provider whose key your organization configured (Anthropic, OpenAI,
          Emergent, or AskSage), under your agreement with that provider. Choose
          providers whose data-use terms fit your needs; API traffic to these
          providers is generally excluded from model training under their API terms.
        </P>

        <H>Cookies</H>
        <P>
          We use strictly necessary cookies only: encrypted, HttpOnly session
          cookies that keep you signed in. We do not use advertising or
          cross-site tracking cookies. A consent notice is shown on your first
          visit; your choice is stored in your browser.
        </P>

        <H>Sharing</H>
        <P>
          We share data only with the service providers that make the platform run
          — database hosting (Supabase/PostgreSQL), email delivery, and the AI
          providers you configure — each bound to process data only to provide
          their service. We may disclose information if required by law. In a
          merger or acquisition, data may transfer subject to this policy.
        </P>

        <H>Security</H>
        <P>
          TLS in transit; encryption at rest for the database; envelope encryption
          with per-organization keys for API credentials; salted bcrypt password
          hashing; role-based access control with audit logging; login throttling.
          No method is 100% secure, but security is a first-class design goal.
          Do not store classified information, CUI, or ITAR-controlled technical
          data in the Service.
        </P>

        <H>Your rights</H>
        <P>
          Depending on your state, you may have rights to access, correct, delete,
          or export your personal information, and to non-discrimination for
          exercising them. Organization administrators can edit or delete workspace
          data directly. For anything else — including account deletion — email
          <a href="mailto:privacy@captureagent.us" className="text-cyan hover:underline"> privacy@captureagent.us</a>.
          We respond within the timelines your state's law requires (45 days under CCPA).
        </P>

        <H>Data retention</H>
        <P>
          Account and workspace data persist until you delete them or your
          organization asks us to. Audit logs are retained for security purposes.
          Password-reset and email-verification tokens expire automatically.
        </P>

        <H>Children</H>
        <P>The Service is for business use and not directed to children under 13; we do not knowingly collect their data.</P>

        <H>Changes</H>
        <P>
          We'll post updates here and change the effective date; material changes
          will be announced in-app or by email.
        </P>

        <H>Contact</H>
        <P>
          CaptureAgent · captureagent.us ·{" "}
          <a href="mailto:privacy@captureagent.us" className="text-cyan hover:underline">privacy@captureagent.us</a>
        </P>
      </div>
    </MarketingLayout>
  );
}
