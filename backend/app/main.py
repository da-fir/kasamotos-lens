from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analyze
from app.services.ocr_service import ocr_service
from app.services.nlp_service import nlp_service
from app.services.ai_service import ai_service
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    ocr_service.initialize()
    nlp_service.initialize()
    ai_service.initialize()
    yield

app = FastAPI(
    title="Nihongo Lens API",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ocr_ready": ocr_service._initialized,
        "nlp_ready": nlp_service._initialized,
        "ai_ready": ai_service._initialized,
    }