"""Get fact usecase - handles fact retrieval business logic."""

from typing import Any

from app.features.graph.repository import GraphRepository


class GetFactUsecase:
    """Business logic for retrieving facts."""

    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(self, fact_id: str) -> dict[str, Any] | None:
        """Execute fact retrieval with business rules."""
        fact_data = await self.repo.find_fact_by_id(fact_id)

        if not fact_data:
            return None

        # Apply any business logic transformations here
        return fact_data
