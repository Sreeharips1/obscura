# apply_ui.py  -- run from the repo root
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
    <title>OBSCURA - Private AI gateway</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
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

export function Stepper({ steps, current }) {
  return (
    <ol className="stepper">
      {steps.map((label, index) => (
        <li
          key={label}
          className={
            index < current ? "done" : index === current ? "current" : ""
          }
          aria-current={index === current ? "step" : undefined}
        >
          <span className="stepDot">{index < current ? "✓" : index + 1}</span>
          <span className="stepLabel">{label}</span>
        </li>
      ))}
    </ol>
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
    <button type="button" className="btn ghost small" onClick={copy}>
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
        className="btn"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Choose file
      </button>
    </div>
  );
}

export function ResponseCard({ text, onReset, note }) {
  return (
    <section className="card">
      <div className="cardHead split">
        <div>
          <h2>AI response</h2>
          {note && <p className="sub">{note}</p>}
        </div>

        <div className="row">
          <CopyButton text={text} label="Copy response" />
          <button type="button" className="btn small" onClick={onReset}>
            Start over
          </button>
        </div>
      </div>

      <div className="responseText">{text}</div>
    </section>
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/TextPanel.jsx"] = r'''import { useMemo, useState } from "react";

import {
  API,
  Banner,
  CopyButton,
  ResponseCard,
  RISK_ORDER,
  RiskBadge,
  Spinner,
  Stepper,
  TokenText,
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

export default function TextPanel() {
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

  const current = aiResponse ? 3 : sanitized ? 2 : analyzed ? 1 : 0;

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
          } found. Review them below.`,
        );
      } else {
        say(
          "success",
          "Nothing sensitive was detected. Detection is automatic, so give your text a quick read yourself.",
        );
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
      say("success", "Protected version ready. Check it before sending.");
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
      say("info", "Sending the protected version to Gemini…");

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
      say("error", error.message || "Could not reach Gemini.");
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
    <div className="panel">
      <Stepper steps={["Write", "Review", "Send"]} current={current} />

      <section className="card">
        <div className="cardHead">
          <h2>Your message</h2>
          <p className="sub">
            Write or paste what you want to ask the AI. Nothing leaves your
            computer until you confirm.
          </p>
        </div>

        <textarea
          className="field"
          value={text}
          onChange={handleTextChange}
          placeholder="Example: My name is Aaron Smith, my phone is 9876543210. Write a job application email to Cisco."
          rows={6}
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
      </section>

      <Banner kind={notice?.kind}>{notice?.text}</Banner>

      {analyzed && !sanitized && !aiResponse && (
        <section className="card">
          <div className="cardHead split">
            <div>
              <h2>Review</h2>
              <p className="sub">
                {hasDetections
                  ? "Highlighted text will be replaced with placeholders before it reaches the AI. Click a highlight to protect or unprotect it."
                  : "No sensitive items were detected."}
              </p>
            </div>

            {hasDetections && (
              <span className="pill">
                {selectedCount} of {detections.length} protected
              </span>
            )}
          </div>

          {hasDetections && (
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
            </>
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
        </section>
      )}

      {sanitized && !aiResponse && (
        <section className="card">
          <div className="cardHead">
            <h2>What Gemini will receive</h2>
            <p className="sub">
              This is the exact text that leaves your computer. The mapping
              back to your real values stays in the OBSCURA backend.
            </p>
          </div>

          <div className="compare">
            <div>
              <div className="paneLabel">Your original</div>
              <div className="pane">{text}</div>
            </div>

            <div>
              <div className="paneLabel">Sent to Gemini</div>
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

          <div className="row split">
            <div className="row">
              <button className="btn" onClick={backToReview}>
                Back to review
              </button>
              <CopyButton text={sanitized} label="Copy protected text" />
            </div>

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
                "Send to Gemini"
              )}
            </button>
          </div>
        </section>
      )}

      {aiResponse && (
        <ResponseCard
          text={aiResponse}
          onReset={startOver}
          note="Private values were restored by the backend, not by Gemini."
        />
      )}
    </div>
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/ImagePanel.jsx"] = r'''import { useEffect, useState } from "react";

import {
  API,
  Banner,
  DropZone,
  ResponseCard,
  Spinner,
  Stepper,
} from "./ui.jsx";

export default function ImagePanel() {
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

  const current = response ? 3 : protectedUrl ? 2 : result ? 1 : 0;

  const hasForced = result?.regions.some(
    (r) => r.recommended_action === "BLOCK",
  );

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
          : "Nothing sensitive was detected. Detection is automatic, so check the image yourself too.",
      );
    } catch (error) {
      console.error(error);
      say("error", error.message || "Could not analyze the image.");
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
      say("success", "Protected image ready. Gemini will receive only this version.");
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
      say("info", "Sending the protected image to Gemini…");

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
      say("error", error.message || "Could not reach Gemini.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <Stepper steps={["Upload", "Review", "Send"]} current={current} />

      {!file && (
        <section className="card">
          <div className="cardHead">
            <h2>Upload an image</h2>
            <p className="sub">
              Text, QR codes, barcodes, faces, license plates and screens
              (phones, laptops, TVs) are found on your computer. Selected areas
              are covered with solid black before anything is sent.
            </p>
          </div>

          <DropZone
            accept="image/png,image/jpeg,image/webp"
            onFile={onFile}
            disabled={busy}
            title="Drop an image here"
            hint="PNG, JPEG or WebP, up to 8 MB"
          />
        </section>
      )}

      <Banner kind={notice?.kind}>{notice?.text}</Banner>

      {file && !protectedUrl && !response && (
        <section className="card">
          <div className="cardHead split">
            <div>
              <h2>Review</h2>
              <p className="sub">{file.name}</p>
            </div>

            <button className="btn small" onClick={startOver} disabled={busy}>
              Choose another image
            </button>
          </div>

          {busy && !result && (
            <div className="loading">
              <Spinner /> Scanning…
            </div>
          )}

          <div className="imageStage">
            <img src={previewUrl} alt="Uploaded" />

            {result &&
              result.regions.map((region) => {
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
                    }${forced ? " (always hidden)" : ""}`}
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

          {result && (
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
          )}

          {hasForced && (
            <Banner kind="error">
              A secret or credential was found in the image. It will always be
              covered.
            </Banner>
          )}

          {result && result.regions.length > 0 && (
            <details className="more">
              <summary>All findings ({result.regions.length})</summary>

              <ul className="findings">
                {result.regions.map((region) => {
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

          {result && (
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
          )}
        </section>
      )}

      {protectedUrl && !response && (
        <section className="card">
          <div className="cardHead">
            <h2>What Gemini will receive</h2>
            <p className="sub">
              Metadata such as GPS location is also removed when the image is
              re-saved.
            </p>
          </div>

          <div className="compare">
            <div>
              <div className="paneLabel">Your original</div>
              <img className="thumb" src={previewUrl} alt="Original" />
            </div>

            <div>
              <div className="paneLabel">Sent to Gemini</div>
              <img className="thumb" src={protectedUrl} alt="Protected" />
            </div>
          </div>

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
              Back to review
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
                "Send to Gemini"
              )}
            </button>
          </div>
        </section>
      )}

      {response && <ResponseCard text={response} onReset={startOver} />}
    </div>
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/PdfPanel.jsx"] = r'''import { useState } from "react";

import {
  API,
  Banner,
  DropZone,
  ResponseCard,
  Spinner,
  Stepper,
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

export default function PdfPanel() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [selected, setSelected] = useState(new Set());

  const [prepared, setPrepared] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");

  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const say = (kind, message) => setNotice({ kind, text: message });

  const current = response ? 3 : prepared ? 2 : analysis ? 1 : 0;

  const hasForced = analysis?.regions.some(
    (r) => r.recommended_action === "BLOCK",
  );

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
          : "Nothing sensitive was detected. Detection is automatic, so review the document yourself too.",
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
      say("success", "Protected PDF ready. Gemini will receive only this version.");
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
      say("info", "Sending the protected PDF to Gemini…");

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
      say("error", error.message || "Could not reach Gemini.");
    } finally {
      setBusy(false);
    }
  }

  const hidden =
    analysis &&
    (analysis.notes.length > 0 || Object.keys(analysis.metadata).length > 0);

  return (
    <div className="panel">
      <Stepper steps={["Upload", "Review", "Send"]} current={current} />

      {!file && (
        <section className="card">
          <div className="cardHead">
            <h2>Upload a PDF</h2>
            <p className="sub">
              Personal data, secrets, hidden metadata and scanned text are found
              on your computer. Selected content is permanently removed from the
              file, not just covered.
            </p>
          </div>

          <DropZone
            accept="application/pdf"
            onFile={onFile}
            disabled={busy}
            title="Drop a PDF here"
            hint="Up to 20 MB and 25 pages. Password-protected files are not supported."
          />
        </section>
      )}

      <Banner kind={notice?.kind}>{notice?.text}</Banner>

      {file && !prepared && !response && (
        <section className="card">
          <div className="cardHead split">
            <div>
              <h2>Review</h2>
              <p className="sub">{file.name}</p>
            </div>

            <button className="btn small" onClick={startOver} disabled={busy}>
              Choose another PDF
            </button>
          </div>

          {busy && !analysis && (
            <div className="loading">
              <Spinner /> Scanning…
            </div>
          )}

          {hidden && (
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

          {hasForced && (
            <Banner kind="error">
              A secret or credential was found. It will always be removed.
            </Banner>
          )}

          {analysis && (
            <>
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
                {analysis.pages.map((page) => (
                  <PageView
                    key={page.page}
                    page={page}
                    regions={analysis.regions.filter(
                      (r) => r.page === page.page,
                    )}
                    selected={selected}
                    onToggle={toggle}
                  />
                ))}
              </div>

              {analysis.regions.length > 0 && (
                <details className="more">
                  <summary>All findings ({analysis.regions.length})</summary>

                  <ul className="findings">
                    {analysis.regions.map((region) => {
                      const forced = region.recommended_action === "BLOCK";

                      return (
                        <li key={region.id}>
                          <label
                            className={`finding ${
                              forced ? "blockedItem" : ""
                            }`}
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
            </>
          )}
        </section>
      )}

      {prepared && !response && (
        <section className="card">
          <div className="cardHead">
            <h2>What Gemini will receive</h2>
            <p className="sub">
              {prepared.redacted} area{prepared.redacted === 1 ? "" : "s"}{" "}
              removed. Document properties and hidden data were stripped.
            </p>
          </div>

          {prepared.still_visible.length > 0 && (
            <Banner kind="error">
              Some protected values may still be readable in the output (
              {prepared.still_visible.join(", ")}). Do not send this file.
              Review it manually.
            </Banner>
          )}

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

          <a
            className="btn small linkBtn"
            href={`data:application/pdf;base64,${prepared.pdf_base64}`}
            download="protected.pdf"
          >
            Download protected PDF
          </a>

          <textarea
            className="field"
            placeholder="Ask something about the document. Your question is also checked for private data."
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={3}
          />

          <div className="row split">
            <button className="btn" onClick={() => setPrepared(null)}>
              Back to review
            </button>

            <button
              className="btn primary"
              onClick={send}
              disabled={!prepared.session_id || busy}
            >
              {busy ? (
                <>
                  <Spinner /> Sending…
                </>
              ) : (
                "Send to Gemini"
              )}
            </button>
          </div>
        </section>
      )}

      {response && <ResponseCard text={response} onReset={startOver} />}
    </div>
  );
}
'''

# ----------------------------------------------------------------------
FILES["frontend/src/App.jsx"] = r'''import { useEffect, useState } from "react";

import { API } from "./ui.jsx";
import TextPanel from "./TextPanel.jsx";
import ImagePanel from "./ImagePanel.jsx";
import PdfPanel from "./PdfPanel.jsx";

const TABS = [
  { id: "text", label: "Text" },
  { id: "image", label: "Images" },
  { id: "pdf", label: "PDF" },
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
  const online = useBackendStatus();

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbarInner">
          <div className="wordmark" aria-label="OBSCURA">
            OBS<span className="redact">CUR</span>A
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
                {item.label}
              </button>
            ))}
          </nav>

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
                ? "Backend connected"
                : "Backend offline"}
          </div>
        </div>
      </header>

      <main className="main">
        <section className="intro">
          <h1>Use AI without handing over your private data.</h1>

          <p>
            OBSCURA finds personal details, secrets and sensitive images on your
            own computer, hides what you choose, and shows you exactly what the
            AI will see before anything is sent.
          </p>

          <ul className="trust">
            <li>Detection runs locally</li>
            <li>You decide what is hidden</li>
            <li>Secrets are never sent</li>
          </ul>
        </section>

        <div hidden={tab !== "text"}>
          <TextPanel />
        </div>

        <div hidden={tab !== "image"}>
          <ImagePanel />
        </div>

        <div hidden={tab !== "pdf"}>
          <PdfPanel />
        </div>
      </main>

      <footer className="footer">
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
   Visual idea: the redaction bar. Protected = black bar, everywhere.
   ============================================================ */

:root {
  color-scheme: light dark;

  --font: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Consolas, monospace;

  --bg: #f3f5f8;
  --surface: #ffffff;
  --surface2: #f7f8fa;
  --line: #dfe3ea;
  --ink: #14181f;
  --muted: #5b6472;

  --accent: #2f5bea;
  --accent-ink: #ffffff;
  --accent-soft: #eaf0ff;

  --good: #1f7a4d;
  --good-bg: #e6f4ec;
  --warn: #8a5300;
  --warn-bg: #fdf1dc;
  --bad: #b42318;
  --bad-bg: #fdeceb;

  --bar: #14181f;
  --bar-text: #ffffff;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1218;
    --surface: #171b23;
    --surface2: #1d222c;
    --line: #2a303c;
    --ink: #eef1f6;
    --muted: #98a2b3;

    --accent: #7c9cff;
    --accent-ink: #0f1218;
    --accent-soft: #1b2542;

    --good: #5bd08f;
    --good-bg: #14301f;
    --warn: #f0b44c;
    --warn-bg: #33270e;
    --bad: #ff8a80;
    --bad-bg: #3a1714;

    --bar: #eef1f6;
    --bar-text: #0f1218;
  }
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
  font: 15px/1.55 var(--font);
  -webkit-font-smoothing: antialiased;
}

h1,
h2,
p,
ul,
ol {
  margin: 0;
}

button,
input,
textarea {
  font: inherit;
  color: inherit;
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.mono {
  font-family: var(--mono);
  font-size: 0.92em;
  word-break: break-all;
}

/* ---------------- Top bar ---------------- */

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}

.topbarInner {
  max-width: 1040px;
  margin: 0 auto;
  padding: 0 24px;
  min-height: 60px;
  display: flex;
  align-items: center;
  gap: 28px;
  flex-wrap: wrap;
}

.wordmark {
  font-weight: 600;
  font-size: 19px;
  letter-spacing: 0.14em;
}

.redact {
  background: var(--bar);
  color: var(--bar);
  border-radius: 2px;
  padding: 0 1px;
  margin: 0 1px;
}

.tabs {
  display: flex;
  gap: 4px;
  align-self: stretch;
}

.tab {
  border: 0;
  background: none;
  padding: 0 14px;
  cursor: pointer;
  color: var(--muted);
  font-weight: 500;
  border-bottom: 2px solid transparent;
  min-height: 60px;
}

.tab:hover {
  color: var(--ink);
}

.tab.active {
  color: var(--ink);
  border-bottom-color: var(--accent);
}

.status {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted);
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
  max-width: 1040px;
  margin: 0 auto;
  padding: 36px 24px 24px;
}

.intro {
  margin-bottom: 28px;
  max-width: 720px;
}

.intro h1 {
  font-size: clamp(26px, 4vw, 36px);
  line-height: 1.15;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-bottom: 12px;
}

.intro p {
  color: var(--muted);
  max-width: 62ch;
}

.trust {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  list-style: none;
  padding: 0;
  margin-top: 16px;
  font-size: 14px;
  font-weight: 500;
}

.trust li::before {
  content: "";
  display: inline-block;
  width: 14px;
  height: 8px;
  margin-right: 8px;
  border-radius: 2px;
  background: var(--bar);
  vertical-align: 1px;
}

.footer {
  max-width: 1040px;
  margin: 0 auto;
  padding: 8px 24px 40px;
  color: var(--muted);
  font-size: 13px;
}

.panel {
  display: grid;
  gap: 16px;
}

/* ---------------- Stepper ---------------- */

.stepper {
  list-style: none;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.stepper li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-weight: 500;
  font-size: 14px;
}

.stepper li:not(:last-child)::after {
  content: "";
  width: 40px;
  height: 1px;
  background: var(--line);
  margin-left: 4px;
}

.stepDot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1.5px solid var(--line);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 600;
  flex: none;
}

.stepper .current {
  color: var(--ink);
}

.stepper .current .stepDot {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-ink);
}

.stepper .done .stepDot {
  background: var(--good);
  border-color: var(--good);
  color: #fff;
}

/* ---------------- Cards ---------------- */

.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 22px;
  display: grid;
  gap: 16px;
}

.cardHead h2 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.sub {
  color: var(--muted);
  font-size: 14px;
  max-width: 70ch;
}

.split {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.row.split {
  align-items: center;
}

.row.end {
  justify-content: flex-end;
}

.hint {
  color: var(--muted);
  font-size: 13px;
}

.pill {
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

/* ---------------- Form ---------------- */

.field {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface2);
  padding: 12px 14px;
  resize: vertical;
  line-height: 1.6;
}

.field:focus {
  outline: 2px solid var(--accent);
  outline-offset: 0;
  background: var(--surface);
}

/* ---------------- Buttons ---------------- */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 8px;
  padding: 9px 16px;
  font-weight: 500;
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
  filter: brightness(1.08);
  background: var(--accent);
  border-color: var(--accent);
}

.btn.ghost {
  border-color: transparent;
  background: none;
}

.btn.small {
  padding: 5px 11px;
  font-size: 13px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.linkBtn {
  justify-self: start;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation-duration: 2s;
  }
}

.loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
}

/* ---------------- Banners ---------------- */

.banner {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 14px;
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
  font-weight: 500;
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
  border-radius: 10px;
  padding: 14px 16px;
  line-height: 2;
}

.mark {
  font: inherit;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 1px 6px;
  margin: 0 1px;
}

.mark.on {
  background: var(--bar);
  color: var(--bar-text);
}

.mark.off {
  background: var(--warn-bg);
  color: var(--warn);
  border: 1px dashed var(--warn);
}

.mark.blocked {
  background: var(--bad);
  color: #fff;
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
}

.swatch.off {
  background: var(--warn-bg);
  border: 1px dashed var(--warn);
}

.swatch.blocked {
  background: var(--bad);
}

/* ---------------- Findings ---------------- */

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
  border-radius: 10px;
  cursor: pointer;
}

.finding:hover {
  background: var(--surface2);
}

.finding input {
  width: 17px;
  height: 17px;
  margin-top: 3px;
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
  font-weight: 500;
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
  font-weight: 600;
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

.more summary {
  cursor: pointer;
  font-weight: 500;
  margin-bottom: 10px;
}

/* ---------------- Preview ---------------- */

.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.paneLabel {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  margin-bottom: 6px;
}

.pane {
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 120px;
  line-height: 1.7;
}

.token {
  font-family: var(--mono);
  font-size: 0.86em;
  background: var(--bar);
  color: var(--bar-text);
  padding: 1px 6px;
  border-radius: 4px;
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
  line-height: 1.75;
  max-width: 80ch;
}

/* ---------------- Dropzone ---------------- */

.dropzone {
  border: 1.5px dashed var(--line);
  border-radius: 12px;
  padding: 36px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
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
  font-weight: 600;
  font-size: 16px;
}

.dropHint {
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 8px;
}

/* ---------------- Image and PDF stages ---------------- */

.imageStage {
  position: relative;
  justify-self: start;
  max-width: 100%;
}

.imageStage img {
  display: block;
  max-width: 100%;
  max-height: 640px;
  border-radius: 8px;
  border: 1px solid var(--line);
}

.thumb {
  display: block;
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--line);
}

.regionBox {
  position: absolute;
  padding: 0;
  cursor: pointer;
  box-sizing: border-box;
  border: 2px solid var(--accent);
  background: rgba(47, 91, 234, 0.12);
}

.regionBox.on {
  border-color: var(--bar);
  background: rgba(20, 24, 31, 0.78);
}

.regionBox.off {
  border-style: dashed;
  border-color: #d97706;
  background: rgba(217, 119, 6, 0.12);
}

.regionBox.forced {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.8);
  cursor: not-allowed;
}

.pdfPages {
  display: grid;
  gap: 18px;
  max-height: 820px;
  overflow: auto;
  padding: 2px;
}

.pdfPage {
  max-width: 760px;
}

.pdfPageStage {
  position: relative;
  border: 1px solid var(--line);
  border-radius: 6px;
  overflow: hidden;
}

.pdfPageStage img {
  display: block;
  width: 100%;
}

/* ---------------- Small screens ---------------- */

@media (max-width: 760px) {
  .topbarInner {
    gap: 8px 16px;
    padding: 8px 16px;
  }

  .status {
    margin-left: 0;
    width: 100%;
  }

  .tab {
    min-height: 44px;
  }

  .main {
    padding: 24px 16px 16px;
  }

  .compare {
    grid-template-columns: 1fr;
  }

  .stepper li:not(:last-child)::after {
    width: 16px;
  }

  .split {
    flex-direction: column;
    align-items: stretch;
  }

  .row.split {
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