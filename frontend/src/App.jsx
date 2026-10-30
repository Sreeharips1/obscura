import { useMemo, useState } from "react";

const API = "http://localhost:8000/api";

// ============================================================
// RISK CONFIGURATION
// ============================================================

const RISK_ORDER = {
  CRITICAL: 1,
  HIGH: 2,
  MEDIUM: 3,
  LOW: 4,
};

const RISK_LABELS = {
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

// ============================================================
// HELPERS
// ============================================================

function riskClass(risk) {
  return risk.toLowerCase();
}

function groupDetections(detections) {
  return [...detections].sort(
    (a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk],
  );
}

function getActionLabel(action) {
  switch (action) {
    case "BLOCK":
      return "Blocked";

    case "PSEUDONYMIZE":
      return "Pseudonymize";

    case "REPLACE":
      return "Replace";

    case "ASK_USER":
      return "Review";

    default:
      return action;
  }
}

// ============================================================
// APP
// ============================================================

export default function App() {
  // ----------------------------------------------------------
  // INPUT
  // ----------------------------------------------------------

  const [text, setText] = useState("");

  // ----------------------------------------------------------
  // PRIVACY DETECTIONS
  // ----------------------------------------------------------

  const [detections, setDetections] = useState([]);

  const [selected, setSelected] = useState(new Set());

  // ----------------------------------------------------------
  // PROTECTED REQUEST
  // ----------------------------------------------------------

  const [sanitized, setSanitized] = useState("");

  const [aliases, setAliases] = useState([]);

  const [sessionId, setSessionId] = useState("");

  // ----------------------------------------------------------
  // AI RESPONSE
  // ----------------------------------------------------------

  const [aiResponse, setAiResponse] = useState("");

  // ----------------------------------------------------------
  // UI STATE
  // ----------------------------------------------------------

  const [status, setStatus] = useState("");

  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [isPreparing, setIsPreparing] = useState(false);

  const [isSending, setIsSending] = useState(false);

  // ----------------------------------------------------------
  // DERIVED DATA
  // ----------------------------------------------------------

  const hasDetections = detections.length > 0;

  const orderedDetections = groupDetections(detections);

  const selectedCount = selected.size;

  const selectedLabels = useMemo(
    () => detections.filter((detection) => selected.has(detection.id)),
    [detections, selected],
  );

  // ==========================================================
  // ANALYZE TEXT
  // ==========================================================

  async function analyze() {
    if (!text.trim()) {
      return;
    }

    try {
      setIsAnalyzing(true);

      setStatus("Checking for potentially sensitive information...");

      // Clear previous result.

      setSanitized("");

      setAliases([]);

      setSessionId("");

      setAiResponse("");

      const response = await fetch(`${API}/privacy/analyze`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          text,
        }),
      });

      if (!response.ok) {
        throw new Error("Privacy analysis failed.");
      }

      const data = await response.json();

      const foundDetections = data.detections || [];

      setDetections(foundDetections);

      // Automatically select everything
      // except BLOCK items.

      const recommendedSelection = foundDetections
        .filter((detection) => detection.recommended_action !== "BLOCK")
        .map((detection) => detection.id);

      setSelected(new Set(recommendedSelection));

      if (foundDetections.length) {
        setStatus(
          `${foundDetections.length} potentially sensitive item${
            foundDetections.length === 1 ? "" : "s"
          } detected.`,
        );
      } else {
        setStatus("No supported sensitive patterns were detected.");
      }
    } catch (error) {
      console.error(error);

      setStatus(error.message || "Unable to analyze the text.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  // ==========================================================
  // TOGGLE DETECTION
  // ==========================================================

  function toggle(id) {
    const detection = detections.find((item) => item.id === id);

    // BLOCK items cannot be selected
    // because they must never be sent.

    if (detection?.recommended_action === "BLOCK") {
      return;
    }

    setSelected((old) => {
      const next = new Set(old);

      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }

      return next;
    });
  }

  // ==========================================================
  // SELECT RECOMMENDED
  // ==========================================================

  function selectRecommended() {
    const recommended = detections
      .filter((detection) => detection.recommended_action !== "BLOCK")
      .map((detection) => detection.id);

    setSelected(new Set(recommended));

    setStatus("Recommended privacy protections selected.");
  }

  // ==========================================================
  // CLEAR ALL
  // ==========================================================

  function clearAll() {
    setSelected(new Set());

    setStatus("All optional privacy protections cleared.");
  }

  // ==========================================================
  // CREATE PROTECTED PREVIEW
  // ==========================================================

  async function createPreview() {
    if (selectedCount === 0) {
      setStatus("Select at least one item to protect.");

      return;
    }

    try {
      setIsPreparing(true);

      setStatus("Creating protected AI input...");

      const response = await fetch(`${API}/privacy/prepare`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          text,

          selected_detection_ids: [...selected],
        }),
      });

      const data = await response.json();

      // ------------------------------------------------------
      // BLOCKED
      // ------------------------------------------------------

      if (data.blocked) {
        setSanitized("");

        setAliases([]);

        setSessionId("");

        setStatus(data.warning || "This request cannot be sent.");

        return;
      }

      // ------------------------------------------------------
      // SUCCESS
      // ------------------------------------------------------

      setSessionId(data.session_id);

      setSanitized(data.sanitized_text);

      setAliases(data.aliases || []);

      setStatus(
        "Protected preview ready. Review exactly what Gemini will receive.",
      );
    } catch (error) {
      console.error(error);

      setStatus(error.message || "Unable to create protected preview.");
    } finally {
      setIsPreparing(false);
    }
  }

  // ==========================================================
  // SEND TO GEMINI
  // ==========================================================

  async function sendToAI() {
    if (!sessionId) {
      setStatus("Create a protected preview first.");

      return;
    }

    try {
      setIsSending(true);

      setStatus("Sending only protected data to Gemini...");

      const response = await fetch(`${API}/chat/send`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "AI request failed.");
      }

      // IMPORTANT:
      //
      // We do NOT restore anything
      // in the frontend.
      //
      // The backend has already:
      //
      // fake value
      //      ↓
      // original value
      //
      // before returning the response.

      setAiResponse(data.response);

      setSessionId("");

      setStatus(
        "Response received. Original private values were restored inside the trusted backend.",
      );
    } catch (error) {
      console.error(error);

      setStatus(error.message || "Unable to communicate with Gemini.");
    } finally {
      setIsSending(false);
    }
  }

  // ==========================================================
  // CLEAR PRIVACY SESSION
  // ==========================================================

  async function clearPrivacySession() {
    if (!sessionId) {
      setSanitized("");

      setAliases([]);

      return;
    }

    try {
      await fetch(`${API}/privacy/clear`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          session_id: sessionId,
        }),
      });
    } catch (error) {
      console.error("Unable to clear session:", error);
    }

    setSessionId("");

    setSanitized("");

    setAliases([]);

    setStatus("Temporary privacy data cleared.");
  }

  // ==========================================================
  // COPY PROTECTED TEXT
  // ==========================================================

  async function copyProtectedText() {
    if (!sanitized) {
      return;
    }

    try {
      await navigator.clipboard.writeText(sanitized);

      setStatus("Protected text copied to clipboard.");
    } catch (error) {
      console.error(error);

      setStatus("Unable to copy protected text.");
    }
  }

  // ==========================================================
  // UI
  // ==========================================================

  return (
    <div className="app">
      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="header">
        <div>
          <div className="brand">OBSCURA</div>

          <div className="subtitle">Privacy-Preserving AI Gateway</div>
        </div>

        <select className="model" defaultValue="Gemini">
          <option>Gemini</option>
        </select>
      </header>

      {/* =====================================================
          MAIN
      ===================================================== */}

      <main className="main">
        {/* ===================================================
            HERO
        =================================================== */}

        <section className="hero">
          <h1>
            Chat with AI without unnecessarily exposing your private data.
          </h1>

          <p>
            OBSCURA checks your input before it reaches the external AI, lets
            you choose what to protect, and shows you the exact protected
            request before transmission.
          </p>
        </section>

        {/* ===================================================
            INPUT
        =================================================== */}

        <section className="composer card">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={
              "Try: My name is Sreehari, phone is " +
              "123455764 and email is example@gmail.com. " +
              "Write a job application email."
            }
          />

          <div className="composerFooter">
            <span className="hint">
              Your raw text is analyzed before external AI transmission.
            </span>

            <button disabled={!text.trim() || isAnalyzing} onClick={analyze}>
              {isAnalyzing ? "Checking..." : "Check Privacy"}
            </button>
          </div>
        </section>

        {/* ===================================================
            STATUS
        =================================================== */}

        {status && <div className="status">{status}</div>}

        {/* ===================================================
            PRIVACY REVIEW
        =================================================== */}

        {hasDetections && (
          <section className="card">
            <div className="sectionTitle">
              <div>
                <h2>Privacy Review</h2>

                <p>
                  We found potentially sensitive information in your request.
                  Choose what should be hidden from the external AI.
                </p>
              </div>

              <span className="count">
                {selectedCount}
                {" / "}
                {detections.length}
                {" selected"}
              </span>
            </div>

            {/* -----------------------------------------------
                PRIVACY ACTIONS
            ------------------------------------------------ */}

            <div className="privacyActions">
              <button className="secondary" onClick={selectRecommended}>
                Select Recommended
              </button>

              <button className="secondary" onClick={clearAll}>
                Clear All
              </button>
            </div>

            {/* -----------------------------------------------
                DETECTIONS
            ------------------------------------------------ */}

            <div className="detections">
              {orderedDetections.map((detection) => {
                const isBlocked = detection.recommended_action === "BLOCK";

                const isSelected = selected.has(detection.id);

                return (
                  <label
                    className={`detection ${riskClass(detection.risk)} ${
                      isBlocked ? "blockedDetection" : ""
                    }`}
                    key={detection.id}
                  >
                    {/* CHECKBOX */}

                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={isBlocked}
                      onChange={() => toggle(detection.id)}
                    />

                    {/* CONTENT */}

                    <div className="detectionBody">
                      <div className="detectionTop">
                        <strong>{detection.value}</strong>

                        <span className={`risk ${riskClass(detection.risk)}`}>
                          {RISK_LABELS[detection.risk]}
                        </span>
                      </div>

                      <div className="meta">
                        {detection.type}

                        {" · "}

                        {detection.category}
                      </div>

                      <div className="reason">{detection.reason}</div>

                      <div className="action">
                        Action:{" "}
                        <strong>
                          {getActionLabel(detection.recommended_action)}
                        </strong>
                      </div>

                      {isBlocked && (
                        <div className="blockedMessage">
                          🔒 This item cannot be sent to the external AI.
                        </div>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>

            {/* -----------------------------------------------
                CREATE PREVIEW
            ------------------------------------------------ */}

            <button
              onClick={createPreview}
              disabled={selectedCount === 0 || isPreparing}
            >
              {isPreparing ? "Preparing..." : "Create Protected Preview"}
            </button>
          </section>
        )}

        {/* ===================================================
            AI PREVIEW
        =================================================== */}

        {sanitized && (
          <section className="card preview">
            <div className="sectionTitle">
              <div>
                <h2>AI Input Preview</h2>

                <p>
                  Review the exact text that will cross the AI privacy boundary.
                </p>
              </div>
            </div>

            {/* -----------------------------------------------
                ORIGINAL VS SANITIZED
            ------------------------------------------------ */}

            <div className="compare">
              <div>
                <div className="label">ORIGINAL</div>

                <pre>{text}</pre>
              </div>

              <div>
                <div className="label">AI WILL RECEIVE</div>

                <pre>{sanitized}</pre>
              </div>
            </div>

            {/* -----------------------------------------------
                ALIAS MAP
            ------------------------------------------------ */}

            {aliases.length > 0 && (
              <div className="aliasSection">
                <div className="label">PROTECTED VALUES</div>

                <div className="aliasList">
                  {aliases.map((alias, index) => (
                    <div className="alias" key={`${alias.original}-${index}`}>
                      <span>{alias.original}</span>

                      <span>→</span>

                      <strong>{alias.alias}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* -----------------------------------------------
                PREVIEW WARNING
            ------------------------------------------------ */}

            <div className="previewNotice">
              🔐 Gemini will receive only the protected version shown above.
              <br />
              The original-to-alias mapping remains inside the OBSCURA backend.
            </div>

            {/* -----------------------------------------------
                ACTIONS
            ------------------------------------------------ */}

            <div className="actions">
              <button className="secondary" onClick={copyProtectedText}>
                Copy Protected Text
              </button>

              <button className="secondary" onClick={clearPrivacySession}>
                Clear Privacy Data
              </button>

              <button onClick={sendToAI} disabled={!sessionId || isSending}>
                {isSending ? "Sending..." : "Confirm & Send to Gemini"}
              </button>
            </div>
          </section>
        )}

        {/* ===================================================
            AI RESPONSE
        =================================================== */}

        {aiResponse && (
          <section className="card response">
            <div className="label">AI RESPONSE</div>

            <div className="responseText">{aiResponse}</div>

            <div className="responseNotice">
              ✓ Private values were restored by the OBSCURA backend.
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
