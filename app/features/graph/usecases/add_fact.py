"""Add fact usecase - handles adding facts to entities business logic."""

from datetime import datetime
from uuid import UUID

from app.features.graph.graph_models import (
    Fact,
    HasFact,
    Source,
    create_fact_with_source,
)
from app.features.graph.repository import GraphRepository


class AddFactUsecase:
    """Business logic for adding facts to entities."""

    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(
        self,
        entity_id: UUID,
        fact_name: str,
        fact_type: str,
        verb: str,
        source_content: str,
        confidence_score: float = 1.0,
        source_timestamp: datetime | None = None,
    ) -> tuple[Fact, Source, HasFact]:
        """Execute fact addition with validation and business rules."""
        fact, source, _ = create_fact_with_source(
            name=fact_name,
            fact_type=fact_type,
            source_content=source_content,
            source_timestamp=source_timestamp,
        )

        has_fact = HasFact(
            from_entity_id=entity_id,
            to_fact_id=fact.fact_id,
            verb=verb,
            confidence_score=confidence_score,
        )

        success = await self.repo.add_fact_to_entity(entity_id, fact, source, has_fact)
        if not success:
            raise ValueError("Failed to add fact to entity.")

        return fact, source, has_fact
