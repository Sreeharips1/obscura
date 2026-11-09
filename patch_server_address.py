# patch_server_address.py  -- run from the repo root
import os, sys

ui = "frontend/src/ui.jsx"

if not os.path.exists(ui):
    sys.exit("Run this from the repo root.")

with open(ui, "r", encoding="utf-8") as f:
    data = f.read()

if "obscura-key" not in data:
    sys.exit("Run apply_hosting.py first (it adds the access code this builds on).")

if "obscura-api" not in data:
    anchor = 'export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";'

    if anchor not in data:
        sys.exit("ui.jsx: the API line was not found. Tell me and I will give you the manual edit.")

    block = '''function resolveApi() {
  try {
    const saved = localStorage.getItem("obscura-api");
    if (saved) return saved;
  } catch {
    /* ignore */
  }

  return import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
}

export const API = resolveApi();

export function hasCustomServer() {
  try {
    return Boolean(localStorage.getItem("obscura-api"));
  } catch {
    return false;
  }
}

// Saves the address, then reloads so the whole app uses it.
export function setServerAddress(value) {
  let address = String(value || "").trim().replace(/\\/+$/, "");

  if (!/^https?:\\/\\//i.test(address)) return false;
  if (!address.endsWith("/api")) address += "/api";

  try {
    localStorage.setItem("obscura-api", address);
  } catch {
    return false;
  }

  window.location.reload();
  return true;
}

export function resetServerAddress() {
  try {
    localStorage.removeItem("obscura-api");
  } catch {
    /* ignore */
  }

  window.location.reload();
}'''

    with open(ui, "w", encoding="utf-8", newline="\n") as f:
        f.write(data.replace(anchor, block, 1))
    print("patched", ui)
else:
    print("ui.jsx already patched")

gate = r'''import { useEffect, useState } from "react";

import {
  API,
  Logo,
  Spinner,
  hasCustomServer,
  resetServerAddress,
  setAccessKey,
  setServerAddress,
} from "./ui.jsx";

export default function AccessGate({ children }) {
  // checking | open | locked | offline
  const [state, setState] = useState("checking");
  const [code, setCode] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);

  async function verify() {
    const res = await fetch(`${API}/auth/check`);
    return res.ok;
  }

  useEffect(() => {
    let active = true;
    setState("checking");

    (async () => {
      try {
        const res = await fetch(`${API}/health`);
        const health = await res.json();

        if (!health.auth_required) {
          if (active) setState("open");
          return;
        }

        const ok = await verify();
        if (active) setState(ok ? "open" : "locked");
      } catch {
        if (active) setState("offline");
      }
    })();

    return () => {
      active = false;
    };
  }, [attempt]);

  async function submitCode(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      setAccessKey(code.trim());

      if (await verify()) {
        setState("open");
      } else {
        setAccessKey("");
        setError("That access code is not correct.");
      }
    } catch {
      setError("Could not reach the server. Try again in a moment.");
    } finally {
      setBusy(false);
    }
  }

  function submitAddress(event) {
    event.preventDefault();
    setError("");

    if (!setServerAddress(address)) {
      setError("Enter an address that starts with https:// or http://");
    }
  }

  if (state === "open") return children;

  if (state === "checking") {
    return (
      <div className="gate">
        <div className="loading">
          <Spinner /> Connecting…
        </div>
      </div>
    );
  }

  if (state === "offline") {
    return (
      <div className="gate">
        <form className="gateCard" onSubmit={submitAddress}>
          <div className="brand">
            <Logo />
            <span className="brandName">Obscura</span>
          </div>

          <h1>Connect to a server</h1>
          <p className="sub">
            Could not reach the Obscura server at <b>{API}</b>. If you are
            running it yourself, paste its address below. It is remembered in
            this browser.
          </p>

          <input
            className="field"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="https://your-tunnel-address.trycloudflare.com"
            autoComplete="off"
          />

          {error && <div className="banner error">{error}</div>}

          <button className="btn primary" disabled={!address.trim()}>
            Connect
          </button>

          <div className="row">
            <button
              type="button"
              className="btn small"
              onClick={() => setAttempt(attempt + 1)}
            >
              Try again
            </button>

            {hasCustomServer() && (
              <button
                type="button"
                className="btn small"
                onClick={resetServerAddress}
              >
                Use the default address
              </button>
            )}
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="gate">
      <form className="gateCard" onSubmit={submitCode}>
        <div className="brand">
          <Logo />
          <span className="brandName">Obscura</span>
        </div>

        <h1>Enter the access code</h1>
        <p className="sub">
          This copy of Obscura is private. Ask the owner for the access code.
        </p>

        <input
          className="field"
          type="password"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="Access code"
          autoFocus
          autoComplete="off"
        />

        {error && <div className="banner error">{error}</div>}

        <button className="btn primary" disabled={!code.trim() || busy}>
          {busy ? "Checking…" : "Unlock"}
        </button>
      </form>
    </div>
  );
}
'''

with open("frontend/src/AccessGate.jsx", "w", encoding="utf-8", newline="\n") as f:
    f.write(gate)
print("wrote frontend/src/AccessGate.jsx")

print("\nDone.")