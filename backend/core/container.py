"""
Core: DI Container

Manual dependency injection wiring.
Single source of truth for which concrete adapter implements each port.
Constructed once during app lifespan — no global mutable state exposed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.itinerary_repo_port import IItineraryRepository
from backend.application.ports.llm_port import ILLMClient
from backend.application.ports.online_adapter_port import IOnlineAdapter
from backend.application.ports.vector_store_port import IVectorStore
from backend.application.use_cases.export_itinerary import ExportItineraryUseCase
from backend.application.use_cases.generate_itinerary import GenerateItineraryUseCase
from backend.application.use_cases.get_itinerary import GetItineraryUseCase
from backend.application.use_cases.list_itineraries import ListItinerariesUseCase
from backend.application.use_cases.list_destinations import ListDestinationsUseCase
from backend.application.use_cases.update_day import UpdateDayUseCase
from backend.application.use_cases.regenerate_day import RegenerateDayUseCase
from backend.application.use_cases.toggle_favorite import ToggleFavoriteUseCase
from backend.application.use_cases.resume_workflow import ResumeWorkflowUseCase
from backend.core.config import Settings
from backend.application.ports.checkpoint_repo_port import ICheckpointRepository
from backend.application.ports.trace_repo_port import ITraceRepository
from backend.infrastructure.repositories.json_checkpoint_repo import JSONFileCheckpointRepository
from backend.infrastructure.repositories.json_trace_repo import JSONFileTraceRepository
import os
from backend.infrastructure.adapters.online_stubs import POIAdapter, WeatherAdapter
from backend.infrastructure.knowledge_base.ingestion_service import IngestionService
from backend.infrastructure.llm.foundry_llm_adapter import FoundryLLMAdapter
from backend.infrastructure.persistence.sqlite_itinerary_repo import SQLiteItineraryRepository
from backend.infrastructure.vector_store.chroma_adapter import ChromaAdapter


@dataclass
class Container:
    """
    Holds all instantiated services and use cases.

    To swap an implementation (e.g., replace ChromaDB with Qdrant):
      1. Create a new adapter implementing IVectorStore
      2. Change the single line in `build()` that constructs vector_store
      3. Nothing else changes
    """

    # ── Ports ─────────────────────────────────────────────────────────────────
    llm_client: ILLMClient
    embedding_client: IEmbeddingClient
    vector_store: IVectorStore
    itinerary_repo: IItineraryRepository
    checkpoint_repo: ICheckpointRepository
    trace_repo: ITraceRepository
    online_adapters: list[IOnlineAdapter]

    # ── Services ──────────────────────────────────────────────────────────────
    ingestion_service: IngestionService

    # ── Use Cases ─────────────────────────────────────────────────────────────
    generate_itinerary: GenerateItineraryUseCase
    get_itinerary: GetItineraryUseCase
    list_itineraries: ListItinerariesUseCase
    export_itinerary: ExportItineraryUseCase
    list_destinations: ListDestinationsUseCase
    update_day: UpdateDayUseCase
    regenerate_day: RegenerateDayUseCase
    toggle_favorite: ToggleFavoriteUseCase
    resume_workflow: ResumeWorkflowUseCase


def build(settings: Settings) -> Container:
    """
    Construct and wire the entire application dependency graph.
    Called once during FastAPI lifespan startup.
    """
    from backend.infrastructure.embeddings.ollama_embedding_adapter import OllamaEmbeddingAdapter

    # ── Infrastructure ────────────────────────────────────────────────────────
    if getattr(settings, "llm_provider", "foundry") == "ollama":
        from backend.infrastructure.llm.ollama_llm_adapter import OllamaLLMAdapter
        ollama_base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
        llm_client = OllamaLLMAdapter(
            base_url=ollama_base_url,
            model=getattr(settings, "ollama_llm_model", "phi4-mini:latest"),
        )
    else:
        llm_client = FoundryLLMAdapter(
            base_url=settings.foundry_base_url,
            model=settings.foundry_llm_model,
            api_key=settings.foundry_api_key,
        )

    # Embeddings — Ollama nomic-embed-text (768-dim) running in local Docker container.
    # LocalEmbeddingAdapter (sentence-transformers, all-MiniLM-L6-v2, 384-dim) is kept
    # as a documented fallback but is NOT wired here.
    # IMPORTANT: ChromaDB collection must be rebuilt when switching embedding models
    # because dimension mismatch (384 vs 768) will cause insert errors.
    ollama_base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
    embedding_client = OllamaEmbeddingAdapter(
        base_url=ollama_base_url,
        model="nomic-embed-text",
    )

    vector_store = ChromaAdapter(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
    )

    checkpoint_repo = JSONFileCheckpointRepository(
        directory=os.path.join(os.path.dirname(settings.sqlite_db_path), ".checkpoints")
    )
    
    trace_repo = JSONFileTraceRepository(
        directory=os.path.join(os.path.dirname(settings.sqlite_db_path), ".traces")
    )

    itinerary_repo = SQLiteItineraryRepository(
        db_path=settings.sqlite_db_path,
    )

    online_adapters: list[IOnlineAdapter] = [
        WeatherAdapter(),
        POIAdapter(),
    ]

    # ── Internal services ─────────────────────────────────────────────────────
    ingestion_service = IngestionService(
        vector_store=vector_store,
        embedding_client=embedding_client,
    )

    # ── Use cases ─────────────────────────────────────────────────────────────
    generate_uc = GenerateItineraryUseCase(
        llm_client=llm_client,
        embedding_client=embedding_client,
        vector_store=vector_store,
        itinerary_repo=itinerary_repo,
        checkpoint_repo=checkpoint_repo,
        trace_repo=trace_repo,
        online_adapters=online_adapters,
    )
    get_uc = GetItineraryUseCase(itinerary_repo)
    list_uc = ListItinerariesUseCase(itinerary_repo)
    export_uc = ExportItineraryUseCase(repo=itinerary_repo)
    list_dest_uc = ListDestinationsUseCase(repo=itinerary_repo)
    update_day_uc = UpdateDayUseCase(repo=itinerary_repo)
    regenerate_day_uc = RegenerateDayUseCase(
        llm_client=llm_client,
        embedding_client=embedding_client,
        vector_store=vector_store,
        itinerary_repo=itinerary_repo,
    )
    toggle_favorite_uc = ToggleFavoriteUseCase(repo=itinerary_repo)
    resume_workflow_uc = ResumeWorkflowUseCase(
        checkpoint_repo=checkpoint_repo,
        generate_itinerary_use_case=generate_uc,
    )

    return Container(
        llm_client=llm_client,
        embedding_client=embedding_client,
        vector_store=vector_store,
        itinerary_repo=itinerary_repo,
        checkpoint_repo=checkpoint_repo,
        trace_repo=trace_repo,
        online_adapters=online_adapters,
        ingestion_service=ingestion_service,
        generate_itinerary=generate_uc,
        get_itinerary=get_uc,
        list_itineraries=list_uc,
        export_itinerary=export_uc,
        list_destinations=list_dest_uc,
        update_day=update_day_uc,
        regenerate_day=regenerate_day_uc,
        toggle_favorite=toggle_favorite_uc,
        resume_workflow=resume_workflow_uc,
    )
