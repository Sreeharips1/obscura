import { useState } from "react";

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
