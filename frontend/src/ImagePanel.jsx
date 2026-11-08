import { useEffect, useState } from "react";

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
