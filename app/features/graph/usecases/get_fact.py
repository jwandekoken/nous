"""Get fact usecase - handles fact retrieval business logic."""

from typing import Any

from app.features.graph.repositories import FactRepository


class GetFactUsecase:
    """Business logic for retrieving facts."""

    def __init__(self, repo: FactRepository):
        self.repo: FactRepository = repo

    async def execute(self, fact_id: str) -> dict[str, Any] | None:
        """Execute fact retrieval with business rules."""
        fact_data = await self.repo.find_fact_by_id(fact_id)

        if not fact_data:
            return None

        # Apply any business logic transformations here
        return fact_data
