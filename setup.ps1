# One-time setup for Windows.
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
