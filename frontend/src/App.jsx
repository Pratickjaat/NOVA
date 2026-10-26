import { useEffect, useRef, useState } from "react";

const NAV_ITEMS = [
  ["Home", "home"], ["Conversations", "chat"], ["Workspace", "grid"],
  ["Activity", "activity"], ["Settings", "settings"],
];

const QUICK_ACTIONS = [
  ["VS Code", "vscode", "open vs code", "blue"],
  ["YouTube", "youtube", "open youtube", "red"],
  ["ChatGPT", "chatgpt", "open chatgpt", "green"],
  ["Calculator", "calculator", "open calculator", "slate"],
  ["Notepad", "notepad", "open notepad", "cyan"],
  ["Google", "google", "open google", "gold"],
];

function Icon({ name, size = 24, className = "" }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  const paths = {
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9M9 20v-7h6v7"/></>,
    chat: <><path d="M4 4h16v13H9l-5 4V4Z"/><path d="M8 10h.01M12 10h.01M16 10h.01" strokeWidth="2.8"/></>,
    grid: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></>,
    activity: <path d="m13.5 2.5-10 12h7l-1 7 11-13h-7l.5-6Z"/>,
    settings: <><path d="M12 8.4a3.6 3.6 0 1 0 0 7.2 3.6 3.6 0 0 0 0-7.2Z"/><path d="m19.4 13.5 1.1.9-1.2 2.1-1.4-.5a7.8 7.8 0 0 1-1.4.8l-.3 1.5h-2.4l-.4-1.5a7.8 7.8 0 0 1-1.5-.6l-1.3.7-1.6-1.7.7-1.3a7.7 7.7 0 0 1-.5-1.5l-1.5-.5v-2.4l1.5-.4a7.8 7.8 0 0 1 .7-1.4l-.6-1.4 1.8-1.5 1.2.8a7.8 7.8 0 0 1 1.5-.4l.5-1.5h2.4l.4 1.5a7.8 7.8 0 0 1 1.4.7l1.4-.6 1.4 1.8-.8 1.2a7.8 7.8 0 0 1 .5 1.5l1.4.5v2.4l-1.5.4Z" transform="translate(-1 -1) scale(.96)"/></>,
    globe: <><circle cx="12" cy="12" r="9.5"/><path d="M2.8 12h18.4M12 2.5a15 15 0 0 1 0 19M12 2.5a15 15 0 0 0 0 19"/></>,
    chevron: <path d="m7 10 5 5 5-5"/>,
    expand: <><path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"/><path d="m3 8 6-5m12 5-6-5M3 16l6 5m12-5-6 5"/></>,
    mic: <><rect x="9" y="2.5" width="6" height="12" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3.5M9 21.5h6"/></>,
    pause: <><path d="M9 5v14M15 5v14"/></>,
    user: <><circle cx="12" cy="8" r="3.5"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/></>,
    trash: <><path d="M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3"/></>,
    send: <path d="m3 11 18-8-8 18-2.5-7.5L3 11Z M10.5 13.5 21 3"/>,
    sparkle: <><path d="m12 2 1.8 7.2L21 12l-7.2 1.8L12 21l-1.8-7.2L3 12l7.2-2.8L12 2Z"/><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z"/></>,
    nova: <><circle cx="12" cy="12" r="8.8"/><circle cx="12" cy="12" r="5" opacity=".7"/></>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    stop: <rect x="6" y="6" width="12" height="12" rx="2"/>,
    maximize: <rect x="5" y="5" width="14" height="14" rx="1"/>,
    restore: <><path d="M8 8V5h11v11h-3"/><rect x="5" y="8" width="11" height="11" rx="1"/></>,
    minimize: <path d="M5 12h14"/>,
  };
  return <svg {...common} className={className}>{paths[name] || null}</svg>;
}

function QuickLogo({ type }) {
  if (type === "youtube") return <svg viewBox="0 0 32 32" aria-hidden="true"><rect x="2" y="6" width="28" height="20" rx="6" fill="currentColor"/><path d="m13 11 9 5-9 5z" fill="white"/></svg>;
  if (type === "vscode") return <svg viewBox="0 0 32 32" aria-hidden="true"><path fill="currentColor" d="M23.5 3.5 12 13l-6-4.7L2 10.5l7.2 5.5L2 21.5l4 2.2 6-4.7 11.5 9.5 5-2.5v-20l-5-2.5Zm0 7v11l-7-5.5 7-5.5Z"/></svg>;
  if (type === "chatgpt") return <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 4.5a7 7 0 0 1 6.7 5 7 7 0 0 1 4.2 9.7 7 7 0 0 1-7 9.3 7 7 0 0 1-11-5.1 7 7 0 0 1-1.8-11.4A7 7 0 0 1 16 4.5Z" fill="none" stroke="currentColor" strokeWidth="2.7" strokeLinejoin="round"/><path d="m11 11 10 5.5v6M21 11l-10 5.5v6M8 13l8-4.5 5 2.8M8 19l8 4.5 5-2.8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>;
  if (type === "calculator") return <svg viewBox="0 0 32 32" aria-hidden="true"><rect x="5" y="3" width="22" height="26" rx="3" fill="currentColor"/><rect x="9" y="7" width="14" height="5" rx="1" fill="#18202d"/><path d="M10 17h2m4 0h2m4 0h1M10 21h2m4 0h2m4 0h1M10 25h2m4 0h2m4 0h1" stroke="#dce8fa" strokeWidth="2.6" strokeLinecap="round"/></svg>;
  if (type === "notepad") return <svg viewBox="0 0 32 32" aria-hidden="true"><rect x="5" y="4" width="22" height="25" rx="3" fill="currentColor"/><path d="M10 11h12M10 16h12M10 21h9" stroke="white" strokeWidth="1.6" strokeLinecap="round"/><path d="M10 3v4m4-4v4m4-4v4m4-4v4" stroke="#e8f6ff" strokeWidth="2" strokeLinecap="round"/></svg>;
  return <span className="google-g">G</span>;
}

function FlowField() {
  return (
    <svg className="flow-field" viewBox="0 0 900 620" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="flowGradient" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#7950d4" stopOpacity="0"/><stop offset=".48" stopColor="#cb9aff" stopOpacity=".9"/><stop offset="1" stopColor="#7550d8" stopOpacity="0"/></linearGradient>
        <filter id="flowGlow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <path className="flow-path flow-a" d="M-60 350 C120 150 205 540 365 360 S665 150 960 340"/>
      <path className="flow-path flow-b" d="M-50 430 C170 570 230 135 415 295 S680 515 950 225"/>
      <path className="flow-path flow-c" d="M-60 235 C160 410 260 80 440 220 S730 445 960 150"/>
      <path className="flow-path flow-d" d="M-40 500 C180 365 240 600 430 430 S715 280 950 465"/>
    </svg>
  );
}

function OrbWeave() {
  return (
    <svg className="orb-weave" viewBox="0 0 460 460" aria-hidden="true">
      <defs>
        <linearGradient id="orbOrbit" x1=".12" y1=".08" x2=".9" y2=".92"><stop stopColor="#b68aff" stopOpacity=".12"/><stop offset=".48" stopColor="#e4c6ff"/><stop offset="1" stopColor="#9860f4" stopOpacity=".2"/></linearGradient>
      </defs>
      <ellipse className="orb-orbit-line" cx="230" cy="230" rx="178" ry="92" transform="rotate(-28 230 230)"/>
    </svg>
  );
}

function Orb({ status }) {
  return (
    <div className={`orb-scene state-${status.toLowerCase()}`}>
      <div className="orb-shell"><div className="orb-shimmer"/><OrbWeave/><i className="orb-core"/></div>
    </div>
  );
}

function Message({ message }) {
  const isNova = message.speaker === "NOVA";
  const time = message.time || new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
  return (
    <article className={`message ${isNova ? "nova" : "user"}`}>
      <div className="avatar">{isNova ? <Icon name="nova" size={29}/> : <Icon name="user" size={25}/>}</div>
      <div className="message-content"><div className="message-meta"><b>{message.speaker}</b><time>{time}</time></div><p>{message.text}</p></div>
    </article>
  );
}

function App() {
  const [bridge, setBridge] = useState(null);
  const [status, setStatus] = useState("STANDBY");
  const [statusMessage, setStatusMessage] = useState("Starting NOVA...");
  const [microphoneEnabled, setMicrophoneEnabled] = useState(false);
  const [language, setLanguage] = useState("English");
  const [languageMenuOpen, setLanguageMenuOpen] = useState(false);
  const [busy, setBusy] = useState(true);
  const [messages, setMessages] = useState([]);
  const [page, setPage] = useState("Home");
  const [command, setCommand] = useState("");
  const conversationRef = useRef(null);
  const commandRef = useRef(null);
  const languagePickerRef = useRef(null);

  useEffect(() => {
    if (!languageMenuOpen) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!languagePickerRef.current?.contains(event.target)) setLanguageMenuOpen(false);
    };
    const closeOnEscape = (event) => { if (event.key === "Escape") setLanguageMenuOpen(false); };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [languageMenuOpen]);

  useEffect(() => {
    if (!window.qt || !window.QWebChannel) {
      setStatusMessage("NOVA's desktop bridge could not be reached.");
      setBusy(false);
      return undefined;
    }
    let active = true;
    new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
      if (!active) return;
      const nova = channel.objects.nova;
      window.novaBridge = nova;
      setBridge(nova);
      const updateState = () => {
        setStatus(nova.status || "STANDBY");
        setStatusMessage(nova.statusMessage || "Ready when you are.");
        setMicrophoneEnabled(Boolean(nova.microphoneEnabled));
      };
      const updateMessages = () => setMessages(Array.from(nova.messages || []).map((message) => ({
        speaker: message.speaker,
        text: message.text,
        time: new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date()),
      })));
      nova.stateChanged.connect(updateState);
      nova.languageChanged.connect(() => setLanguage(nova.languageProperty || "English"));
      nova.conversationChanged.connect(updateMessages);
      nova.busyChanged.connect(() => setBusy(Boolean(nova.busyProperty)));
      updateState(); updateMessages();
      setLanguage(nova.languageProperty || "English");
      setBusy(Boolean(nova.busyProperty));
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (conversationRef.current) conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
  }, [messages]);

  const sendCommand = (value = command) => {
    const text = value.trim();
    if (!text || !bridge || busy) return;
    bridge.submitCommand(text);
    setCommand("");
    commandRef.current?.focus();
  };
  const selectPage = (nextPage) => { setPage(nextPage); bridge?.setPage(nextPage); };
  const beginWindowDrag = (event) => {
    if (event.button !== 0 || event.target.closest(".window-controls")) return;
    event.preventDefault();
    let lastX = event.screenX;
    let lastY = event.screenY;
    const move = (next) => {
      const dx = Math.round(next.screenX - lastX);
      const dy = Math.round(next.screenY - lastY);
      if (dx || dy) bridge?.moveWindow(dx, dy);
      lastX = next.screenX; lastY = next.screenY;
    };
    const stop = () => { window.removeEventListener("pointermove", move); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
  };
  const beginWindowResize = (edge, event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    let lastX = event.screenX;
    let lastY = event.screenY;
    const move = (next) => {
      const dx = Math.round(next.screenX - lastX);
      const dy = Math.round(next.screenY - lastY);
      if (dx || dy) bridge?.resizeWindow(edge, dx, dy);
      lastX = next.screenX; lastY = next.screenY;
    };
    const stop = () => { window.removeEventListener("pointermove", move); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
  };

  return (
    <div className="app-shell" data-state={status}>
      <div className="window-drag-region" onPointerDown={beginWindowDrag} onDoubleClick={() => bridge?.toggleWindowMaximize()} aria-hidden="true"/>
      <div className="window-controls" aria-label="Window controls">
        <button onClick={() => bridge?.minimizeWindow()} aria-label="Minimize"><Icon name="minimize" size={18}/></button>
        <button onClick={() => bridge?.toggleWindowMaximize()} aria-label="Maximize or restore"><Icon name="maximize" size={15}/></button>
        <button className="close-window" onClick={() => bridge?.closeWindow()} aria-label="Close"><Icon name="close" size={19}/></button>
      </div>
      {[["top", "north"], ["bottom", "south"], ["left", "west"], ["right", "east"], ["top-left", "north-west"], ["top-right", "north-east"], ["bottom-left", "south-west"], ["bottom-right", "south-east"]].map(([edge, className]) => <div key={edge} className={`resize-edge ${className}`} onPointerDown={(event) => beginWindowResize(edge, event)} aria-hidden="true"/>)}
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Icon name="nova" size={26}/></div><div><div className="brand-name">NOVA</div><div className="brand-caption">PERSONAL AI ASSISTANT</div></div></div>
        <div className="sidebar-rule"/>
        <nav className="navigation" aria-label="Main navigation">
          {NAV_ITEMS.map(([name, icon]) => <button key={name} className={`nav-item ${page === name ? "active" : ""}`} onClick={() => selectPage(name)}><Icon className="nav-icon" name={icon} size={27}/><span>{name}</span></button>)}
        </nav>
        <div className="sidebar-bottom">
          <label id="language-label">Language</label>
          <div className={`language-picker ${languageMenuOpen ? "open" : ""}`} ref={languagePickerRef}>
            <Icon className="globe" name="globe" size={24}/>
            <button className="language-trigger" type="button" aria-labelledby="language-label" aria-haspopup="listbox" aria-expanded={languageMenuOpen} onClick={() => setLanguageMenuOpen((open) => !open)}>
              <span>{language}</span><Icon className="select-chevron" name="chevron" size={19}/>
            </button>
            {languageMenuOpen && <div className="language-menu" role="listbox" aria-label="Choose language">
              {["English", "Hindi"].map((option) => <button key={option} type="button" role="option" aria-selected={language === option} className={`language-option ${language === option ? "selected" : ""}`} onClick={() => { bridge?.setLanguage(option); setLanguage(option); setLanguageMenuOpen(false); }}><span>{option}</span>{language === option && <span className="language-check" aria-hidden="true">✓</span>}</button>)}
            </div>}
          </div>
          <div className="ready-card"><span className="ready-dot"/><div><b>NOVA</b><small>{status === "LISTENING" ? "Ready when you are." : statusMessage}</small></div></div>
        </div>
      </aside>

      <main className="main-area">
        <section className="dashboard">
          <section className="center-stage" aria-label="NOVA assistant">
            <div className="orb-area"><Orb status={status}/></div>
            <div className="assistant-state">{[...status].join(" ")}</div>
            <div className="status-pill">{statusMessage}</div>
            <div className="assistant-controls">
              <button className="control-button" onClick={() => bridge?.toggleFullscreen()} title="Toggle fullscreen" aria-label="Toggle fullscreen"><Icon name="expand" size={25}/></button>
              <button className={`mic-button ${microphoneEnabled ? "enabled" : ""}`} onClick={() => bridge?.toggleMicrophone()} disabled={busy || !bridge} title={microphoneEnabled ? "Pause microphone" : "Resume microphone"} aria-label={microphoneEnabled ? "Pause microphone" : "Enable microphone"}><Icon name="mic" size={32}/></button>
              {status === "SPEAKING" && <button className="control-button interrupt-button" onClick={() => bridge?.interruptSpeech()} title="Interrupt NOVA" aria-label="Interrupt NOVA"><Icon name="stop" size={26}/></button>}
              <button className="control-button" onClick={() => selectPage("Settings")} title="Settings" aria-label="Settings"><Icon name="settings" size={26}/></button>
            </div>
          </section>

          <aside className="conversation-panel">
            <div className="conversation-heading"><h2>Conversation</h2><button onClick={() => bridge?.clearConversation()} disabled={!bridge}>Clear <Icon name="trash" size={19}/></button></div>
            <div className="conversation-list" ref={conversationRef} aria-live="polite">{messages.length === 0 ? <p className="empty-conversation">Your conversation will appear here.</p> : messages.map((message, index) => <Message key={`${index}-${message.speaker}`} message={message}/>)}</div>
            <div className="panel-divider"/><h2 className="quick-heading">Quick Actions</h2>
            <div className="quick-actions">{QUICK_ACTIONS.map(([name, icon, action, color]) => <button key={name} className="quick-action" onClick={() => sendCommand(action)} disabled={!bridge || busy}><span className={`quick-icon ${color}`}><QuickLogo type={icon}/></span><span>{name}</span></button>)}</div>
          </aside>
        </section>
        <form className="command-bar" onSubmit={(event) => { event.preventDefault(); sendCommand(); }}>
          <div className="command-sparkle"><Icon name="sparkle" size={31}/></div>
          <input ref={commandRef} value={command} onChange={(event) => setCommand(event.target.value)} disabled={busy || !bridge} placeholder="Type a command or message..." aria-label="Command or message"/>
          <button type="submit" className="send-button" disabled={busy || !command.trim()} aria-label="Send command"><Icon name="send" size={23}/></button>
        </form>
      </main>
    </div>
  );
}

export default App;
