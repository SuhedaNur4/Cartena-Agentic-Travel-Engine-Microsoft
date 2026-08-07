"""
Local Knowledge Provider using ChromaDB.
"""
import logging

from backend.application.ports.embedding_port import IEmbeddingClient
from backend.application.ports.vector_store_port import IVectorStore
from backend.application.ports.knowledge_provider import IDestinationKnowledgeProvider
from backend.domain.models.destination import ResolvedDestination, KnowledgeDocument

logger = logging.getLogger(__name__)


from backend.domain.services.city import normalize_city


class LocalKnowledgeProvider(IDestinationKnowledgeProvider):
    def __init__(self, embedding_client: IEmbeddingClient, vector_store: IVectorStore):
        self.embedding_client = embedding_client
        self.vector_store = vector_store

    async def get_destination_context(self, destination: ResolvedDestination, query_text: str) -> list[KnowledgeDocument]:
        query_vector = await self.embedding_client.embed(query_text)
        city_key = normalize_city(destination.canonical_name)

        raw_chunks = await self.vector_store.retrieve(
            query_vector=query_vector,
            city=city_key,
            top_k=5,
        )

        unique_contents = list(
            dict.fromkeys(chunk.content for chunk, _score in raw_chunks)
        )

        if not unique_contents:
            return []

        docs = []
        for content in unique_contents:
            docs.append(KnowledgeDocument(
                source="local",
                title=destination.canonical_name,
                content=content,
                destination=destination.canonical_name,
                metadata={"provider": "local"}
            ))

        return docs
