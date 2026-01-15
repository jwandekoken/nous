"""Qdrant implementation of the VectorRepository protocol.

This module provides the QdrantRepository class for managing semantic memory
vectors in Qdrant with strict tenant isolation.
"""

import uuid
from typing import override
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
)

from app.features.graph.models import Fact
from app.features.graph.repositories.protocols import (
    SemanticSearchResult,
    VectorRepository,
)
from app.features.graph.services.embedding_service import EmbeddingService

# Namespace for generating deterministic UUIDs (UUIDv5)
# Using a custom namespace based on our domain
VECTOR_NAMESPACE = uuid.NAMESPACE_DNS


class QdrantRepository(VectorRepository):
    """Repository for Qdrant vector operations with tenant isolation.

    All operations are scoped to a specific tenant_id which is enforced
    at the repository level. Every query automatically filters by tenant_id.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        tenant_id: str,
        collection_name: str = "agent_memory",
    ):
        """Initialize the vector repository.

        Args:
            client: The AsyncQdrantClient instance.
            embedding_service: Service for generating text embeddings.
            tenant_id: The tenant ID for isolation (applied to all operations).
            collection_name: The Qdrant collection name (default: agent_memory).
        """
        self.client: AsyncQdrantClient = client
        self.embedding_service: EmbeddingService = embedding_service
        self.tenant_id: str = tenant_id
        self.collection_name: str = collection_name

    def _generate_point_id(self, entity_id: UUID, verb: str, fact_id: str) -> str:
        """Generate a deterministic point ID for idempotent upserts.

        Uses UUIDv5 to create a reproducible ID from the relationship key.
        This ensures that upserting the same fact twice results in an update,
        not a duplicate.

        Args:
            entity_id: The entity UUID.
            verb: The relationship verb.
            fact_id: The fact's synthetic ID.

        Returns:
            A deterministic UUID string for the Qdrant point.
        """
        relationship_key = self._create_relationship_key(entity_id, verb, fact_id)
        # Include tenant_id in the UUID generation for multi-tenant safety
        composite_key = f"{self.tenant_id}:{relationship_key}"
        point_uuid = uuid.uuid5(VECTOR_NAMESPACE, composite_key)
        return str(point_uuid)

    def _create_relationship_key(self, entity_id: UUID, verb: str, fact_id: str) -> str:
        """Create the relationship key for a semantic memory entry.

        Args:
            entity_id: The entity UUID.
            verb: The relationship verb.
            fact_id: The fact's synthetic ID.

        Returns:
            A string key in the format "{entity_id}:{verb}:{fact_id}".
        """
        return f"{entity_id}:{verb}:{fact_id}"

    def _create_synthetic_sentence(self, fact: Fact, verb: str) -> str:
        """Create a synthetic sentence for embedding.

        This creates a rich semantic representation of the fact that
        captures the relationship context.

        Args:
            fact: The Fact model instance.
            verb: The relationship verb.

        Returns:
            A synthetic sentence like "The entity enjoys Hobby: Hiking".
        """
        return f"The entity {verb} {fact.type}: {fact.name}"

    @override
    async def add_semantic_memory(
        self,
        entity_id: UUID,
        fact: Fact,
        verb: str,
    ) -> bool:
        """Add a semantic memory vector for a fact.

        Creates an embedding of a synthetic sentence representing the fact
        and stores it in Qdrant with full metadata for retrieval.

        Args:
            entity_id: The entity UUID this fact belongs to.
            fact: The Fact model instance.
            verb: The relationship verb (e.g., "lives_in", "works_at").

        Returns:
            True if the operation succeeded.
        """
        if fact.fact_id is None:
            raise ValueError("Fact must have a fact_id")

        # Generate embedding for the synthetic sentence
        synthetic_sentence = self._create_synthetic_sentence(fact, verb)
        embedding = await self.embedding_service.embed_text(
            synthetic_sentence,
            feature="graph",
            operation="semantic_memory_embed",
        )

        # Generate deterministic point ID for idempotent upserts
        point_id = self._generate_point_id(entity_id, verb, fact.fact_id)
        relationship_key = self._create_relationship_key(entity_id, verb, fact.fact_id)

        # Create the point with full payload
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "tenant_id": self.tenant_id,
                "entity_id": str(entity_id),
                "fact_id": fact.fact_id,
                "verb": verb,
                "relationship_key": relationship_key,
                "type": "semantic",
                # Store additional metadata for debugging/display
                "fact_name": fact.name,
                "fact_type": fact.type,
                "synthetic_sentence": synthetic_sentence,
            },
        )

        # Upsert the point (idempotent due to deterministic ID)
        _ = await self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return True

    @override
    async def search_semantic_memory(
        self,
        entity_id: UUID,
        query_text: str,
        top_k: int = 10,
        min_score: float | None = None,
    ) -> list[SemanticSearchResult]:
        """Search semantic memories for an entity.

        Performs a vector similarity search scoped to the tenant and entity.
        Returns matching facts ordered by relevance.

        Args:
            entity_id: The entity UUID to search within.
            query_text: The query text to embed and search for.
            top_k: Maximum number of results to return (default: 10).
            min_score: Optional minimum similarity score threshold.

        Returns:
            List of SemanticSearchResult ordered by score (descending).
        """
        # Embed the query text
        query_embedding = await self.embedding_service.embed_text(
            query_text,
            feature="graph",
            operation="rag_query_embed",
        )

        # Build filter with tenant and entity isolation
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=self.tenant_id),
                ),
                FieldCondition(
                    key="entity_id",
                    match=MatchValue(value=str(entity_id)),
                ),
                FieldCondition(
                    key="type",
                    match=MatchValue(value="semantic"),
                ),
            ]
        )

        # Perform the search using query_points (the async API method)
        response = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=search_filter,
            limit=top_k,
            score_threshold=min_score,
            with_payload=True,
        )

        # Convert to SemanticSearchResult with null-safety checks
        results: list[SemanticSearchResult] = []
        for hit in response.points:
            # Skip results with missing payload (shouldn't happen with with_payload=True)
            if hit.payload is None:
                continue

            # Safely extract payload fields
            fact_id = hit.payload.get("fact_id")
            verb = hit.payload.get("verb")
            relationship_key = hit.payload.get("relationship_key")

            # Skip results with incomplete payload data
            if fact_id is None or verb is None or relationship_key is None:
                continue

            results.append(
                SemanticSearchResult(
                    fact_id=str(fact_id),
                    verb=str(verb),
                    relationship_key=str(relationship_key),
                    score=hit.score,
                )
            )

        return results

    @override
    async def delete_semantic_memory(
        self,
        entity_id: UUID,
        fact_id: str,
        verb: str,
    ) -> bool:
        """Delete a semantic memory vector for a fact.

        Uses the deterministic point ID to locate and delete the vector.

        Args:
            entity_id: The entity UUID.
            fact_id: The fact's synthetic ID.
            verb: The relationship verb.

        Returns:
            True if the operation succeeded.
        """
        point_id = self._generate_point_id(entity_id, verb, fact_id)

        _ = await self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=[point_id]),
        )

        return True

    @override
    async def delete_all_semantic_memories_for_entity(self, entity_id: UUID) -> int:
        """Delete all semantic memory vectors for an entity.

        Removes all semantic memory vectors associated with an entity.
        Useful when an entity is deleted from the graph.

        Args:
            entity_id: The entity UUID.

        Returns:
            The number of points deleted.
        """
        # Build filter to match all vectors for this entity within the tenant
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=self.tenant_id),
                ),
                FieldCondition(
                    key="entity_id",
                    match=MatchValue(value=str(entity_id)),
                ),
            ]
        )

        # First, count how many points match
        # Note: Qdrant's delete returns UpdateResult which doesn't include count
        # We'll count before deletion
        count_result = await self.client.count(
            collection_name=self.collection_name,
            count_filter=delete_filter,
        )
        count = count_result.count

        # Delete the points
        _ = await self.client.delete(
            collection_name=self.collection_name,
            points_selector=delete_filter,
        )

        return count
