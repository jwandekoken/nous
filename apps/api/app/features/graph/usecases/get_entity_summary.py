"""Use case for generating natural language summaries of entity data.

This module defines the use case for creating LLM-optimized textual summaries
of entity information including facts and relationships.
"""

from app.features.graph.dtos.knowledge_dto import (
    GetEntityResponse,
    GetEntitySummaryResponse,
)
from app.features.graph.services.protocols import DataSummarizer
from app.features.graph.usecases.protocols import GetEntityUseCase


class GetEntitySummaryUseCaseImpl:
    """Implementation of the get entity summary use case."""

    def __init__(
        self,
        get_entity_use_case: GetEntityUseCase,
        data_summarizer: DataSummarizer,
    ):
        """Initialize the use case with dependencies.

        Args:
            get_entity_use_case: Use case for fetching entity data
            data_summarizer: Service for generating natural language summaries
        """
        self.get_entity_use_case = get_entity_use_case
        self.data_summarizer = data_summarizer

    async def execute(
        self,
        identifier_value: str,
        identifier_type: str,
        lang: str | None = None,
        rag_query: str | None = None,
        rag_top_k: int = 10,
        rag_min_score: float | None = None,
        rag_expand_hops: int = 0,
    ) -> GetEntitySummaryResponse:
        """Generate a natural language summary of entity data.

        Args:
            identifier_value: The identifier value (e.g., 'user@example.com')
            identifier_type: The identifier type (e.g., 'email', 'phone')
            lang: Optional language code (e.g., 'pt-br', 'es', 'fr'). Defaults to English.
            rag_query: Optional conversational query for semantic search
            rag_top_k: Number of vector candidates to retrieve
            rag_min_score: Optional similarity threshold
            rag_expand_hops: Optional graph expansion depth

        Returns:
            GetEntitySummaryResponse containing only the summary

        Raises:
            HTTPException: If the entity is not found (404) - propagated from GetEntityUseCaseImpl
        """
        # Fetch the entity data
        entity_data: GetEntityResponse = await self.get_entity_use_case.execute(
            identifier_value=identifier_value,
            identifier_type=identifier_type,
            rag_query=rag_query,
            rag_top_k=rag_top_k,
            rag_min_score=rag_min_score,
            rag_expand_hops=rag_expand_hops,
        )

        # Check if entity has facts - if not, skip LLM call to save costs
        if len(entity_data.facts) == 0:
            return GetEntitySummaryResponse(
                summary="This entity has no recorded facts in the knowledge graph."
            )

        # Generate summary using the LLM
        summary = await self.data_summarizer.summarize(entity_data, lang=lang)

        return GetEntitySummaryResponse(summary=summary)
