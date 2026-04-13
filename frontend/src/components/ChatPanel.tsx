"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { streamChat, type ChartData } from "@/lib/api";

const InlineChart = dynamic(() => import("./InlineChart"), { ssr: false });

interface MessagePart {
  type: "text" | "chart";
  content?: string;
  chart?: ChartData;
}

interface Message {
  role: "user" | "assistant";
  parts: MessagePart[];
}

function msgText(m: Message): string {
  return m.parts.filter(p => p.type === "text").map(p => p.content).join("");
}

const SUGGESTIONS = [
  "Can you give me a graph on race?",
  "Show me attendance by team",
  "Chart of students at risk vs OK",
  "Graph gender breakdown",
  "Which students need intervention?",
];

export default function ChatPanel({ onClose }: { onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      parts: [{
        type: "text",
        content: "Hi! I'm your Program IQ assistant. Ask me anything about your data — attendance, teams, demographics — or say **\"give me a graph\"** and I'll draw one right here in chat.",
      }],
    },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  async function send(text: string) {
    if (!text.trim() || streaming) return;
    setError("");

    const userMsg: Message = { role: "user", parts: [{ type: "text", content: text }] };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setStreaming(true);

    // Add placeholder assistant message
    const assistantMsg: Message = { role: "assistant", parts: [] };
    setMessages([...history, assistantMsg]);

    // Build plain-text history for API
    const apiHistory = history.map(m => ({
      role: m.role,
      content: msgText(m),
    }));

    try {
      for await (const event of streamChat(apiHistory)) {
        if (event.type === "error") {
          setError(event.message);
          break;
        }

        setMessages(prev => {
          const updated = [...prev];
          const last = { ...updated[updated.length - 1] };
          const parts = [...last.parts];

          if (event.type === "text") {
            // Append to last text part or create new one
            const lastPart = parts[parts.length - 1];
            if (lastPart?.type === "text") {
              parts[parts.length - 1] = { type: "text", content: (lastPart.content ?? "") + event.content };
            } else {
              parts.push({ type: "text", content: event.content });
            }
          } else if (event.type === "chart") {
            parts.push({ type: "chart", chart: event.chart });
          }

          last.parts = parts;
          updated[updated.length - 1] = last;
          return updated;
        });
      }
    } catch (e: any) {
      setError(e.message || "Chat failed. Check your OPENAI_API_KEY.");
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        if (last.parts.length === 0) {
          updated.pop(); // Remove empty assistant message
        }
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div
      className="fixed bottom-6 right-6 w-[440px] flex flex-col rounded-2xl overflow-hidden z-50"
      style={{
        background: "#13131f",
        border: "1px solid #252540",
        boxShadow: "0 24px 64px rgba(0,0,0,0.7)",
        height: "620px",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid #252540" }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
            style={{ background: "#7c3aed20", color: "#7c3aed" }}>
            🤖
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "#e2e8f0" }}>AI Assistant</p>
            <p className="text-xs" style={{ color: "#64748b" }}>Powered by GPT-4o · charts enabled</p>
          </div>
        </div>
        <button onClick={onClose}
          className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors hover:opacity-70"
          style={{ color: "#64748b", background: "#1a1a2e" }}>
          ✕
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"} fade-up`}>
            {m.role === "assistant" && (
              <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-0.5"
                style={{ background: "#7c3aed20", color: "#7c3aed" }}>
                ✦
              </div>
            )}

            <div className="max-w-[90%]">
              {/* Render each part */}
              {m.parts.length === 0 && streaming && i === messages.length - 1 ? (
                /* Streaming placeholder */
                <div className="rounded-2xl px-4 py-3 text-sm"
                  style={{ background: "#1a1a2e", border: "1px solid #252540" }}>
                  <span className="flex gap-1">
                    {[0, 0.2, 0.4].map((d, j) => (
                      <span key={j} className="blink" style={{ color: "#7c3aed", animationDelay: `${d}s` }}>●</span>
                    ))}
                  </span>
                </div>
              ) : (
                m.parts.map((part, pi) => {
                  if (part.type === "text" && part.content) {
                    return (
                      <div key={pi}
                        className="rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
                        style={m.role === "user"
                          ? { background: "#ff6b3520", color: "#e2e8f0", border: "1px solid #ff6b3540" }
                          : { background: "#1a1a2e", color: "#cbd5e1", border: "1px solid #252540", marginBottom: 4 }
                        }
                      >
                        {part.content}
                      </div>
                    );
                  }
                  if (part.type === "chart" && part.chart) {
                    return <InlineChart key={pi} chart={part.chart} />;
                  }
                  return null;
                })
              )}
            </div>
          </div>
        ))}

        {/* Suggestion chips on first load */}
        {messages.length === 1 && (
          <div className="pt-2">
            <p className="text-xs mb-2" style={{ color: "#475569" }}>Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="text-xs px-3 py-1.5 rounded-full transition-colors hover:opacity-80"
                  style={{ background: "#1a1a2e", border: "1px solid #252540", color: "#94a3b8" }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="text-xs rounded-xl px-4 py-3"
            style={{ background: "#ef444420", color: "#fca5a5", border: "1px solid #ef444440" }}>
            ⚠️ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4" style={{ borderTop: "1px solid #252540" }}>
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything or request a chart…"
            disabled={streaming}
            className="flex-1 rounded-xl px-4 py-2.5 text-sm outline-none"
            style={{
              background: "#1a1a2e",
              border: "1px solid #252540",
              color: "#e2e8f0",
              opacity: streaming ? 0.6 : 1,
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || streaming}
            className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:opacity-80 disabled:opacity-30"
            style={{ background: "#ff6b35", color: "white" }}
          >
            {streaming ? (
              <span className="blink text-xs">●</span>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M22 2L11 13M22 2L15 22 11 13 2 9l20-7z" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
