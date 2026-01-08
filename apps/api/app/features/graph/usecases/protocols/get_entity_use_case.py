"""Protocol for the get entity use case."""

from typing import Protocol

from app.features.graph.dtos.knowledge_dto import GetEntityResponse


class GetEntityUseCase(Protocol):
    """Protocol for use cases that retrieve entity information.

    This protocol defines the contract for retrieving entity data by identifier.
    Implementations may use different data sources or include additional
    features like RAG-based filtering.
    """

    async def execute(
        self,
        identifier_value: str,
        identifier_type: str,
        rag_query: str | None = None,
        rag_top_k: int = 10,
        rag_min_score: float | None = None,
        rag_expand_hops: int = 0,
        rag_debug: bool = False,
    ) -> GetEntityResponse:
        """Retrieve entity information by identifier.

        Args:
            identifier_value: The identifier value (e.g., 'user@example.com')
            identifier_type: The identifier type (e.g., 'email', 'phone')
            rag_query: Optional conversational query for semantic search
            rag_top_k: Number of vector candidates to retrieve (default: 10)
            rag_min_score: Optional similarity threshold for filtering
            rag_expand_hops: Optional graph expansion depth
            rag_debug: Whether to return debug metadata about the RAG process

        Returns:
            GetEntityResponse containing the entity, identifier, and facts
        """
        ...
