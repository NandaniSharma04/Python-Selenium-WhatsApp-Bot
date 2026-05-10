import { useState, useEffect, useCallback, useRef } from "react";
import "./App.css";

const API = "http://localhost:8000";

/* ── Avatar ── */
function Avatar({ name, size = 42, onClick }) {
  const clean = (name || "").replace(/[^\w\s]/g, "").trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  const initials = parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : (clean[0] || "?").toUpperCase();
  const colors = ["#D9FDD3","#FFF3CD","#D1ECF1","#F8D7DA","#E2D9F3","#D4EDDA","#FCE8D5","#D6EAF8"];
  const textColors = ["#128C7E","#856404","#0C5460","#721C24","#4A235A","#155724","#7D3C00","#1A5276"];
  const idx = ((name || "").charCodeAt(0) || 0) % colors.length;
  return (
    <div
      className="wa-avatar"
      onClick={onClick}
      style={{ width: size, height: size, minWidth: size, background: colors[idx], color: textColors[idx] }}
    >
      {initials}
    </div>
  );
}

/* ── Thumbs-up burst ── */
function ThumbsBurst({ onDone }) {
  useEffect(() => { const t = setTimeout(onDone, 3000); return () => clearTimeout(t); }, [onDone]);
  const particles = Array.from({ length: 20 }, (_, i) => i);
  return (
    <div className="burst-overlay">
      <div className="burst-box">
        <div className="burst-thumb">👍</div>
        {particles.map(i => (
          <div key={i} className="burst-p" style={{
            "--a": `${(i / 20) * 360}deg`,
            "--d": `${80 + Math.random() * 100}px`,
            "--dl": `${Math.random() * 0.3}s`,
            "--em": `"${["✨","🎉","💚","⚡","🚀","💬","🌟","🎊"][i % 8]}"`,
          }} />
        ))}
        <div className="burst-label">Messages Sent!</div>
        <div className="burst-sub">Form will reset automatically</div>
      </div>
    </div>
  );
}

/* ── Toast ── */
function Toast({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  return (
    <div className={`wa-toast wa-toast-${type}`}>
      <span>{type === "success" ? "✓" : "✗"}</span>{msg}
    </div>
  );
}

/* ── Main App ── */
export default function App() {
  const [theme, setTheme]       = useState(() => localStorage.getItem("blastwa-theme") || "dark");
  const [health, setHealth]     = useState(null);
  const [contacts, setContacts] = useState([]);
  const [ccs, setCcs]           = useState([]);
  const [cc, setCc]             = useState("91");
  const [selected, setSelected] = useState([]);
  const [message, setMessage]   = useState("");
  const [search, setSearch]     = useState("");
  const [sending, setSending]   = useState(false);
  const [toast, setToast]       = useState(null);
  const [burst, setBurst]       = useState(false);
  const [history, setHistory]   = useState([]);
  const [panel, setPanel]       = useState("chat");   // "chat" | "history" | "settings"
  const [activeContact, setActiveContact] = useState(null);
  const [progress, setProgress] = useState(null);
  const textRef = useRef(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("blastwa-theme", theme);
  }, [theme]);

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(d => setHealth(d.status)).catch(() => setHealth("offline"));
    fetch(`${API}/contacts`).then(r => r.json()).then(d => {
      setContacts(d.contacts || []);
      setCcs(d.countryCodes || []);
    }).catch(console.error);
  }, []);

  const filtered = contacts.filter(c =>
    !search ||
    (c.name || "").toLowerCase().includes(search.toLowerCase()) ||
    (c.phone || "").includes(search)
  );
  const allSel = filtered.length > 0 && filtered.every(c => selected.includes(c.phone));

  const togglePhone = useCallback(phone => {
    setSelected(p => p.includes(phone) ? p.filter(x => x !== phone) : [...p, phone]);
  }, []);

  const toggleAll = () => {
    const phones = filtered.map(c => c.phone);
    if (allSel) setSelected(p => p.filter(x => !phones.includes(x)));
    else setSelected(p => [...new Set([...p, ...phones])]);
  };

  const insertFmt = (prefix, suffix = prefix) => {
    const el = textRef.current;
    if (!el) return;
    const { selectionStart: s, selectionEnd: e, value: v } = el;
    setMessage(v.slice(0, s) + prefix + v.slice(s, e) + suffix + v.slice(e));
    setTimeout(() => { el.focus(); el.setSelectionRange(s + prefix.length, e + prefix.length); }, 0);
  };

  const resetForm = () => {
    setSelected([]);
    setMessage("");
    setSearch("");
    setProgress(null);
    setActiveContact(null);
  };

  const handleSend = async () => {
    if (!message.trim() || selected.length === 0) {
      setToast({ msg: "Select contacts and type a message.", type: "error" });
      return;
    }
    setSending(true);
    setProgress({ pct: 5, done: 0, total: selected.length, success: 0, failed: 0 });
    try {
      const res = await fetch(`${API}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phones: selected, message, countryCode: cc }),
      });
      const data = await res.json();
      setProgress({ pct: 100, done: selected.length, total: selected.length, success: selected.length, failed: 0 });
      setHistory(h => [{ time: new Date().toLocaleTimeString(), date: new Date().toLocaleDateString(), count: selected.length, preview: message.slice(0, 100), status: data.status }, ...h]);
      setBurst(true);
    } catch {
      setToast({ msg: "Backend not reachable.", type: "error" });
      setSending(false);
    } finally {
      setSending(false);
    }
  };

  const words = message.trim() ? message.trim().split(/\s+/).length : 0;
  const charPct = Math.min(100, Math.round((message.length / 4096) * 100));
  const isDark = theme === "dark";

  return (
    <div className="wa-shell">
      {burst && <ThumbsBurst onDone={() => { setBurst(false); resetForm(); }} />}
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      {/* ══ LEFT SIDEBAR ══ */}
      <div className="wa-left">

        {/* Header */}
        <div className="wa-left-header">
          <div className="wa-brand">
            <div className="wa-brand-logo">
              <svg width="22" height="22" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12c0 1.85.5 3.58 1.37 5.07L2 22l5.09-1.35A9.96 9.96 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2z" fill="currentColor"/>
                <path d="M17 14.93c-.28-.14-1.65-.81-1.9-.9-.26-.09-.45-.14-.63.14s-.72.9-.88 1.09c-.16.18-.33.2-.61.07-.28-.14-1.18-.44-2.25-1.4-.83-.74-1.39-1.66-1.55-1.94-.16-.28-.02-.43.12-.57.12-.12.28-.32.42-.47.14-.16.18-.27.28-.45.09-.18.05-.34-.02-.47-.07-.14-.63-1.52-.86-2.08-.23-.55-.46-.47-.63-.48h-.54c-.18 0-.49.07-.75.34-.25.27-1 .98-1 2.38s1.03 2.76 1.17 2.95c.14.18 2.03 3.1 4.93 4.35.69.3 1.23.47 1.65.6.69.22 1.32.19 1.82.12.56-.08 1.65-.67 1.88-1.32.23-.65.23-1.2.16-1.32-.07-.12-.26-.19-.54-.33z" fill="white"/>
              </svg>
              <div className="wa-brand-text">
                <span className="wa-brand-name">WhatsApp</span>
                <span className="wa-brand-sub">Bulk Messenger</span>
              </div>
            </div>
          </div>
          <div className="wa-header-actions">
            <button className="wa-icon-btn" onClick={() => setPanel(p => p === "history" ? "chat" : "history")} title="History">
              {/* History icon */}
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </button>
            <button className="wa-icon-btn" onClick={() => setTheme(t => t === "dark" ? "light" : "dark")} title="Toggle theme">
              {isDark
                ? <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.389 5.389 0 0 1-4.4 2.26 5.403 5.403 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1z"/></svg>
                : <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58a.996.996 0 0 0-1.41 0 .996.996 0 0 0 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37a.996.996 0 0 0-1.41 0 .996.996 0 0 0 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0a.996.996 0 0 0 0-1.41l-1.06-1.06zm1.06-10.96a.996.996 0 0 0 0-1.41.996.996 0 0 0-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36a.996.996 0 0 0 0-1.41.996.996 0 0 0-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/></svg>
              }
            </button>
            <div className={`wa-status-dot ${health === "ok" ? "dot-on" : "dot-off"}`} title={health === "ok" ? "Server online" : "Offline"} />
          </div>
        </div>

        {/* Search bar */}
        <div className="wa-search-wrap">
          <div className="wa-search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <input
              className="wa-search-input"
              placeholder="Search or start new chat"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && <button className="wa-search-x" onClick={() => setSearch("")}>×</button>}
          </div>
        </div>

        {/* Country + select all bar */}
        <div className="wa-filter-bar">
          <select className="wa-cc-select" value={cc} onChange={e => setCc(e.target.value)}>
            {ccs.map(([label, code]) => <option key={label} value={code}>{label}</option>)}
          </select>
          <div className="wa-filter-right">
            <span className="wa-count-badge">{contacts.length}</span>
            <button className="wa-sel-all-btn" onClick={toggleAll}>
              {allSel ? "None" : "All"}
            </button>
          </div>
        </div>

        {/* Selected strip */}
        {selected.length > 0 && (
          <div className="wa-sel-strip">
            <span className="wa-sel-check">✓</span>
            <span>{selected.length} selected</span>
            <button className="wa-sel-clear" onClick={() => setSelected([])}>Clear</button>
          </div>
        )}

        {/* Contact list */}
        <div className="wa-contact-list">
          {filtered.length === 0 && (
            <div className="wa-list-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" opacity=".25"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <span>No contacts found</span>
            </div>
          )}
          {filtered.map(c => {
            const sel = selected.includes(c.phone);
            const isActive = activeContact?.phone === c.phone;
            return (
              <div
                key={c.phone}
                className={`wa-contact-item ${sel ? "wa-contact-sel" : ""} ${isActive ? "wa-contact-active" : ""}`}
                onClick={() => { togglePhone(c.phone); setActiveContact(c); setPanel("chat"); }}
              >
                <div className="wa-contact-avatar-wrap">
                  <Avatar name={c.name} size={42} />
                  {sel && <div className="wa-sel-tick">✓</div>}
                </div>
                <div className="wa-contact-info">
                  <div className="wa-contact-row1">
                    <span className="wa-contact-name">{c.name || "Unknown"}</span>
                    {sel && <span className="wa-contact-sel-dot" />}
                  </div>
                  <div className="wa-contact-phone">{c.phone}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ══ RIGHT PANEL ══ */}
      <div className="wa-right">

        {/* ── CHAT PANEL ── */}
        {panel === "chat" && (
          <>
            {/* Chat header */}
            <div className="wa-chat-header">
              {activeContact ? (
                <>
                  <Avatar name={activeContact.name} size={38} />
                  <div className="wa-chat-header-info">
                    <div className="wa-chat-header-name">{activeContact.name || "Unknown"}</div>
                    <div className="wa-chat-header-sub">{activeContact.phone}</div>
                  </div>
                </>
              ) : (
                <>
                  <div className="wa-chat-header-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  </div>
                  <div className="wa-chat-header-info">
                    <div className="wa-chat-header-name">Bulk Broadcast</div>
                    <div className="wa-chat-header-sub">
                      {selected.length === 0 ? "Select contacts from the left panel" : `${selected.length} recipient${selected.length > 1 ? "s" : ""} selected`}
                    </div>
                  </div>
                </>
              )}
              <div className="wa-chat-header-actions">
                {/* Search icon */}
                <button className="wa-icon-btn">
                  <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                </button>
                {/* More icon */}
                <button className="wa-icon-btn">
                  <svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
                </button>
              </div>
            </div>

            {/* Chat background / body */}
            <div className="wa-chat-body">
              <div className="wa-chat-bg" />

              {/* Recipients chips */}
              {selected.length > 0 && (
                <div className="wa-recipients-bubble">
                  <div className="wa-recipients-title">📢 Broadcast to {selected.length} contact{selected.length > 1 ? "s" : ""}</div>
                  <div className="wa-recipients-chips">
                    {selected.slice(0, 10).map(p => {
                      const c = contacts.find(x => x.phone === p);
                      return (
                        <span key={p} className="wa-r-chip" onClick={() => togglePhone(p)}>
                          {c?.name || p} ×
                        </span>
                      );
                    })}
                    {selected.length > 10 && <span className="wa-r-chip wa-r-chip-more">+{selected.length - 10} more</span>}
                  </div>
                </div>
              )}

              {/* Progress */}
              {progress && (
                <div className="wa-progress-bubble">
                  <div className="wa-pb-row">
                    <span>Sending… {progress.done} / {progress.total}</span>
                    <span className="wa-pb-green">✓ {progress.success}</span>
                  </div>
                  <div className="wa-pb-track">
                    <div className="wa-pb-fill" style={{ width: `${progress.pct}%` }} />
                  </div>
                </div>
              )}

              {/* Empty state */}
              {selected.length === 0 && !progress && (
                <div className="wa-empty-state">
                  <div className="wa-empty-icon">
                    <svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  </div>
                  <div className="wa-empty-title">Send a bulk broadcast</div>
                  <div className="wa-empty-sub">Select contacts on the left, type your message below, and hit send.</div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Message input footer */}
            <div className="wa-footer">
              {/* Format toolbar */}
              <div className="wa-fmt-row">
                <button className="wa-fmt-btn" onClick={() => insertFmt("*")} title="Bold"><b>B</b></button>
                <button className="wa-fmt-btn" onClick={() => insertFmt("_")} title="Italic"><i>I</i></button>
                <button className="wa-fmt-btn" onClick={() => insertFmt("~")} title="Strike"><s>S</s></button>
                <button className="wa-fmt-btn wa-fmt-mono" onClick={() => insertFmt("```")} title="Code">{"{}"}</button>
                <div className="wa-fmt-sep" />
                <span className="wa-char-count">{message.length}/4096</span>
                <div className="wa-charbar-mini">
                  <div className="wa-charfill-mini" style={{ width: `${charPct}%`, background: charPct > 85 ? "#f43f5e" : "var(--wa-green)" }} />
                </div>
                <span className="wa-word-count">{words}w</span>
              </div>

              <div className="wa-input-row">
                {/* Emoji placeholder */}
                <button className="wa-emoji-btn">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
                </button>

                <div className="wa-textarea-wrap">
                  <textarea
                    ref={textRef}
                    className="wa-textarea"
                    placeholder="Type a message"
                    value={message}
                    onChange={e => setMessage(e.target.value)}
                    maxLength={4096}
                    rows={1}
                    onInput={e => {
                      e.target.style.height = "auto";
                      e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
                    }}
                  />
                </div>

                {/* Send / mic button */}
                <button
                  className={`wa-send-btn ${sending ? "wa-send-busy" : ""}`}
                  onClick={handleSend}
                  disabled={sending}
                  title={`Send to ${selected.length} contacts`}
                >
                  {sending
                    ? <span className="wa-spin" />
                    : (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                      </svg>
                    )
                  }
                </button>
              </div>
            </div>
          </>
        )}

        {/* ── HISTORY PANEL ── */}
        {panel === "history" && (
          <>
            <div className="wa-chat-header">
              <button className="wa-icon-btn" onClick={() => setPanel("chat")}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
              </button>
              <div className="wa-chat-header-info" style={{ marginLeft: 8 }}>
                <div className="wa-chat-header-name">Send History</div>
                <div className="wa-chat-header-sub">{history.length} campaign{history.length !== 1 ? "s" : ""} this session</div>
              </div>
            </div>
            <div className="wa-chat-body">
              <div className="wa-chat-bg" />
              {history.length === 0 ? (
                <div className="wa-empty-state">
                  <div className="wa-empty-icon" style={{ fontSize: 56 }}>📭</div>
                  <div className="wa-empty-title">No history yet</div>
                  <div className="wa-empty-sub">Campaigns you send will appear here.</div>
                </div>
              ) : (
                <div className="wa-history-list">
                  {history.map((h, i) => (
                    <div key={i} className="wa-history-msg">
                      <div className="wa-history-bubble">
                        <div className="wa-history-count">📤 Sent to {h.count} contacts</div>
                        <div className="wa-history-preview">"{h.preview}{h.preview.length >= 100 ? "…" : ""}"</div>
                        <div className="wa-history-meta">{h.date} · {h.time} <span className="wa-ticks">✓✓</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ── STATS BAR (bottom of right, always visible) ── */}
        <div className="wa-stats-bar">
          {[
            { n: contacts.length, l: "Contacts", e: "👥" },
            { n: selected.length, l: "Selected",  e: "✅" },
            { n: words,           l: "Words",     e: "✍️" },
            { n: history.length,  l: "Sent",      e: "📤" },
          ].map(s => (
            <div key={s.l} className="wa-stat">
              <span className="wa-stat-e">{s.e}</span>
              <span className="wa-stat-n">{s.n}</span>
              <span className="wa-stat-l">{s.l}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}