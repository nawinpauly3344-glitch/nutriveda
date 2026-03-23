"""
NutriVeda Nutrition Consultation System — FastAPI Backend
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

from models.database import init_db
from api.intake import router as intake_router
from api.admin import router as admin_router
from api.payment import router as payment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    log.info("=" * 60)
    log.info("  NutriVeda Nutrition System starting up...")
    log.info("=" * 60)

    # Initialize database
    await init_db()
    log.info("✓ Database initialized")

    # Check RAG status
    try:
        from rag.vectorstore import vectorstore_exists
        exists, count = vectorstore_exists()
        if exists:
            log.info(f"✓ RAG knowledge base loaded: {count} chunks from NutriVeda material")
        else:
            log.warning(
                "⚠ RAG knowledge base is EMPTY. Run: build_rag.bat\n"
                "  This indexes your MHB PDF/PPT files using OpenAI embeddings."
            )
    except Exception as e:
        log.warning(f"Could not check RAG status: {e}")

    log.info("✓ API ready at http://localhost:8000")
    log.info("✓ Docs at http://localhost:8000/docs")

    yield

    log.info("NutriVeda Nutrition System shutting down...")


app = FastAPI(
    title="MHB Nutrition Consultation API",
    description="Personalized nutrition consultation system powered by RAG + GPT-4o",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js frontend
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(intake_router)
app.include_router(admin_router)
app.include_router(payment_router)

# Serve PDF files
pdf_dir = Path(__file__).parent / "pdf_plans"
pdf_dir.mkdir(exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=str(pdf_dir)), name="pdfs")


@app.get("/")
async def root():
    return {
        "message": "MHB Nutrition Consultation API",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
