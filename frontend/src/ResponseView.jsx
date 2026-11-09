import { useMemo, useState } from "react";

import Markdown from "./markdown.jsx";

// Pulls a leading "Subject: ..." line out of an email-style answer.
function splitSubject(text) {
  const lines = String(text).replace(/\r\n?/g, "\n").split("\n");
  const first = lines.findIndex((line) => line.trim());

  if (first === -1) return { subject: "", body: text };

  const m = lines[first].match(
    /^\s*(?:\*\*|__)?\s*Subject\s*:\s*(?:\*\*|__)?\s*(.+?)\s*$/i,
  );

  if (!m) return { subject: "", body: text };

  return {
    subject: m[1].replace(/\*\*|__/g, "").trim(),
    body: lines.slice(first + 1).join("\n").replace(/^\s*\n/, ""),
  };
}

export default function ResponseView({ text }) {
  const [view, setView] = useState("formatted");

  const { subject, body } = useMemo(() => splitSubject(text), [text]);

  const words = String(text).trim().split(/\s+/).filter(Boolean).length;
  const minutes = Math.max(1, Math.round(words / 200));

  function download() {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "obscura-response.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  }

  return (
    <div className="respWrap">
      <div className="respBar">
        <div className="seg" role="tablist" aria-label="Response view">
          <button
            type="button"
            className={view === "formatted" ? "on" : ""}
            onClick={() => setView("formatted")}
          >
            Formatted
          </button>

          <button
            type="button"
            className={view === "plain" ? "on" : ""}
            onClick={() => setView("plain")}
          >
            Plain text
          </button>
        </div>

        <div className="row">
          <span className="respMeta">
            {words} words · {minutes} min read
          </span>

          <button type="button" className="btn small" onClick={download}>
            Download
          </button>
        </div>
      </div>

      <div className="respDoc">
        {view === "formatted" && subject && (
          <div className="respSubject">
            <span>Subject</span>
            <b>{subject}</b>
          </div>
        )}

        <div className="respBody">
          {view === "formatted" ? (
            <Markdown text={subject ? body : text} />
          ) : (
            <pre className="plainText">{text}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
