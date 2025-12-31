"""Use case for retrieving entity information by identifier.

This module defines the use case for fetching entity details including
their identifiers and associated facts with sources.
"""

from __future__ import annotations

import logging
import time

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
    RagDebugDto,
    RagDebugHit,
    SourceDto,
)
from app.features.graph.models.fact_model import Fact
from app.features.graph.repositories.protocols import (
    FindEntityResult,
    GraphRepository,
    VectorRepository,
)

logger = logging.getLogger(__name__)


class GetEntityUseCaseImpl:
    """Implementation of the get entity use case."""

    def __init__(
        self,
        repository: GraphRepository,
        vector_repository: VectorRepository | None = None,
    ):
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for graph database operations
            vector_repository: Optional repository for vector search operations.
                               When provided, enables RAG-based fact filtering.
        """
        self.repository: GraphRepository = repository
        self.vector_repository: VectorRepository | None = vector_repository

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
            rag_query: Optional conversational query for semantic search.
                       When provided and vector_repository is available,
                       facts are filtered based on semantic similarity.
            rag_top_k: Number of vector candidates to retrieve (default: 10)
            rag_min_score: Optional similarity threshold for filtering
            rag_expand_hops: Optional graph expansion depth (currently unused)
            rag_debug: Whether to return debug metadata about the RAG process

        Returns:
            GetEntityResponse containing the entity, identifier, and facts.
            When rag_query is provided, only matching facts are returned.

        Raises:
            HTTPException: If the entity is not found (404)
        """
        timings: dict[str, float] = {}

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

        # Determine if we should use RAG filtering
        # Note: rag_expand_hops is reserved for future graph expansion feature
        _ = rag_expand_hops  # Suppress unused variable warning

        use_rag = bool(rag_query and self.vector_repository is not None)
        rag_debug_dto: RagDebugDto | None = None
        vector_hits: list[RagDebugHit] = []
        verified_fact_ids: set[str] = set()

        if use_rag:
            # At this point, we know rag_query and vector_repository are not None
            assert rag_query is not None
            assert self.vector_repository is not None

            # Perform vector search
            start_time = time.perf_counter()
            search_results = await self.vector_repository.search_semantic_memory(
                entity_id=entity_result["entity"].id,
                query_text=rag_query,
                top_k=rag_top_k,
                min_score=rag_min_score,
            )
            timings["vector_search_ms"] = (time.perf_counter() - start_time) * 1000

            # Build a lookup of graph fact_ids for verification
            start_time = time.perf_counter()
            graph_fact_ids: set[str] = {
                fws["fact"].fact_id
                for fws in entity_result["facts_with_sources"]
                if fws["fact"].fact_id is not None
            }

            # Verify vector hits against graph (prevent cross-entity leakage)
            for hit in search_results:
                is_verified = hit.fact_id in graph_fact_ids
                if is_verified:
                    verified_fact_ids.add(hit.fact_id)
                vector_hits.append(
                    RagDebugHit(
                        fact_id=hit.fact_id,
                        verb=hit.verb,
                        score=hit.score,
                        verified=is_verified,
                    )
                )
            timings["graph_verify_ms"] = (time.perf_counter() - start_time) * 1000

            # Build debug metadata if requested
            if rag_debug:
                rag_debug_dto = RagDebugDto(
                    query=rag_query,
                    top_k=rag_top_k,
                    min_score=rag_min_score,
                    vector_hits=vector_hits,
                    verified_count=len(verified_fact_ids),
                    timings_ms=timings,
                )

        # Map facts with sources to DTOs, optionally filtering by RAG results
        facts_with_sources_dto: list[FactWithSourceDto] = []
        for fact_with_source in entity_result["facts_with_sources"]:
            fact: Fact = fact_with_source["fact"]

            # If RAG is active, only include verified facts
            if use_rag and fact.fact_id not in verified_fact_ids:
                continue

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
            rag_debug=rag_debug_dto,
        )
