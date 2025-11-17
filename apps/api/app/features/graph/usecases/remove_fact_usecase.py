"""Use case for removing a fact from an entity."""

from uuid import UUID

from fastapi import HTTPException, status

from app.features.graph.dtos.knowledge_dto import RemoveFactFromEntityResponse
from app.features.graph.repositories.base import GraphRepository


class RemoveFactFromEntityUseCaseImpl:
    """Implementation of the remove fact from entity use case."""

    def __init__(self, repository: GraphRepository):
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for graph database operations
        """
        self.repository = repository

    async def execute(
        self, entity_id: UUID, fact_id: str
    ) -> RemoveFactFromEntityResponse:
        """Remove a fact from an entity.

        Args:
            entity_id: The entity's unique identifier
            fact_id: The fact's synthetic ID to remove

        Returns:
            RemoveFactFromEntityResponse with operation result

        Raises:
            HTTPException: If entity or fact relationship not found (404)
        """
        # Call repository method
        success = await self.repository.remove_fact_from_entity(str(entity_id), fact_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fact '{fact_id}' not found for entity '{entity_id}'",
            )

        return RemoveFactFromEntityResponse(
            success=True,
            message=f"Fact '{fact_id}' successfully removed from entity '{entity_id}'",
            entity_id=entity_id,
            fact_id=fact_id,
        )
