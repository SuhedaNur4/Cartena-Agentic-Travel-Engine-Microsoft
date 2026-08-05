"""
Core: Application settings via pydantic-settings.

All values read from environment variables (or .env file).
Type-safe, validated at startup — fails fast on misconfiguration.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────────
    llm_provider: str = "foundry"  # "foundry" or "ollama"
    
    # ── Foundry Local ─────────────────────────────────────────────────────────
    foundry_base_url: str = "http://localhost:5273/v1"
    foundry_api_key: str = "foundry"
    foundry_llm_model: str = "phi-4-mini"
    
    # ── Ollama Local ──────────────────────────────────────────────────────────
    ollama_llm_model: str = "phi4-mini:latest"
    # KULLANILMIYOR: Foundry Local kataloğunda embedding modeli yok.
    # Embedding LocalEmbeddingAdapter (sentence-transformers) ile çalışır.
    # Geriye dönük .env uyumluluğu için duruyor; hiçbir şeyi yapılandırmaz.
    foundry_embedding_model: str = "qwen3-embedding-0.6b"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "destinations"

    # ── SQLite ────────────────────────────────────────────────────────────────
    sqlite_db_path: str = "./data/cartena.db"

    # ── Knowledge Base ────────────────────────────────────────────────────────
    kb_data_path: str = "./backend/data/kb/destinations.json"

    # ── API Server ────────────────────────────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "INFO"

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


# Module-level singleton — imported wherever config is needed
settings = Settings()
