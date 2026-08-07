"""
Wikipedia Knowledge Provider.
Fetches general context from Wikipedia REST API.
"""
import logging
import httpx

from backend.application.ports.knowledge_provider import IDestinationKnowledgeProvider
from backend.domain.models.destination import ResolvedDestination, KnowledgeDocument

logger = logging.getLogger(__name__)


class WikipediaProvider(IDestinationKnowledgeProvider):
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
        # Wikipedia requires a descriptive User-Agent
        self.headers = {
            "User-Agent": "CartenaTravelAgent/1.0 (contact@example.com)"
        }

    async def get_destination_context(self, destination: ResolvedDestination, query_text: str) -> list[KnowledgeDocument]:
        """
        Fetch summary from Wikipedia. Note that query_text is ignored here because
        Wikipedia's summary API just takes the page title.
        """
        page_title = destination.canonical_name.replace(" ", "_")
        url = f"{self.base_url}{page_title}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                
            if response.status_code == 200:
                data = response.json()
                extract = data.get("extract", "")
                if extract:
                    doc = KnowledgeDocument(
                        source="wikipedia",
                        title=data.get("title", destination.canonical_name),
                        content=extract,
                        destination=destination.canonical_name,
                        metadata={"provider": "wikipedia", "dynamic": True}
                    )
                    return [doc]
                
            logger.warning(f"Wikipedia returned {response.status_code} for {page_title}")
        except Exception as e:
            logger.error(f"Error fetching Wikipedia data for {page_title}: {e}")
            
        return []
