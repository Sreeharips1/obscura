import { useMemo, useState } from "react";

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
