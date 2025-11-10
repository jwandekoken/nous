"""Use case for generating natural language summaries of entity data.

This module defines the use case for creating LLM-optimized textual summaries
of entity information including facts and relationships.
"""

from app.features.graph.dtos.knowledge_dto import (
    GetEntityResponse,
    GetEntitySummaryResponse,
)
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)
from app.features.graph.usecases.get_entity_usecase import GetEntityUseCaseImpl


class GetEntitySummaryUseCaseImpl:
    """Implementation of the get entity summary use case."""

    def __init__(
        self,
        get_entity_use_case: GetEntityUseCaseImpl,
        data_summarizer: LangChainDataSummarizer,
    ):
        """Initialize the use case with dependencies.

        Args:
            get_entity_use_case: Use case for fetching entity data
            data_summarizer: Service for generating natural language summaries
        """
        self.get_entity_use_case = get_entity_use_case
        self.data_summarizer = data_summarizer

    async def execute(
        self, identifier_value: str, identifier_type: str
    ) -> GetEntitySummaryResponse:
        """Generate a natural language summary of entity data.

        Args:
            identifier_value: The identifier value (e.g., 'user@example.com')
            identifier_type: The identifier type (e.g., 'email', 'phone')

        Returns:
            GetEntitySummaryResponse containing the summary, entity, and identifier

        Raises:
            HTTPException: If the entity is not found (404) - propagated from GetEntityUseCaseImpl
        """
        # Fetch the entity data
        entity_data: GetEntityResponse = await self.get_entity_use_case.execute(
            identifier_value=identifier_value, identifier_type=identifier_type
        )

        # Check if entity has facts - if not, skip LLM call to save costs
        if len(entity_data.facts) == 0:
            return GetEntitySummaryResponse(
                summary="This entity has no recorded facts in the knowledge graph.",
                entity=entity_data.entity,
                identifier=entity_data.identifier,
            )

        # Generate summary using the LLM
        summary = await self.data_summarizer.summarize(entity_data)

        return GetEntitySummaryResponse(
            summary=summary,
            entity=entity_data.entity,
            identifier=entity_data.identifier,
        )
