import { useRef, useState } from "react";

export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

// Only Gemini is wired up in the backend today.
export const PROVIDERS = [
  { id: "gemini", name: "Gemini", available: true },
  { id: "chatgpt", name: "ChatGPT", available: false },
  { id: "claude", name: "Claude", available: false },
];

export const RISK_LABELS = {
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

export const RISK_ORDER = { CRITICAL: 1, HIGH: 2, MEDIUM: 3, LOW: 4 };

export function humanize(type) {
  const text = String(type || "").replace(/_/g, " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function countBy(items, keyFn) {
  const map = new Map();

  for (const item of items) {
    const key = keyFn(item);
    map.set(key, (map.get(key) || 0) + 1);
  }

  return [...map.entries()];
}

// ---------------- Icons ----------------

const ICONS = {
  text: <path d="M4 6h16M4 12h16M4 18h10" />,
  image: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="1.6" />
      <path d="M21 16l-5-5-8 8" />
    </>
  ),
  pdf: (
    <>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  moon: <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />,
};

export function Icon({ name, size = 18 }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

export function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 28 28" aria-hidden="true">
      <rect className="logoBg" width="28" height="28" rx="8" />
      <rect x="6" y="9" width="16" height="3.6" rx="1.8" fill="#fff" />
      <rect x="6" y="15.4" width="10" height="3.6" rx="1.8" fill="#fff" opacity="0.75" />
    </svg>
  );
}

// ---------------- Small pieces ----------------

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export function Banner({ kind = "info", children }) {
  if (!children) return null;

  return (
    <div
      className={`banner ${kind}`}
      role={kind === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

export function RiskBadge({ risk }) {
  return (
    <span className={`risk ${String(risk).toLowerCase()}`}>
      {RISK_LABELS[risk] || risk}
    </span>
  );
}

export function CopyButton({ text, label = "Copy" }) {
  const [done, setDone] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <button type="button" className="btn small" onClick={copy}>
      {done ? "Copied" : label}
    </button>
  );
}

// Shows OBSCURA placeholders as redaction-style chips.
export function TokenText({ text }) {
  const parts = String(text).split(/(<OBSCURA_[A-Z_]+_\d+>)/);

  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <span className="token" key={index}>
        {part}
      </span>
    ) : (
      <span key={index}>{part}</span>
    ),
  );
}

export function DropZone({ accept, onFile, disabled, title, hint }) {
  const inputRef = useRef(null);
  const [over, setOver] = useState(false);

  function handle(files) {
    const file = files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      className={`dropzone ${over ? "over" : ""} ${disabled ? "disabled" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        if (!disabled) handle(event.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(event) => {
          handle(event.target.files);
          event.target.value = "";
        }}
      />

      <div className="dropTitle">{title}</div>
      <div className="dropHint">{hint}</div>

      <button
        type="button"
        className="btn primary"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Choose file
      </button>
    </div>
  );
}

// ---------------- Layout: steps on the left, outputs on the right ----------------

export function Workspace({ banner, steps, outputs }) {
  return (
    <div className="workspace">
      <div className="stepsCol">
        <div className="colTitle">Steps</div>
        {banner}
        {steps}
      </div>

      <aside className="outputsCol">
        <div className="colTitle">Outputs</div>
        {outputs}
      </aside>
    </div>
  );
}

// state: "locked" | "active" | "done"
export function Step({ n, title, hint, state, summary, action, children }) {
  const showSummary = state === "done" && Boolean(summary);
  const showBody = state === "active" || (state === "done" && !summary);

  return (
    <section className={`step ${state}`}>
      <header className="stepHead">
        <span className="stepNum">{state === "done" ? "✓" : n}</span>

        <div className="stepTitle">
          <h2>{title}</h2>

          {state !== "done" && hint && <p className="sub">{hint}</p>}
          {showSummary && <p className="sub">{summary}</p>}
        </div>

        {showSummary && action}
      </header>

      {showBody && <div className="stepBody">{children}</div>}
    </section>
  );
}

export function Output({ title, step, ready, empty, actions, children }) {
  return (
    <section className={`output ${ready ? "ready" : ""}`}>
      <header className="outHead">
        <div className="outTitle">
          <h3>{title}</h3>
          <span className="stepChip">Step {step}</span>
        </div>

        {ready && actions && <div className="row">{actions}</div>}
      </header>

      {ready ? (
        <div className="outBody">{children}</div>
      ) : (
        <p className="empty">{empty}</p>
      )}
    </section>
  );
}

export function Report({ total, risks = [], types = [], children }) {
  return (
    <div className="report">
      {total === 0 ? (
        <div className="reportTotal good">
          Nothing sensitive was detected. Detection is automatic, so still read
          your content yourself.
        </div>
      ) : (
        <>
          <div className="reportTotal">
            <span className="big">{total}</span>
            <span>
              possible private item{total === 1 ? "" : "s"} found
            </span>
          </div>

          {risks.length > 0 && (
            <div className="chips">
              {risks.map(([risk, count]) => (
                <span className="chipRisk" key={risk}>
                  <RiskBadge risk={risk} /> <b>×{count}</b>
                </span>
              ))}
            </div>
          )}

          {types.length > 0 && (
            <div className="chips">
              {types.map(([label, count]) => (
                <span className="chip" key={label}>
                  {label} <b>{count}</b>
                </span>
              ))}
            </div>
          )}
        </>
      )}

      {children}
    </div>
  );
}
