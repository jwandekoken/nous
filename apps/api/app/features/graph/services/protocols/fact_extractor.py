"""Protocol for fact extraction services."""

from typing import Protocol

from app.features.graph.dtos.knowledge_dto import ExtractedFactDto, IdentifierDto


class FactExtractor(Protocol):
    """Protocol for extracting facts from text content.

    This protocol defines the contract for fact extraction services.
    Implementations can use different LLM providers or extraction strategies.
    """

    async def extract_facts(
        self,
        content: str,
        entity_identifier: IdentifierDto,
        history: list[str] | None = None,
    ) -> list[ExtractedFactDto]:
        """Extract facts from text content.

        Args:
            content: The text content to extract facts from
            entity_identifier: The entity identifier payload
            history: Optional list of previous conversational turns for context.

        Returns:
            List of extracted facts
        """
        ...
