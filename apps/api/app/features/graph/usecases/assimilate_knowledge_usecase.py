"""Use case for assimilating knowledge into the graph database.

This module defines the use case for processing textual content,
extracting facts, and associating them with entities.
"""

import logging
from datetime import datetime, timezone
from typing import Protocol, cast
from uuid import uuid4

from app.features.graph.dtos.knowledge_dto import (
    AssimilatedFactDto,
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
    EntityDto,
    ExtractedFactDto,
    FactDto,
    HasFactDto,
    IdentifierDto,
    SourceDto,
)
from app.features.graph.models import (
    Entity,
    Fact,
    HasIdentifier,
    Identifier,
    Source,
)
from app.features.graph.repositories.protocols import GraphRepository, VectorRepository

logger = logging.getLogger(__name__)


class FactExtractor(Protocol):
    """Protocol for extracting facts from text content."""

    async def extract_facts(
        self,
        content: str,
        entity_identifier: IdentifierDto,
        history: list[str] | None = None,
    ) -> list[ExtractedFactDto]:
        """Extract facts from text content."""
        ...


class AssimilateKnowledgeUseCaseImpl:
    """Implementation of the assimilate knowledge use case."""

    def __init__(
        self,
        repository: GraphRepository,
        fact_extractor: FactExtractor,
        vector_repository: VectorRepository | None = None,
    ):
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for graph database operations
            fact_extractor: Service for extracting facts from text
            vector_repository: Optional repository for vector operations (semantic memory)
        """
        self.repository: GraphRepository = repository
        self.fact_extractor: FactExtractor = fact_extractor
        self.vector_repository: VectorRepository | None = vector_repository

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

        # 3. Extract facts using fact_extractor
        extracted_facts_data = await self.fact_extractor.extract_facts(
            request.content, request.identifier, request.history
        )
        assimilated_facts: list[AssimilatedFactDto] = []

        # 4. Create and link facts to entity
        for fact_data in extracted_facts_data:
            # Create fact model
            fact = Fact(name=fact_data.name, type=fact_data.type)

            # Ensure fact_id is not None (this should be set by the model validator)
            if not fact.fact_id:
                raise ValueError(f"Fact ID cannot be None for fact: {fact.name}")

            # Add fact to entity using repository method
            result = await self.repository.add_fact_to_entity(
                entity_id=str(entity.id),
                fact=fact,
                source=source,
                verb=fact_data.verb,
                confidence_score=fact_data.confidence_score,
            )

            # 4.1. [NEW] Add to semantic memory if vector_repository is available
            if self.vector_repository:
                try:
                    _ = await self.vector_repository.add_semantic_memory(
                        entity_id=entity.id,
                        fact=result["fact"],
                        verb=result["has_fact_relationship"].verb,
                    )
                except Exception as e:
                    # Log error but don't fail assimilation (graceful degradation)
                    logger.warning(
                        "Failed to add semantic memory for fact %s: %s",
                        result["fact"].fact_id,
                        e,
                    )

            # Add to response
            fact_dto = FactDto(
                name=result["fact"].name,
                type=result["fact"].type,
                fact_id=result["fact"].fact_id,
            )
            has_fact_dto = HasFactDto(
                verb=result["has_fact_relationship"].verb,
                confidence_score=result["has_fact_relationship"].confidence_score,
                created_at=result["has_fact_relationship"].created_at,
            )
            assimilated_fact_dto = AssimilatedFactDto(
                fact=fact_dto,
                relationship=has_fact_dto,
            )
            assimilated_facts.append(assimilated_fact_dto)

        # 4. Return response with entity, source, and assimilated facts
        return AssimilateKnowledgeResponse(
            entity=EntityDto(
                id=entity.id,
                created_at=entity.created_at,
                metadata=entity.metadata or {},
            ),
            source=SourceDto(
                id=source.id,
                content=source.content,
                timestamp=source.timestamp,
            ),
            assimilated_facts=assimilated_facts,
        )
