# apply_deploy.py  -- run from the repo root
import os, sys

if not (os.path.isdir("backend/app") and os.path.isdir("frontend/src")):
    sys.exit("Run this from the repo root (the folder containing backend/ and frontend/).")

FILES = {}

# ======================================================================
# BACKEND DOCKER
# ======================================================================
FILES["backend/Dockerfile"] = r'''FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# CPU-only PyTorch keeps the image far smaller than the default CUDA build.
# ultralytics installs plain opencv-python, which breaks the contrib build,
# so every opencv package is removed and one is installed again.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt \
    && pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless \
    && pip install "opencv-contrib-python-headless>=4.10,<5" \
    && python -m spacy download en_core_web_sm

RUN useradd --create-home --uid 1000 app && chown app:app /app
USER app

# Download the models at build time so the container starts fast
# and never needs internet access at runtime.
RUN python -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_small-v2.1')" \
    && python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY --chown=app:app app ./app

ENV HF_HUB_OFFLINE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# ONE worker on purpose: the privacy vault lives in this process's memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

FILES["backend/.dockerignore"] = '''.venv
__pycache__
*.pyc
.env
.pytest_cache
tests
test_*.py
*.webp
'''

FILES["backend/.env.example"] = '''# Copy this file to .env and fill in your key. Never commit .env.
GEMINI_API_KEY=put_your_key_here
GEMINI_MODEL=gemini-3.6-flash

# Set to 1 only while developing. Debug output can contain private values.
OBSCURA_DEBUG=0

# Comma-separated list of origins allowed to call the API from a browser.
OBSCURA_CORS_ORIGINS=http://localhost:5173,http://localhost:8080
'''

# ======================================================================
# FRONTEND DOCKER
# ======================================================================
FILES["frontend/Dockerfile"] = r'''FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# "/api" is forwarded to the backend by nginx, so the browser only
# ever talks to one address.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
'''

FILES["frontend/nginx.conf"] = r'''server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Image and PDF uploads.
    client_max_body_size 25m;

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;
    add_header X-Frame-Options DENY always;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # OCR and the models can be slow, especially on the first request.
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files $uri /index.html;
    }
}
'''

FILES["frontend/.dockerignore"] = '''node_modules
dist
.env
'''

# ======================================================================
# COMPOSE (local) AND PRODUCTION
# ======================================================================
FILES["docker-compose.yml"] = r'''# Local run:  docker compose up --build
# Then open:  http://localhost:8080
services:
  backend:
    build: ./backend
    env_file: ./backend/.env
    environment:
      OBSCURA_CORS_ORIGINS: http://localhost:8080
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_URL: /api
    ports:
      - "8080:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
'''

FILES["docker-compose.prod.yml"] = r'''# Used on the server. Images come from the GitLab registry.
services:
  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      DOMAIN: ${DOMAIN}
      APP_USER: ${APP_USER}
      APP_PASSWORD_HASH: ${APP_PASSWORD_HASH}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend

  frontend:
    image: ${IMAGE_PREFIX}/frontend:latest
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy

  backend:
    image: ${IMAGE_PREFIX}/backend:latest
    restart: unless-stopped
    env_file: ./backend.env
    environment:
      OBSCURA_CORS_ORIGINS: https://${DOMAIN}

volumes:
  caddy_data:
  caddy_config:
'''

FILES["Caddyfile"] = r'''# Automatic HTTPS for {$DOMAIN}. The login keeps strangers from using
# your Gemini quota and uploading files to your server.
{$DOMAIN} {
	basicauth {
		{$APP_USER} {$APP_PASSWORD_HASH}
	}

	reverse_proxy frontend:80
}
'''

# ======================================================================
# GITLAB CI
# ======================================================================
FILES[".gitlab-ci.yml"] = r'''stages:
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  npm_config_cache: "$CI_PROJECT_DIR/.cache/npm"

test:backend:
  stage: test
  image: python:3.12-slim
  cache:
    key: pip-backend
    paths:
      - .cache/pip
  before_script:
    - apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0
    - cd backend
    - pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    - pip install -r requirements.txt
    - pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless
    - pip install "opencv-contrib-python-headless>=4.10,<5"
    - python -m spacy download en_core_web_sm
  script:
    - pytest -q

test:frontend:
  stage: test
  image: node:22-alpine
  cache:
    key: npm-frontend
    paths:
      - .cache/npm
  script:
    - cd frontend
    - npm ci
    - npm run build

build:images:
  stage: build
  image: docker:27
  services:
    - docker:27-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  before_script:
    - echo "$CI_REGISTRY_PASSWORD" | docker login -u "$CI_REGISTRY_USER" --password-stdin "$CI_REGISTRY"
  script:
    - docker build -t "$CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHORT_SHA" -t "$CI_REGISTRY_IMAGE/backend:latest" backend
    - docker build --build-arg VITE_API_URL=/api -t "$CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHORT_SHA" -t "$CI_REGISTRY_IMAGE/frontend:latest" frontend
    - docker push --all-tags "$CI_REGISTRY_IMAGE/backend"
    - docker push --all-tags "$CI_REGISTRY_IMAGE/frontend"

deploy:production:
  stage: deploy
  image: alpine:3.20
  needs:
    - build:images
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: manual
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
    - mkdir -p ~/.ssh && chmod 700 ~/.ssh
    - ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts
  script:
    - scp docker-compose.prod.yml Caddyfile "$SSH_USER@$SSH_HOST:/opt/obscura/"
    - ssh "$SSH_USER@$SSH_HOST" "cd /opt/obscura && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d && docker image prune -f"
'''

# ======================================================================
# SMOKE TEST
# ======================================================================
FILES["scripts/smoke_test.py"] = r'''"""End-to-end check against a RUNNING Obscura.

    python scripts/smoke_test.py                       (http://localhost:8080)
    python scripts/smoke_test.py --base https://your-domain --auth user:pass
    python scripts/smoke_test.py --send                (also calls Gemini)
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request


def call(base, path, payload=None, auth=None):
    headers = {"Content-Type": "application/json"}

    if auth:
        token = base64.b64encode(auth.encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    data = json.dumps(payload).encode() if payload is not None else None

    request = urllib.request.Request(base + path, data=data, headers=headers)

    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8080")
    parser.add_argument("--auth", default=None, help="user:password")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    failures = []

    def check(name, ok):
        print(("PASS  " if ok else "FAIL  ") + name)
        if not ok:
            failures.append(name)

    try:
        health = call(args.base, "/api/health", auth=args.auth)
        check("health endpoint", health.get("status") == "ok")

        text = (
            "My name is Aaron Smith. Email aaron.smith@example.com "
            "and phone 9876543210. Write a job application email."
        )

        analysis = call(args.base, "/api/privacy/analyze", {"text": text}, args.auth)
        found = analysis["detections"]
        types = {d["type"] for d in found}

        check("detects an email", "EMAIL" in types)
        check("detects a phone number", "PHONE" in types)

        ids = [d["id"] for d in found if d["recommended_action"] != "BLOCK"]

        prepared = call(
            args.base,
            "/api/privacy/prepare",
            {"text": text, "selected_detection_ids": ids},
            args.auth,
        )

        sanitized = prepared["sanitized_text"]

        check("email is removed from the outgoing text", "aaron.smith@example.com" not in sanitized)
        check("phone is removed from the outgoing text", "9876543210" not in sanitized)
        check("placeholders were inserted", "<OBSCURA_" in sanitized)

        secret = call(
            args.base,
            "/api/privacy/analyze",
            {"text": "my password: hunter2xyz99"},
            args.auth,
        )
        blocked = call(
            args.base,
            "/api/privacy/prepare",
            {"text": "my password: hunter2xyz99", "selected_detection_ids": []},
            args.auth,
        )
        check("secret is detected", any(d["recommended_action"] == "BLOCK" for d in secret["detections"]))
        check("secret blocks the request", blocked.get("blocked") is True)

        if args.send:
            reply = call(
                args.base,
                "/api/chat/send",
                {"session_id": prepared["session_id"]},
                args.auth,
            )
            check("AI reply received", bool(reply.get("response")))
            print("      " + reply["response"][:100].replace("\n", " ") + "...")

    except urllib.error.HTTPError as error:
        print(f"FAIL  HTTP {error.code} from the server")
        sys.exit(1)
    except Exception as error:
        print(f"FAIL  could not run the checks: {error}")
        sys.exit(1)

    print()
    print("All checks passed." if not failures else f"{len(failures)} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
'''

# ======================================================================
# README
# ======================================================================
FILES["README.md"] = r'''# Obscura

**Use AI without handing over your private data.**

Obscura sits between you and an external AI. It finds personal details, secrets
and sensitive images on your own machine, lets you choose what to hide, shows
you exactly what the AI will receive, and puts your real values back into the
answer afterwards.

Works for **text**, **images** and **PDFs**. Currently talks to **Gemini**; the
interface is ready for more providers.

## How it works

~~~mermaid
flowchart LR
  A[Your content] --> B[Local detection]
  B --> C[You review and choose]
  C --> D[Protected copy]
  D --> E[AI provider]
  E --> F[Response guard]
  F --> G[Restore your values]
  G --> H[Answer shown to you]
~~~

1. **Detect locally.** Rules, a spaCy model and a GLiNER model find names,
   emails, phones, addresses, IDs, cards and secrets. For images and scanned
   PDFs, OCR reads the text first. YOLO finds phones, laptops and TVs, and
   OpenCV finds faces, QR codes and barcodes.
2. **Review.** Every finding is shown. You choose what to hide.
3. **Protect.**
   - Text: values become placeholders such as `<OBSCURA_NAME_001>`.
   - Images: selected areas are filled with solid black (not blurred).
   - PDFs: selected content is permanently removed from the file, and metadata
     and hidden data are stripped.
4. **Send** only the protected copy.
5. **Check and restore.** The response is scanned for leaked originals. If it
   is clean, placeholders are replaced with your real values in the backend.

Secrets (passwords, API keys, tokens, private keys) are **never** sent. They are
removed whether or not you select them.

## Features

| Area | What it does |
| --- | --- |
| Text | Highlighted review, reversible placeholders, one alias per repeated value |
| Images | OCR, faces, QR/barcodes, license plates, phone and laptop screens, metadata stripped |
| PDF | Text and scanned pages, hidden metadata report, real redaction, output re-checked |
| Safety | Secret blocking, response guard, no private values in logs |
| UI | Steps on the left, outputs on the right, light and dark mode, model picker |

## Run it with Docker (easiest)

Requirements: Docker Desktop (or Docker Engine) and about 4 GB of free memory.

~~~bash
cp backend/.env.example backend/.env      # Windows: copy backend\.env.example backend\.env
# edit backend/.env and set GEMINI_API_KEY

docker compose up --build
~~~

Open **http://localhost:8080**. The first build downloads the models and takes
several minutes. Check it works:

~~~bash
python scripts/smoke_test.py
~~~

## Run it for development (Windows PowerShell)

Backend:

~~~powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless
pip install "opencv-contrib-python-headless>=4.10,<5"
python -m spacy download en_core_web_sm

copy .env.example .env      # then set GEMINI_API_KEY
uvicorn app.main:app --port 8000
~~~

The `opencv` lines matter: `ultralytics` installs a second OpenCV build that
breaks face and barcode detection.

Frontend (second terminal):

~~~powershell
cd frontend
npm install
npm run dev
~~~

Open the address Vite prints (http://localhost:5173).

## Configuration

| Variable | Where | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | `backend/.env` | Your Gemini key (required) |
| `GEMINI_MODEL` | `backend/.env` | Model name your key can use |
| `OBSCURA_CORS_ORIGINS` | `backend/.env` | Browser origins allowed to call the API |
| `OBSCURA_DEBUG` | `backend/.env` | `1` prints debug output. It can contain private data, so keep it `0` |
| `OBSCURA_PDF_OCR_IMAGES` | `backend/.env` | `1` also OCRs images inside text PDFs (slower) |
| `VITE_API_URL` | frontend build | API address. Docker uses `/api`; dev defaults to `http://localhost:8000/api` |

## API

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Liveness check |
| `POST /api/privacy/analyze` | Detect sensitive text |
| `POST /api/privacy/prepare` | Create the protected text and a short-lived session |
| `POST /api/chat/send` | Send the protected text, restore the answer |
| `POST /api/image/analyze`, `/prepare`, `/send` | Same flow for images |
| `POST /api/pdf/analyze`, `/prepare`, `/send` | Same flow for PDFs |

Interactive docs are at `/docs` when you run the backend directly.

## Tests

~~~bash
cd backend
pytest -v                          # unit and API tests
python ../scripts/smoke_test.py    # end-to-end check on a running instance
~~~

The pytest suite covers detection patterns, fusion, the protect-and-restore
round trip, secret blocking, the response guard, image redaction and PDF
redaction. The GitLab pipeline runs it on every push.

For responsive checks, open the app in browser DevTools device mode at about
375, 768 and 1280 px wide and test all three tabs in light and dark mode.

## Deploy

The pipeline in `.gitlab-ci.yml` runs tests, builds both images, pushes them to
the GitLab registry and deploys to your server on a manual click.

**You need:** a Linux server with 4 GB RAM or more (a small VPS is fine), Docker
with the Compose plugin, and a domain name pointing at the server.

Why a server and not a free tier: the backend loads PyTorch, two language
models, an OCR engine and an object detector. Free tiers with 512 MB of memory
cannot run it.

### One-time server setup

~~~bash
sudo mkdir -p /opt/obscura && sudo chown $USER /opt/obscura
cd /opt/obscura

# Log in to the GitLab registry with a deploy token (scope: read_registry)
docker login registry.gitlab.com

# Backend secrets
cat > backend.env <<EOF
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.6-flash
OBSCURA_DEBUG=0
EOF

# Create a login password hash
docker run --rm caddy caddy hash-password --plaintext 'choose-a-strong-password'
~~~

Create `/opt/obscura/.env` (keep the hash in single quotes):

~~~
DOMAIN=obscura.example.com
IMAGE_PREFIX=registry.gitlab.com/your-group/your-project
APP_USER=admin
APP_PASSWORD_HASH='$2a$14$...paste the hash here...'
~~~

### GitLab setup

1. Create a project and push the code (`git remote add origin ...`, then
   `git push -u origin main`).
2. In **Settings > CI/CD > Variables** add `SSH_HOST`, `SSH_USER` and
   `SSH_PRIVATE_KEY` (a key whose public half is in the server's
   `~/.ssh/authorized_keys`).
3. Push to the default branch. When the build finishes, press **Run** on the
   `deploy:production` job.
4. Open `https://your-domain` and confirm with
   `python scripts/smoke_test.py --base https://your-domain --auth admin:password`.

Caddy gets and renews the HTTPS certificate automatically.

## Security model and limits

- **Detection is not perfect.** It can miss things and can flag harmless text.
  Always check the "What the AI receives" output before sending.
- **Not detected yet:** physical documents with no readable text, faces that are
  small, masked or turned away, and secrets in unusual formats.
- **Sessions live in memory** for 15 minutes and are deleted after use. The
  backend runs a single worker for this reason. Restarting it clears them.
- **No built-in accounts or rate limits.** A public deployment must sit behind
  the login shown above, or anyone can spend your Gemini quota.
- **Gemini receives the protected copy.** Check Google's terms for how API data
  is handled before using sensitive material.
- **Logs** never contain original values unless `OBSCURA_DEBUG=1`.

## Project structure

~~~
backend/
  app/
    privacy/        detectors, fusion, pseudonymizer, vault, response guard
      image/        OCR, faces, devices, redaction
      pdf/          PDF analysis and redaction
    routes/         privacy, chat, image, pdf
    ai/gemini.py    provider call
  tests/
frontend/
  src/              React app (Text, Images, PDF)
docker-compose.yml          local run
docker-compose.prod.yml     server run
.gitlab-ci.yml              test, build, deploy
scripts/smoke_test.py
~~~

## Roadmap

- More providers (ChatGPT, Claude) behind one interface
- Multi-turn chat with a shared alias map
- Document-shape detection for ID cards and paper forms
- Accounts and rate limits
'''.replace("~~~", "`" * 3)

# ----------------------------------------------------------------------
for path, content in FILES.items():
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("wrote", path)


def patch(path, marker, old, new):
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if marker in data:
        print("already patched", path)
        return
    if old not in data:
        print(f"!! {path}: could not find the text to change. Patch it by hand (see chat).")
        return
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data.replace(old, new, 1))
    print("patched", path)


# Frontend: API address from the environment
patch(
    "frontend/src/ui.jsx",
    "VITE_API_URL",
    'export const API = "http://localhost:8000/api";',
    'export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";',
)

# Backend: CORS origins from the environment
patch(
    "backend/app/main.py",
    "OBSCURA_CORS_ORIGINS",
    'allow_origins=["http://localhost:5173"],',
    'allow_origins=[\n'
    '        origin.strip()\n'
    '        for origin in os.getenv(\n'
    '            "OBSCURA_CORS_ORIGINS",\n'
    '            "http://localhost:5173,http://localhost:8080",\n'
    '        ).split(",")\n'
    '        if origin.strip()\n'
    '    ],',
)

patch(
    "backend/app/main.py",
    "import os\n",
    "from fastapi import FastAPI\n",
    "import os\n\nfrom fastapi import FastAPI\n",
)

# .gitignore
ignore = ".gitignore"
extra = [
    "yolov8n.pt",
    ".pytest_cache/",
    "frontend/dist/",
    ".cache/",
    "backend.env",
]
with open(ignore, "r", encoding="utf-8") as f:
    current = f.read()
missing = [line for line in extra if line not in current.split()]
if missing:
    with open(ignore, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n# Added by apply_deploy.py\n" + "\n".join(missing) + "\n")
    print("updated .gitignore")

print("\nDone. Next: docker compose up --build")