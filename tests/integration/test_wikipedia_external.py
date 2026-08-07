import pytest
import asyncio
from backend.infrastructure.knowledge_base.wikipedia_provider import WikipediaProvider
from backend.domain.models.destination import ResolvedDestination

@pytest.mark.external
@pytest.mark.asyncio
async def test_wikipedia_external_api_call():
    provider = WikipediaProvider()
    
    dest = ResolvedDestination(
        input_name="eskişehir",
        canonical_name="Eskişehir",
        country="Turkey",
        destination_type="city"
    )
    docs = await provider.get_destination_context(dest, "")
    
    assert docs is not None
    assert len(docs) > 0
    assert docs[0].destination == "Eskişehir"
    assert docs[0].source == "wikipedia"
    assert len(docs[0].content) > 0
