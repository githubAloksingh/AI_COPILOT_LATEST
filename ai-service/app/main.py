import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.routes import router
from app.api.schemas import HealthResponse
from app.services.retrieval_service import retrieval_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Service on port %s", settings.port)
    try:
        retrieval_service.ensure_collection()
    except Exception as e:
        logger.warning("Could not connect to Chroma on startup (will retry lazily): %s", e)
    yield
    logger.info("Shutting down AI Service")


app = FastAPI(
    title="AI Work Copilot - AI & RAG Service",
    description="Dedicated microservice handling document parsing, vector embeddings, Chroma RAG retrieval, and Gemini prompt generation.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal AI Service Error: {str(exc)}"}
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint checking service status, Chroma connectivity, and Gemini configuration."""
    chroma_status = "connected" if (retrieval_service.base_collection_url or retrieval_service._local_collection) else "ready (lazy init)"
    gemini_configured = bool(settings.gemini_api_key and settings.gemini_api_key.strip())

    return HealthResponse(
        status="healthy",
        service="ai-service",
        chroma=chroma_status,
        gemini_configured=gemini_configured
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "AI Work Copilot - Python AI/RAG Service",
        "status": "online",
        "docs": "/docs"
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
