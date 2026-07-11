import React, { useState } from "react";
import { Send, CheckCircle2, Loader2, Mail } from "lucide-react";
import MarketingLayout from "./MarketingLayout";
import { api, errMsg } from "../../lib/api";
import { SECTORS, INDUSTRIES, INQUIRY_TYPES } from "./formData";

const EMPTY = {
  firstName: "", lastName: "", company: "", email: "",
  sector: "", industry: "", inquiryType: "", message: "", website: "",
};

export default function Contact() {
  const [form, setForm] = useState(EMPTY);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSending(true);
    try {
      await api.post("/public/contact", form);
      setSent(true);
      setForm(EMPTY);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setSending(false);
    }
  };

  const sel = "field";
  return (
    <MarketingLayout>
      <section className="mx-auto max-w-6xl px-5 pt-14">
        <div className="grid gap-12 lg:grid-cols-2">
          <div>
            <div className="label-mono text-cyan">Contact</div>
            <h1 className="mt-2 text-4xl font-bold tracking-tight text-ink sm:text-5xl">
              Talk to the team
            </h1>
            <p className="mt-4 max-w-md leading-relaxed text-dim">
              Questions about billing, the API, a bug, privacy, or anything else —
              send a note and we'll get back to you at your company email.
            </p>
            <div className="mt-8 flex items-center gap-2 text-sm text-faint">
              <Mail size={15} className="text-cyan" />
              Your message goes straight to our team's inbox.
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-white/[0.03] p-6">
            {sent ? (
              <div className="py-14 text-center" data-testid="contact-sent">
                <CheckCircle2 size={40} className="mx-auto text-ok" />
                <h3 className="mt-4 text-lg font-semibold text-ink">Message sent!</h3>
                <p className="mt-2 text-sm text-dim">
                  Thanks for reaching out — we'll reply to your company email shortly.
                </p>
                <button className="btn btn-ghost mt-5" onClick={() => setSent(false)} data-testid="contact-again">
                  Send another message
                </button>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-3" data-testid="contact-form">
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-xs text-faint">First name *
                    <input className={sel} required maxLength={60} value={form.firstName} onChange={set("firstName")} data-testid="ct-first" />
                  </label>
                  <label className="block text-xs text-faint">Last name *
                    <input className={sel} required maxLength={60} value={form.lastName} onChange={set("lastName")} data-testid="ct-last" />
                  </label>
                </div>
                <label className="block text-xs text-faint">Company name *
                  <input className={sel} required maxLength={120} value={form.company} onChange={set("company")} data-testid="ct-company" />
                </label>
                <label className="block text-xs text-faint">Company email *
                  <input type="email" className={sel} required value={form.email} onChange={set("email")} data-testid="ct-email" />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-xs text-faint">Sector *
                    <select className={sel} required value={form.sector} onChange={set("sector")} data-testid="ct-sector">
                      <option value="" disabled>Select…</option>
                      {SECTORS.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </label>
                  <label className="block text-xs text-faint">Industry *
                    <select className={sel} required value={form.industry} onChange={set("industry")} data-testid="ct-industry">
                      <option value="" disabled>Select…</option>
                      {INDUSTRIES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </label>
                </div>
                <label className="block text-xs text-faint">Inquiry type *
                  <select className={sel} required value={form.inquiryType} onChange={set("inquiryType")} data-testid="ct-inquiry">
                    <option value="" disabled>Select…</option>
                    {INQUIRY_TYPES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </label>
                <label className="block text-xs text-faint">Message *
                  <textarea className={`${sel} min-h-[120px]`} required maxLength={4000}
                    value={form.message} onChange={set("message")}
                    placeholder="How can we help?" data-testid="ct-message" />
                </label>
                {/* honeypot — hidden from real users */}
                <input className="hidden" tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} aria-hidden="true" />
                {error && <p className="text-xs text-bad" data-testid="contact-error">{error}</p>}
                <button type="submit" className="btn btn-primary w-full" disabled={sending} data-testid="contact-send">
                  {sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />} Send
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
