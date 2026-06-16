from contextlib import asynccontextmanager

from agents import set_default_openai_key
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routers.assistant import router as assistant_router
from api.routers.chat import router as chat_router
from api.routers.research import router as research_router
from config import settings
from db import close_db, init_db
from services.pinecone import AsyncPineconeServerlessHook
from utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    if not settings.openai_api_key:
        logger.error(
            "[app] [lifespan] : OPENAI_API_KEY not set; please define it in your .env file"
        )
    else:
        set_default_openai_key(settings.openai_api_key)
        logger.info("[app] [lifespan] : OpenAI API key configured")

    await init_db()

    logger.info("[app] [lifespan] : Startup complete")

    yield

    await AsyncPineconeServerlessHook.cleanup_all()
    await close_db()

    logger.info("[app] [lifespan] : Shutdown complete")


app = FastAPI(
    title="Akin Chat API",
    description="Akin Chat API is a RESTful API for the Akin Chat application. It provides endpoints for the Akin Chat application to interact with the database and the OpenAI API.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing."""
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Routes
app.include_router(research_router, prefix=f"/{settings.api_version}")
app.include_router(assistant_router, prefix=f"/{settings.api_version}")
app.include_router(chat_router, prefix=f"/{settings.api_version}")


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to the OpenAI Agents Streaming API",
        "version": settings.app_version,
        "architecture": "Dedicated routers per agent",
        "features": [
            "Per-agent dedicated endpoints",
            "Streaming events for agent updates, raw responses, and run items",
            "Simple and scalable",
            "OpenAI Agents SDK",
        ],
        "api_version": settings.api_version,
        "endpoints": {
            "chat": f"/{settings.api_version}/chat",
            "assistant": f"/{settings.api_version}/assistant",
            "research": f"/{settings.api_version}/research",
        },
        "api_docs": "/docs",
    }


@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
        app_dir="src",
    )
