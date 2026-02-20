import { useState, useRef, useEffect } from "react";

const SUGGESTIONS = [
  "What's the overall grade?",
  "What are the top skills?",
  "What are the weaknesses?",
  "Show me the strengths",
  "What do students say?",
  "What's trending in news?",
  "Any emerging 2026 tech?",
  "What courses are offered?",
  "What should be improved?",
];

export default function Chatbot({ selectedMajor, majorName, isStatic }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "bot", text: `Hi! I'm SyncEd AI. Ask me anything about **${majorName || "this major"}** — grades, skills, gaps, reviews, news, or recommendations.` },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setMessages([
      { role: "bot", text: `Hi! I'm SyncEd AI. Ask me anything about **${majorName}** — grades, skills, gaps, reviews, news, or recommendations.` },
    ]);
  }, [majorName]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const send = async (text) => {
    const q = (text || input).trim();
    if (!q) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setLoading(true);

    try {
      let answer;
      if (isStatic) {
        answer = "Chatbot is available when running locally with the backend. Try `localhost:3000` for the full experience!";
      } else {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, major: selectedMajor }),
        });
        const data = await res.json();
        answer = data.answer || "Sorry, I couldn't find an answer.";
      }
      setMessages((m) => [...m, { role: "bot", text: answer }]);
    } catch {
      setMessages((m) => [...m, { role: "bot", text: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const renderMarkdown = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br/>");
  };

  return (
    <>
      <button
        className="chatbot-fab"
        onClick={() => setOpen(!open)}
        title="Ask SyncEd AI"
      >
        {open ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        )}
      </button>

      {open && (
        <div className="chatbot-panel">
          <div className="chatbot-header">
            <div>
              <span className="chatbot-title">SyncEd AI</span>
              <span className="chatbot-subtitle">Powered by Oracle DB insights</span>
            </div>
            <button className="chatbot-close" onClick={() => setOpen(false)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div className="chatbot-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chatbot-msg ${m.role}`}>
                {m.role === "bot" && <span className="chatbot-avatar">AI</span>}
                <div
                  className="chatbot-bubble"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(m.text) }}
                />
              </div>
            ))}
            {loading && (
              <div className="chatbot-msg bot">
                <span className="chatbot-avatar">AI</span>
                <div className="chatbot-bubble chatbot-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {messages.length <= 2 && (
            <div className="chatbot-suggestions">
              {SUGGESTIONS.slice(0, 4).map((s) => (
                <button key={s} className="chatbot-chip" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          )}

          <form className="chatbot-input-row" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input
              ref={inputRef}
              className="chatbot-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about ${majorName}...`}
              disabled={loading}
            />
            <button className="chatbot-send" type="submit" disabled={loading || !input.trim()}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </form>
        </div>
      )}
    </>
  );
}
