"""Protocol for data summarization services."""

from typing import Protocol

from app.features.graph.dtos.knowledge_dto import GetEntityResponse


class DataSummarizer(Protocol):
    """Protocol for services that generate natural language summaries of entity data.

    This protocol defines the contract for data summarization services.
    Implementations can use different LLM providers or summarization strategies.
    """

    async def summarize(
        self, entity_data: GetEntityResponse, lang: str | None = None
    ) -> str:
        """Generate a natural language summary of entity data.

        Args:
            entity_data: The complete entity data including facts and relationships
            lang: Optional language code (e.g., 'pt-br', 'es', 'fr'). Defaults to English.

        Returns:
            A natural language summary string optimized for LLM consumption
        """
        ...
