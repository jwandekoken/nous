"""Protocol definition for vector repository operations."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.features.graph.models import Fact


@dataclass
class SemanticSearchResult:
    """Result from a semantic memory search."""

    fact_id: str
    verb: str
    relationship_key: str
    score: float


class VectorRepository(Protocol):
    """Protocol for vector repository operations.

    This protocol defines the interface for vector database operations
    with tenant isolation. Implementations include QdrantRepository.
    """

    async def add_semantic_memory(
        self,
        entity_id: UUID,
        fact: Fact,
        verb: str,
    ) -> bool:
        """Add a semantic memory vector for a fact.

        Args:
            entity_id: The entity UUID this fact belongs to.
            fact: The Fact model instance.
            verb: The relationship verb (e.g., "lives_in", "works_at").

        Returns:
            True if the operation succeeded.
        """
        ...

    async def search_semantic_memory(
        self,
        entity_id: UUID,
        query_text: str,
        top_k: int = 10,
        min_score: float | None = None,
    ) -> list[SemanticSearchResult]:
        """Search semantic memories for an entity.

        Args:
            entity_id: The entity UUID to search within.
            query_text: The query text to embed and search for.
            top_k: Maximum number of results to return (default: 10).
            min_score: Optional minimum similarity score threshold.

        Returns:
            List of SemanticSearchResult ordered by score (descending).
        """
        ...

    async def delete_semantic_memory(
        self,
        entity_id: UUID,
        fact_id: str,
        verb: str,
    ) -> bool:
        """Delete a semantic memory vector for a fact.

        Args:
            entity_id: The entity UUID.
            fact_id: The fact's synthetic ID.
            verb: The relationship verb.

        Returns:
            True if the operation succeeded.
        """
        ...

    async def delete_all_semantic_memories_for_entity(self, entity_id: UUID) -> int:
        """Delete all semantic memory vectors for an entity.

        Args:
            entity_id: The entity UUID.

        Returns:
            The number of points deleted.
        """
        ...
