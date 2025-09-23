"""Use case for assimilating knowledge into the graph database.

This module defines the use case for processing textual content,
extracting facts, and associating them with entities.
"""

from datetime import datetime, timezone
from typing import Any, Protocol, cast
from uuid import uuid4

from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
    EntityDto,
    FactDto,
    IdentifierPayload,
    SourceDto,
)
from app.features.graph.models import (
    DerivedFrom,
    Entity,
    Fact,
    HasFact,
    HasIdentifier,
    Identifier,
    Source,
)
from app.features.graph.repositories.arcadedb_repository import ArcadedbRepository


class FactExtractor(Protocol):
    """Protocol for extracting facts from text content."""

    async def extract_facts(
        self, content: str, entity_identifier: IdentifierPayload
    ) -> list[dict[str, Any]]:
        """Extract facts from text content."""
        ...


class AssimilateKnowledgeUseCase(Protocol):
    """Protocol for the assimilate knowledge use case."""

    async def execute(
        self, request: AssimilateKnowledgeRequest
    ) -> AssimilateKnowledgeResponse:
        """Process content and associate facts with an entity."""
        ...


class AssimilateKnowledgeUseCaseImpl:
    """Implementation of the assimilate knowledge use case."""

    def __init__(self, repository: ArcadedbRepository, fact_extractor: FactExtractor):
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for graph database operations
            fact_extractor: Service for extracting facts from text
        """
        self.repository: ArcadedbRepository = repository
        self.fact_extractor: FactExtractor = fact_extractor

    async def execute(
        self, request: AssimilateKnowledgeRequest
    ) -> AssimilateKnowledgeResponse:
        """Process content and associate facts with an entity.

        Args:
            request: The request containing identifier, content, and timestamp

        Returns:
            Response containing the entity, source, and extracted facts
        """
        # 1. Find or create entity based on identifier
        entity_result = await self.repository.find_entity_by_identifier(
            request.identifier.value, request.identifier.type
        )

        if entity_result is None:
            # Create new entity with identifier
            new_entity = Entity(id=uuid4(), created_at=datetime.now(timezone.utc))
            identifier = Identifier(
                value=request.identifier.value, type=request.identifier.type
            )
            has_identifier = HasIdentifier(
                from_entity_id=new_entity.id,
                to_identifier_value=identifier.value,
                is_primary=True,
                created_at=datetime.now(timezone.utc),
            )

            create_result = await self.repository.create_entity(
                new_entity, identifier, has_identifier
            )
            entity_result = {
                "entity": create_result["entity"],
                "identifier": create_result["identifier"],
                "relationship": create_result["relationship"],
            }

        entity: Entity = cast(Entity, entity_result["entity"])

        # 2. Create source from content and timestamp
        source = Source(
            id=uuid4(),
            content=request.content,
            timestamp=request.timestamp or datetime.now(timezone.utc),
        )
        created_source = await self.repository.create_source(source)

        # 3. Extract facts using fact_extractor
        extracted_facts_data = await self.fact_extractor.extract_facts(
            request.content, request.identifier
        )
        extracted_facts: list[FactDto] = []

        # 4. Create and link facts to entity
        for fact_data in extracted_facts_data:
            # Create fact model
            fact = Fact(name=fact_data["name"], type=fact_data["type"])

            # Ensure fact_id is not None (this should be set by the model validator)
            if not fact.fact_id:
                raise ValueError(f"Fact ID cannot be None for fact: {fact.name}")

            # Create relationships
            has_fact = HasFact(
                from_entity_id=entity.id,
                to_fact_id=fact.fact_id,
                verb=fact_data.get("verb", "has"),
                confidence_score=fact_data.get("confidence_score", 1.0),
                created_at=datetime.now(timezone.utc),
            )

            derived_from = DerivedFrom(
                from_fact_id=fact.fact_id, to_source_id=created_source.id
            )

            # Link fact to entity with source in single transaction
            created_fact, _, _ = await self.repository.link_fact_to_entity_with_source(
                entity, fact, created_source, has_fact, derived_from
            )

            # Add to response
            fact_dto = FactDto(
                name=created_fact.name,
                type=created_fact.type,
                fact_id=created_fact.fact_id,
            )
            extracted_facts.append(fact_dto)

        # 5. Return response with entity, source, and extracted facts
        return AssimilateKnowledgeResponse(
            entity=EntityDto(
                id=entity.id,
                created_at=entity.created_at,
                metadata=entity.metadata or {},
            ),
            source=SourceDto(
                id=created_source.id,
                content=created_source.content,
                timestamp=created_source.timestamp,
            ),
            extracted_facts=extracted_facts,
        )
