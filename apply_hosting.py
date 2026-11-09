# apply_hosting.py  -- run from the repo root
import os, sys

if not (os.path.isdir("backend/app") and os.path.isdir("frontend/src")):
    sys.exit("Run this from the repo root.")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("wrote", path)


# ---------------------------------------------------------------- backend main.py
main = "backend/app/main.py"
data = read(main)

if "OBSCURA_ACCESS_KEY" in data:
    print("main.py already has the access code")
else:
    ok = True

    middleware = '''ACCESS_KEY = os.getenv("OBSCURA_ACCESS_KEY", "")


@app.middleware("http")
async def require_access_key(request, call_next):
    # Declared BEFORE the CORS middleware, so CORS stays outermost and
    # the browser is able to read the 401 response.
    path = request.url.path

    if (
        ACCESS_KEY
        and request.method != "OPTIONS"
        and path.startswith("/api")
        and path != "/api/health"
    ):
        supplied = request.headers.get("x-obscura-key", "")

        if not hmac.compare_digest(
            supplied.encode("utf-8"), ACCESS_KEY.encode("utf-8")
        ):
            return JSONResponse(
                {"detail": "Access code required."}, status_code=401
            )

    return await call_next(request)


'''

    if "app.add_middleware(" not in data:
        print("!! main.py: app.add_middleware( not found. Add the access code by hand.")
        ok = False
    else:
        data = data.replace("app.add_middleware(", middleware + "app.add_middleware(", 1)

    health_old = 'return {"status": "ok", "service": "obscura"}'
    health_new = (
        'return {"status": "ok", "service": "obscura", '
        '"auth_required": bool(ACCESS_KEY)}'
    )

    if health_old not in data:
        print("!! main.py: health return line not found. Change it by hand.")
        ok = False
    else:
        data = data.replace(health_old, health_new, 1)

    if ok:
        data = (
            "import hmac\nimport os\n\n"
            "from fastapi.responses import JSONResponse\n"
            + data.rstrip("\n")
            + '\n\n\n@app.get("/api/auth/check")\ndef auth_check():\n    return {"ok": True}\n'
        )
        write(main, data)

# ---------------------------------------------------------------- frontend ui.jsx
ui = "frontend/src/ui.jsx"
data = read(ui)

if "obscura-key" in data:
    print("ui.jsx already has the access code")
else:
    anchor = 'export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";'

    if anchor not in data:
        print("!! ui.jsx: the API line was not found. Tell me and I will give you the manual edit.")
    else:
        addition = anchor + '''

// ---- Access code (used when the backend sets OBSCURA_ACCESS_KEY) ----
const KEY_STORE = "obscura-key";

export function getAccessKey() {
  try {
    return sessionStorage.getItem(KEY_STORE) || "";
  } catch {
    return "";
  }
}

export function setAccessKey(value) {
  try {
    if (value) sessionStorage.setItem(KEY_STORE, value);
    else sessionStorage.removeItem(KEY_STORE);
  } catch {
    /* ignore */
  }
}

// Adds the access code to every call to our own API.
if (typeof window !== "undefined" && !window.__obscuraFetch) {
  window.__obscuraFetch = true;
  const nativeFetch = window.fetch.bind(window);

  window.fetch = (input, init = {}) => {
    const url = typeof input === "string" ? input : input?.url || "";

    if (url.startsWith(API)) {
      const key = getAccessKey();

      if (key) {
        const headers = new Headers(init.headers || {});
        headers.set("X-Obscura-Key", key);
        init = { ...init, headers };
      }
    }

    return nativeFetch(input, init);
  };
}'''
        write(ui, data.replace(anchor, addition, 1))

# ---------------------------------------------------------------- frontend gate
write("frontend/src/AccessGate.jsx", r'''import { useEffect, useState } from "react";

import { API, Logo, Spinner, setAccessKey } from "./ui.jsx";

export default function AccessGate({ children }) {
  // checking | open | locked
  const [state, setState] = useState("checking");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function verify() {
    const res = await fetch(`${API}/auth/check`);
    return res.ok;
  }

  useEffect(() => {
    let active = true;

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
        // Backend unreachable: show the app, which displays the offline status.
        if (active) setState("open");
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  async function submit(event) {
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

  return (
    <div className="gate">
      <form className="gateCard" onSubmit={submit}>
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
''')

write("frontend/src/main.jsx", r'''import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import AccessGate from "./AccessGate.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AccessGate>
      <App />
    </AccessGate>
  </React.StrictMode>
);
''')

css = "frontend/src/styles.css"
data = read(css)
if ".gateCard" not in data:
    data += '''

/* ---------------- Access gate ---------------- */

.gate {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.gateCard {
  width: min(420px, 100%);
  display: grid;
  gap: 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 28px;
  box-shadow: var(--shadow);
}

.gateCard h1 {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.01em;
}
'''
    write(css, data)

# ---------------------------------------------------------------- Dockerfile port
docker = "backend/Dockerfile"
data = read(docker)
old = 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'
new = 'CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]'
if new in data:
    print("Dockerfile already uses PORT")
elif old in data:
    write(docker, data.replace(old, new, 1))
else:
    print("!! backend/Dockerfile: CMD line not found. Change it by hand.")

# ---------------------------------------------------------------- Netlify
write("netlify.toml", '''[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "22"
''')

# ---------------------------------------------------------------- env example
env = "backend/.env.example"
data = read(env)
if "OBSCURA_ACCESS_KEY" not in data:
    data += '''
# Set this on any public deployment. The site asks for it before it works.
# Make one with: python -c "import secrets; print(secrets.token_urlsafe(16))"
OBSCURA_ACCESS_KEY=
'''
    write(env, data)

# ---------------------------------------------------------------- Hugging Face packager
write("scripts/make_hf_space.py", r'''"""Packages the backend for a Hugging Face Docker Space.

    python scripts/make_hf_space.py

Creates build/hf_space/ . Copy its contents into your cloned Space repo.
"""
import os
import shutil

SRC = "backend"
OUT = os.path.join("build", "hf_space")

HEADER = """---
title: Obscura Backend
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
---

Obscura privacy gateway API.
"""

if os.path.isdir(OUT):
    shutil.rmtree(OUT)

os.makedirs(OUT)

shutil.copy(os.path.join(SRC, "Dockerfile"), OUT)
shutil.copy(os.path.join(SRC, "requirements.txt"), OUT)

shutil.copytree(
    os.path.join(SRC, "app"),
    os.path.join(OUT, "app"),
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
)

with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(HEADER)

print("Ready:", OUT)
print("Copy everything inside it into your Space repo, then commit and push.")
''')

# ---------------------------------------------------------------- .gitignore
ignore = ".gitignore"
data = read(ignore)
if "build/" not in data.split():
    with open(ignore, "a", encoding="utf-8", newline="\n") as f:
        f.write("\nbuild/\n")
    print("updated .gitignore")

print("\nDone.")