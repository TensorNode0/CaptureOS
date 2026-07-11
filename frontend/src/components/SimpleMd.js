import React from "react";

/* Minimal markdown renderer for AI-generated reports (headings, tables,
   bullets, bold, links). Deliberately tiny — no raw HTML passthrough. */

function inline(text, key) {
  const parts = [];
  // links first, then bold inside the remaining text
  const re = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*]+)\*\*/g;
  let last = 0, m, i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2]) {
      parts.push(
        <a key={`${key}-${i++}`} href={m[2]} target="_blank" rel="noreferrer"
           className="text-cyan hover:underline">{m[1]}</a>);
    } else {
      parts.push(<strong key={`${key}-${i++}`} className="text-ink">{m[3]}</strong>);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function cells(row) {
  return row.replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

export default function SimpleMd({ md, className = "" }) {
  const lines = (md || "").split("\n");
  const out = [];
  let i = 0, k = 0;
  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (!t) { i++; continue; }
    if (t.startsWith("|") && lines[i + 1] && /^\|?[\s:|-]+\|?$/.test(lines[i + 1].trim())) {
      const header = cells(t);
      const body = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        body.push(cells(lines[i].trim()));
        i++;
      }
      out.push(
        <div key={k++} className="overflow-x-auto">
          <table className="my-2 w-full text-xs">
            <thead>
              <tr className="border-b border-line text-left text-dim">
                {header.map((h, j) => <th key={j} className="px-2 py-1.5 font-medium">{inline(h, `${k}h${j}`)}</th>)}
              </tr>
            </thead>
            <tbody>
              {body.map((r, ri) => (
                <tr key={ri} className="border-b border-line/50 align-top">
                  {r.map((c, ci) => <td key={ci} className="px-2 py-1.5 text-dim">{inline(c, `${k}b${ri}-${ci}`)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>);
      continue;
    }
    const h = t.match(/^(#{1,4})\s+(.*)/);
    if (h) {
      const cls = h[1].length <= 2
        ? "mt-4 text-sm font-semibold text-ink"
        : "mt-3 text-xs font-semibold text-ink";
      out.push(<div key={k++} className={cls}>{inline(h[2], `${k}t`)}</div>);
      i++;
      continue;
    }
    if (/^[-*]\s+/.test(t)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i++;
      }
      out.push(
        <ul key={k++} className="my-1.5 list-disc space-y-1 pl-5 text-xs text-dim">
          {items.map((it, j) => <li key={j}>{inline(it, `${k}l${j}`)}</li>)}
        </ul>);
      continue;
    }
    out.push(<p key={k++} className="my-1.5 text-xs leading-relaxed text-dim">{inline(t, `${k}p`)}</p>);
    i++;
  }
  return <div className={className}>{out}</div>;
}
