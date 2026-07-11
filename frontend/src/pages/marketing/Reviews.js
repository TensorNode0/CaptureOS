import React, { useEffect, useRef, useState } from "react";
import { Star, Upload, X, CheckCircle2, Loader2, Building2 } from "lucide-react";
import MarketingLayout from "./MarketingLayout";
import { api, errMsg } from "../../lib/api";
import { SECTORS, INDUSTRIES, INQUIRY_TYPES } from "./formData";

const EMPTY = {
  firstName: "", lastName: "", showFullName: true, company: "",
  companyAnonymous: false, email: "", sector: "", industry: "",
  inquiryType: "", message: "", headshot: "", website: "",
};

function ReviewCard({ r }) {
  return (
    <div className="rounded-2xl border border-line bg-white/[0.03] p-5" data-testid={`review-${r.id}`}>
      <div className="flex items-center gap-3">
        {r.headshot ? (
          <img src={r.headshot} alt={r.name}
            className="h-11 w-11 rounded-full border border-line object-cover" />
        ) : (
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-line bg-white/5 text-sm font-semibold text-cyan">
            {r.name.slice(0, 1)}
          </div>
        )}
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink">{r.name}</div>
          <div className="flex items-center gap-1 truncate text-xs text-faint">
            <Building2 size={11} />
            {r.company || "Company undisclosed"} · {r.sector}{r.industry ? ` · ${r.industry}` : ""}
          </div>
        </div>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-dim">{r.message}</p>
      <div className="mt-3 text-[11px] text-faint">
        {r.inquiryType} · {new Date(r.createdAt).toLocaleDateString()}
      </div>
    </div>
  );
}

export default function Reviews() {
  const [form, setForm] = useState(EMPTY);
  const [reviews, setReviews] = useState(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  useEffect(() => {
    api.get("/public/reviews").then((r) => setReviews(r.data)).catch(() => setReviews([]));
  }, []);

  const set = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const pickHeadshot = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Headshot must be a JPEG, PNG, or WEBP image.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError("Headshot must be under 2 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setForm((f) => ({ ...f, headshot: String(reader.result) }));
    reader.readAsDataURL(file);
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSending(true);
    try {
      const { data } = await api.post("/public/reviews", form);
      if (data.review) setReviews((prev) => [data.review, ...(prev || [])]);
      setSent(true);
      setForm(EMPTY);
      if (fileRef.current) fileRef.current.value = "";
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
        <div className="max-w-2xl">
          <div className="label-mono text-cyan">Reviews</div>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-ink sm:text-5xl">
            What capture teams say
          </h1>
          <p className="mt-3 text-dim">
            Share your experience with CaptureAgent. Reviews are posted below —
            you control how your name and company appear.
          </p>
        </div>

        <div className="mt-10 grid gap-10 lg:grid-cols-5">
          {/* form */}
          <div className="lg:col-span-2">
            <div className="rounded-2xl border border-line bg-white/[0.03] p-6">
              {sent ? (
                <div className="py-10 text-center" data-testid="review-sent">
                  <CheckCircle2 size={40} className="mx-auto text-ok" />
                  <h3 className="mt-4 text-lg font-semibold text-ink">Thank you — review sent!</h3>
                  <p className="mt-2 text-sm text-dim">Your review has been posted below.</p>
                  <button className="btn btn-ghost mt-5" onClick={() => setSent(false)} data-testid="review-again">
                    Write another
                  </button>
                </div>
              ) : (
                <form onSubmit={submit} className="space-y-3" data-testid="review-form">
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block text-xs text-faint">First name *
                      <input className={sel} required maxLength={60} value={form.firstName} onChange={set("firstName")} data-testid="rv-first" />
                    </label>
                    <label className="block text-xs text-faint">Last name *
                      <input className={sel} required maxLength={60} value={form.lastName} onChange={set("lastName")} data-testid="rv-last" />
                    </label>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-dim">
                    <input type="checkbox" checked={!form.showFullName}
                      onChange={(e) => setForm((f) => ({ ...f, showFullName: !e.target.checked }))}
                      data-testid="rv-initial" />
                    Show only my initials (e.g. “T. S.”)
                  </label>
                  <label className="block text-xs text-faint">Company name *
                    <input className={sel} required maxLength={120} value={form.company} onChange={set("company")} data-testid="rv-company" />
                  </label>
                  <label className="flex items-center gap-2 text-xs text-dim">
                    <input type="checkbox" checked={form.companyAnonymous} onChange={set("companyAnonymous")} data-testid="rv-anon" />
                    Keep my company anonymous
                  </label>
                  <label className="block text-xs text-faint">Company email * <span className="text-[10px]">(never displayed)</span>
                    <input type="email" className={sel} required value={form.email} onChange={set("email")} data-testid="rv-email" />
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block text-xs text-faint">Sector *
                      <select className={sel} required value={form.sector} onChange={set("sector")} data-testid="rv-sector">
                        <option value="" disabled>Select…</option>
                        {SECTORS.map((s) => <option key={s}>{s}</option>)}
                      </select>
                    </label>
                    <label className="block text-xs text-faint">Industry *
                      <select className={sel} required value={form.industry} onChange={set("industry")} data-testid="rv-industry">
                        <option value="" disabled>Select…</option>
                        {INDUSTRIES.map((s) => <option key={s}>{s}</option>)}
                      </select>
                    </label>
                  </div>
                  <label className="block text-xs text-faint">Inquiry type *
                    <select className={sel} required value={form.inquiryType} onChange={set("inquiryType")} data-testid="rv-inquiry">
                      <option value="" disabled>Select…</option>
                      {INQUIRY_TYPES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </label>
                  <label className="block text-xs text-faint">Your review *
                    <textarea className={`${sel} min-h-[110px]`} required maxLength={4000}
                      value={form.message} onChange={set("message")}
                      placeholder="How has CaptureAgent helped your capture process?" data-testid="rv-message" />
                  </label>
                  {/* honeypot — hidden from real users */}
                  <input className="hidden" tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} aria-hidden="true" />
                  <div>
                    <span className="text-xs text-faint">Headshot (optional — must be an appropriate photo of you)</span>
                    <div className="mt-1 flex items-center gap-3">
                      {form.headshot ? (
                        <span className="relative inline-block">
                          <img src={form.headshot} alt="preview" className="h-14 w-14 rounded-full border border-line object-cover" />
                          <button type="button" onClick={() => { setForm((f) => ({ ...f, headshot: "" })); if (fileRef.current) fileRef.current.value = ""; }}
                            className="absolute -right-1.5 -top-1.5 rounded-full border border-line bg-deep p-0.5 text-faint hover:text-bad"
                            data-testid="rv-headshot-remove"><X size={11} /></button>
                        </span>
                      ) : (
                        <button type="button" className="btn btn-ghost !py-1.5 text-xs" onClick={() => fileRef.current?.click()} data-testid="rv-headshot-button">
                          <Upload size={13} /> Upload photo
                        </button>
                      )}
                      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={pickHeadshot} data-testid="rv-headshot-input" />
                    </div>
                  </div>
                  {error && <p className="text-xs text-bad" data-testid="review-error">{error}</p>}
                  <button type="submit" className="btn btn-primary w-full" disabled={sending} data-testid="review-send">
                    {sending ? <Loader2 size={15} className="animate-spin" /> : <Star size={15} />} Send review
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* reviews wall */}
          <div className="lg:col-span-3">
            {reviews === null ? (
              <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-32 animate-pulse rounded-2xl border border-line bg-white/[0.03]" />)}</div>
            ) : reviews.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-line p-12 text-center text-sm text-faint" data-testid="reviews-empty">
                No reviews yet — be the first to share your experience.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2" data-testid="reviews-list">
                {reviews.map((r) => <ReviewCard key={r.id} r={r} />)}
              </div>
            )}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
