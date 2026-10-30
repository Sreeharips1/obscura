from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.privacy import router as privacy_router
from app.routes.chat import router as chat_router

app = FastAPI(
    title="OBSCURA API",
    version="0.1.0",
    description="Privacy-preserving AI gateway",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(privacy_router, prefix="/api/privacy", tags=["privacy"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "obscura"}
