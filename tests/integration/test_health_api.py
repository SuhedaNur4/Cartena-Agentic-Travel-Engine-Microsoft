"""/health gerçekten kullanılan modelleri raporluyor mu?"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.v1.routers import health as health_router
from tests.fakes.embedding import FakeEmbeddingClient
from tests.fakes.llm import FakeLLMClient
from tests.fakes.vector_store import FakeVectorStore


class FakeContainer:
    def __init__(self):
        self.llm_client = FakeLLMClient("", model_name="smollm2-135m-instruct")
        self.embedding_client = FakeEmbeddingClient(model_name="all-MiniLM-L6-v2")
        self.vector_store = FakeVectorStore([])


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(health_router.router, prefix="/api/v1")
    app.state.container = FakeContainer()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthReportsReality:
    async def test_embedding_model_is_the_one_actually_used(self, client):
        """
        Bugün settings.foundry_embedding_model raporlanıyor
        ('qwen3-0.6b-cuda-gpu:2') ama gerçekte all-MiniLM-L6-v2 çalışıyor.
        """
        body = (await client.get("/api/v1/health")).json()
        assert body["embedding_model"] == "all-MiniLM-L6-v2"

    async def test_llm_model_comes_from_the_adapter(self, client):
        body = (await client.get("/api/v1/health")).json()
        assert body["llm_model"] == "smollm2-135m-instruct"
