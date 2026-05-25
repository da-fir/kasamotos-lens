from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analyze
from app.services.ocr_service import ocr_service
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load heavy models before accepting requests
    ocr_service.initialize()
    yield
    # Shutdown: nothing to clean up for now

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
    return {"status": "ok", "ocr_ready": ocr_service._initialized}