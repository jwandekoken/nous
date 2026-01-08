Here is the finalized implementation plan for adding **Vectorized Semantic Memory** to your project. This strategy ensures strict linking between your Vector Store (Qdrant) and your Graph Store (Apache AGE) using the UUIDs and identifiers you have already defined.

---

# 0. Repo Discoveries, Criticisms, and Suggestions (Addendum)

This section captures implementation-relevant discoveries from the current codebase, plus suggested corrections to this plan to ensure it matches what's already implemented (AGE schema/repository patterns, DTO shapes, multi-tenancy, and expected runtime behavior).

## A) Qdrant Collection Design (dimensions, versioning, and idempotency)

- **Collection creation must know vector dimension up-front**

  - Qdrant requires `vector_size` at collection creation time.
  - **Decision:** Standardize on `gemini-embedding-001` with **768** dimensions (`embedding_dim = 768`).
  - **Important:** The model's default output is 3072 dimensions. To get 768, you must pass `output_dimensionality=768` to the `embed_query()`/`embed_documents()` methods (not the constructor). The model uses Matryoshka Representation Learning (MRL), so smaller dimensions are still high quality.
  - **Plan action:** Add settings for `embedding_model` and `embedding_dim` (single source of truth) and a migration rule when models/dims change:
    - Fail fast and require a manual migration, or
    - Create versioned collections (e.g., `agent_memory_v2`) and route reads/writes accordingly.

- **Unified Collection with Type Discriminator**

  - **Decision:** Use a **single collection** (`agent_memory`) for both semantic and episodic memory types.
  - **Rationale:**
    - Simpler infrastructure management (one collection to create, monitor, backup)
    - Qdrant is optimized for payload filtering — filtering by `type` adds negligible overhead when indexed
    - Enables unified search across memory types if needed in the future
    - Both memory types share the same embedding model/dimensions
  - **Discriminator:** A mandatory `type` field in the payload (`"semantic"` or `"episodic"`).
  - **Alternative (when to use separate collections):** Only if memory types require different vector dimensions, different distance metrics, or vastly different retention policies.

- **Make vector writes idempotent**
  - **Plan action:** Use deterministic Qdrant point IDs:
    - Semantic: `relationship_key = "{entity_id}:{verb}:{fact_id}"`, then `point_id = hash(tenant_id, relationship_key)` (or UUIDv5).
    - Episodic (future): `window_key = "{entity_id}:{source_id}:{window_index}"`, then `point_id = hash(tenant_id, window_key)`.

## A.1) Payload Indexes (Critical for Performance)

Qdrant requires explicit payload index creation for efficient filtering. Without indexes, filters perform full scans. The following indexes **must** be created during collection initialization:

| Field       | Index Type | Rationale                                                                                                                     |
| ----------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `tenant_id` | `keyword`  | **Mandatory.** Every query filters by tenant for isolation. High cardinality but always in filter.                            |
| `entity_id` | `keyword`  | **Mandatory.** Semantic searches are scoped to a specific entity. Used in every semantic query.                               |
| `type`      | `keyword`  | **Mandatory.** Discriminator for memory type (`semantic` / `episodic`). Low cardinality, highly selective.                    |
| `fact_id`   | `keyword`  | **Recommended.** Enables efficient deletion/update by fact ID. Used for idempotent operations and cleanup.                    |
| `verb`      | `keyword`  | **Optional.** Enables filtering by relationship type (e.g., "find all hobbies" = `verb=enjoys`). Useful for advanced queries. |

**Index creation example (in `init_db.py`):**

```python
from qdrant_client.models import PayloadSchemaType

# Create indexes for efficient filtering
await client.create_payload_index(
    collection_name="agent_memory",
    field_name="tenant_id",
    field_schema=PayloadSchemaType.KEYWORD,
)
await client.create_payload_index(
    collection_name="agent_memory",
    field_name="entity_id",
    field_schema=PayloadSchemaType.KEYWORD,
)
await client.create_payload_index(
    collection_name="agent_memory",
    field_name="type",
    field_schema=PayloadSchemaType.KEYWORD,
)
await client.create_payload_index(
    collection_name="agent_memory",
    field_name="fact_id",
    field_schema=PayloadSchemaType.KEYWORD,
)
await client.create_payload_index(
    collection_name="agent_memory",
    field_name="verb",
    field_schema=PayloadSchemaType.KEYWORD,
)
```

**Note:** Index creation is idempotent — calling `create_payload_index` on an existing index is a no-op.

## B) Multi-Tenancy Enforcement (match existing FastAPI + AGE approach)

- **Tenant resolution already exists (`TenantInfo`)**
  - Graph isolation is achieved by passing `tenant_info.graph_name` into `AgeRepository`.
  - **Plan action:** Mirror this in vectors:
    - Construct the vector repo with `tenant_id`.
    - Enforce `tenant_id` filtering in _every_ Qdrant search (not optional).

## C) Embedding Provider / Defaults (make the plan match actual stack)

- **Embedding model choice should match dependencies**
  - Current dependencies include `langchain-google-genai`; the plan's default `text-embedding-3-small` implies OpenAI.
  - **Decision:** Use Google embeddings via `langchain-google-genai` with `gemini-embedding-001` (**768 dims**, via `output_dimensionality` parameter).
  - **Plan action:** Treat `embedding_dim=768` as the Qdrant collection `vector_size` and fail fast if config and collection schema disagree.
  - **Implementation note:** The `EmbeddingService.embed_text()` method must pass `output_dimensionality=embedding_dim` to the underlying Google API. This is done via `aembed_query(text, output_dimensionality=...)`, NOT in the constructor.

## D) Retrieval Workflows (Anchor & Expand)

- This plan currently covers ingestion; it should also specify retrieval:
  1. Embed query → Qdrant search (filtered by `tenant_id` **and `entity_id`**)
  2. Convert hits → AGE anchor IDs: `fact_id` + `verb` (or `relationship_key`)
  3. Graph verification + traversal ("expand"):
     - Semantic results MUST be resolved in AGE by following only the relationship for the same entity:
       - Match `(Entity {id = entity_id}) -[verb]-> (Fact {fact_id = fact_id})`
       - Do not return the same `fact_id` from a different entity
     - Return a compact graph-context bundle for LLM consumption
  - **Plan action:** Add a new step for retrieval endpoints/usecases (e.g., "search memories" and "expand from anchors").

### D.1) API Retrieval Contract (Option A: opt-in params, no breaking changes)

We will **keep the existing lookup endpoints and response models**, and add **optional query params** that enable vector-gated Graph-RAG behavior.

- **Existing endpoints (unchanged by default)**:

  - `GET /api/v1/graph/entities/lookup?type=...&value=...` → `GetEntityResponse`
  - `GET /api/v1/graph/entities/lookup/summary?type=...&value=...` → `GetEntitySummaryResponse`

- **Default behavior (no RAG params)**:

  - `/lookup`: returns _all facts_ for the entity (current behavior).
  - `/lookup/summary`: summarizes _all facts_ for the entity (current behavior).

- **RAG behavior (opt-in)**:
  - If `rag_query` is present, the server will perform:
    1. Resolve entity via existing identifier lookup (`type` + `value`)
    2. Vector search (Qdrant) constrained by `tenant_id` and `entity_id`
    3. Convert vector hits → graph anchors
    4. Verify anchors in AGE (prevent cross-entity leakage)
    5. Fetch and return a **subset of facts** (fact-only response)

#### D.1.1) Query params

- **`rag_query: str | None`**

  - Conversational user turn (free text).
  - If omitted/empty → identical behavior to today.

- **`rag_top_k: int`** (default: 10)

  - Number of vector candidates to retrieve before graph verification.

- **`rag_min_score: float | None`**

  - Optional similarity threshold for filtering vector hits before graph verification.

- **`rag_expand_hops: int`** (default: 0)
  - Optional graph expansion depth starting from verified anchors.
  - `0` returns only matched facts; `1` may include adjacent facts depending on expansion rules.

#### D.1.2) Fact-only response semantics

- **Semantic mode**:
  - Qdrant hits return `relationship_key` / (`fact_id`, `verb`)
  - AGE verification ensures the relationship exists for the resolved entity
  - Response `facts[]` is filtered to verified hits (plus any optional expansion)

#### D.1.3) Optional RAG debug metadata (opt-in, does not change default behavior)

We may add an **optional** field to the response DTO(s) to surface retrieval provenance when requested.

- **DTO field**: `rag_debug: RagDebugDto | None = None`
- **Enabled by**: a query param like `rag_debug=true` (default false)
- **Contains** (suggested minimal shape):
  - `top_k`, `min_score`
  - `vector_hits`: list of `{collection, score, anchor_type, anchor_id, relationship_key?}`
  - `verified_anchors`: list of anchors that passed AGE verification
  - `timings_ms` (optional): `{vector_search, graph_verify, graph_fetch}`

## E) Docker / Runtime Gotchas

- When running under Docker Compose, Qdrant host will typically be `qdrant` (service name), not `localhost`.
- **Plan action:** Document environment-specific defaults (`localhost` for local dev outside compose; `qdrant` inside compose).

---

# 1. High-Level Architecture: The "Anchor & Link" Strategy

The core principle is **"Vectors are Entry Points; Graphs are the Truth."**

- **Qdrant** is used to find the _ID_ of a node based on fuzzy meaning.
- **Apache AGE** is used to retrieve the actual trusted data using that ID.

---

# 2. Vectorized Semantic Memory (The Facts)

This memory allows the agent to find specific facts based on vague queries (e.g., query "outdoor activities" -> finds fact "Hiking").

- **The Data:** Extracted atomic facts (Subject, Verb, Object).
- **The Vector:** Embedding of a **synthetic sentence** representation of the fact. Embedding just the word "Paris" is weak; embedding "The entity lives in Paris" is strong.
- **The Linkage:**
  - **Graph Anchor:** The `Fact` node in AGE.
  - **Link:** The Qdrant payload stores the `fact_id` (synthetic ID like `Location:Paris`) from AGE, plus `verb` and a deterministic `relationship_key = "{entity_id}:{verb}:{fact_id}"`.
  - **Note:** `relationship_key` is derivable from (`entity_id`, `verb`, `fact_id`). We store it anyway because it makes idempotent upserts/deletes straightforward (it can double as the deterministic point identifier input) and helps with debugging/traceability.
- **Implementation Logic:**
  1.  **Input:** LLM extracts fact: `name="Hiking"`, `type="Hobby"`, `verb="enjoys"`.
  2.  **Graph Action:** Merge `Fact` node. Get `fact.fact_id` (`Hobby:Hiking`).
  3.  **Vector Action:**
      - Text to Embed: `"The entity enjoys Hobby: Hiking"` (Constructed from fact parts).
      - Payload:
        ```json
        {
          "tenant_id": "...", // For isolation
          "entity_id": "...", // UUID of the Entity
          "fact_id": "Hobby:Hiking", // ID of the Fact Node
          "verb": "enjoys",
          "relationship_key": "{entity_id}:enjoys:Hobby:Hiking",
          "type": "semantic"
        }
        ```

---

# 3. Implementation Plan

Here is the step-by-step code integration plan.

## Step 1: Configuration (`apps/api/app/core/settings.py`)

Add the Qdrant connection details.

```python
# ... existing settings ...
    # Qdrant
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")
    embedding_model: str = Field(default="gemini-embedding-001", description="Embedding model name")
    embedding_dim: int = Field(default=768, description="Embedding vector dimension (Qdrant vector_size)")
```

## Step 2: Database Layer (`apps/api/app/db/qdrant/`)

Create the connection and initialization logic.

- `connection.py`: Returns a singleton `AsyncQdrantClient`.
- `init_db.py`:
  - Checks if `agent_memory` collection exists.
  - If not, creates it with `Cosine` distance and `embedding_dim` vector size.
  - **Critical:** Creates payload indexes as defined in **Section A.1** (`tenant_id`, `entity_id`, `type`, `fact_id`, `verb`) for efficient filtering.

## Step 3: Repository Layer (`apps/api/app/features/graph/repositories/`)

Create `vector_repository.py` to abstract the Qdrant client. This ensures `tenant_id` is _always_ injected.

```python
class VectorRepository:
    def __init__(self, client, tenant_id: str, collection_name: str = "agent_memory"):
        self.client = client
        self.tenant_id = tenant_id
        self.collection_name = collection_name

    async def add_semantic_memory(self, entity_id: UUID, fact: Fact, verb: str):
        # relationship_key must uniquely represent the assertion in the graph:
        # f"{entity_id}:{verb}:{fact.fact_id}"
        # Construct text: f"The entity {verb} {fact.type}: {fact.name}"
        # Embed text
        # Upsert to collection with type="semantic" in payload
        # Payload includes: tenant_id, entity_id, fact_id, verb, relationship_key, type
```

## Step 4: Use Case Integration (`assimilate_knowledge_usecase.py`)

Update the `execute` method to call the vector repository after each fact is added to the graph.

```python
# ... inside execute method ...

# 1. (Existing) Create/Find Entity
# 2. (Existing) Create Source object
source = Source(...)

# 3. (Existing) Extract Facts
extracted_facts = await self.fact_extractor.extract_facts(...)

for fact_data in extracted_facts:
    # 4. (Existing) Add to Graph
    result = await self.repository.add_fact_to_entity(...)

    # 5. [NEW] Add to Semantic Memory
    # We use the fact data returned from the repository to ensure IDs match
    await self.vector_repo.add_semantic_memory(
        entity_id=entity.id,
        fact=result["fact"],
        verb=result["has_fact_relationship"].verb
    )
```

## Step 5: Test-Driven Development (TDD)

Follow TDD principles: write tests first, then implement to make them pass. Tests live in `apps/api/tests/features/graph/`.

### 5.1 Test Infrastructure: Qdrant Fixtures (`tests/conftest.py`)

Add Qdrant fixtures alongside existing PostgreSQL fixtures:

```python
import pytest_asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

@pytest_asyncio.fixture(scope="function")
async def qdrant_client(test_settings: Settings) -> AsyncGenerator[AsyncQdrantClient, None]:
    """Provide Qdrant client for vector operations tests.

    Creates a fresh client for each test and cleans up the agent_memory collection after.
    """
    client = AsyncQdrantClient(
        host=test_settings.qdrant_host,
        port=test_settings.qdrant_port,
    )

    # Ensure collection exists for tests
    collection_name = "agent_memory_test"
    try:
        await client.delete_collection(collection_name)
    except Exception:
        pass  # Collection might not exist

    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=test_settings.embedding_dim,
            distance=Distance.COSINE,
        ),
    )

    # Create payload indexes (matching production setup from Section A.1)
    for field in ["tenant_id", "entity_id", "type", "fact_id", "verb"]:
        await client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    yield client

    # Cleanup after test
    try:
        await client.delete_collection(collection_name)
    except Exception:
        pass
    await client.close()
```

### 5.2 Repository Tests (`tests/features/graph/repositories/test_vector_repository.py`)

Test the `VectorRepository` in isolation.

```python
"""Integration tests for VectorRepository using a real Qdrant connection."""

import uuid
import pytest
from qdrant_client import AsyncQdrantClient

from app.features.graph.models import Fact
from app.features.graph.repositories.vector_repository import VectorRepository


@pytest.fixture
async def vector_repository(
    qdrant_client: AsyncQdrantClient,
) -> VectorRepository:
    """Fixture to get a VectorRepository instance."""
    return VectorRepository(
        client=qdrant_client,
        tenant_id="test_tenant",
        collection_name="agent_memory_test",
    )


@pytest.fixture
def test_fact() -> Fact:
    """Test fact for vector operations."""
    return Fact(name="Paris", type="Location")


class TestVectorRepositoryAddSemantic:
    """Integration tests for VectorRepository.add_semantic_memory method."""

    @pytest.mark.asyncio
    async def test_add_semantic_memory_basic(
        self,
        vector_repository: VectorRepository,
        test_fact: Fact,
    ) -> None:
        """Test basic semantic vector addition."""
        entity_id = uuid.uuid4()

        # Act
        result = await vector_repository.add_semantic_memory(
            entity_id=entity_id,
            fact=test_fact,
            verb="lives_in",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_add_semantic_memory_is_idempotent(
        self,
        vector_repository: VectorRepository,
        test_fact: Fact,
    ) -> None:
        """Test that adding the same semantic vector is idempotent."""
        entity_id = uuid.uuid4()

        # Add twice
        await vector_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await vector_repository.add_semantic_memory(entity_id, test_fact, "lives_in")

        # Assert: Should have only one point (due to deterministic ID)
        # Verify by searching
        results = await vector_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Where does the entity live?",
            top_k=10,
        )
        assert len(results) == 1


class TestVectorRepositorySearchSemantic:
    """Integration tests for VectorRepository.search_semantic_memory method."""

    @pytest.mark.asyncio
    async def test_search_semantic_memory_finds_relevant_fact(
        self,
        vector_repository: VectorRepository,
    ) -> None:
        """Test that semantic search finds relevant facts."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await vector_repository.add_semantic_memory(
            entity_id, Fact(name="Paris", type="Location"), "lives_in"
        )
        await vector_repository.add_semantic_memory(
            entity_id, Fact(name="Software Engineering", type="Profession"), "works_as"
        )
        await vector_repository.add_semantic_memory(
            entity_id, Fact(name="Hiking", type="Hobby"), "enjoys"
        )

        # Search for location-related query
        results = await vector_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="Where does this person live?",
            top_k=3,
        )

        # The top result should be the location fact
        assert len(results) > 0
        assert results[0]["fact_id"] == "Location:Paris"

    @pytest.mark.asyncio
    async def test_search_semantic_memory_respects_tenant_isolation(
        self,
        qdrant_client: AsyncQdrantClient,
    ) -> None:
        """Test that search only returns results for the current tenant."""
        entity_id = uuid.uuid4()

        # Create repos for two different tenants
        repo_tenant_a = VectorRepository(
            client=qdrant_client,
            tenant_id="tenant_a",
            collection_name="agent_memory_test",
        )
        repo_tenant_b = VectorRepository(
            client=qdrant_client,
            tenant_id="tenant_b",
            collection_name="agent_memory_test",
        )

        # Add fact from tenant A
        await repo_tenant_a.add_semantic_memory(
            entity_id, Fact(name="Paris", type="Location"), "lives_in"
        )

        # Search from tenant B - should NOT find tenant A's data
        results = await repo_tenant_b.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )

        assert len(results) == 0


class TestVectorRepositoryDeleteSemantic:
    """Integration tests for VectorRepository.delete_semantic_memory method."""

    @pytest.mark.asyncio
    async def test_delete_semantic_memory_removes_vector(
        self,
        vector_repository: VectorRepository,
        test_fact: Fact,
    ) -> None:
        """Test that deleting a semantic vector removes it from the collection."""
        entity_id = uuid.uuid4()

        # Add then delete
        await vector_repository.add_semantic_memory(entity_id, test_fact, "lives_in")
        await vector_repository.delete_semantic_memory(
            entity_id=entity_id,
            fact_id=test_fact.fact_id,
            verb="lives_in",
        )

        # Search should return nothing
        results = await vector_repository.search_semantic_memory(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )
        assert len(results) == 0
```

### 5.3 UseCase Integration Tests (`tests/features/graph/usecases/test_assimilate_knowledge_with_vectors.py`)

Test the full flow including vectorization.

```python
"""Integration tests for AssimilateKnowledgeUseCaseImpl with vector memory."""

import uuid
import pytest
from qdrant_client import AsyncQdrantClient
import asyncpg

from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    IdentifierDto,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.repositories.vector_repository import VectorRepository
from app.features.graph.services.langchain_fact_extractor import LangChainFactExtractor
from app.features.graph.usecases.assimilate_knowledge_usecase import (
    AssimilateKnowledgeUseCaseImpl,
)


@pytest.fixture
async def assimilate_usecase_with_vectors(
    postgres_pool: asyncpg.Pool,
    qdrant_client: AsyncQdrantClient,
) -> AssimilateKnowledgeUseCaseImpl:
    """UseCase with both graph and vector repositories."""
    age_repo = AgeRepository(postgres_pool, graph_name="test_graph")
    vector_repo = VectorRepository(
        client=qdrant_client,
        tenant_id="test_tenant",
        collection_name="agent_memory_test",
    )
    fact_extractor = LangChainFactExtractor()

    return AssimilateKnowledgeUseCaseImpl(
        repository=age_repo,
        fact_extractor=fact_extractor,
        vector_repository=vector_repo,  # New dependency
    )


class TestAssimilateKnowledgeWithVectors:
    """Integration tests for assimilation with semantic vectorization."""

    @pytest.mark.asyncio
    async def test_assimilate_creates_semantic_vectors(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
        qdrant_client: AsyncQdrantClient,
    ) -> None:
        """Test that assimilating knowledge also creates semantic vectors."""
        identifier = IdentifierDto(
            value=f"test.{uuid.uuid4()}@example.com",
            type="email",
        )

        request = AssimilateKnowledgeRequest(
            identifier=identifier,
            content="I live in Paris and work as a Software Engineer.",
        )

        # Act
        result = await assimilate_usecase_with_vectors.execute(request)

        # Assert: Facts were created
        assert len(result.assimilated_facts) > 0

        # Assert: Vectors were created (one per fact)
        # We can verify by searching
        vector_repo = assimilate_usecase_with_vectors.vector_repository
        search_results = await vector_repo.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="Where does this person live?",
            top_k=10,
        )

        # Should find at least the location fact
        assert len(search_results) > 0

    @pytest.mark.asyncio
    async def test_semantic_search_returns_graph_verified_facts(
        self,
        assimilate_usecase_with_vectors: AssimilateKnowledgeUseCaseImpl,
    ) -> None:
        """Test that semantic search results can be verified against the graph."""
        identifier = IdentifierDto(
            value=f"test.{uuid.uuid4()}@example.com",
            type="email",
        )

        request = AssimilateKnowledgeRequest(
            identifier=identifier,
            content="I enjoy hiking and photography.",
        )

        result = await assimilate_usecase_with_vectors.execute(request)

        # Search for hobbies
        vector_repo = assimilate_usecase_with_vectors.vector_repository
        search_results = await vector_repo.search_semantic_memory(
            entity_id=result.entity.id,
            query_text="What are their hobbies?",
            top_k=5,
        )

        # Verify each result exists in the graph
        graph_repo = assimilate_usecase_with_vectors.repository
        for hit in search_results:
            fact_in_graph = await graph_repo.find_fact_by_id(hit["fact_id"])
            assert fact_in_graph is not None, f"Fact {hit['fact_id']} not found in graph"
```

### 5.4 Service Tests (`tests/features/graph/services/test_embedding_service.py`)

If you create a separate embedding service, test it in isolation.

```python
"""Unit tests for the embedding service."""

import pytest
from app.features.graph.services.embedding_service import EmbeddingService


@pytest.fixture
def embedding_service() -> EmbeddingService:
    """EmbeddingService instance for testing."""
    return EmbeddingService()


class TestEmbeddingService:
    """Tests for the embedding service."""

    @pytest.mark.asyncio
    async def test_embed_text_returns_correct_dimension(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that embeddings have the expected dimension (768 for gemini-embedding-001)."""
        text = "The entity lives in Paris"
        embedding = await embedding_service.embed_text(text)

        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_embed_text_is_deterministic(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that the same text produces the same embedding."""
        text = "The entity enjoys hiking"

        embedding1 = await embedding_service.embed_text(text)
        embedding2 = await embedding_service.embed_text(text)

        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_similar_texts_have_high_similarity(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        """Test that semantically similar texts have high cosine similarity."""
        text1 = "The entity lives in Paris, France"
        text2 = "The entity resides in Paris"

        emb1 = await embedding_service.embed_text(text1)
        emb2 = await embedding_service.embed_text(text2)

        # Calculate cosine similarity
        import numpy as np
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        assert similarity > 0.8  # High similarity expected
```

### 5.5 Running Tests

```bash
# Run only vector-related tests
pytest apps/api/tests/features/graph/repositories/test_vector_repository.py -v

# Run all graph tests including new vector tests
pytest apps/api/tests/features/graph/ -v

# Run with coverage
pytest apps/api/tests/features/graph/ --cov=app.features.graph --cov-report=term-missing
```

---

# 4. Future Considerations: Vectorized Episodic Memory

> **Status:** Deferred — captured here for future exploration.

This section outlines a potential future enhancement to add **Vectorized Episodic Memory**, which would allow the agent to recall _what happened_ and _how it was said_ during conversations.

## Concept

- **The Data:** Sliding window of conversation text (e.g., 3 turns).
- **The Vector:** Embedding of a conversational window (e.g., `"{n-2}n{n-1}n{n}"` representing User → Agent → User turns).
- **The Linkage:** Qdrant payload stores a reference to a graph anchor (e.g., `source_id` or a dedicated `window_id`).

## Challenges Identified

1. **API Complexity:** Requiring clients to format and send conversation history (e.g., `["User: Hi", "Agent: Hello"]`) places burden on API consumers and complicates the interface.

2. **Graph Anchor Mismatch:** The plan proposed storing a `Source` node with only the current turn's `content`, while vectorizing a 3-turn window. This creates a semantic disconnect between what the vector represents and what the graph stores.

3. **Overlapping Windows:** Consecutive turns would create overlapping windows, leading to redundant storage and retrieval complexity.

## Possible Future Directions

- **Server-side conversation tracking:** Instead of relying on client-provided history, the server could maintain conversation state per session/entity.

- **Dedicated EpisodicWindow storage:** Use a relational table (not graph) to store full window text, linked to the `Source` node via `source_id`.

- **Deferred vectorization:** Process episodic windows asynchronously or in batch, rather than at assimilation time.

When revisiting this feature, the key principle remains: **"Vectors are Entry Points; Graphs are the Truth."** Any episodic solution must ensure the vector's semantic content aligns with its graph anchor.

---

# 5. Implementation Tasks

This section breaks down the vectorized semantic memory implementation into discrete, manageable tasks. Each task is designed to be independently implementable while maintaining clear dependencies.

## Task Overview

| Task # | Name                                 | Depends On | Estimated Effort | Status  |
| ------ | ------------------------------------ | ---------- | ---------------- | ------- |
| 1      | Configuration & Settings             | -          | Small            | ✅ Done |
| 2      | Qdrant Database Layer                | Task 1     | Medium           | ✅ Done |
| 3      | Embedding Service                    | Task 1     | Small            | ✅ Done |
| 4      | Vector Repository                    | Task 2, 3  | Medium           | ✅ Done |
| 5      | Qdrant Test Infrastructure           | Task 2     | Small            | ✅ Done |
| 6      | Vector Repository Tests              | Task 4, 5  | Medium           | ✅ Done |
| 7      | Assimilate UseCase Integration       | Task 4     | Medium           | ✅ Done |
| 8      | Assimilate UseCase Integration Tests | Task 6, 7  | Medium           | ✅ Done |
| 9      | RAG Lookup Query Parameters          | Task 4     | Small            | ✅ Done |
| 10     | RAG Lookup UseCase                   | Task 9     | Medium           | ✅ Done |
| 11     | RAG Lookup Tests                     | Task 10    | Medium           | ✅ Done |
| 12     | Documentation & Cleanup              | All        | Small            | ⬜ TODO |

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Settings added in `apps/api/app/core/settings.py`

## Task 1: Configuration & Settings

**Goal:** Add Qdrant connection and embedding configuration to `settings.py`.

**Files to modify:**

- `apps/api/app/core/settings.py`

**Changes:**

```python
# Add to Settings class:

# Qdrant
qdrant_host: str = Field(default="localhost", description="Qdrant host")
qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")

# Embeddings
embedding_model: str = Field(default="gemini-embedding-001", description="Embedding model name")
embedding_dim: int = Field(default=768, description="Embedding vector dimension (Qdrant vector_size)")

# Collection
vector_collection_name: str = Field(default="agent_memory", description="Qdrant collection name for agent memory")
```

**Acceptance Criteria:**

- [x] Settings include `qdrant_host`, `qdrant_port`, `embedding_model`, `embedding_dim`, `vector_collection_name`
- [x] Settings load correctly from environment variables
- [x] Default values work for local development (localhost:6333)
- [x] Tests pass with existing functionality unchanged

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Files created in `apps/api/app/db/qdrant/`

## Task 2: Qdrant Database Layer

**Goal:** Create Qdrant connection management and collection initialization.

**Files to create:**

- `apps/api/app/db/qdrant/__init__.py`
- `apps/api/app/db/qdrant/connection.py`
- `apps/api/app/db/qdrant/init_db.py`

**connection.py responsibilities:**

- Singleton `AsyncQdrantClient` factory
- Connection pool management similar to PostgreSQL pattern
- Graceful shutdown support

**init_db.py responsibilities:**

- Create `agent_memory` collection if not exists
- Configure vector parameters (768 dim, cosine distance)
- Create all payload indexes (tenant_id, entity_id, type, fact_id, verb)
- Idempotent - safe to call multiple times

**Files to modify:**

- `apps/api/app/main.py` - Add Qdrant initialization to lifespan

**Acceptance Criteria:**

- [x] `get_qdrant_client()` returns singleton AsyncQdrantClient
- [x] `close_qdrant_client()` properly closes connection
- [x] `init_qdrant_db()` creates collection with correct configuration
- [x] All payload indexes created per Section A.1
- [ ] Lifespan initializes Qdrant on startup, closes on shutdown
- [x] No errors when Qdrant already initialized (idempotent)

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Service created at `apps/api/app/features/graph/services/embedding_service.py`

## Task 3: Embedding Service

**Goal:** Create a service for generating text embeddings using Google's Gemini.

**Files to create:**

- `apps/api/app/features/graph/services/embedding_service.py`

**EmbeddingService responsibilities:**

- Wrap `langchain-google-genai` embeddings
- Expose async `embed_text(text: str) -> list[float]`
- Use configured model (`gemini-embedding-001`)
- Handle errors gracefully (rate limits, API failures)

**Acceptance Criteria:**

- [x] `EmbeddingService.embed_text()` returns 768-dimensional vector
- [x] Same text produces consistent embeddings
- [x] Service is injectable and testable
- [x] Uses `GOOGLE_API_KEY` from settings

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Repository created at `apps/api/app/features/graph/repositories/vector_repository.py`

## Task 4: Vector Repository

**Goal:** Create repository for Qdrant vector operations with tenant isolation.

**Files to create:**

- `apps/api/app/features/graph/repositories/vector_repository.py`

**VectorRepository class:**

```python
class VectorRepository:
    def __init__(
        self,
        client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        tenant_id: str,
        collection_name: str = "agent_memory"
    ):
        ...

    async def add_semantic_memory(
        self,
        entity_id: UUID,
        fact: Fact,
        verb: str
    ) -> bool:
        """Add semantic memory vector for a fact."""
        ...

    async def search_semantic_memory(
        self,
        entity_id: UUID,
        query_text: str,
        top_k: int = 10,
        min_score: float | None = None
    ) -> list[SemanticSearchResult]:
        """Search semantic memories for an entity."""
        ...

    async def delete_semantic_memory(
        self,
        entity_id: UUID,
        fact_id: str,
        verb: str
    ) -> bool:
        """Delete semantic memory vector for a fact."""
        ...

    async def delete_all_semantic_memories_for_entity(
        self,
        entity_id: UUID
    ) -> int:
        """Delete all vectors for an entity. Returns count deleted."""
        ...
```

**Key implementation details:**

- Deterministic point IDs using UUIDv5: `uuid5(NAMESPACE, f"{tenant_id}:{entity_id}:{verb}:{fact_id}")`
- Synthetic sentence generation: `"The entity {verb} {fact.type}: {fact.name}"`
- All queries MUST filter by `tenant_id` - enforced at repository level
- Payload includes: `tenant_id`, `entity_id`, `fact_id`, `verb`, `relationship_key`, `type="semantic"`

**Files to modify:**

- `apps/api/app/features/graph/repositories/__init__.py` - Export VectorRepository

**Acceptance Criteria:**

- [x] `add_semantic_memory()` creates vector with correct payload
- [x] Point IDs are deterministic (idempotent upserts)
- [x] `search_semantic_memory()` always filters by `tenant_id` and `entity_id`
- [x] `delete_semantic_memory()` removes vector by relationship_key
- [x] All operations handle Qdrant errors gracefully

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Fixtures added in `apps/api/tests/conftest.py`, smoke tests in `apps/api/tests/features/graph/test_qdrant_fixtures.py`

## Task 5: Qdrant Test Infrastructure

**Goal:** Add Qdrant fixtures to test infrastructure.

**Files modified:**

- `apps/api/tests/conftest.py`

**Files created:**

- `apps/api/tests/features/graph/test_qdrant_fixtures.py`

**New fixtures:**

```python
@pytest_asyncio.fixture(scope="function")
async def qdrant_client(test_settings: Settings) -> AsyncGenerator[AsyncQdrantClient, None]:
    """Provide Qdrant client with test collection."""
    ...

@pytest_asyncio.fixture(scope="function")
async def embedding_service(test_settings: Settings) -> EmbeddingService:
    """Provide embedding service for tests."""
    ...
```

**Test collection behavior:**

- Use `agent_memory_test` collection name
- Create fresh collection before each test
- Create all payload indexes
- Delete collection after test

**Implementation notes:**

- Fixed `EmbeddingService` to pass `output_dimensionality=768` to embed methods (Gemini default is 3072)
- Point IDs in Qdrant must be UUID or integer (not arbitrary strings)

**Acceptance Criteria:**

- [x] `qdrant_client` fixture provides working client
- [x] Test collection created with correct configuration (768 dim, COSINE)
- [x] Indexes created matching production setup (tenant_id, entity_id, type, fact_id, verb)
- [x] Cleanup happens after each test
- [x] Existing tests continue to pass (59/62 — 3 pre-existing failures unrelated)

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Tests created at `apps/api/tests/features/graph/repositories/test_vector_repository.py`

## Task 6: Vector Repository Tests

**Goal:** Comprehensive tests for VectorRepository.

**Files created:**

- `apps/api/tests/features/graph/repositories/test_vector_repository.py`

**Test classes (25 tests total):**

- `TestVectorRepositoryAddSemantic` - Add operations (6 tests)
- `TestVectorRepositorySearchSemantic` - Search operations (7 tests)
- `TestVectorRepositoryDeleteSemantic` - Delete operations (4 tests)
- `TestVectorRepositoryDeleteAllForEntity` - Bulk delete operations (3 tests)
- `TestVectorRepositoryTenantIsolation` - Multi-tenant security (3 tests)
- `TestVectorRepositoryEntityScoping` - Entity boundary tests (2 tests)

**Key test cases:**

- Basic add/search/delete flow
- Idempotent adds (same fact twice = one vector)
- Tenant isolation (Tenant A cannot see Tenant B's data)
- Search relevance (location query finds location fact)
- Min score filtering
- Entity scoping (search is scoped to entity)
- Different verbs create separate vectors
- Correct payload storage verification
- Results ordered by score
- Delete all for entity with isolation

**Acceptance Criteria:**

- [x] All CRUD operations tested
- [x] Tenant isolation verified
- [x] Idempotency verified
- [x] Search relevance validated
- [x] Tests pass in CI (requires valid GOOGLE_API_KEY)

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — UseCase modified, route updated with vector injection

## Task 7: Assimilate UseCase Integration

**Goal:** Integrate vector repository into the assimilate knowledge flow.

**Files to modify:**

- `apps/api/app/features/graph/usecases/assimilate_knowledge_usecase.py`
- `apps/api/app/features/graph/routes/assimilate.py`

**Changes to AssimilateKnowledgeUseCaseImpl:**

```python
class AssimilateKnowledgeUseCaseImpl:
    def __init__(
        self,
        repository: GraphRepository,
        fact_extractor: FactExtractor,
        vector_repository: VectorRepository | None = None  # Optional for backward compat
    ):
        ...

    async def execute(self, request: AssimilateKnowledgeRequest) -> AssimilateKnowledgeResponse:
        # ... existing logic ...

        for fact_data in extracted_facts:
            result = await self.repository.add_fact_to_entity(...)

            # [NEW] Add to semantic memory if vector_repository is available
            if self.vector_repository:
                await self.vector_repository.add_semantic_memory(
                    entity_id=entity.id,
                    fact=result["fact"],
                    verb=result["has_fact_relationship"].verb
                )
```

**Changes to assimilate.py route:**

- Inject `VectorRepository` into use case via dependency
- Create `EmbeddingService` instance
- Get Qdrant client from connection pool

**Acceptance Criteria:**

- [x] Facts are vectorized during assimilation
- [x] Backward compatible (works without vector_repository)
- [x] Errors in vectorization logged but don't fail assimilation (graceful degradation)
- [x] Vectors include correct metadata (tenant_id, entity_id, fact_id, verb, type)

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Tests created at `apps/api/tests/features/graph/usecases/test_assimilate_knowledge_with_vectors.py`

## Task 8: Assimilate UseCase Integration Tests

**Goal:** Test the full assimilation flow with vectorization.

**Files to create:**

- `apps/api/tests/features/graph/usecases/test_assimilate_knowledge_with_vectors.py`

**Test scenarios:**

- Assimilate content → verify vectors created
- Assimilate multiple facts → verify all vectorized
- Search for facts by semantic query
- Vector-to-graph consistency (vectors point to real graph data)

**Acceptance Criteria:**

- [x] Integration tests verify full flow (9 tests passing)
- [x] Graph and vector stores stay in sync
- [x] Semantic search finds relevant facts

---

## Task 9: RAG Lookup Query Parameters

**Goal:** Add optional RAG query parameters to lookup endpoints.

**Files to modify:**

- `apps/api/app/features/graph/dtos/knowledge_dto.py`
- `apps/api/app/features/graph/routes/lookup.py`

**New DTOs:**

```python
class RagDebugHit(BaseModel):
    """Debug info for a single vector hit."""
    fact_id: str
    verb: str
    score: float
    verified: bool

class RagDebugDto(BaseModel):
    """Optional RAG debug metadata."""
    query: str
    top_k: int
    min_score: float | None
    vector_hits: list[RagDebugHit]
    verified_count: int
    timings_ms: dict[str, float] | None = None
```

**Modified lookup endpoints:**

```python
@router.get("/entities/lookup", response_model=GetEntityResponse)
async def get_entity(
    type: str,
    value: str,
    # New optional RAG params
    rag_query: str | None = None,
    rag_top_k: int = 10,
    rag_min_score: float | None = None,
    rag_expand_hops: int = 0,
    rag_debug: bool = False,
    use_case: GetEntityUseCase = Depends(get_get_entity_use_case),
) -> GetEntityResponse:
    ...
```

**Acceptance Criteria:**

- [x] New query params defined and documented
- [x] Without RAG params → existing behavior unchanged
- [x] DTOs support debug metadata
- [x] OpenAPI spec updated with new params

---

## Task 10: RAG Lookup UseCase

**Goal:** Implement vector-gated retrieval logic for entity lookup.

**Files to modify:**

- `apps/api/app/features/graph/usecases/get_entity_usecase.py` (primary implementation)
- `apps/api/app/features/graph/usecases/get_entity_summary.py` (inherits RAG behavior)
- `apps/api/app/features/graph/routes/lookup.py` (inject VectorRepository dependency)

**Architecture note:**

Both lookup usecases need to support RAG retrieval:

1. **`GetEntityUseCaseImpl`** — Primary implementation. This is where the vector search and graph verification logic lives. Currently accepts RAG params but doesn't use them.

2. **`GetEntitySummaryUseCaseImpl`** — Delegates to `GetEntityUseCaseImpl`. Already passes RAG params through, so it will automatically benefit once the underlying usecase is updated. No additional logic changes needed, but may need `VectorRepository` injection to pass down.

3. **`lookup.py` route** — Already has RAG query params wired up (from Task 9). Needs to inject `VectorRepository` into the usecases via dependency injection.

**New logic in GetEntityUseCaseImpl.execute():**

```python
async def execute(
    self,
    identifier_value: str,
    identifier_type: str,
    rag_query: str | None = None,
    rag_top_k: int = 10,
    rag_min_score: float | None = None,
    rag_expand_hops: int = 0,
) -> GetEntityResponse:
    # 1. Resolve entity (existing)
    entity_result = await self.repository.find_entity_by_identifier(...)

    if not rag_query:
        # 2a. No RAG → return all facts (existing behavior)
        return await self._build_full_response(entity_result)

    # 2b. RAG mode → vector search
    vector_hits = await self.vector_repository.search_semantic_memory(
        entity_id=entity.id,
        query_text=rag_query,
        top_k=rag_top_k,
        min_score=rag_min_score,
    )

    # 3. Verify hits in graph (prevent cross-entity leakage)
    verified_fact_ids = await self._verify_facts_in_graph(
        entity_id=entity.id,
        fact_ids=[hit.fact_id for hit in vector_hits]
    )

    # 4. Build filtered response with only verified facts
    return await self._build_filtered_response(entity_result, verified_fact_ids)
```

**Changes to GetEntityUseCaseImpl constructor:**

```python
class GetEntityUseCaseImpl:
    def __init__(
        self,
        repository: GraphRepository,
        vector_repository: VectorRepository | None = None  # Optional for backward compat
    ):
        self.repository = repository
        self.vector_repository = vector_repository
```

**Acceptance Criteria:**

- [x] Without `rag_query` → all facts returned (unchanged)
- [x] With `rag_query` → only matching facts returned
- [x] Graph verification prevents cross-entity data leakage
- [ ] `rag_expand_hops` allows adjacent fact inclusion (reserved for future)
- [ ] Performance acceptable (<500ms for typical queries) (needs testing)
- [x] Both `/entities/lookup` and `/entities/lookup/summary` support RAG filtering

---

> [!NOTE] > **Status: ✅ IMPLEMENTED** — Tests created at `apps/api/tests/features/graph/usecases/test_get_entity_with_rag.py`, `apps/api/tests/features/graph/usecases/test_get_entity_summary_with_rag.py`, and `apps/api/tests/features/graph/routes/test_lookup_rag.py`

## Task 11: RAG Lookup Tests

**Goal:** Test the RAG-enabled lookup functionality for both usecases.

**Files created:**

- `apps/api/tests/features/graph/usecases/test_get_entity_with_rag.py` (12 tests)
- `apps/api/tests/features/graph/usecases/test_get_entity_summary_with_rag.py` (8 tests)
- `apps/api/tests/features/graph/routes/test_lookup_rag.py` (12 tests)

**Test scenarios for GetEntityUseCaseImpl:**

- Lookup without RAG → full facts list (backward compatibility)
- Lookup with RAG → filtered facts list
- RAG returns relevant facts first (ordered by score)
- Graph verification rejects orphan vectors
- `rag_min_score` filtering works
- `rag_debug` returns metadata
- Empty RAG results → empty facts list

**Test scenarios for GetEntitySummaryUseCaseImpl:**

- Summary without RAG → summarizes all facts
- Summary with RAG → summarizes only matched facts
- Summary with no matching facts → appropriate message
- RAG params correctly passed through to underlying usecase

**Test scenarios for routes (integration):**

- `/entities/lookup` endpoint with RAG params
- `/entities/lookup/summary` endpoint with RAG params
- Both endpoints return correct response shapes

**Acceptance Criteria:**

- [x] All RAG scenarios tested for both usecases (32 tests total)
- [x] Backward compatibility verified (no RAG params = existing behavior)
- [x] Graph verification tested (prevents cross-entity leakage)
- [x] Debug mode tested
- [x] Summary endpoint correctly uses RAG-filtered facts

---

## Task 12: Documentation & Cleanup

**Goal:** Update documentation and clean up any loose ends.

**Files to modify:**

- `apps/api/README.md` - Add vector memory section
- `docs/plans/vectorized-episodic-and-semantic-mem.md` - Mark completed tasks
- `.env.example` - Add Qdrant environment variables

**Documentation updates:**

- How to set up Qdrant (docker-compose already has it)
- Environment variables for vector configuration
- API usage examples for RAG queries
- Architecture diagram update (if exists)

**Acceptance Criteria:**

- [ ] README documents vector memory feature
- [ ] Environment variables documented
- [ ] API examples provided
- [ ] Plan document updated with completion status

---

## Implementation Order Recommendation

For a phased rollout, implement tasks in this order:

### Phase 1: Foundation (Tasks 1-3)

Set up configuration, Qdrant connection, and embedding service. No user-facing changes.

### Phase 2: Core Vector Operations (Tasks 4-6)

Implement and test the VectorRepository. Can be developed in parallel with Phase 1 completion.

### Phase 3: Write Path (Tasks 7-8)

Integrate vectorization into the assimilate flow. This enables semantic memory creation.

### Phase 4: Read Path (Tasks 9-11)

Implement RAG-enabled lookup. This enables semantic retrieval.

### Phase 5: Polish (Task 12)

Documentation and cleanup after all features are working
