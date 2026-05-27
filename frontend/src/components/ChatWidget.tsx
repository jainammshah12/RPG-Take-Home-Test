import { useEffect, useRef, useState } from "react";
import { sendChat } from "../api";
import type { ChatMessage } from "../types";
import { formatChatError } from "../utils";

const WELCOME =
  "Hi! I'm **LedgerLens Assistant**. Ask me about revenue, card spend, invoices, or receipts.";

const SUGGESTIONS = [
  "What's my net cash flow?",
  "Who are my top clients?",
  "Summarize my card spend",
  "Any outstanding invoices?",
];

type Props = { shoebox: string };

function renderSimpleMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

export function ChatWidget({ shoebox }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: WELCOME },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const send = async (text: string) => {
    if (!text.trim() || thinking) return;
    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    const history = messages.filter((m) => m.content !== WELCOME);
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setThinking(true);
    try {
      const { reply } = await sendChat(shoebox, text.trim(), history);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: formatChatError(e), isError: true } as ChatMessage & { isError?: boolean },
      ]);
    } finally {
      setThinking(false);
    }
  };

  return (
    <>
      {open && (
        <div className="chat-panel">
          <div className="chat-header">
            <div>
              <strong>LedgerLens Assistant</strong>
              <p className="chat-header-caption">Uses cached dashboard data</p>
            </div>
            <button
              type="button"
              className="chat-close-btn"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </div>

          <div className="chat-messages">
            {messages.map((msg, i) => {
              const isError = (msg as ChatMessage & { isError?: boolean }).isError;
              return (
                <div
                  key={i}
                  className={`chat-bubble ${msg.role}${isError ? " error" : ""}`}
                >
                  {renderSimpleMarkdown(msg.content)}
                </div>
              );
            })}
            {thinking && (
              <div className="chat-bubble assistant thinking">
                <span className="chat-dots">Thinking</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-suggestions">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                className="chat-suggest-chip"
                disabled={thinking}
                onClick={() => send(s)}
              >
                {s}
              </button>
            ))}
          </div>

          <form
            className="chat-input-row"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your finances…"
              disabled={thinking}
              aria-label="Chat message"
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={thinking || !input.trim()}
              aria-label="Send message"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </form>
        </div>
      )}

      <div className="chat-fab">
        <button type="button" className="chat-fab-btn" onClick={() => setOpen(!open)}>
          {open ? (
            <span aria-hidden="true">×</span>
          ) : (
            <>
              <span className="chat-fab-icon" aria-hidden="true">
                💬
              </span>
              Ask LedgerLens
            </>
          )}
        </button>
      </div>
    </>
  );
}
