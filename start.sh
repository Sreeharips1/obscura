#!/usr/bin/env bash
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
