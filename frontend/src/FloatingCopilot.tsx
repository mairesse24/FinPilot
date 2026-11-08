import { useEffect, useRef, useState } from "react";
import { MessageSquareText, X, Send } from "lucide-react";
import { useFinancialWorkspace } from "./FinancialWorkspace";
import { API_BASE } from "./api";
import ChatRichText from "./ChatRichText";

export type Delivery = {
  mode: "live" | "offline" | "fallback";
  provider: string;
  model?: string | null;
  code?: string | null;
  message: string;
};
export function DeliveryStatus({ delivery }: { delivery: Delivery }) {
  return (
    <div
      className={`chat-delivery ${delivery.mode === "fallback" ? "delivery-warning" : ""}`}
      role="status"
    >
      <strong>
        {delivery.mode === "live"
          ? `Live ${delivery.provider === "openai" ? "OpenAI" : delivery.provider === "gemini" ? "Gemini" : delivery.provider}`
          : delivery.mode === "fallback"
            ? "Live AI unavailable — local response"
            : "Local calculation-based assistant"}
      </strong>
      <p>{delivery.message}</p>
      {delivery.code === "quota_exhausted" && (
        <a
          href="https://platform.openai.com/settings/organization/billing/overview"
          target="_blank"
          rel="noreferrer"
        >
          Review API billing
        </a>
      )}
    </div>
  );
}
type Message = { role: "user" | "assistant"; content: string; delivery?: Delivery };

export default function FloatingCopilot() {
  const { confirmedFacts, scope } = useFinancialWorkspace();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const thread = useRef<HTMLDivElement>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const previousScope = useRef(scope);
  useEffect(() => {
    if (previousScope.current && scope && previousScope.current !== scope) {
      activeRequest.current?.abort();
      activeRequest.current = null;
      setMessages([]);
      setQuestion("");
      setError("");
      setBusy(false);
      setOpen(false);
    }
    previousScope.current = scope;
  }, [scope]);
  useEffect(() => () => activeRequest.current?.abort(), []);
  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);
  useEffect(() => {
    if (thread.current) thread.current.scrollTop = thread.current.scrollHeight;
  }, [messages, busy]);
  const close = () => {
    setOpen(false);
    button.current?.focus();
  };
  useEffect(() => {
    if (!open) return;
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !document.querySelector("dialog[open]")) close();
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [open]);
  const send = async () => {
    if (!question.trim() || busy) return;
    const next: Message[] = [...messages, { role: "user", content: question.trim() }];
    setMessages(next);
    setQuestion("");
    setBusy(true);
    setError("");
    const controller = new AbortController();
    activeRequest.current = controller;
    const timer = window.setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        cache: "no-store",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: next.slice(-20).map(({ role, content }) => ({ role, content })),
          financial_facts: confirmedFacts ?? undefined,
        }),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "The request could not be completed. Check confirmed inputs and try again.",
        );
      if (activeRequest.current === controller)
        setMessages([
          ...next,
          { role: "assistant", content: result.reply, delivery: result.delivery },
        ]);
    } catch (e) {
      if (activeRequest.current === controller)
        setError(
          controller.signal.aborted
            ? "The response took too long. Try again; this does not establish an invalid API key."
            : (e as Error).message,
        );
    } finally {
      window.clearTimeout(timer);
      if (activeRequest.current === controller) {
        setBusy(false);
        activeRequest.current = null;
      }
    }
  };
  return (
    <>
      <button
        ref={button}
        className="copilot-floating"
        aria-label="Open FinPilot chat"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <MessageSquareText size={20} />
      </button>
      {open && (
        <aside
          className="copilot-window"
          role="dialog"
          aria-modal="false"
          aria-label="FinPilot chat"
          onKeyDown={(e) => {
            if (e.key === "Escape") close();
          }}
        >
          <header>
            <div>
              <h2>FinPilot Copilot</h2>
              <small>Your accounts. Verified calculations.</small>
            </div>
            <button aria-label="Close FinPilot chat" onClick={close}>
              <X size={18} />
            </button>
          </header>
          <div className="chat-scope">
            {confirmedFacts ? (
              "Using your confirmed financial inputs for this session."
            ) : (
              <>
                Using your imported financial records.{" "}
                <a href="#/health-score">Review or refine your score</a>.
              </>
            )}
          </div>
          <div className="chat-thread" ref={thread} aria-live="polite">
            {!messages.length && (
              <div className="chat-welcome">
                <h3>What would you like to understand?</h3>
                <p>
                  Ask about your balances, upcoming bills, financial health or a hypothetical
                  spending change.
                </p>
                <button
                  onClick={() =>
                    setQuestion("Explain my financial health score and what is missing.")
                  }
                >
                  Help me understand my score
                </button>
              </div>
            )}
            {messages.map((m, i) => (
              <article key={i} className={`chat-message chat-${m.role}`}>
                <strong>{m.role === "user" ? "You" : "FinPilot"}</strong>
                <ChatRichText content={m.content} />
                {m.delivery && <DeliveryStatus delivery={m.delivery} />}
              </article>
            ))}
            {busy && <p role="status">Looking up your financial calculations...</p>}
            {error && (
              <p className="field-error" role="alert">
                {error}
              </p>
            )}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <label className="sr-only" htmlFor="floating-chat-question">
              Message FinPilot
            </label>
            <textarea
              id="floating-chat-question"
              ref={input}
              maxLength={2000}
              value={question}
              disabled={busy}
              placeholder="Ask a financial question..."
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button disabled={busy || !question.trim()} aria-label="Send FinPilot message">
              <Send size={18} />
            </button>
          </form>
          <small className="chat-footnote">
            Prototype estimates. No bank transactions can be executed.
          </small>
        </aside>
      )}
    </>
  );
}
