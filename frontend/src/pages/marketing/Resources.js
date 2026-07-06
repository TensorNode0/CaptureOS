import React from "react";
import { Link } from "react-router-dom";
import { KeyRound, ExternalLink, ShieldCheck } from "lucide-react";
import MarketingLayout from "./MarketingLayout";

function Step({ n, children }) {
  return (
    <li className="flex gap-3 text-sm text-dim">
      <span className="mono mt-0.5 shrink-0 text-cyan">{n}.</span>
      <span>{children}</span>
    </li>
  );
}

function Ext({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noreferrer"
       className="inline-flex items-center gap-1 text-cyan hover:underline">
      {children} <ExternalLink size={12} />
    </a>
  );
}

export default function Resources() {
  return (
    <MarketingLayout>
      <section className="mx-auto max-w-4xl px-5 pb-8 pt-16">
        <div className="label-mono mb-3">Resources</div>
        <h1 className="text-4xl font-bold text-ink">Get your API keys, step by step</h1>
        <p className="mt-4 text-lg text-dim">
          CaptureAgent runs on keys your organization owns. You'll need two —
          SAM.gov (free) and Anthropic Claude — plus OpenAI if you want ChatGPT
          as a second drafting engine. Budget about 15 minutes total.
        </p>
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-ok/30 bg-ok/5 p-3 text-sm text-dim">
          <ShieldCheck size={16} className="mt-0.5 shrink-0 text-ok" />
          <span>Keys are entered in <span className="text-ink">Settings → API Keys</span> by
          your workspace admin, encrypted per organization, and never visible to
          anyone afterward — including us. Never share keys in email or chat.</span>
        </div>
      </section>

      <section className="mx-auto max-w-4xl space-y-6 px-5 py-6">
        <article className="glass p-6" id="sam">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan/40 bg-cyan/10"><KeyRound size={18} className="text-cyan" /></div>
            <div>
              <h2 className="text-lg font-semibold text-ink">SAM.gov public API key</h2>
              <div className="text-xs text-faint">Free · powers live opportunity pulls · ~5 minutes</div>
            </div>
          </div>
          <ol className="mt-4 space-y-2.5">
            <Step n={1}>Sign in (or register) at <Ext href="https://sam.gov">sam.gov</Ext> — any
              individual account works; you do not need entity registration just for the API key.</Step>
            <Step n={2}>Click your name (top right) → <span className="text-ink">Account Details</span>.</Step>
            <Step n={3}>On the Account Details page, find the <span className="text-ink">API Key</span> section,
              enter your password, and click to generate the key. Copy it immediately.</Step>
            <Step n={4}>Paste it into CaptureAgent under <span className="text-ink">Settings → API Keys → SAM.gov</span>.</Step>
          </ol>
          <p className="mt-3 text-xs text-faint">
            Reference: the key serves the{" "}
            <Ext href="https://open.gsa.gov/api/get-opportunities-public-api/">Get Opportunities Public API</Ext>.
            Keys expire every 90 days — regenerate from the same page when pulls start failing with a 401/403.
          </p>
        </article>

        <article className="glass p-6" id="anthropic">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-violet/40 bg-violet/10"><KeyRound size={18} className="text-violet" /></div>
            <div>
              <h2 className="text-lg font-semibold text-ink">Anthropic (Claude) API key</h2>
              <div className="text-xs text-faint">Pay-as-you-go · powers intelligence scans, capability design, and drafting · ~5 minutes</div>
            </div>
          </div>
          <ol className="mt-4 space-y-2.5">
            <Step n={1}>Create an account at <Ext href="https://console.anthropic.com">console.anthropic.com</Ext>.</Step>
            <Step n={2}>Add a payment method under <span className="text-ink">Settings → Billing</span> and
              buy a small amount of credit — $10–20 goes a long way for a small team.</Step>
            <Step n={3}>Go to <Ext href="https://console.anthropic.com/settings/keys">Settings → API Keys</Ext> →
              <span className="text-ink"> Create Key</span>. Name it (e.g. "CaptureAgent") and copy it —
              it is shown only once.</Step>
            <Step n={4}>Paste it into <span className="text-ink">Settings → API Keys → Anthropic</span> in CaptureAgent.</Step>
          </ol>
          <p className="mt-3 text-xs text-faint">
            Typical costs on your account: an intelligence scan runs a few cents to ~$1 depending on
            depth; drafting a full proposal package is usually a few dollars. Set a monthly spend limit
            in the Anthropic console for peace of mind.
          </p>
        </article>

        <article className="glass p-6" id="openai">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-white/5"><KeyRound size={18} className="text-dim" /></div>
            <div>
              <h2 className="text-lg font-semibold text-ink">OpenAI (ChatGPT) API key — optional</h2>
              <div className="text-xs text-faint">Pay-as-you-go · adds a second drafting engine · ~5 minutes</div>
            </div>
          </div>
          <ol className="mt-4 space-y-2.5">
            <Step n={1}>Create an account at <Ext href="https://platform.openai.com">platform.openai.com</Ext> —
              note this is the API platform, separate from a ChatGPT Plus subscription.</Step>
            <Step n={2}>Add billing under <span className="text-ink">Settings → Billing</span>.</Step>
            <Step n={3}>Go to <Ext href="https://platform.openai.com/api-keys">API keys</Ext> →
              <span className="text-ink"> Create new secret key</span> and copy it.</Step>
            <Step n={4}>Paste it into <span className="text-ink">Settings → API Keys → OpenAI</span>; the
              ChatGPT option then unlocks in every volume's Draft-with-AI selector.</Step>
          </ol>
        </article>
      </section>

      <section className="mx-auto max-w-3xl px-5 py-12 text-center">
        <h2 className="text-2xl font-semibold text-ink">Keys in hand?</h2>
        <p className="mt-3 text-dim">Create your workspace, paste them once, and start scanning.</p>
        <Link to="/register" className="btn btn-primary mt-6 !px-6 !py-3 text-base">Create your workspace</Link>
      </section>
    </MarketingLayout>
  );
}
