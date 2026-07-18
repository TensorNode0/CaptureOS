import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Save, Sparkles, RefreshCw } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { Spinner, Field, Pill } from "./ui";

/* Fillable, per-field accelerator application form.
   The schema lives on the venture_docs row's `content_json`:
     { kind: "acceleratorApplication",
       programName: "…",
       keyFacts: { Deadline: "…", Eligibility: "…", … },
       questions: [ { id, label, type, answer, tip } ] }
   Saving updates the whole schema back on the doc via PUT.

   For accelerators where the AI produced questions with tips, we render each
   question as its own labeled textarea/input plus the tip below. No free-form
   markdown editing — this is a form, not a document. */

const TYPE_TO_INPUT = { short: "input", url: "input", number: "input", long: "textarea" };


export default function AcceleratorForm({ orgId, doc, onSaved, onRedraft, redrafting }) {
  const schema = doc?.contentJson || {};
  const initialQuestions = useMemo(
    () => (Array.isArray(schema.questions) ? schema.questions : []),
    [schema.questions]);
  const [questions, setQuestions] = useState(initialQuestions);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    // Reset local edits when the underlying document changes (e.g. after
    // a redraft returns a fresh schema).
    setQuestions(initialQuestions);
    setDirty(false);
  }, [initialQuestions, doc?.id, doc?.updatedAt]);

  const updateAnswer = (idx, value) => {
    setQuestions((qs) => qs.map((q, i) => i === idx ? { ...q, answer: value } : q));
    setDirty(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      // Rebuild a plain-text markdown mirror so exports/downloads still work
      // for anyone reading only content_md (e.g. the .docx export path).
      const md = _renderMd(schema.programName || doc.title || "Application",
                           schema.keyFacts || {}, questions);
      const { data } = await api.put(`/orgs/${orgId}/venture-docs/${doc.id}`, {
        contentJson: { ...schema, questions },
        contentMd: md,
      });
      onSaved?.(data);
      toast.success("Application saved");
      setDirty(false);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  const keyFacts = schema.keyFacts || {};
  const shownFacts = Object.entries(keyFacts).filter(([, v]) => v);

  return (
    <div className="space-y-4" data-testid="accelerator-form">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 pb-3">
        <div>
          <div className="text-sm font-medium text-ink">
            {schema.programName || doc.title}
          </div>
          <div className="mt-0.5 text-[11px] text-faint">
            {questions.length} question{questions.length === 1 ? "" : "s"}
            {dirty && <span className="ml-2 text-warn">· unsaved changes</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onRedraft && (
            <button className="btn btn-ghost !py-1.5 !px-3 text-xs"
                    onClick={onRedraft} disabled={redrafting || saving}
                    data-testid="accel-form-redraft">
              {redrafting ? <Spinner size={12} /> : <RefreshCw size={13} />} Redraft with AI
            </button>
          )}
          <button className="btn btn-primary !py-1.5 !px-3 text-xs"
                  onClick={save} disabled={saving || !dirty}
                  data-testid="accel-form-save">
            {saving ? <Spinner size={12} /> : <Save size={13} />} Save
          </button>
        </div>
      </div>

      {shownFacts.length > 0 && (
        <div className="rounded-md border border-line/60 bg-white/5 p-3">
          <div className="mb-1.5 text-[10px] uppercase tracking-widest text-faint">Key facts</div>
          <div className="grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
            {shownFacts.map(([k, v]) => (
              <div key={k}>
                <span className="text-[11px] text-faint">{k}: </span>
                <span className="text-xs text-dim">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {questions.length === 0 ? (
        <div className="rounded-md border border-warn/30 bg-warn/10 p-3 text-xs text-warn">
          No structured questions were extracted. Click <b>Redraft with AI</b> to try again,
          or fall back to editing the markdown draft.
        </div>
      ) : (
        <div className="space-y-4">
          {questions.map((q, i) => (
            <div key={q.id || i} data-testid={`accel-form-q-${i}`}>
              <Field label={<span className="flex items-center gap-1.5">
                              <span>{q.label}</span>
                              {q.type && <Pill tone="neutral" className="!text-[9px] !py-0">{q.type}</Pill>}
                            </span>}
                     hint={q.tip ? <span className="flex items-start gap-1"><Sparkles size={11} className="mt-0.5 shrink-0 text-cyan" /> {q.tip}</span> : undefined}>
                {TYPE_TO_INPUT[q.type] === "input" ? (
                  <input className="field text-sm"
                         type={q.type === "number" ? "number" : q.type === "url" ? "url" : "text"}
                         value={q.answer || ""}
                         onChange={(e) => updateAnswer(i, e.target.value)}
                         data-testid={`accel-form-input-${i}`} />
                ) : (
                  <textarea className="field min-h-[110px] text-sm"
                            value={q.answer || ""}
                            onChange={(e) => updateAnswer(i, e.target.value)}
                            data-testid={`accel-form-input-${i}`} />
                )}
              </Field>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function _renderMd(name, keyFacts, questions) {
  const parts = [`# ${name} — Application draft\n`];
  const facts = Object.entries(keyFacts || {}).filter(([, v]) => v);
  if (facts.length) {
    parts.push("## Key facts");
    for (const [k, v] of facts) parts.push(`- **${k}:** ${v}`);
    parts.push("");
  }
  for (const q of questions || []) {
    parts.push(`## ${q.label || q.id || "Question"}`);
    parts.push(q.answer?.trim() || "[FILL]");
    if (q.tip) parts.push(`*Tip: ${q.tip}*`);
    parts.push("");
  }
  return parts.join("\n");
}
