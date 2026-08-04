"""
FastAPI Application Entry Point

Responsibilities:
  - Create the FastAPI app with lifespan context
  - Build the DI container
  - Run knowledge base ingestion on startup
  - Mount all routers
  - Configure CORS and exception handlers
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1.routers import generate, health, itineraries, destinations, world
from backend.core.config import settings
from backend.core.container import build as build_container
from backend.core.exceptions import CartenaError
from backend.infrastructure.knowledge_base import loader

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup / shutdown lifecycle.

    On startup:
      1. Build DI container (instantiates all adapters)
      2. Load KB data from JSON
      3. Run idempotent ingestion into ChromaDB

    On shutdown:
      - Nothing critical; ChromaDB persists automatically.
    """
    logger.info("Starting Cartena AI Travel Assistant...")

    # Build and store container on app state
    container = build_container(settings)
    app.state.container = container

    # Load + ingest knowledge base
    chunks = loader.load(settings.kb_data_path)
    ingested = await container.ingestion_service.ingest(chunks)
    if ingested == 0:
        logger.error(
            "Knowledge base is EMPTY (0 chunks indexed). RAG retrieval will "
            "miss for every city. Check KB_DATA_PATH=%s — the file is "
            "likely missing or empty at that path.",
            settings.kb_data_path,
        )
    else:
        logger.info("Knowledge base ready. %d chunks re-indexed.", ingested)

    logger.info(
        "Cartena is ready. LLM: %s | Embedding: %s",
        container.llm_client.model_name,
        container.embedding_client.model_name,
    )

    yield  # Application runs here

    logger.info("Cartena shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cartena – AI Travel Assistant API",
        description="Offline-capable AI travel planning with local LLM + RAG.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(CartenaError)
    async def cartena_error_handler(request: Request, exc: CartenaError):
        return JSONResponse(
            status_code=500,
            content={"error": type(exc).__name__, "detail": str(exc)},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(health.router,       prefix=prefix, tags=["System"])
    app.include_router(generate.router,     prefix=prefix, tags=["Itinerary"])
    app.include_router(itineraries.router,  prefix=prefix, tags=["Itinerary"])
    app.include_router(destinations.router, prefix=prefix, tags=["Destinations"])
    app.include_router(world.router,        prefix=prefix + "/world", tags=["World"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
