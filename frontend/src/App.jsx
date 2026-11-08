import { useEffect, useState } from "react";

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
