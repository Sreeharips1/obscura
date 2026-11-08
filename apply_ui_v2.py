# apply_ui_v2.py  -- run from the repo root
import os, sys

if not os.path.isdir("frontend/src"):
    sys.exit("Run this from the repo root (the folder containing backend/ and frontend/).")

FILES = {}

# ----------------------------------------------------------------------
FILES["frontend/index.html"] = r'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="light dark" />
    <title>Obscura - Private AI gateway</title>
    <script>
      // Set the theme before the page paints, so there is no flash.
      try {
        var t = localStorage.getItem("obscura-theme");
        if (!t) {
          t = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }
        document.documentElement.dataset.theme = t;
      } catch (e) {}
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
      rel="stylesheet"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''

# ----------------------------------------------------------------------
FILES["frontend/src/ui.jsx"] = r'''import { useRef, useState } from "react";

export const API = "http://localhost:8000/api";

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
'''

# ----------------------------------------------------------------------
FILES["frontend/src/TextPanel.jsx"] = r'''import { useMemo, useState } from "react";

import {
  API,
  Banner,
  CopyButton,
  Output,
  Report,
  RISK_ORDER,
  RiskBadge,
  Spinner,
  Step,
  TokenText,
  Workspace,
  countBy,
  humanize,
} from "./ui.jsx";

function HighlightedText({ text, detections, selected, onToggle }) {
  // Only highlight detections whose position matches the text exactly.
  const usable = detections
    .filter(
      (d) =>
        d.start >= 0 &&
        d.end <= text.length &&
        text.slice(d.start, d.end) === d.value,
    )
    .sort((a, b) => a.start - b.start);

  const parts = [];
  let cursor = 0;

  for (const d of usable) {
    if (d.start < cursor) continue;

    if (d.start > cursor) {
      parts.push(<span key={`t${cursor}`}>{text.slice(cursor, d.start)}</span>);
    }

    const blocked = d.recommended_action === "BLOCK";
    const on = blocked || selected.has(d.id);

    parts.push(
      <button
        type="button"
        key={d.id}
        className={`mark ${on ? "on" : "off"} ${blocked ? "blocked" : ""}`}
        title={
          blocked
            ? "Secret: always removed"
            : `${humanize(d.type)}: click to ${on ? "show" : "hide"}`
        }
        onClick={() => onToggle(d.id)}
      >
        {d.value}
      </button>,
    );

    cursor = d.end;
  }

  if (cursor < text.length) {
    parts.push(<span key="tail">{text.slice(cursor)}</span>);
  }

  return <div className="marked">{parts}</div>;
}

export default function TextPanel({ provider }) {
  const [text, setText] = useState("");

  const [analyzed, setAnalyzed] = useState(false);
  const [detections, setDetections] = useState([]);
  const [selected, setSelected] = useState(new Set());

  const [sanitized, setSanitized] = useState("");
  const [aliases, setAliases] = useState([]);
  const [sessionId, setSessionId] = useState("");

  const [aiResponse, setAiResponse] = useState("");

  const [notice, setNotice] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const say = (kind, message) => setNotice({ kind, text: message });

  const hasDetections = detections.length > 0;
  const hasBlocked = detections.some((d) => d.recommended_action === "BLOCK");
  const selectedCount = selected.size;

  const ordered = useMemo(
    () =>
      [...detections].sort(
        (a, b) => (RISK_ORDER[a.risk] ?? 9) - (RISK_ORDER[b.risk] ?? 9),
      ),
    [detections],
  );

  const recommendedIds = useMemo(
    () =>
      detections
        .filter((d) => d.recommended_action !== "BLOCK")
        .map((d) => d.id),
    [detections],
  );

  const riskCounts = useMemo(
    () =>
      ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        .map((risk) => [risk, detections.filter((d) => d.risk === risk).length])
        .filter(([, count]) => count > 0),
    [detections],
  );

  const typeCounts = useMemo(
    () => countBy(detections, (d) => humanize(d.type)),
    [detections],
  );

  // 0 = writing, 1 = reviewing, 2 = ready to send, 3 = finished
  const stage = aiResponse ? 3 : sanitized ? 2 : analyzed ? 1 : 0;
  const stepState = (i) => (stage > i ? "done" : stage === i ? "active" : "locked");

  function resetResults() {
    setAnalyzed(false);
    setDetections([]);
    setSelected(new Set());
    setSanitized("");
    setAliases([]);
    setSessionId("");
    setAiResponse("");
  }

  function startOver() {
    resetResults();
    setText("");
    setNotice(null);
  }

  function handleTextChange(event) {
    setText(event.target.value);

    if (analyzed || sanitized || aiResponse) {
      resetResults();
      setNotice(null);
    }
  }

  async function analyze() {
    if (!text.trim()) return;

    try {
      setIsAnalyzing(true);
      resetResults();
      say("info", "Checking your text for private data…");

      const response = await fetch(`${API}/privacy/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) throw new Error("The privacy check failed.");

      const data = await response.json();
      const found = data.detections || [];

      setDetections(found);
      setAnalyzed(true);
      setSelected(
        new Set(
          found
            .filter((d) => d.recommended_action !== "BLOCK")
            .map((d) => d.id),
        ),
      );

      if (found.some((d) => d.recommended_action === "BLOCK")) {
        say(
          "error",
          "A secret or credential was found. Remove it from your text, then check again.",
        );
      } else if (found.length) {
        say(
          "warn",
          `${found.length} possible private item${
            found.length === 1 ? "" : "s"
          } found. Choose what to protect in step 2.`,
        );
      } else {
        say("success", "Nothing sensitive was detected. You can continue.");
      }
    } catch (error) {
      console.error(error);
      say(
        "error",
        error.message ||
          "Could not reach the backend. Is it running on port 8000?",
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  function toggle(id) {
    const detection = detections.find((d) => d.id === id);
    if (detection?.recommended_action === "BLOCK") return;

    setSelected((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function createPreview() {
    if (hasBlocked) {
      say("error", "Remove the secret or credential before continuing.");
      return;
    }

    try {
      setIsPreparing(true);
      say("info", "Creating the protected version…");

      const response = await fetch(`${API}/privacy/prepare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          selected_detection_ids: [...selected],
        }),
      });

      if (!response.ok) throw new Error("Could not create the protected version.");

      const data = await response.json();

      if (data.blocked) {
        say("error", data.warning || "This request cannot be sent.");
        return;
      }

      setSessionId(data.session_id);
      setSanitized(data.sanitized_text);
      setAliases(data.aliases || []);
      say("success", "Protected version ready. Check it on the right, then send.");
    } catch (error) {
      console.error(error);
      say("error", error.message || "Could not create the protected version.");
    } finally {
      setIsPreparing(false);
    }
  }

  async function sendToAI() {
    if (!sessionId) return;

    try {
      setIsSending(true);
      say("info", `Sending the protected version to ${provider}…`);

      const response = await fetch(`${API}/chat/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.detail || "The AI request failed.");

      setAiResponse(data.response);
      setSessionId("");
      say("success", "Done. Your private values were put back by the backend.");
    } catch (error) {
      console.error(error);
      say("error", error.message || `Could not reach ${provider}.`);
    } finally {
      setIsSending(false);
    }
  }

  async function backToReview() {
    if (sessionId) {
      try {
        await fetch(`${API}/privacy/clear`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
      } catch (error) {
        console.error(error);
      }
    }

    setSessionId("");
    setSanitized("");
    setAliases([]);
    say("info", "Back to review. Temporary privacy data was cleared.");
  }

  return (
    <Workspace
      banner={<Banner kind={notice?.kind}>{notice?.text}</Banner>}
      steps={
        <>
          <Step
            n={1}
            title="Write your message"
            hint="Type or paste what you want to ask. Nothing leaves your computer until you confirm."
            state={stepState(0)}
          >
            <textarea
              className="field"
              value={text}
              onChange={handleTextChange}
              placeholder="Example: My name is Aaron Smith, my phone is 9876543210. Write a job application email to Cisco."
              rows={7}
            />

            <div className="row split">
              <span className="hint">{text.length} characters</span>

              <button
                className="btn primary"
                disabled={!text.trim() || isAnalyzing}
                onClick={analyze}
              >
                {isAnalyzing ? (
                  <>
                    <Spinner /> Checking…
                  </>
                ) : (
                  "Check for private data"
                )}
              </button>
            </div>
          </Step>

          <Step
            n={2}
            title="Choose what to protect"
            hint="Available after the privacy check. Click highlighted text to protect or unprotect it."
            state={stepState(1)}
            summary={
              hasDetections
                ? `${selectedCount} of ${detections.length} items protected`
                : "No protection needed"
            }
            action={
              stage === 2 && (
                <button className="btn small" onClick={backToReview}>
                  Change
                </button>
              )
            }
          >
            {hasDetections ? (
              <>
                <HighlightedText
                  text={text}
                  detections={detections}
                  selected={selected}
                  onToggle={toggle}
                />

                <div className="legend">
                  <span>
                    <i className="swatch on" /> Will be hidden
                  </span>
                  <span>
                    <i className="swatch off" /> Stays visible
                  </span>
                  <span>
                    <i className="swatch blocked" /> Secret, always removed
                  </span>
                </div>

                <div className="row">
                  <button
                    className="btn small"
                    onClick={() => setSelected(new Set(recommendedIds))}
                  >
                    Protect all recommended
                  </button>
                  <button
                    className="btn small"
                    onClick={() => setSelected(new Set())}
                  >
                    Protect none
                  </button>
                </div>

                <details className="more">
                  <summary>Details for each item ({detections.length})</summary>

                  <ul className="findings">
                    {ordered.map((d) => {
                      const blocked = d.recommended_action === "BLOCK";

                      return (
                        <li key={d.id}>
                          <label
                            className={`finding ${blocked ? "blockedItem" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={blocked || selected.has(d.id)}
                              disabled={blocked}
                              onChange={() => toggle(d.id)}
                            />

                            <div className="findingBody">
                              <div className="findingTop">
                                <span className="mono">{d.value}</span>
                                <RiskBadge risk={d.risk} />
                              </div>

                              <div className="meta">
                                {humanize(d.type)}
                                {blocked ? " - always removed" : ""}
                              </div>

                              <div className="reason">{d.reason}</div>
                            </div>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </details>
              </>
            ) : (
              <p className="sub">No sensitive items were detected.</p>
            )}

            <div className="row end">
              <button
                className="btn primary"
                onClick={createPreview}
                disabled={hasBlocked || isPreparing}
              >
                {isPreparing ? (
                  <>
                    <Spinner /> Preparing…
                  </>
                ) : selectedCount === 0 ? (
                  "Continue without protection"
                ) : (
                  "Create protected version"
                )}
              </button>
            </div>
          </Step>

          <Step
            n={3}
            title={`Send to ${provider}`}
            hint="Available after you create the protected version."
            state={stepState(2)}
            summary="Response received."
          >
            <p className="sub">
              Check the protected version in the outputs. When it looks right,
              send it. {provider} only ever sees that version.
            </p>

            <div className="row split">
              <button className="btn" onClick={backToReview}>
                Back
              </button>

              <button
                className="btn primary"
                onClick={sendToAI}
                disabled={!sessionId || isSending}
              >
                {isSending ? (
                  <>
                    <Spinner /> Sending…
                  </>
                ) : (
                  `Send to ${provider}`
                )}
              </button>
            </div>
          </Step>
        </>
      }
      outputs={
        <>
          <Output
            title="Privacy report"
            step={1}
            ready={analyzed}
            empty="Run the privacy check in step 1 to see what was found."
          >
            <Report
              total={detections.length}
              risks={riskCounts}
              types={typeCounts}
            >
              {hasBlocked && (
                <Banner kind="error">
                  A secret or credential was found. It is never sent.
                </Banner>
              )}
            </Report>
          </Output>

          <Output
            title="What the AI receives"
            step={2}
            ready={Boolean(sanitized)}
            empty="Create the protected version in step 2 and it will appear here."
            actions={<CopyButton text={sanitized} label="Copy" />}
          >
            <div className="compare">
              <div>
                <div className="paneLabel">Your original</div>
                <div className="pane">{text}</div>
              </div>

              <div>
                <div className="paneLabel">Sent to {provider}</div>
                <div className="pane">
                  <TokenText text={sanitized} />
                </div>
              </div>
            </div>

            {aliases.length > 0 && (
              <div className="aliases">
                <div className="paneLabel">Replaced values</div>

                {aliases.map((alias, index) => (
                  <div className="aliasRow" key={`${alias.alias}-${index}`}>
                    <span className="mono">{alias.original}</span>
                    <span className="arrow">becomes</span>
                    <span className="token">{alias.alias}</span>
                  </div>
                ))}
              </div>
            )}
          </Output>

          <Output
            title="AI response"
            step={3}
            ready={Boolean(aiResponse)}
            empty="The answer from the AI will appear here after you send."
            actions={
              <>
                <CopyButton text={aiResponse} label="Copy" />
                <button className="btn small" onClick={startOver}>
                  Start over
                </button>
              </>
            }
          >
            <div className="responseText">{aiResponse}</div>
            <p className="hint">
              Private values were restored by the backend, not by {provider}.
            </p>
          </Output>
        </>
      }
    />
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/ImagePanel.jsx"] = r'''import { useEffect, useState } from "react";

import {
  API,
  Banner,
  CopyButton,
  DropZone,
  Output,
  Report,
  Spinner,
  Step,
  Workspace,
  countBy,
} from "./ui.jsx";

export default function ImagePanel({ provider }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(new Set());

  const [protectedUrl, setProtectedUrl] = useState("");
  const [sessionId, setSessionId] = useState("");

  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");

  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const say = (kind, message) => setNotice({ kind, text: message });

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const stage = response ? 3 : protectedUrl ? 2 : result ? 1 : 0;
  const stepState = (i) => (stage > i ? "done" : stage === i ? "active" : "locked");

  const regions = result?.regions || [];
  const forcedCount = regions.filter((r) => r.recommended_action === "BLOCK").length;
  const coveredCount = selected.size + forcedCount;

  function reset() {
    setResult(null);
    setSelected(new Set());
    setProtectedUrl("");
    setSessionId("");
    setResponse("");
    setPrompt("");
  }

  function startOver() {
    reset();
    setFile(null);
    setPreviewUrl("");
    setNotice(null);
  }

  async function onFile(chosen) {
    reset();
    setFile(chosen);
    setPreviewUrl(URL.createObjectURL(chosen));

    try {
      setBusy(true);
      say("info", "Scanning the image. The first scan loads the OCR model and can take a while.");

      const form = new FormData();
      form.append("file", chosen);

      const res = await fetch(`${API}/image/analyze`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Image analysis failed.");

      setResult(data);
      setSelected(
        new Set(
          data.regions
            .filter((r) => r.recommended_action !== "BLOCK")
            .map((r) => r.id),
        ),
      );

      say(
        data.regions.length ? "warn" : "success",
        data.regions.length
          ? `${data.regions.length} sensitive area${
              data.regions.length === 1 ? "" : "s"
            } found. Click a box on the image to protect or unprotect it.`
          : "Nothing sensitive was detected. You can continue.",
      );
    } catch (error) {
      console.error(error);
      say("error", error.message || "Could not analyze the image.");
      setFile(null);
      setPreviewUrl("");
    } finally {
      setBusy(false);
    }
  }

  function toggle(region) {
    if (region.recommended_action === "BLOCK") return;

    setSelected((old) => {
      const next = new Set(old);
      if (next.has(region.id)) next.delete(region.id);
      else next.add(region.id);
      return next;
    });
  }

  async function createPreview() {
    try {
      setBusy(true);
      say("info", "Covering the selected areas…");

      const form = new FormData();
      form.append("file", file);
      form.append("selected_ids", [...selected].join(","));

      const res = await fetch(`${API}/image/prepare`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Could not protect the image.");

      setSessionId(data.session_id);
      setProtectedUrl(`data:image/png;base64,${data.image_base64}`);
      say("success", `Protected image ready. ${provider} will receive only this version.`);
    } catch (error) {
      console.error(error);
      say("error", error.message || "Could not protect the image.");
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    try {
      setBusy(true);
      say("info", `Sending the protected image to ${provider}…`);

      const res = await fetch(`${API}/image/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, prompt }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "The AI request failed.");

      setResponse(data.response);
      setSessionId("");
      say("success", "Done.");
    } catch (error) {
      console.error(error);
      say("error", error.message || `Could not reach ${provider}.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Workspace
      banner={<Banner kind={notice?.kind}>{notice?.text}</Banner>}
      steps={
        <>
          <Step
            n={1}
            title="Upload an image"
            hint="Text, QR codes, barcodes, faces, license plates and screens (phones, laptops, TVs) are found on your computer."
            state={stepState(0)}
          >
            {!file ? (
              <DropZone
                accept="image/png,image/jpeg,image/webp"
                onFile={onFile}
                disabled={busy}
                title="Drop an image here"
                hint="PNG, JPEG or WebP, up to 8 MB"
              />
            ) : (
              <div className="fileRow">
                <span className="fileName">{file.name}</span>

                {busy && !result && (
                  <span className="loading">
                    <Spinner /> Scanning…
                  </span>
                )}

                <button className="btn small" onClick={startOver} disabled={busy}>
                  Choose another
                </button>
              </div>
            )}
          </Step>

          <Step
            n={2}
            title="Choose what to cover"
            hint="Available after the scan. Click a box on the image to cover or uncover it."
            state={stepState(1)}
            summary={`${coveredCount} area${coveredCount === 1 ? "" : "s"} covered`}
            action={
              stage === 2 && (
                <button
                  className="btn small"
                  onClick={() => {
                    setProtectedUrl("");
                    setSessionId("");
                  }}
                >
                  Change
                </button>
              )
            }
          >
            <div className="imageStage">
              <img src={previewUrl} alt="Uploaded" />

              {regions.map((region) => {
                const forced = region.recommended_action === "BLOCK";
                const on = forced || selected.has(region.id);

                return (
                  <button
                    type="button"
                    key={region.id}
                    className={`regionBox ${on ? "on" : "off"} ${
                      forced ? "forced" : ""
                    }`}
                    title={`${region.label}${
                      region.text ? `: ${region.text}` : ""
                    }${forced ? " (always covered)" : ""}`}
                    onClick={() => toggle(region)}
                    style={{
                      left: `${(region.x / result.width) * 100}%`,
                      top: `${(region.y / result.height) * 100}%`,
                      width: `${(region.width / result.width) * 100}%`,
                      height: `${(region.height / result.height) * 100}%`,
                    }}
                  />
                );
              })}
            </div>

            <div className="legend">
              <span>
                <i className="swatch on" /> Will be covered
              </span>
              <span>
                <i className="swatch off" /> Stays visible
              </span>
              <span>
                <i className="swatch blocked" /> Secret, always covered
              </span>
            </div>

            {regions.length > 0 && (
              <details className="more">
                <summary>All findings ({regions.length})</summary>

                <ul className="findings">
                  {regions.map((region) => {
                    const forced = region.recommended_action === "BLOCK";

                    return (
                      <li key={region.id}>
                        <label
                          className={`finding ${forced ? "blockedItem" : ""}`}
                        >
                          <input
                            type="checkbox"
                            checked={forced || selected.has(region.id)}
                            disabled={forced}
                            onChange={() => toggle(region)}
                          />

                          <div className="findingBody">
                            <div className="findingTop">
                              <span>{region.label}</span>
                              {region.text && (
                                <span className="mono">{region.text}</span>
                              )}
                            </div>

                            <div className="meta">
                              {Math.round(region.confidence * 100)}% sure
                              {forced ? " - always covered" : ""}
                            </div>
                          </div>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </details>
            )}

            <div className="row end">
              <button
                className="btn primary"
                onClick={createPreview}
                disabled={busy}
              >
                {busy ? (
                  <>
                    <Spinner /> Working…
                  </>
                ) : (
                  "Create protected image"
                )}
              </button>
            </div>
          </Step>

          <Step
            n={3}
            title={`Ask ${provider} about it`}
            hint="Available after you create the protected image."
            state={stepState(2)}
            summary="Response received."
          >
            <textarea
              className="field"
              placeholder="Ask something about the image. Your question is also checked for private data."
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={3}
            />

            <div className="row split">
              <button
                className="btn"
                onClick={() => {
                  setProtectedUrl("");
                  setSessionId("");
                }}
              >
                Back
              </button>

              <button
                className="btn primary"
                onClick={send}
                disabled={!sessionId || busy}
              >
                {busy ? (
                  <>
                    <Spinner /> Sending…
                  </>
                ) : (
                  `Send to ${provider}`
                )}
              </button>
            </div>
          </Step>
        </>
      }
      outputs={
        <>
          <Output
            title="Privacy report"
            step={1}
            ready={Boolean(result)}
            empty="Upload an image in step 1 to see what was found."
          >
            <Report
              total={regions.length}
              types={countBy(regions, (r) => r.label)}
            >
              {forcedCount > 0 && (
                <Banner kind="error">
                  A secret or credential was found. It is always covered.
                </Banner>
              )}
            </Report>
          </Output>

          <Output
            title="What the AI receives"
            step={2}
            ready={Boolean(protectedUrl)}
            empty="Create the protected image in step 2 and it will appear here."
          >
            <div className="compare">
              <div>
                <div className="paneLabel">Your original</div>
                <img className="thumb" src={previewUrl} alt="Original" />
              </div>

              <div>
                <div className="paneLabel">Sent to {provider}</div>
                <img className="thumb" src={protectedUrl} alt="Protected" />
              </div>
            </div>

            <p className="hint">
              Hidden data such as GPS location is also removed when the image is
              re-saved.
            </p>
          </Output>

          <Output
            title="AI response"
            step={3}
            ready={Boolean(response)}
            empty="The answer from the AI will appear here after you send."
            actions={
              <>
                <CopyButton text={response} label="Copy" />
                <button className="btn small" onClick={startOver}>
                  Start over
                </button>
              </>
            }
          >
            <div className="responseText">{response}</div>
          </Output>
        </>
      }
    />
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/PdfPanel.jsx"] = r'''import { useState } from "react";

import {
  API,
  Banner,
  CopyButton,
  DropZone,
  Output,
  Report,
  Spinner,
  Step,
  Workspace,
  countBy,
} from "./ui.jsx";

function PageView({ page, regions, selected, onToggle }) {
  return (
    <div className="pdfPage">
      <div className="paneLabel">Page {page.page + 1}</div>

      <div className="pdfPageStage">
        <img src={`data:image/png;base64,${page.image_base64}`} alt="" />

        {onToggle &&
          regions.map((region) => {
            const forced = region.recommended_action === "BLOCK";
            const on = forced || selected.has(region.id);

            return (
              <button
                type="button"
                key={region.id}
                className={`regionBox ${on ? "on" : "off"} ${
                  forced ? "forced" : ""
                }`}
                title={`${region.label}${
                  region.text ? `: ${region.text}` : ""
                }${forced ? " (always removed)" : ""}`}
                onClick={() => onToggle(region)}
                style={{
                  left: `${(region.x / page.width) * 100}%`,
                  top: `${(region.y / page.height) * 100}%`,
                  width: `${(region.width / page.width) * 100}%`,
                  height: `${(region.height / page.height) * 100}%`,
                }}
              />
            );
          })}
      </div>
    </div>
  );
}

export default function PdfPanel({ provider }) {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [selected, setSelected] = useState(new Set());

  const [prepared, setPrepared] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");

  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const say = (kind, message) => setNotice({ kind, text: message });

  const stage = response ? 3 : prepared ? 2 : analysis ? 1 : 0;
  const stepState = (i) => (stage > i ? "done" : stage === i ? "active" : "locked");

  const regions = analysis?.regions || [];
  const forcedCount = regions.filter((r) => r.recommended_action === "BLOCK").length;
  const removedCount = selected.size + forcedCount;

  const hiddenInfo =
    analysis &&
    (analysis.notes.length > 0 || Object.keys(analysis.metadata).length > 0);

  function reset() {
    setAnalysis(null);
    setSelected(new Set());
    setPrepared(null);
    setResponse("");
    setPrompt("");
  }

  function startOver() {
    reset();
    setFile(null);
    setNotice(null);
  }

  async function onFile(chosen) {
    reset();
    setFile(chosen);

    try {
      setBusy(true);
      say("info", "Scanning the PDF. Scanned pages need OCR and take longer.");

      const form = new FormData();
      form.append("file", chosen);

      const res = await fetch(`${API}/pdf/analyze`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "PDF analysis failed.");

      setAnalysis(data);
      setSelected(
        new Set(
          data.regions
            .filter(
              (r) =>
                r.recommended_action !== "BLOCK" &&
                r.type !== "CONFIDENTIAL_CONTEXT",
            )
            .map((r) => r.id),
        ),
      );

      say(
        data.regions.length ? "warn" : "success",
        data.regions.length
          ? `${data.regions.length} sensitive area${
              data.regions.length === 1 ? "" : "s"
            } found. Click a box on a page to protect or unprotect it.`
          : "Nothing sensitive was detected. You can continue.",
      );
    } catch (error) {
      console.error(error);
      say("error", error.message || "Could not analyze the PDF.");
      setFile(null);
    } finally {
      setBusy(false);
    }
  }

  function toggle(region) {
    if (region.recommended_action === "BLOCK") return;

    setSelected((old) => {
      const next = new Set(old);
      if (next.has(region.id)) next.delete(region.id);
      else next.add(region.id);
      return next;
    });
  }

  async function createProtected() {
    try {
      setBusy(true);
      say("info", "Removing the selected content from the PDF…");

      const form = new FormData();
      form.append("file", file);
      form.append("selected_ids", [...selected].join(","));

      const res = await fetch(`${API}/pdf/prepare`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Could not protect the PDF.");

      setPrepared(data);
      say("success", `Protected PDF ready. ${provider} will receive only this version.`);
    } catch (error) {
      console.error(error);
      say("error", error.message || "Could not protect the PDF.");
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    try {
      setBusy(true);
      say("info", `Sending the protected PDF to ${provider}…`);

      const res = await fetch(`${API}/pdf/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: prepared.session_id, prompt }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "The AI request failed.");

      setResponse(data.response);
      setPrepared({ ...prepared, session_id: "" });
      say("success", "Done.");
    } catch (error) {
      console.error(error);
      say("error", error.message || `Could not reach ${provider}.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Workspace
      banner={<Banner kind={notice?.kind}>{notice?.text}</Banner>}
      steps={
        <>
          <Step
            n={1}
            title="Upload a PDF"
            hint="Personal data, secrets, hidden metadata and scanned text are found on your computer."
            state={stepState(0)}
          >
            {!file ? (
              <DropZone
                accept="application/pdf"
                onFile={onFile}
                disabled={busy}
                title="Drop a PDF here"
                hint="Up to 20 MB and 25 pages. Password-protected files are not supported."
              />
            ) : (
              <div className="fileRow">
                <span className="fileName">{file.name}</span>

                {busy && !analysis && (
                  <span className="loading">
                    <Spinner /> Scanning…
                  </span>
                )}

                <button className="btn small" onClick={startOver} disabled={busy}>
                  Choose another
                </button>
              </div>
            )}
          </Step>

          <Step
            n={2}
            title="Choose what to remove"
            hint="Available after the scan. Selected content is permanently removed from the file, not just covered."
            state={stepState(1)}
            summary={`${removedCount} area${removedCount === 1 ? "" : "s"} removed`}
            action={
              stage === 2 && (
                <button className="btn small" onClick={() => setPrepared(null)}>
                  Change
                </button>
              )
            }
          >
            <div className="legend">
              <span>
                <i className="swatch on" /> Will be removed
              </span>
              <span>
                <i className="swatch off" /> Stays visible
              </span>
              <span>
                <i className="swatch blocked" /> Secret, always removed
              </span>
            </div>

            <div className="pdfPages">
              {(analysis?.pages || []).map((page) => (
                <PageView
                  key={page.page}
                  page={page}
                  regions={regions.filter((r) => r.page === page.page)}
                  selected={selected}
                  onToggle={toggle}
                />
              ))}
            </div>

            {regions.length > 0 && (
              <details className="more">
                <summary>All findings ({regions.length})</summary>

                <ul className="findings">
                  {regions.map((region) => {
                    const forced = region.recommended_action === "BLOCK";

                    return (
                      <li key={region.id}>
                        <label
                          className={`finding ${forced ? "blockedItem" : ""}`}
                        >
                          <input
                            type="checkbox"
                            checked={forced || selected.has(region.id)}
                            disabled={forced}
                            onChange={() => toggle(region)}
                          />

                          <div className="findingBody">
                            <div className="findingTop">
                              <span>{region.label}</span>
                              {region.text && (
                                <span className="mono">{region.text}</span>
                              )}
                            </div>

                            <div className="meta">
                              Page {region.page + 1},{" "}
                              {Math.round(region.confidence * 100)}% sure
                              {forced ? " - always removed" : ""}
                            </div>
                          </div>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </details>
            )}

            <div className="row end">
              <button
                className="btn primary"
                onClick={createProtected}
                disabled={busy}
              >
                {busy ? (
                  <>
                    <Spinner /> Working…
                  </>
                ) : (
                  "Create protected PDF"
                )}
              </button>
            </div>
          </Step>

          <Step
            n={3}
            title={`Ask ${provider} about it`}
            hint="Available after you create the protected PDF."
            state={stepState(2)}
            summary="Response received."
          >
            <textarea
              className="field"
              placeholder="Ask something about the document. Your question is also checked for private data."
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={3}
            />

            <div className="row split">
              <button className="btn" onClick={() => setPrepared(null)}>
                Back
              </button>

              <button
                className="btn primary"
                onClick={send}
                disabled={!prepared?.session_id || busy}
              >
                {busy ? (
                  <>
                    <Spinner /> Sending…
                  </>
                ) : (
                  `Send to ${provider}`
                )}
              </button>
            </div>
          </Step>
        </>
      }
      outputs={
        <>
          <Output
            title="Privacy report"
            step={1}
            ready={Boolean(analysis)}
            empty="Upload a PDF in step 1 to see what was found."
          >
            <Report
              total={regions.length}
              types={countBy(regions, (r) => r.label)}
            >
              {forcedCount > 0 && (
                <Banner kind="error">
                  A secret or credential was found. It is always removed.
                </Banner>
              )}

              {hiddenInfo && (
                <div className="banner warn">
                  <div>
                    <strong>Hidden information in this file</strong>

                    <ul className="plain">
                      {Object.entries(analysis.metadata).map(([key, value]) => (
                        <li key={key}>
                          {key}: {value}
                        </li>
                      ))}
                      {analysis.notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </Report>
          </Output>

          <Output
            title="What the AI receives"
            step={2}
            ready={Boolean(prepared)}
            empty="Create the protected PDF in step 2 and it will appear here."
            actions={
              prepared && (
                <a
                  className="btn small"
                  href={`data:application/pdf;base64,${prepared.pdf_base64}`}
                  download="protected.pdf"
                >
                  Download
                </a>
              )
            }
          >
            {prepared && (
              <>
                {prepared.still_visible.length > 0 && (
                  <Banner kind="error">
                    Some protected values may still be readable in the output (
                    {prepared.still_visible.join(", ")}). Do not send this file.
                    Review it manually.
                  </Banner>
                )}

                <p className="hint">
                  {prepared.redacted} area{prepared.redacted === 1 ? "" : "s"}{" "}
                  removed. Document properties and hidden data were stripped.
                </p>

                <div className="pdfPages">
                  {prepared.pages.map((page) => (
                    <PageView
                      key={page.page}
                      page={page}
                      regions={[]}
                      selected={selected}
                    />
                  ))}
                </div>
              </>
            )}
          </Output>

          <Output
            title="AI response"
            step={3}
            ready={Boolean(response)}
            empty="The answer from the AI will appear here after you send."
            actions={
              <>
                <CopyButton text={response} label="Copy" />
                <button className="btn small" onClick={startOver}>
                  Start over
                </button>
              </>
            }
          >
            <div className="responseText">{response}</div>
          </Output>
        </>
      }
    />
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/App.jsx"] = r'''import { useEffect, useState } from "react";

import { API, Icon, Logo, PROVIDERS } from "./ui.jsx";
import TextPanel from "./TextPanel.jsx";
import ImagePanel from "./ImagePanel.jsx";
import PdfPanel from "./PdfPanel.jsx";

const TABS = [
  { id: "text", label: "Text", icon: "text" },
  { id: "image", label: "Images", icon: "image" },
  { id: "pdf", label: "PDF", icon: "pdf" },
];

function useBackendStatus() {
  const [online, setOnline] = useState(null);

  useEffect(() => {
    let active = true;

    async function check() {
      try {
        const res = await fetch(`${API}/health`);
        if (active) setOnline(res.ok);
      } catch {
        if (active) setOnline(false);
      }
    }

    check();
    const timer = setInterval(check, 15000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return online;
}

export default function App() {
  const [tab, setTab] = useState("text");
  const [provider, setProvider] = useState("gemini");
  const [theme, setTheme] = useState(
    () => document.documentElement.dataset.theme || "light",
  );

  const online = useBackendStatus();

  const providerName =
    PROVIDERS.find((item) => item.id === provider)?.name || "AI";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;

    try {
      localStorage.setItem("obscura-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="shell topbarInner">
          <div className="brand">
            <Logo />
            <span className="brandName">Obscura</span>
          </div>

          <nav className="tabs" role="tablist" aria-label="Content type">
            {TABS.map((item) => (
              <button
                key={item.id}
                role="tab"
                aria-selected={tab === item.id}
                className={`tab ${tab === item.id ? "active" : ""}`}
                onClick={() => setTab(item.id)}
              >
                <Icon name={item.icon} size={17} />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="topRight">
            <label className="modelPick">
              <span>AI model</span>

              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
              >
                {PROVIDERS.map((item) => (
                  <option
                    key={item.id}
                    value={item.id}
                    disabled={!item.available}
                  >
                    {item.name}
                    {item.available ? "" : " (coming soon)"}
                  </option>
                ))}
              </select>
            </label>

            <button
              className="iconBtn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={
                theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
              }
              title={theme === "dark" ? "Light mode" : "Dark mode"}
            >
              <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
            </button>

            <div
              className={`status ${
                online === null ? "" : online ? "online" : "offline"
              }`}
              title={
                online === false
                  ? "Start the backend: uvicorn app.main:app --reload --port 8000"
                  : ""
              }
            >
              <i className="dot" />
              {online === null
                ? "Connecting"
                : online
                  ? "Connected"
                  : "Backend offline"}
            </div>
          </div>
        </div>
      </header>

      <main className="shell main">
        <section className="intro">
          <h1>Use AI without handing over your private data.</h1>

          <p>
            Obscura finds personal details, secrets and sensitive images on your
            own computer, hides what you choose, and shows exactly what the AI
            will see before anything is sent.
          </p>

          <ul className="trust">
            <li>Detection runs locally</li>
            <li>You decide what is hidden</li>
            <li>Secrets are never sent</li>
          </ul>
        </section>

        <div hidden={tab !== "text"}>
          <TextPanel provider={providerName} />
        </div>

        <div hidden={tab !== "image"}>
          <ImagePanel provider={providerName} />
        </div>

        <div hidden={tab !== "pdf"}>
          <PdfPanel provider={providerName} />
        </div>
      </main>

      <footer className="shell footer">
        Automatic detection can miss things. Always check the preview before you
        send.
      </footer>
    </div>
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/styles.css"] = r'''/* ============================================================
   OBSCURA
   Idea: the redaction bar. Anything protected becomes a black bar,
   in both light and dark mode.
   ============================================================ */

:root,
:root[data-theme="light"] {
  color-scheme: light;

  --font: "Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;

  --bg: #eef1f7;
  --surface: #ffffff;
  --surface2: #f6f8fc;
  --line: #e0e5ef;
  --ink: #0e1525;
  --muted: #586377;

  --accent: #3558f0;
  --accent-ink: #ffffff;
  --accent-soft: #e8edff;

  --good: #17703f;
  --good-bg: #e3f4ea;
  --warn: #8a5300;
  --warn-bg: #fdf0d8;
  --bad: #b42318;
  --bad-bg: #fdeceb;

  --bar: #0b0f19;
  --bar-text: #ffffff;
  --bar-edge: #0b0f19;

  --shadow: 0 1px 2px rgba(15, 23, 42, 0.05), 0 4px 14px rgba(15, 23, 42, 0.05);
}

:root[data-theme="dark"] {
  color-scheme: dark;

  --bg: #0a0e17;
  --surface: #121826;
  --surface2: #182033;
  --line: #252f45;
  --ink: #edf1f9;
  --muted: #94a1b8;

  --accent: #7b93ff;
  --accent-ink: #0a0e17;
  --accent-soft: #1b2545;

  --good: #5bd08f;
  --good-bg: #12301f;
  --warn: #f0b44c;
  --warn-bg: #33270e;
  --bad: #ff8a80;
  --bad-bg: #3a1714;

  --bar: #02040a;
  --bar-text: #f3f6fc;
  --bar-edge: #43506e;

  --shadow: none;
}

* {
  box-sizing: border-box;
}

[hidden] {
  display: none !important;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 16px/1.6 var(--font);
  -webkit-font-smoothing: antialiased;
}

h1,
h2,
h3,
p,
ul,
ol {
  margin: 0;
}

button,
input,
textarea,
select {
  font: inherit;
  color: inherit;
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.mono {
  font-family: var(--mono);
  font-size: 0.88em;
  word-break: break-all;
}

.logoBg {
  fill: var(--accent);
}

.shell {
  max-width: 1360px;
  margin: 0 auto;
  padding-left: 28px;
  padding-right: 28px;
}

/* ---------------- Top bar ---------------- */

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}

.topbarInner {
  display: flex;
  align-items: center;
  gap: 20px;
  min-height: 68px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brandName {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.tabs {
  display: flex;
  gap: 2px;
  margin: 0 auto;
  padding: 4px;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  padding: 8px 18px;
  border-radius: 9px;
  font-weight: 600;
  font-size: 14.5px;
  color: var(--muted);
  cursor: pointer;
}

.tab:hover {
  color: var(--ink);
}

.tab.active {
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.14);
}

.topRight {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modelPick {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 6px 3px 12px;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}

.modelPick select {
  border: 0;
  background: transparent;
  font-weight: 700;
  font-size: 14px;
  padding: 6px 4px;
  cursor: pointer;
}

.iconBtn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--surface2);
  display: grid;
  place-items: center;
  cursor: pointer;
}

.iconBtn:hover {
  border-color: var(--muted);
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--surface2);
  border: 1px solid var(--line);
  white-space: nowrap;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted);
}

.status.online {
  color: var(--good);
}

.status.online .dot {
  background: var(--good);
}

.status.offline {
  color: var(--bad);
}

.status.offline .dot {
  background: var(--bad);
}

/* ---------------- Page ---------------- */

.main {
  padding-top: 32px;
  padding-bottom: 16px;
}

.intro {
  margin-bottom: 28px;
  max-width: 760px;
}

.intro h1 {
  font-size: clamp(26px, 3.2vw, 36px);
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 10px;
}

.intro p {
  color: var(--muted);
  font-size: 16.5px;
}

.trust {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 22px;
  list-style: none;
  padding: 0;
  margin-top: 16px;
  font-size: 14.5px;
  font-weight: 600;
}

.trust li::before {
  content: "✓";
  color: var(--good);
  margin-right: 8px;
  font-weight: 800;
}

.footer {
  color: var(--muted);
  font-size: 13.5px;
  padding-top: 8px;
  padding-bottom: 40px;
}

/* ---------------- Workspace: steps left, outputs right ---------------- */

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}

.stepsCol,
.outputsCol {
  display: grid;
  gap: 16px;
  align-content: start;
  min-width: 0;
}

.outputsCol {
  position: sticky;
  top: 88px;
  max-height: calc(100vh - 108px);
  overflow-y: auto;
  padding: 2px 4px 2px 2px;
}

.colTitle {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  font-weight: 700;
  color: var(--muted);
}

.colTitle::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--line);
}

/* Steps */

.step {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 20px 22px;
  box-shadow: var(--shadow);
}

.step.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.step.locked {
  background: transparent;
  border-style: dashed;
  box-shadow: none;
}

.step.locked .stepTitle h2,
.step.locked .sub {
  opacity: 0.65;
}

.stepHead {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.stepNum {
  width: 32px;
  height: 32px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
  border: 2px solid var(--line);
  color: var(--muted);
}

.step.active .stepNum {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-ink);
}

.step.done .stepNum {
  background: var(--good);
  border-color: var(--good);
  color: #fff;
}

.stepTitle {
  flex: 1;
  min-width: 0;
}

.stepTitle h2 {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.3;
  margin: 4px 0 2px;
}

.sub {
  color: var(--muted);
  font-size: 14.5px;
}

.stepBody {
  margin-top: 16px;
  display: grid;
  gap: 14px;
}

/* Outputs */

.output {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.output:not(.ready) {
  background: transparent;
  border-style: dashed;
  box-shadow: none;
}

.outHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  background: var(--surface2);
  border-bottom: 1px solid var(--line);
}

.output:not(.ready) .outHead {
  background: transparent;
  border-bottom: 0;
  padding-bottom: 0;
}

.outTitle {
  display: flex;
  align-items: center;
  gap: 10px;
}

.outTitle h3 {
  font-size: 16px;
  font-weight: 700;
}

.stepChip {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 2px 10px;
  border-radius: 999px;
}

.outBody {
  padding: 18px;
  display: grid;
  gap: 14px;
}

.empty {
  padding: 8px 18px 18px;
  color: var(--muted);
  font-size: 14.5px;
}

/* Report */

.report {
  display: grid;
  gap: 14px;
}

.reportTotal {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-weight: 600;
}

.reportTotal .big {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
}

.reportTotal.good {
  color: var(--good);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip,
.chipRisk {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 3px 10px;
  font-size: 13.5px;
  font-weight: 500;
}

/* ---------------- Layout helpers ---------------- */

.row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.row.split {
  justify-content: space-between;
}

.row.end {
  justify-content: flex-end;
}

.hint {
  color: var(--muted);
  font-size: 13.5px;
}

/* ---------------- Form ---------------- */

.field {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface2);
  padding: 14px 16px;
  resize: vertical;
  line-height: 1.65;
}

.field:focus {
  outline: 2px solid var(--accent);
  outline-offset: 0;
  background: var(--surface);
}

.fileRow {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.fileName {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------------- Buttons ---------------- */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 10px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 14.5px;
  cursor: pointer;
  text-decoration: none;
  color: var(--ink);
}

.btn:hover:not(:disabled) {
  background: var(--surface2);
  border-color: var(--muted);
}

.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-ink);
}

.btn.primary:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--accent);
  filter: brightness(1.08);
}

.btn.small {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  display: inline-block;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation-duration: 2.5s;
  }
}

.loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 14px;
}

/* ---------------- Banners ---------------- */

.banner {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14.5px;
}

.banner.info {
  background: var(--accent-soft);
  border-color: transparent;
}

.banner.success {
  background: var(--good-bg);
  color: var(--good);
  border-color: transparent;
}

.banner.warn {
  background: var(--warn-bg);
  color: var(--warn);
  border-color: transparent;
}

.banner.error {
  background: var(--bad-bg);
  color: var(--bad);
  border-color: transparent;
  font-weight: 600;
}

.plain {
  margin: 6px 0 0;
  padding-left: 18px;
}

/* ---------------- Highlighted text ---------------- */

.marked {
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
  line-height: 2.1;
}

.mark {
  font: inherit;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 5px;
  padding: 1px 7px;
  margin: 0 1px;
}

.mark.on {
  background: var(--bar);
  color: var(--bar-text);
  border-color: var(--bar-edge);
}

.mark.off {
  background: var(--warn-bg);
  color: var(--warn);
  border: 1px dashed var(--warn);
}

.mark.blocked {
  background: var(--bad);
  color: #fff;
  border-color: var(--bad);
  cursor: not-allowed;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  font-size: 13px;
  color: var(--muted);
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 10px;
  border-radius: 3px;
  margin-right: 6px;
  vertical-align: -1px;
}

.swatch.on {
  background: var(--bar);
  border: 1px solid var(--bar-edge);
}

.swatch.off {
  background: var(--warn-bg);
  border: 1px dashed var(--warn);
}

.swatch.blocked {
  background: var(--bad);
}

/* ---------------- Findings ---------------- */

.more summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 14.5px;
  margin-bottom: 10px;
}

.findings {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 8px;
}

.finding {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
}

.finding:hover {
  background: var(--surface2);
}

.finding input {
  width: 17px;
  height: 17px;
  margin-top: 4px;
  accent-color: var(--accent);
}

.blockedItem {
  background: var(--bad-bg);
  cursor: not-allowed;
}

.findingBody {
  flex: 1;
  min-width: 0;
}

.findingTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
}

.meta {
  color: var(--muted);
  font-size: 13px;
}

.reason {
  color: var(--muted);
  font-size: 13px;
  margin-top: 4px;
}

.risk {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 9px;
  border-radius: 999px;
  white-space: nowrap;
}

.risk.critical {
  background: var(--bad-bg);
  color: var(--bad);
}

.risk.high {
  background: var(--warn-bg);
  color: var(--warn);
}

.risk.medium {
  background: var(--accent-soft);
  color: var(--accent);
}

.risk.low {
  background: var(--good-bg);
  color: var(--good);
}

/* ---------------- Output content ---------------- */

.compare {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.paneLabel {
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
  margin-bottom: 6px;
}

.pane {
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 110px;
  line-height: 1.8;
  font-size: 15px;
}

.token {
  font-family: var(--mono);
  font-size: 0.84em;
  background: var(--bar);
  color: var(--bar-text);
  border: 1px solid var(--bar-edge);
  padding: 1px 7px;
  border-radius: 5px;
  white-space: nowrap;
}

.aliases {
  display: grid;
  gap: 8px;
}

.aliasRow {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 14px;
}

.arrow {
  color: var(--muted);
  font-size: 13px;
}

.responseText {
  white-space: pre-wrap;
  line-height: 1.8;
  max-width: 78ch;
}

/* ---------------- Dropzone ---------------- */

.dropzone {
  border: 1.5px dashed var(--line);
  border-radius: 14px;
  padding: 34px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  background: var(--surface2);
}

.dropzone.over {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.dropzone.disabled {
  opacity: 0.6;
}

.dropTitle {
  font-weight: 700;
  font-size: 17px;
}

.dropHint {
  color: var(--muted);
  font-size: 13.5px;
  margin-bottom: 10px;
}

/* ---------------- Image and PDF ---------------- */

.imageStage {
  position: relative;
  justify-self: start;
  max-width: 100%;
}

.imageStage img {
  display: block;
  max-width: 100%;
  max-height: 520px;
  border-radius: 10px;
  border: 1px solid var(--line);
}

.thumb {
  display: block;
  width: 100%;
  border-radius: 10px;
  border: 1px solid var(--line);
}

.regionBox {
  position: absolute;
  padding: 0;
  cursor: pointer;
  box-sizing: border-box;
  border: 2px solid var(--accent);
  background: rgba(53, 88, 240, 0.12);
}

.regionBox.on {
  border-color: #000;
  background: rgba(0, 0, 0, 0.8);
}

.regionBox.off {
  border-style: dashed;
  border-color: #e08a00;
  background: rgba(224, 138, 0, 0.14);
}

.regionBox.forced {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.82);
  cursor: not-allowed;
}

.pdfPages {
  display: grid;
  gap: 16px;
  max-height: 560px;
  overflow: auto;
  padding: 2px;
}

.pdfPage {
  max-width: 720px;
}

.pdfPageStage {
  position: relative;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

.pdfPageStage img {
  display: block;
  width: 100%;
}

/* ---------------- Responsive ---------------- */

@media (max-width: 1100px) {
  .workspace {
    grid-template-columns: minmax(0, 1fr);
  }

  .outputsCol {
    position: static;
    max-height: none;
    overflow: visible;
  }
}

@media (max-width: 900px) {
  .topbarInner {
    flex-wrap: wrap;
    padding-top: 10px;
    padding-bottom: 10px;
    gap: 12px;
  }

  .tabs {
    order: 3;
    width: 100%;
    margin: 0;
  }

  .tab {
    flex: 1;
    justify-content: center;
  }

  .topRight {
    margin-left: auto;
  }

  .modelPick span {
    display: none;
  }
}

@media (max-width: 600px) {
  .shell {
    padding-left: 16px;
    padding-right: 16px;
  }

  .status {
    display: none;
  }

  .step {
    padding: 16px;
  }

  .row.split {
    flex-direction: column;
    align-items: stretch;
  }

  .row.end {
    justify-content: stretch;
  }

  .row.end .btn,
  .row.split > .btn {
    width: 100%;
  }
}
'''

# ----------------------------------------------------------------------
for path, content in FILES.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("wrote", path)

print("\nDone. Run:  cd frontend  then  npm run dev")