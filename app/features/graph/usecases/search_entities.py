"""Search entities usecase - handles entity search business logic."""

from typing import Any

from app.features.graph.repository import GraphRepository


class SearchEntitiesUsecase:
    """Business logic for searching entities."""

    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(
        self,
        identifier_value: str | None = None,
        identifier_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Execute entity search with business rules and validation."""
        # Apply business rules for search parameters
        if limit > 1000:  # Example business rule
            limit = 1000
        if limit < 1:
            limit = 1

        entities = await self.repo.find_entities(
            identifier_value, identifier_type, limit
        )

        # Apply any post-processing business logic here
        return entities
