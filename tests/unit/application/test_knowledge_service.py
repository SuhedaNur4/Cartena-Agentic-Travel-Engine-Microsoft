import pytest
from unittest.mock import Mock, AsyncMock
from backend.application.services.knowledge_service import KnowledgeService
from backend.application.ports.knowledge_provider import IDestinationKnowledgeProvider
from backend.domain.models.destination import ResolvedDestination, KnowledgeDocument
from backend.application.services.knowledge_service import DestinationResolutionError

class MockProvider(IDestinationKnowledgeProvider):
    def __init__(self, name, returns_doc=True):
        self._name = name
        self._returns_doc = returns_doc

    @property
    def name(self) -> str:
        return self._name

    async def get_destination_context(self, destination: ResolvedDestination, query_text: str = "") -> list[KnowledgeDocument]:
        if self._returns_doc:
            return [KnowledgeDocument(
                destination=destination.canonical_name,
                source=self._name,
                title="Test title",
                content="Test content",
                metadata={"chunked_contents": ["Test chunk"]}
            )]
        return []

@pytest.fixture
def mock_resolver():
    resolver = Mock()
    resolver.resolve.side_effect = lambda raw: ResolvedDestination(
        input_name=raw,
        canonical_name=raw.capitalize(),
        country="Test Country",
        destination_type="city"
    )
    return resolver

@pytest.mark.asyncio
async def test_local_hit_returns_immediately(mock_resolver):
    local_provider = MockProvider("local", returns_doc=True)
    wiki_provider = MockProvider("wikipedia", returns_doc=True)
    
    service = KnowledgeService(resolver=mock_resolver, providers=[local_provider, wiki_provider])
    docs = await service.get_context_for_destination("tokyo", "query")
    
    assert docs
    assert docs[0].source == "local"

@pytest.mark.asyncio
async def test_local_miss_triggers_wikipedia(mock_resolver):
    local_provider = MockProvider("local", returns_doc=False)
    wiki_provider = MockProvider("wikipedia", returns_doc=True)
    
    service = KnowledgeService(resolver=mock_resolver, providers=[local_provider, wiki_provider])
    docs = await service.get_context_for_destination("eskisehir", "query")
    
    assert docs
    assert docs[0].source == "wikipedia"

@pytest.mark.asyncio
async def test_unknown_destination_raises_error(mock_resolver):
    local_provider = MockProvider("local", returns_doc=False)
    wiki_provider = MockProvider("wikipedia", returns_doc=False)
    
    service = KnowledgeService(resolver=mock_resolver, providers=[local_provider, wiki_provider])
    
    with pytest.raises(DestinationResolutionError):
        await service.get_context_for_destination("fakeland", "query")
