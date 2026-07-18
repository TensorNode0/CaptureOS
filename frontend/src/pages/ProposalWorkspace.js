import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Sparkles, Save, Download, FileText, FileSpreadsheet,
  Presentation, Package, CheckCircle2, AlertTriangle, PencilLine, Gauge,
  Crosshair, ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card, SectionLabel, Pill, Spinner, PageReveal, EmptyState, Modal, Field } from "../components/ui";
import { canEdit, canCreateProposal, canSubmitProposal } from "../lib/helpers";
import AIButton from "../components/AIButton";
import AIChatButton from "../components/AIChatButton";
import OverleafPanel from "../components/OverleafPanel";
import FilesPanel from "../components/FilesPanel";
import {
  PEO_SOURCES, GOV_SECTORS, CIVIL_AGENCIES, DEFENSE_BRANCHES, IC_AGENCIES,
  COMMERCIAL_MARKETS,
} from "../lib/peoDirectory";

const FMT_META = {
  docx: { icon: FileText, label: "Word", tone: "cyan" },
  xlsx: { icon: FileSpreadsheet, label: "Excel", tone: "ok" },
  pptx: { icon: Presentation, label: "PowerPoint", tone: "violet" },
};

const STATUS_META = {
  empty: { tone: "neutral", label: "Not drafted" },
  drafted: { tone: "cyan", label: "AI draft" },
  edited: { tone: "warn", label: "Edited" },
  final: { tone: "ok", label: "Final" },
};

function downloadBlob(data, filename) {
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ProposalWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { activeOrgId, activeOrg } = useAuth();
  const editor = canEdit(activeOrg?.role);
  const cm = canCreateProposal(activeOrg?.role);
  const admin = canSubmitProposal(activeOrg?.role);
  const [opp, setOpp] = useState(null);
  const [proposal, setProposal] = useState(undefined);
  const [busy, setBusy] = useState("");
  const [editDoc, setEditDoc] = useState(null);

  const load = useCallback(async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/opportunities/${id}/proposal`);
    setProposal(data);
    return data;
  }, [activeOrgId, id]);

  useEffect(() => {
    if (!activeOrgId) return;
    api.get(`/orgs/${activeOrgId}/opportunities/${id}`).then((r) => setOpp(r.data))
      .catch((e) => { toast.error(errMsg(e)); navigate("/opportunities"); });
    load().catch((e) => toast.error(errMsg(e)));
  }, [activeOrgId, id, load, navigate]);

  const anyDrafting = (proposal?.documents || []).some((d) => d.draftStatus === "drafting");

  useEffect(() => {
    if (!anyDrafting) return undefined;
    const timer = setInterval(async () => {
      try {
        const data = await load();
        const still = (data?.documents || []).some((d) => d.draftStatus === "drafting");
        if (!still) {
          const errs = (data?.documents || []).filter((d) => d.draftStatus === "error");
          if (errs.length) toast.error(errs[0].draftError || "A draft failed");
          else toast.success("Draft complete");
        }
      } catch { /* keep polling */ }
    }, 4000);
    return () => clearInterval(timer);
  }, [anyDrafting, load]);

  const createPackage = async () => {
    setBusy("create");
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/${id}/proposal`);
      setProposal(data);
      toast.success("Proposal package created for this solicitation");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const draft = (doc) => async ({ engine: eng, model, effort }) => {
    const { data } = await api.post(
      `/orgs/${activeOrgId}/opportunities/${id}/proposal/documents/${doc.id}/draft`,
      { engine: eng, model: model || "", effort: effort || "standard" });
    await load();
    return data; // jobId powers the telemetry panel
  };

  const finalize = async (doc) => {
    setBusy(`final-${doc.id}`);
    try {
      await api.post(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/documents/${doc.id}/finalize`);
      await load();
      toast.success(`${doc.title} marked final`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const download = async (doc) => {
    setBusy(`dl-${doc.id}`);
    try {
      const r = await api.get(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/documents/${doc.id}/download`,
        { responseType: "blob", timeout: 60000 });
      downloadBlob(r.data, `${doc.title.replace(/\s+/g, "_")}.${doc.fmt}`);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  const downloadZip = async () => {
    setBusy("zip");
    try {
      const r = await api.get(
        `/orgs/${activeOrgId}/opportunities/${id}/proposal/download-zip`,
        { responseType: "blob", timeout: 120000 });
      downloadBlob(r.data, `Proposal_Package_${opp?.solNumber || "package"}.zip`);
    } catch (e) {
      // blob error responses need decoding
      try {
        const text = await e.response.data.text();
        toast.error(JSON.parse(text).detail || "Download failed");
      } catch { toast.error(errMsg(e)); }
    }
    finally { setBusy(""); }
  };

  const evaluate = async ({ engine: eng, model, effort }) => {
    const { data } = await api.post(
      `/orgs/${activeOrgId}/opportunities/${id}/proposal/evaluate`,
      { engine: eng, model: model || "", effort: effort || "standard" });
    return data; // jobId — panel streams progress; onDone reloads the report
  };

  const reloadProposal = async () => {
    const { data } = await api.get(`/orgs/${activeOrgId}/opportunities/${id}/proposal`);
    setProposal(data);
  };

  const markSubmitted = async () => {
    if (!window.confirm("Mark this proposal package as submitted to the government? "
        + "This sets the opportunity stage to Submitted.")) return;
    setBusy("submit");
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/opportunities/${id}/proposal/submit`);
      setProposal(data);
      toast.success("Proposal marked as submitted");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(""); }
  };

  if (!opp || proposal === undefined) {
    return <div className="flex h-64 items-center justify-center"><Spinner size={26} className="text-cyan" /></div>;
  }

  const docs = proposal?.documents || [];
  const drafted = docs.filter((d) => d.status !== "empty").length;

  return (
    <PageReveal className="space-y-5">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <button onClick={() => navigate(`/opportunities/${id}`)}
            className="mb-2 inline-flex items-center gap-1.5 text-sm text-dim hover:text-cyan"
            data-testid="back-to-opportunity">
            <ArrowLeft size={15} /> {opp.title}
          </button>
          <h1 className="flex flex-wrap items-center gap-3 text-2xl font-semibold text-ink">
            Proposal Package
            {proposal && <Pill tone="cyan">{drafted}/{docs.length} drafted</Pill>}
            {proposal?.status === "submitted" && <Pill tone="ok">Submitted</Pill>}
          </h1>
          <div className="mt-1 text-sm text-faint">
            <span className="mono">{opp.solNumber || "—"}</span> · {opp.agency} · {opp.vehicle}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn btn-ghost" onClick={() => navigate(`/opportunities/${id}/capability`)}
            data-testid="goto-capability">
            <Sparkles size={15} /> Capability
          </button>
          {/* engine/model/effort now live on each Draft button (AIButton) */}
          {proposal && drafted > 0 && (
            <button className="btn btn-primary" onClick={downloadZip} disabled={busy === "zip"}
              data-testid="download-zip">
              {busy === "zip" ? <Spinner /> : <Package size={15} />} Download package (.zip)
            </button>
          )}
          {admin && proposal && drafted > 0 && proposal.status !== "submitted" && (
            <button className="btn btn-violet" onClick={markSubmitted} disabled={busy === "submit"}
              data-testid="mark-submitted">
              {busy === "submit" ? <Spinner /> : <CheckCircle2 size={15} />} Mark as Submitted
            </button>
          )}
        </div>
      </div>

      {!proposal && (
        <Card className="p-6">
          <EmptyState icon={Package} title="No proposal package yet"
            subtitle={`Creates the volume set for a ${opp.vehicle} solicitation — each volume gets a one-click AI draft button, human review/editing, and Word/Excel/PowerPoint export.`}
            action={cm ? (
              <button className="btn btn-primary" onClick={createPackage} disabled={busy === "create"}
                data-testid="create-proposal">
                {busy === "create" ? <Spinner /> : <Package size={16} />} Create proposal package
              </button>
            ) : (
              <span className="text-xs text-faint">Your capture manager creates the proposal package.</span>
            )} />
        </Card>
      )}

      {proposal && (
        <CustomerCard proposal={proposal} setProposal={setProposal}
          orgId={activeOrgId} oppId={id} editor={editor} />
      )}

      {proposal && (
        <OverleafPanel orgId={activeOrgId} proposal={proposal}
          canEdit={editor}
          onSynced={(fresh) => setProposal((p) => ({ ...p, ...fresh }))} />
      )}

      {proposal && (
        <FilesPanel orgId={activeOrgId} mode="entity"
          entityType="proposal" entityId={proposal.id}
          label="Attached files (SoW, WBS, schedule, budget, tech volume, past proposals — extracted text feeds AI redrafts)"
          canEdit={editor} testid="proposal-files" />
      )}

      {proposal && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {docs.map((doc) => {
            const fmt = FMT_META[doc.fmt] || FMT_META.docx;
            const st = STATUS_META[doc.status] || STATUS_META.empty;
            const drafting = doc.draftStatus === "drafting";
            const FmtIcon = fmt.icon;
            return (
              <Card key={doc.id} hover className="flex flex-col p-5" data-testid={`doc-${doc.docType}`}>
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="rounded-xl border border-line bg-white/5 p-2">
                      <FmtIcon size={18} className="text-cyan" />
                    </div>
                    <div>
                      <div className="font-medium text-ink">{doc.title}</div>
                      <div className="mono text-[10px] uppercase tracking-widest text-faint">
                        {fmt.label} · .{doc.fmt}
                      </div>
                    </div>
                  </div>
                  <Pill tone={st.tone}>{st.label}</Pill>
                </div>

                {doc.draftStatus === "error" && (
                  <div className="mb-2 flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-2 text-xs text-bad">
                    <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {doc.draftError}
                  </div>
                )}
                {doc.model && (
                  <div className="mb-2 text-[11px] text-faint">Last draft: {doc.model}</div>
                )}

                <div className="mt-auto flex flex-wrap gap-1.5 pt-2">
                  {editor && (
                    <AIButton orgId={activeOrgId} compact
                      label={drafting ? "Drafting…" : doc.status === "empty" ? "Draft with AI" : "Redraft"}
                      onStart={draft(doc)} onDone={load}
                      disabled={drafting} testid={`draft-${doc.docType}`} />
                  )}
                  {editor && doc.status !== "empty" && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => setEditDoc(doc)}
                      data-testid={`edit-${doc.docType}`}>
                      <PencilLine size={13} /> Review & edit
                    </button>
                  )}
                  {doc.status !== "empty" && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => download(doc)}
                      disabled={busy === `dl-${doc.id}`} data-testid={`download-${doc.docType}`}>
                      {busy === `dl-${doc.id}` ? <Spinner size={13} /> : <Download size={13} />} Download
                    </button>
                  )}
                  {editor && (doc.status === "drafted" || doc.status === "edited") && !drafting && (
                    <button className="btn btn-ghost px-3 py-1.5 text-xs" onClick={() => finalize(doc)}
                      data-testid={`finalize-${doc.docType}`}>
                      <CheckCircle2 size={13} /> Finalize
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {proposal && drafted > 0 && (
        <Card className="p-5" data-testid="evaluation-section">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <SectionLabel>AI Evaluation</SectionLabel>
              <p className="mt-1 text-xs text-faint">
                A source-selection-board color review of the drafted package —
                scores, strengths, weaknesses, risks, and the edits that raise your score.
              </p>
            </div>
            {editor && (
              <AIButton orgId={activeOrgId} icon={Gauge}
                label={proposal.evaluation ? "Re-evaluate with AI" : "Evaluate with AI"}
                onStart={evaluate} onDone={reloadProposal}
                disabled={drafted < docs.length}
                disabledReason={drafted < docs.length
                  ? `Finish every volume first — ${docs.length - drafted} still empty. The AI evaluates the complete package.`
                  : ""}
                testid="evaluate-proposal" />
            )}
          </div>

          {proposal.evaluation && (
            <div className="mt-4 space-y-4" data-testid="evaluation-report">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-baseline gap-2">
                  <span className="mono text-4xl font-semibold text-cyan">{proposal.evaluation.overallScore}</span>
                  <span className="text-xs text-faint">/ 100</span>
                </div>
                {proposal.evaluation.colorReview && (
                  <Pill tone={{ pink: "violet", red: "warn", gold: "ok" }[proposal.evaluation.colorReview] || "neutral"}>
                    {proposal.evaluation.colorReview} team
                  </Pill>
                )}
                <span className="text-sm text-dim">{proposal.evaluation.verdict}</span>
              </div>

              {Array.isArray(proposal.evaluation.factors) && (
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                  {proposal.evaluation.factors.map((f, i) => (
                    <div key={i} className="rounded-lg border border-line bg-white/5 p-3">
                      <div className="mono text-lg text-ink">{f.score}</div>
                      <div className="text-xs font-medium text-dim">{f.name}</div>
                      <div className="mt-1 text-[11px] leading-snug text-faint">{f.note}</div>
                    </div>
                  ))}
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <div className="label-mono mb-1.5 text-ok">Strengths</div>
                  {(proposal.evaluation.strengths || []).map((s, i) => (
                    <div key={i} className="mb-1 text-xs leading-relaxed text-dim">▲ {s}</div>
                  ))}
                </div>
                <div>
                  <div className="label-mono mb-1.5 text-warn">Weaknesses</div>
                  {(proposal.evaluation.weaknesses || []).map((s, i) => (
                    <div key={i} className="mb-1 text-xs leading-relaxed text-dim">▽ {s}</div>
                  ))}
                </div>
              </div>

              {(proposal.evaluation.risks || []).length > 0 && (
                <div>
                  <div className="label-mono mb-1.5">Risks</div>
                  {(proposal.evaluation.risks || []).map((r, i) => (
                    <div key={i} className="mb-1 text-xs leading-relaxed text-dim">
                      <Pill tone={{ high: "bad", medium: "warn", low: "neutral" }[r.severity] || "neutral"}>{r.severity}</Pill>{" "}
                      {r.risk} <span className="text-faint">— {r.mitigation}</span>
                    </div>
                  ))}
                </div>
              )}

              {(proposal.evaluation.complianceGaps || []).length > 0 && (
                <div>
                  <div className="label-mono mb-1.5 text-bad">Compliance gaps</div>
                  {(proposal.evaluation.complianceGaps || []).map((g, i) => (
                    <div key={i} className="mb-1 text-xs leading-relaxed text-dim">✕ {g}</div>
                  ))}
                </div>
              )}

              {(proposal.evaluation.recommendations || []).length > 0 && (
                <div className="rounded-lg border border-cyan/30 bg-cyan/5 p-3">
                  <div className="label-mono mb-1.5 text-cyan">Do these next</div>
                  {(proposal.evaluation.recommendations || []).map((r, i) => (
                    <div key={i} className="mb-1 text-xs leading-relaxed text-dim">{i + 1}. {r}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      <DocEditor doc={editDoc} onClose={() => setEditDoc(null)} orgId={activeOrgId} oppId={id}
        onSaved={async () => { setEditDoc(null); await load(); }} />

      {proposal && (
        <AIChatButton
          contextTitle={`Federal Proposal · ${opp.title}`}
          contextText={
            `Solicitation: ${opp.solNumber || "—"} · Agency: ${opp.agency || "—"}\n\n` +
            (proposal.documents || []).map((d) =>
              `--- ${d.title} (${d.status}) ---\n${d.contentMd || "(empty)"}`).join("\n\n").slice(0, 55000)
          }
          suggestions={[
            "Tighten the executive summary volume.",
            "Draft a compliance matrix for the SOW.",
            "Flag risky claims that need proof.",
          ]}
        />
      )}
    </PageReveal>
  );
}

/* Who the proposal serves: commercial market + government customer down to
   the PEO, TPOC, and contracting officer — with an AI directory-currency
   check against the Stanford Gordian Knot 2026 PEO directory. */
function CustomerCard({ proposal, setProposal, orgId, oppId, editor }) {
  const saved = proposal.customer || {};
  const [form, setForm] = useState(saved);
  const [saving, setSaving] = useState(false);
  useEffect(() => { setForm(proposal.customer || {}); }, [proposal.customer]);

  const set = (k) => (e) => {
    const v = e.target.value;
    setForm((f) => {
      const next = { ...f, [k]: v };
      if (k === "sector") { next.branch = ""; next.agency = ""; next.peo = ""; }
      if (k === "branch") next.peo = "";
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put(
        `/orgs/${orgId}/opportunities/${oppId}/proposal/customer`, {
          commercialMarket: form.commercialMarket || "",
          sector: form.sector || "", branch: form.branch || "",
          agency: form.agency || "", peo: form.peo || "",
          tpoc: form.tpoc || "", contractingOfficer: form.contractingOfficer || "",
        });
      setProposal(data);
      toast.success("Customer saved");
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  const check = async ({ engine, model, effort }) => {
    const { data } = await api.post(
      `/orgs/${orgId}/opportunities/${oppId}/proposal/customer/check`,
      { engine: engine || "claude", model: model || "", effort: effort || "standard" });
    return data; // jobId → telemetry panel
  };

  const reload = async () => {
    const { data } = await api.get(`/orgs/${orgId}/opportunities/${oppId}/proposal`);
    setProposal(data);
  };

  const check_ = saved.aiCheck;
  const isDefense = form.sector === "Defense";
  const isIC = form.sector === "Intelligence Community";
  const isCivil = form.sector === "Civil";
  const dirty = JSON.stringify(form) !== JSON.stringify(saved);

  return (
    <Card className="p-5" data-testid="customer-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionLabel>Customer</SectionLabel>
          <p className="mt-1 max-w-2xl text-xs text-faint">
            Who this proposal serves — the commercial market and the government
            customer down to the program executive office, TPOC, and contracting
            officer. Defense/IC structure follows the{" "}
            {PEO_SOURCES.map((s, i) => (
              <span key={s.href}>{i > 0 ? " · " : ""}
                <a href={s.href} target="_blank" rel="noreferrer" className="text-cyan hover:underline">
                  {i === 0 ? "Stanford 2026 PEO Directory" : i === 1 ? "SVDG DoW Directory" : "Steve Blank's guide"}
                </a>
              </span>
            ))}.
          </p>
        </div>
        {check_ && (
          <div className="text-right">
            <Pill tone={check_.upToDate ? "ok" : "warn"} data-testid="peo-check-pill">
              <Crosshair size={11} /> {check_.upToDate ? "Up to date" : "Outdated"}
            </Pill>
            <div className="mt-1 max-w-[280px] text-[11px] leading-snug text-faint">
              {check_.note}{" "}
              {check_.source && (
                <a href={check_.source} target="_blank" rel="noreferrer"
                   className="text-cyan hover:underline">source <ExternalLink size={9} className="inline" /></a>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Field label="Commercial market / user" hint="Dual-use matters — pick or type your own.">
          <input className="field" value={form.commercialMarket || ""} onChange={set("commercialMarket")}
            list="commercial-markets" placeholder="e.g. Critical infrastructure security"
            disabled={!editor} data-testid="customer-market" />
          <datalist id="commercial-markets">
            {COMMERCIAL_MARKETS.map((m) => <option key={m} value={m} />)}
          </datalist>
        </Field>
        <Field label="Government sector">
          <select className="field" value={form.sector || ""} onChange={set("sector")}
            disabled={!editor} data-testid="customer-sector">
            <option value="">Select sector…</option>
            {GOV_SECTORS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </Field>
        {isDefense && (
          <Field label="Branch">
            <select className="field" value={form.branch || ""} onChange={set("branch")}
              disabled={!editor} data-testid="customer-branch">
              <option value="">Select branch…</option>
              {Object.keys(DEFENSE_BRANCHES).map((b) => <option key={b}>{b}</option>)}
            </select>
          </Field>
        )}
        {isDefense && form.branch && (
          <Field label="Program Executive Office">
            <select className="field" value={form.peo || ""} onChange={set("peo")}
              disabled={!editor} data-testid="customer-peo">
              <option value="">Select PEO…</option>
              {(DEFENSE_BRANCHES[form.branch] || []).map((p) => <option key={p}>{p}</option>)}
            </select>
          </Field>
        )}
        {(isIC || isCivil) && (
          <Field label="Agency">
            <select className="field" value={form.agency || ""} onChange={set("agency")}
              disabled={!editor} data-testid="customer-agency">
              <option value="">Select agency…</option>
              {(isIC ? IC_AGENCIES : CIVIL_AGENCIES).map((a) => <option key={a}>{a}</option>)}
            </select>
          </Field>
        )}
        {(form.sector || "") !== "" && (
          <>
            <Field label="TPOC (technical point of contact)">
              <input className="field" value={form.tpoc || ""} onChange={set("tpoc")}
                placeholder="Name · office · email" disabled={!editor} data-testid="customer-tpoc" />
            </Field>
            <Field label="Contracting officer">
              <input className="field" value={form.contractingOfficer || ""} onChange={set("contractingOfficer")}
                placeholder="Name · office · email" disabled={!editor} data-testid="customer-co" />
            </Field>
          </>
        )}
      </div>

      {editor && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className="btn btn-primary" onClick={save} disabled={saving || !dirty}
            data-testid="customer-save">
            {saving ? <Spinner /> : <Save size={14} />} Save customer
          </button>
          {(saved.peo || saved.agency) && (
            <AIButton orgId={orgId} compact icon={Crosshair}
              label="Check directory currency"
              note="Anthropic checks the live PEO directory; other engines answer from model knowledge."
              onStart={check} onDone={reload} testid="peo-check" />
          )}
        </div>
      )}
    </Card>
  );
}

function DocEditor({ doc, onClose, orgId, oppId, onSaved }) {
  const [md, setMd] = useState("");
  const [json, setJson] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (doc) {
      setMd(doc.contentMd || "");
      setJson(doc.contentJson || {});
    }
  }, [doc]);

  if (!doc) return null;

  const save = async () => {
    setSaving(true);
    try {
      const body = doc.fmt === "docx" ? { contentMd: md } : { contentJson: json };
      await api.put(`/orgs/${orgId}/opportunities/${oppId}/proposal/documents/${doc.id}`, body);
      toast.success(`${doc.title} saved`);
      await onSaved();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setSaving(false); }
  };

  return (
    <Modal open={!!doc} onClose={onClose} title={`Edit — ${doc.title}`} maxW="max-w-4xl">
      {doc.fmt === "docx" && (
        <Field label="Content (markdown — exported to Word)">
          <textarea className="field mono min-h-[420px] text-[13px]" value={md}
            onChange={(e) => setMd(e.target.value)} data-testid="doc-editor-md" />
        </Field>
      )}
      {doc.fmt === "xlsx" && (
        <CostEditor json={json} setJson={setJson} />
      )}
      {doc.fmt === "pptx" && (
        <DeckEditor json={json} setJson={setJson} />
      )}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={save} disabled={saving} data-testid="doc-editor-save">
          {saving ? <Spinner /> : <Save size={15} />} Save
        </button>
      </div>
    </Modal>
  );
}

function CostEditor({ json, setJson }) {
  const rows = json?.rows || [];
  const total = rows.reduce((s, r) => s + (Number(r.cost) || 0), 0);
  const setRow = (i, patch) => {
    const next = [...rows];
    next[i] = { ...next[i], ...patch };
    setJson({ ...json, rows: next });
  };
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <SectionLabel>Cost lines</SectionLabel>
        <div className="mono text-sm text-ink">Total: ${total.toLocaleString()}</div>
      </div>
      <div className="max-h-[380px] overflow-y-auto rounded-xl border border-line">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-[var(--bg-elev)]">
            <tr className="text-left text-xs text-dim">
              <th className="p-2">Category</th><th className="p-2">Item</th>
              <th className="p-2">Basis</th><th className="p-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-line/50">
                <td className="p-1.5"><input className="field py-1 text-xs" value={r.category || ""}
                  onChange={(e) => setRow(i, { category: e.target.value })} /></td>
                <td className="p-1.5"><input className="field py-1 text-xs" value={r.item || ""}
                  onChange={(e) => setRow(i, { item: e.target.value })} /></td>
                <td className="p-1.5"><input className="field py-1 text-xs" value={r.basis || ""}
                  onChange={(e) => setRow(i, { basis: e.target.value })} /></td>
                <td className="p-1.5"><input type="number" className="field w-28 py-1 text-right text-xs"
                  value={r.cost ?? 0} onChange={(e) => setRow(i, { cost: Number(e.target.value) || 0 })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Field label="Cost narrative">
        <textarea className="field min-h-[90px] text-sm" value={json?.narrative || ""}
          onChange={(e) => setJson({ ...json, narrative: e.target.value })} />
      </Field>
    </div>
  );
}

function DeckEditor({ json, setJson }) {
  const slides = json?.slides || [];
  const setSlide = (i, patch) => {
    const next = [...slides];
    next[i] = { ...next[i], ...patch };
    setJson({ ...json, slides: next });
  };
  return (
    <div className="max-h-[460px] space-y-3 overflow-y-auto pr-1">
      {slides.map((s, i) => (
        <div key={i} className="rounded-xl border border-line bg-white/[0.02] p-3">
          <div className="mb-1.5 flex items-center gap-2">
            <Pill tone="violet">Slide {i + 1}</Pill>
            <input className="field flex-1 py-1 text-sm font-medium" value={s.title || ""}
              onChange={(e) => setSlide(i, { title: e.target.value })} />
          </div>
          <textarea className="field mono min-h-[70px] text-xs"
            value={(s.bullets || []).join("\n")}
            onChange={(e) => setSlide(i, { bullets: e.target.value.split("\n") })}
            placeholder="One bullet per line" />
        </div>
      ))}
    </div>
  );
}
