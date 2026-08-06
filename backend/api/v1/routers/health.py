"""API Router: GET /api/v1/health — system health check."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from backend.api.schemas.responses import HealthResponseDTO
from backend.core.container import Container

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponseDTO,
    summary="Check system health (Ollama + ChromaDB status)",
)
async def health_check(request: Request) -> HealthResponseDTO:
    container: Container = request.app.state.container

    # Run health checks concurrently
    import asyncio
    llm_ok, emb_ok, chroma_ok = await asyncio.gather(
        container.llm_client.health_check(),
        container.embedding_client.health_check(),
        container.vector_store.health_check(),
    )

    kb_count = 0
    if chroma_ok:
        try:
            kb_count = await container.vector_store.document_count()
        except Exception:
            pass

    if llm_ok and chroma_ok:
        status = "healthy"
    elif chroma_ok:
        status = "degraded"
    else:
        status = "offline"

    # Model adları adapter'lardan gelir, ayarlardan değil: ayar bir şeyi
    # yapılandırmıyorsa raporlamak kullanıcıya yalan söylemektir.
    return HealthResponseDTO(
        status=status,
        llm="online" if llm_ok else "offline",
        embedding="online" if emb_ok else "offline",
        chroma="ready" if chroma_ok else "not_ready",
        kb_document_count=kb_count,
        llm_model=container.llm_client.model_name,
        embedding_model=container.embedding_client.model_name,
    )
