"""Use case for retrieving entity information by identifier.

This module defines the use case for fetching entity details including
their identifiers and associated facts with sources.
"""

from fastapi import HTTPException, status

from app.features.graph.dtos.knowledge_dto import (
    EntityDto,
    FactDto,
    FactWithSourceDto,
    GetEntityResponse,
    HasFactDto,
    HasIdentifierDto,
    IdentifierDto,
    IdentifierWithRelationshipDto,
    SourceDto,
)
from app.features.graph.models.fact_model import Fact
from app.features.graph.repositories.base import GraphRepository
from app.features.graph.repositories.types import FindEntityResult


class GetEntityUseCaseImpl:
    """Implementation of the get entity use case."""

    def __init__(self, repository: GraphRepository):
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for graph database operations
        """
        self.repository: GraphRepository = repository

    async def execute(
        self, identifier_value: str, identifier_type: str
    ) -> GetEntityResponse:
        """Retrieve entity information by identifier.

        Args:
            identifier_value: The identifier value (e.g., 'user@example.com')
            identifier_type: The identifier type (e.g., 'email', 'phone')

        Returns:
            GetEntityResponse containing the entity, identifier, and facts

        Raises:
            HTTPException: If the entity is not found (404)
        """
        entity_result: (
            FindEntityResult | None
        ) = await self.repository.find_entity_by_identifier(
            identifier_value, identifier_type
        )

        if entity_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity with identifier '{identifier_type}:{identifier_value}' not found",
            )

        # Map entity to DTO
        entity_dto = EntityDto(
            id=entity_result["entity"].id,
            created_at=entity_result["entity"].created_at,
            metadata=entity_result["entity"].metadata or {},
        )

        # Map identifier and relationship to DTOs
        identifier_dto = IdentifierDto(
            value=entity_result["identifier"]["identifier"].value,
            type=entity_result["identifier"]["identifier"].type,
        )
        has_identifier_dto = HasIdentifierDto(
            is_primary=entity_result["identifier"]["relationship"].is_primary,
            created_at=entity_result["identifier"]["relationship"].created_at,
        )
        identifier_with_relationship_dto = IdentifierWithRelationshipDto(
            identifier=identifier_dto,
            relationship=has_identifier_dto,
        )

        # Map facts with sources to DTOs
        facts_with_sources_dto: list[FactWithSourceDto] = []
        for fact_with_source in entity_result["facts_with_sources"]:
            fact: Fact = fact_with_source["fact"]
            relationship_dto = HasFactDto(
                verb=fact_with_source["relationship"].verb,
                confidence_score=fact_with_source["relationship"].confidence_score,
                created_at=fact_with_source["relationship"].created_at,
            )
            source_dto = None
            if fact_with_source["source"] is not None:
                source_dto = SourceDto(
                    id=fact_with_source["source"].id,
                    content=fact_with_source["source"].content,
                    timestamp=fact_with_source["source"].timestamp,
                )
            fact_with_source_dto = FactWithSourceDto(
                fact=FactDto(
                    name=fact.name,
                    type=fact.type,
                    fact_id=fact.fact_id,
                ),
                relationship=relationship_dto,
                source=source_dto,
            )
            facts_with_sources_dto.append(fact_with_source_dto)

        return GetEntityResponse(
            entity=entity_dto,
            identifier=identifier_with_relationship_dto,
            facts=facts_with_sources_dto,
        )
