#!/usr/bin/env bash
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
