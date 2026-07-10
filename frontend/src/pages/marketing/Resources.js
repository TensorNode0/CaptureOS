import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import MarketingLayout from "./MarketingLayout";
import { ARTICLES, ARTICLE_ORDER } from "./resources/articleData";

export default function Resources() {
  return (
    <MarketingLayout>
      <div className="mx-auto max-w-5xl px-5 pb-10 pt-14">
        <div className="label-mono">RESOURCES</div>
        <h1 className="mt-2 text-3xl font-semibold text-ink">The GovCon field guide</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-dim">
          Practical, step-by-step playbooks for winning federal work — registrations,
          compliance, official proposal templates, and the AI keys that power your
          workspace. Every link points at the official source.
        </p>

        <div className="mt-10 grid gap-4 md:grid-cols-2">
          {ARTICLE_ORDER.map((slug) => {
            const a = ARTICLES[slug];
            return (
              <Link key={slug} to={`/resources/${slug}`} data-testid={`resource-${slug}`}
                    className="group flex flex-col rounded-xl border border-line bg-white/5 p-5 transition-colors hover:border-cyan/40">
                <div className="label-mono">{a.tag}</div>
                <div className="mt-2 text-lg font-semibold leading-snug text-ink">{a.title}</div>
                <p className="mt-2 flex-1 text-xs leading-relaxed text-faint">{a.summary}</p>
                <div className="mt-4 inline-flex items-center gap-1.5 text-xs text-cyan">
                  Read the guide <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </MarketingLayout>
  );
}
