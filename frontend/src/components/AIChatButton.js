import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { MessageSquare, X, Send, Sparkles, RefreshCw } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useSubscription, hasTier } from "../lib/billing";
import { Spinner } from "./ui";

/* Reusable AI chat drawer bound to any workspace document.
   Usage:
     <AIChatButton
        contextTitle="Federal Proposal · Technical Volume"
        contextText={proposalMd}
        suggestions={["Tighten the executive summary", "Draft a compliance matrix"]}
     />
   - Engine dropdown (OpenAI / Anthropic / Gemini / Emergent / AskSage) driven
     by /ai/options — only configured engines are selectable.
   - Message history is kept in-memory per drawer instance; closing loses it.
   - Server is stateless: we re-send the full transcript every turn. */
const STORAGE_PREFIX = "captureagent.chat.engine";

export default function AIChatButton({ contextTitle = "", contextText = "",
                                       suggestions = [] }) {
  const { activeOrgId } = useAuth();
  const { sub } = useSubscription();
  // AI chat is a Full-plan feature. Hide the launcher entirely for lower
  // tiers so the pricing story stays honest — users on OI/free won't see
  // the button at all and can't discover it accidentally.
  const isFull = hasTier(sub, "full");
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);      // {role, content}
  const [engines, setEngines] = useState([]);
  const [engine, setEngine] = useState("");
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!activeOrgId || !open) return;
    let cancelled = false;
    (async () => {
      try {
        const { data: opts } = await api.get(`/orgs/${activeOrgId}/ai/options`);
        if (cancelled) return;
        setEngines(opts.engines || []);
        const stored = localStorage.getItem(`${STORAGE_PREFIX}.${activeOrgId}`);
        const pick = (id) => (opts.engines || []).some((e) => e.id === id && e.configured) && id;
        setEngine(pick(stored) || pick("claude") || pick("openai") || pick("gemini") ||
                  (opts.engines || []).find((e) => e.configured)?.id || "");
      } catch {/* silent — the drawer will show 'no keys' hint */}
    })();
    return () => { cancelled = true; };
  }, [activeOrgId, open]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, sending]);

  const chosen = engines.find((e) => e.id === engine);
  const configured = engines.filter((e) => e.configured);
  const anyConfigured = configured.length > 0;

  const send = async (text) => {
    const trimmed = (text ?? input).trim();
    if (!trimmed || sending || !engine) return;
    setInput("");
    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setSending(true);
    try {
      const { data } = await api.post(`/orgs/${activeOrgId}/ai/chat`, {
        engine, model: "",
        contextTitle: contextTitle.slice(0, 200),
        contextText: (contextText || "").slice(0, 60000),
        messages: nextMessages,
      });
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      localStorage.setItem(`${STORAGE_PREFIX}.${activeOrgId}`, engine);
    } catch (e) {
      toast.error(errMsg(e));
      setMessages((m) => m.slice(0, -1));   // roll back the user bubble on failure
    } finally { setSending(false); }
  };

  // Full-plan-only feature — hide entirely for lower tiers.
  if (!isFull) return null;

  return (
    <>
      {/* Floating trigger */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full border border-cyan/40 bg-cyan/10 px-4 py-2.5 text-sm font-medium text-cyan shadow-lg backdrop-blur transition hover:bg-cyan/20"
        data-testid="ai-chat-open"
        title="AI chat about this document"
      >
        <MessageSquare size={16} /> Ask AI
      </button>

      {open && (
        <div className="fixed inset-0 z-50" data-testid="ai-chat-drawer">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <aside
            className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col border-l border-line px-4 py-4 shadow-2xl"
            style={{ background: "var(--bg-elev)" }}
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-medium text-ink">
                <Sparkles size={15} className="text-cyan" />
                AI assistant
                {contextTitle && <span className="ml-1 text-[11px] text-faint">· {contextTitle}</span>}
              </div>
              <div className="flex items-center gap-2">
                {messages.length > 0 && (
                  <button
                    onClick={() => setMessages([])}
                    className="text-faint hover:text-ink"
                    aria-label="Clear conversation"
                    title="Clear conversation"
                    data-testid="ai-chat-reset"
                  >
                    <RefreshCw size={14} />
                  </button>
                )}
                <button onClick={() => setOpen(false)} className="text-faint hover:text-ink"
                        data-testid="ai-chat-close" aria-label="Close chat">
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="mb-2 flex items-center gap-2 text-xs text-faint">
              <label htmlFor="ai-chat-engine" className="shrink-0">Engine</label>
              <select id="ai-chat-engine"
                      className="field mono !py-1 !text-xs"
                      value={engine}
                      onChange={(e) => setEngine(e.target.value)}
                      data-testid="ai-chat-engine"
                      disabled={!anyConfigured}>
                {engines.length === 0 && <option value="">Loading engines…</option>}
                {engines.map((e) => (
                  <option key={e.id} value={e.id} disabled={!e.configured}>
                    {e.label}{e.configured ? "" : " (no key)"}
                  </option>
                ))}
              </select>
              {chosen?.configured === false && anyConfigured && (
                <span className="text-warn">Switch to a configured engine</span>
              )}
            </div>

            {!anyConfigured && (
              <div className="mb-2 rounded-md border border-warn/30 bg-warn/10 p-2 text-xs text-warn"
                   data-testid="ai-chat-no-keys">
                No AI keys configured for this org. Add one in Settings → API Keys.
              </div>
            )}

            {/* Scrollback */}
            <div ref={scrollRef}
                 className="flex-1 space-y-2 overflow-y-auto rounded-md border border-line/60 bg-black/20 p-3 text-sm"
                 data-testid="ai-chat-scroll">
              {messages.length === 0 && (
                <div className="text-xs text-faint">
                  Ask a question about the document, or pick a suggestion below.
                  Context is sent automatically so the assistant can reason over what you see.
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
                     data-testid={`ai-chat-msg-${m.role}-${i}`}>
                  <div className={`max-w-[90%] whitespace-pre-wrap rounded-lg px-3 py-2 text-xs leading-relaxed ${
                                     m.role === "user"
                                       ? "bg-cyan/15 text-ink"
                                       : "bg-white/5 text-dim"}`}>
                    {m.content}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-lg bg-white/5 px-3 py-2 text-xs text-faint">
                    <Spinner size={12} /> thinking…
                  </div>
                </div>
              )}
            </div>

            {suggestions.length > 0 && messages.length === 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {suggestions.map((s, i) => (
                  <button key={i}
                          onClick={() => send(s)}
                          className="rounded-full border border-line/60 bg-white/5 px-2.5 py-1 text-[11px] text-dim hover:bg-white/10"
                          data-testid={`ai-chat-suggest-${i}`}
                          disabled={!engine || sending}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            <div className="mt-2 flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
                }}
                rows={2}
                placeholder={anyConfigured ? "Ask about this document…" : "Add an AI key in Settings first."}
                className="field flex-1 text-sm"
                data-testid="ai-chat-input"
                disabled={!engine || sending}
              />
              <button className="btn btn-primary !px-3"
                      onClick={() => send()}
                      disabled={!engine || sending || !input.trim()}
                      data-testid="ai-chat-send">
                {sending ? <Spinner /> : <Send size={14} />}
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
