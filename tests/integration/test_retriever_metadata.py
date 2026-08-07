import pytest
import asyncio
from unittest.mock import AsyncMock
from backend.application.use_cases.state_graph.state import CartenaState
from backend.application.use_cases.state_graph.nodes import retriever_node
from backend.domain.models.trip_request import TripRequest, BudgetLevel, Interest
from backend.domain.models.destination import KnowledgeDocument
from backend.application.services.knowledge_service import DestinationResolutionError

@pytest.mark.asyncio
async def test_retriever_metadata_preservation():
    # Setup mock KnowledgeService
    mock_ks = AsyncMock()
    async def mock_get_context(dest_name, query):
        return [KnowledgeDocument(
            destination=dest_name,
            source="mock_source",
            title=f"title {dest_name}",
            content=f"Content for {dest_name}",
            metadata={}
        )]

    mock_ks.get_context_for_destination.side_effect = mock_get_context
    
    # Setup State
    req = TripRequest(
        destinations=("Tokyo", "Kyoto"),
        duration_days=5,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 3, "Kyoto": 2}
    )
    
    state = CartenaState(
        workflow_id="test_wf",
        request=req
    )
    
    # Run retriever_node
    state = await retriever_node(state, mock_ks)
    
    # Verify metadata is preserved in chunks
    tokyo_chunks = [c for c in state.rag_chunks if "title Tokyo" in c]
    kyoto_chunks = [c for c in state.rag_chunks if "title Kyoto" in c]
    
    assert len(tokyo_chunks) == 1
    assert len(kyoto_chunks) == 1
    assert "Content for Tokyo" in tokyo_chunks[0]
    assert "Content for Kyoto" in kyoto_chunks[0]


@pytest.mark.asyncio
async def test_retriever_controlled_failure():
    mock_ks = AsyncMock()
    def side_effect_mock(dest, query):
        if dest == "Fakeland":
            raise DestinationResolutionError("Could not resolve Fakeland")
        return [KnowledgeDocument(destination=dest, source="local", title=dest, content="Content")]
        
    mock_ks.get_context_for_destination.side_effect = side_effect_mock
    
    req = TripRequest(
        destinations=("Tokyo", "Fakeland"),
        duration_days=5,
        budget=BudgetLevel.MEDIUM,
        interests=(Interest.CULTURE,),
        allocation_mode="USER",
        allocations={"Tokyo": 3, "Fakeland": 2}
    )
    
    events = []
    state = CartenaState(
        workflow_id="test_wf",
        request=req
    )
    # mock emit directly on the object to capture events
    state.emit = lambda x: events.append(x)
    
    # Run retriever_node
    with pytest.raises(RuntimeError, match="Fakeland"):
        await retriever_node(state, mock_ks)
    
    # Check if error event was emitted
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) > 0
    assert "Fakeland" in error_events[0]["message"]
