# apply_quickstart.py  -- run from the repo root
import os, re, subprocess, sys

if not (os.path.isdir("backend/app") and os.path.isdir("frontend/src")):
    sys.exit("Run this from the repo root.")


def write(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("wrote", path)


# ---------------------------------------------------------------- repo address
url = "https://github.com/YOUR-USERNAME/YOUR-REPO.git"

try:
    raw = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    m = re.match(r"git@github\.com:(.+?)(?:\.git)?$", raw)

    if m:
        url = f"https://github.com/{m.group(1)}.git"
    elif raw.startswith("http"):
        url = raw if raw.endswith(".git") else raw + ".git"
except Exception:
    print("Could not read the git remote. The README will show a placeholder address.")

folder = url.rsplit("/", 1)[-1].replace(".git", "") or "obscura"

# ---------------------------------------------------------------- Windows setup
write("setup.ps1", r'''# One-time setup for Windows.
# Run from the project folder:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Fail($message) {
    Write-Host ""
    Write-Host $message -ForegroundColor Red
    exit 1
}

function Step($label, [scriptblock]$command) {
    Write-Host ""
    Write-Host "== $label" -ForegroundColor Cyan
    & $command
    if ($LASTEXITCODE -ne 0) { Fail "That step failed: $label" }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail "Python was not found. Install Python 3.11 to 3.13 from python.org and tick 'Add python.exe to PATH'."
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Fail "Node.js was not found. Install the LTS version from nodejs.org."
}

python -c "import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)"
if ($LASTEXITCODE -ne 0) { Fail "Please use Python 3.10 to 3.13. Other versions may not work with the AI libraries yet." }

node -e "const [a,b]=process.versions.node.split('.').map(Number); process.exit((a>22||(a===22&&b>=12)||(a===20&&b>=19))?0:1)"
if ($LASTEXITCODE -ne 0) { Fail "Please use Node.js 20.19 or newer (22 LTS is recommended)." }

$py = Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Step "Creating the Python environment" { python -m venv backend\.venv }
}

Step "Updating pip" { & $py -m pip install --upgrade pip }

Step "Installing backend packages (this takes several minutes)" {
    & $py -m pip install -r backend\requirements.txt
}

Step "Fixing the OpenCV install" {
    & $py -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless
    & $py -m pip install "opencv-contrib-python-headless>=4.10,<5"
}

Step "Downloading the language model" { & $py -m spacy download en_core_web_sm }

Write-Host ""
Write-Host "== Downloading the detection models (one time, a few hundred MB)" -ForegroundColor Cyan
Push-Location backend
& $py -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_small-v2.1')"
if ($LASTEXITCODE -ne 0) { Write-Host "Could not pre-download the name model. It will download on first use." -ForegroundColor Yellow }
& $py -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
if ($LASTEXITCODE -ne 0) { Write-Host "Could not pre-download the screen detector. It will download on first use." -ForegroundColor Yellow }
Pop-Location

if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "Created backend\.env" -ForegroundColor Green
}

Write-Host ""
Write-Host "== Installing the website packages" -ForegroundColor Cyan
Push-Location frontend
npm install
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { Fail "npm install failed." }

Write-Host ""
Write-Host "Setup finished." -ForegroundColor Green
Write-Host "Next:"
Write-Host "  1. Open backend\.env and put your Gemini key after GEMINI_API_KEY="
Write-Host "  2. Run:  powershell -ExecutionPolicy Bypass -File .\start.ps1"
''')

write("start.ps1", r'''# Starts Obscura (backend and website) on Windows.
#   powershell -ExecutionPolicy Bypass -File .\start.ps1

Set-Location $PSScriptRoot

if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
    Write-Host "Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

$hasKey = Select-String -Path "backend\.env" -Pattern "^GEMINI_API_KEY=(?!put_your_key_here)\S+" -Quiet
if (-not $hasKey) {
    Write-Host "No Gemini key found in backend\.env." -ForegroundColor Yellow
    Write-Host "Privacy checks will work, but sending to the AI will fail until you add one." -ForegroundColor Yellow
}

$backend = "Set-Location '$PSScriptRoot\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backend

$frontend = "Set-Location '$PSScriptRoot\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontend

Write-Host "Waiting for the backend. The first start can take a few minutes..."

$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        Invoke-RestMethod "http://localhost:8000/api/health" -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($ready) {
    Write-Host "Backend is up. Opening the app." -ForegroundColor Green
    Write-Host "The first privacy check can be slow while the models load."
    Start-Process "http://localhost:5173"
} else {
    Write-Host "The backend did not answer in time. Look at its window for errors." -ForegroundColor Red
}
''')

# ---------------------------------------------------------------- Mac / Linux
write("setup.sh", r'''#!/usr/bin/env bash
# One-time setup for Mac and Linux.   Run:  bash setup.sh
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Install Python 3.11 to 3.13 first."; exit 1; }
command -v node >/dev/null || { echo "Install Node.js 22 LTS first."; exit 1; }

python3 -c "import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)" \
  || { echo "Please use Python 3.10 to 3.13."; exit 1; }

node -e "const [a,b]=process.versions.node.split('.').map(Number); process.exit((a>22||(a===22&&b>=12)||(a===20&&b>=19))?0:1)" \
  || { echo "Please use Node.js 20.19 or newer (22 LTS recommended)."; exit 1; }

[ -d backend/.venv ] || python3 -m venv backend/.venv
PY=backend/.venv/bin/python

$PY -m pip install --upgrade pip

# CPU-only PyTorch keeps the download much smaller on Linux.
if [ "$(uname)" = "Linux" ]; then
  $PY -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

$PY -m pip install -r backend/requirements.txt

$PY -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless || true
$PY -m pip install "opencv-contrib-python-headless>=4.10,<5"

$PY -m spacy download en_core_web_sm

echo "Downloading the detection models (one time)..."
(cd backend && ../$PY -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_small-v2.1')") \
  || echo "Could not pre-download the name model. It will download on first use."
(cd backend && ../$PY -c "from ultralytics import YOLO; YOLO('yolov8n.pt')") \
  || echo "Could not pre-download the screen detector. It will download on first use."

[ -f backend/.env ] || { cp backend/.env.example backend/.env; echo "Created backend/.env"; }

(cd frontend && npm install)

echo
echo "Setup finished."
echo "Next:"
echo "  1. Open backend/.env and put your Gemini key after GEMINI_API_KEY="
echo "  2. Run:  bash start.sh"
''')

write("start.sh", r'''#!/usr/bin/env bash
# Starts Obscura (backend and website) on Mac and Linux.   Run:  bash start.sh
cd "$(dirname "$0")"

[ -x backend/.venv/bin/python ] || { echo "Run: bash setup.sh first."; exit 1; }

if ! grep -Eq '^GEMINI_API_KEY=[^[:space:]]+' backend/.env || grep -q 'put_your_key_here' backend/.env; then
  echo "No Gemini key found in backend/.env. Privacy checks will work,"
  echo "but sending to the AI will fail until you add one."
fi

(cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT INT TERM

echo "Waiting for the backend. The first start can take a few minutes..."

for i in $(seq 1 90); do
  curl -s http://localhost:8000/api/health >/dev/null 2>&1 && break
  sleep 2
done

echo "Opening the app. Press Ctrl+C here to stop everything."
cd frontend && npm run dev -- --open
''')

write(".gitattributes", "*.sh text eol=lf\n")

# ---------------------------------------------------------------- README
quick = r'''## Quick start (for anyone who downloads the code)

**You need:**

- [Git](https://git-scm.com), [Python](https://www.python.org/downloads/) 3.10 to 3.13 and [Node.js](https://nodejs.org) 22 LTS (20.19 or newer)
- Your own free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- About 5 GB of free disk space and an internet connection for the first setup

**Windows (PowerShell):**

~~~powershell
git clone REPO_URL
cd REPO_DIR
powershell -ExecutionPolicy Bypass -File .\setup.ps1
~~~

When it finishes, open `backend\.env` in Notepad and paste your key after `GEMINI_API_KEY=`. Then:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
~~~

The app opens at http://localhost:5173. The first start and the first privacy check are slow because the models load. Later runs are faster.

**Mac or Linux:**

~~~bash
git clone REPO_URL
cd REPO_DIR
bash setup.sh
# edit backend/.env and add your Gemini key
bash start.sh
~~~

**Something not working?**

| What you see | What to do |
| --- | --- |
| "running scripts is disabled" | Use the full `powershell -ExecutionPolicy Bypass -File ...` command shown above |
| "Connect to a server" page | The backend is still loading. Wait a minute and click **Try again** |
| Sending to the AI fails | Check `GEMINI_API_KEY` in `backend/.env`. If you get a model not found error, set `GEMINI_MODEL` to a model name your key can use |
| `npm` complains about the Node version | Install Node.js 22 LTS |
| Face or barcode detection errors | Run the setup script again (it repairs the OpenCV install) |
| Setup stops with a red message | Read the message, fix that one thing, and run setup again. It is safe to repeat |

Your key stays in `backend/.env` on your own computer. That file is never uploaded to GitHub.

'''.replace("~~~", "`" * 3).replace("REPO_URL", url).replace("REPO_DIR", folder)

readme = "README.md"

if not os.path.exists(readme):
    print("!! README.md not found, skipped")
else:
    with open(readme, "r", encoding="utf-8") as f:
        text = f.read()

    if "## Quick start" in text:
        print("README already has a Quick start section")
    elif "## How it works" in text:
        write(readme, text.replace("## How it works", quick + "## How it works", 1))
    else:
        write(readme, text.rstrip("\n") + "\n\n" + quick)
        print("(Quick start was added at the end of the README)")

print("\nDone. Repo address used in the README:", url)