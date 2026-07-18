import React from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, Info } from "lucide-react";
import MarketingLayout from "../MarketingLayout";
import { ARTICLES } from "./articleData";

/* Data-driven article renderer. Blocks: h2, p, note, steps, links, table, related. */

function Block({ b }) {
  if (b.h2) return <h2 className="mt-10 text-xl font-semibold text-ink">{b.h2}</h2>;
  if (b.p) return <p className="mt-4 text-sm leading-relaxed text-dim">{b.p}</p>;
  if (b.note) return (
    <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-cyan/30 bg-cyan/5 p-3.5 text-xs leading-relaxed text-dim">
      <Info size={15} className="mt-0.5 shrink-0 text-cyan" /><span>{b.note}</span>
    </div>
  );
  if (b.steps) return (
    <ol className="mt-4 space-y-3">
      {b.steps.map((s, i) => (
        <li key={i} className="flex gap-3 text-sm leading-relaxed text-dim">
          <span className="mono mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-cyan/40 bg-cyan/10 text-xs text-cyan">{i + 1}</span>
          <span><span className="font-medium text-ink">{s.t}</span>{s.d ? <> — {s.d}</> : null}
            {s.href && <> <a className="text-cyan hover:underline" href={s.href} target="_blank" rel="noreferrer">{s.hrefLabel || "link"} <ExternalLink size={11} className="inline" /></a></>}
          </span>
        </li>
      ))}
    </ol>
  );
  if (b.links) return (
    <div className="mt-4 space-y-2">
      {b.links.map((l, i) => (
        <a key={i} href={l.href} target={l.href.startsWith("/") ? "_self" : "_blank"} rel="noreferrer"
           className="liquid liquid-hover flex items-start justify-between gap-3 px-4 py-3">
          <span>
            <span className="text-sm font-medium text-ink">{l.label}</span>
            {l.note && <span className="mt-0.5 block text-xs text-faint">{l.note}</span>}
          </span>
          <ExternalLink size={14} className="mt-1 shrink-0 text-cyan" />
        </a>
      ))}
    </div>
  );
  if (b.table) return (
    <div className="liquid mt-4 overflow-x-auto !rounded-2xl">
      <table className="w-full text-sm">
        <thead className="bg-white/[0.04] text-xs text-dim">
          <tr>{b.table.headers.map((h, i) => <th key={i} className="px-3 py-2.5 text-left font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {b.table.rows.map((r, i) => (
            <tr key={i} className="border-t border-white/10">
              {r.map((c, j) => <td key={j} className="px-3 py-2.5 align-top text-xs leading-relaxed text-dim">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  if (b.related) return (
    <div className="mt-5 flex flex-wrap gap-2">
      {b.related.map((slug) => {
        const a = ARTICLES[slug];
        return a ? (
          <Link key={slug} to={`/resources/${slug}`}
                className="liquid liquid-hover !rounded-full px-3.5 py-1.5 text-xs text-dim hover:text-cyan">
            {a.title}
          </Link>
        ) : null;
      })}
    </div>
  );
  return null;
}

export default function Article() {
  const { slug } = useParams();
  const a = ARTICLES[slug];
  if (!a) return <Navigate to="/resources" replace />;
  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-5 pb-10 pt-12">
        <Link to="/resources" className="inline-flex items-center gap-1.5 text-sm text-dim hover:text-cyan">
          <ArrowLeft size={15} /> All resources
        </Link>
        <div className="label-mono mt-6">{a.tag}</div>
        <h1 className="mt-2 text-3xl font-semibold leading-tight text-ink">{a.title}</h1>
        <p className="mt-3 text-sm leading-relaxed text-faint">{a.summary}</p>
        {a.blocks.map((b, i) => <Block key={i} b={b} />)}
        <div className="liquid liquid-hover mt-12 p-5 text-center">
          <div className="text-sm font-medium text-ink">Put this to work in CaptureAgent</div>
          <p className="mx-auto mt-1 max-w-md text-xs text-faint">
            Track opportunities, design capabilities, and draft compliant proposal packages with your own AI keys.
          </p>
          <Link to="/register" className="btn btn-liquid liquid-cyan mt-3 !py-2">Start Now</Link>
        </div>
      </article>
    </MarketingLayout>
  );
}
