import hmac
import os

from fastapi.responses import JSONResponse
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.privacy import router as privacy_router
from app.routes.chat import router as chat_router
from app.routes.image import router as image_router
from app.routes.pdf import router as pdf_router

import threading
from contextlib import asynccontextmanager


def _warm_up():
    try:
        from app.privacy.detectors.pii_model import get_model
        from app.privacy.image.ocr import get_engine

        get_model()
        get_engine()
        print("[OBSCURA] Models ready.")
    except Exception as error:
        print(f"[OBSCURA] Warm-up skipped: {type(error).__name__}: {error}")


@asynccontextmanager
async def lifespan(app):
    # Background thread: the server starts immediately.
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="OBSCURA API",
    version="0.2.0",
    description="Privacy-preserving AI gateway",
)

ACCESS_KEY = os.getenv("OBSCURA_ACCESS_KEY", "")


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "OBSCURA_CORS_ORIGINS",
            "http://localhost:5173,http://localhost:8080",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(privacy_router, prefix="/api/privacy", tags=["privacy"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(image_router, prefix="/api/image", tags=["image"])
app.include_router(pdf_router, prefix="/api/pdf", tags=["pdf"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "obscura", "auth_required": bool(ACCESS_KEY)}


@app.get("/api/auth/check")
def auth_check():
    return {"ok": True}
