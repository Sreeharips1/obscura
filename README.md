# OBSCURA — Privacy-Preserving AI Gateway

OBSCURA is a single-platform AI chat application that detects potentially sensitive
information before an external AI provider receives the user's content.

Current milestone: **Phase 1 — Text privacy detection + reversible pseudonymization + Gemini chat**

## Current flow

User text
→ local privacy detection
→ user chooses detected items
→ temporary aliases are generated locally
→ sanitized preview
→ Gemini receives only sanitized text
→ Gemini response is restored locally
→ user sees the original values

## Security boundary

The alias mapping is never sent to Gemini.

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- Privacy engine: Python rules/regex (Phase 1)
- AI provider: Gemini via official `google-genai` SDK
- Temporary alias mapping: in-memory for Phase 1

## Run

### Backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Put your Gemini API key in .env
copy .env.example .env

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Gemini API

The current implementation uses the official `google-genai` Python SDK.
Create a Gemini API key in Google AI Studio and put it in `backend/.env`.

Do NOT commit `.env`.

## Next phases

1. Improve text detection with NER/context.
2. Add image OCR, face, QR and license-plate detection.
3. Add image sanitization and preview.
4. Add task-aware privacy.
5. Add risk scoring and explainability.
6. Add additional AI providers behind the same provider interface.
