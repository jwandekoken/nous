Here is the finalized implementation plan for adding **Vectorized Semantic Memory** to your project. This strategy ensures strict linking between your Vector Store (Qdrant) and your Graph Store (Apache AGE) using the UUIDs and identifiers you have already defined.

---

# 0. Repo Discoveries, Criticisms, and Suggestions (Addendum)

This section captures implementation-relevant discoveries from the current codebase, plus suggested corrections to this plan to ensure it matches what's already implemented (AGE schema/repository patterns, DTO shapes, multi-tenancy, and expected runtime behavior).

## A) Qdrant Collection Design (dimensions, versioning, and idempotency)

- **Collection creation must know vector dimension up-front**

  - Qdrant requires `vector_size` at collection creation time.
  - **Decision:** Standardize on `gemini-embedding-001` with **768** dimensions (`embedding_dim = 768`).
  - **Plan action:** Add settings for `embedding_model` and `embedding_dim` (single source of truth) and a migration rule when models/dims change:
    - Fail fast and require a manual migration, or
    - Create versioned collections (e.g., `semantic_memory_v2`) and route reads/writes accordingly.

- **Make vector writes idempotent**
  - **Plan action:** Use deterministic Qdrant point IDs:
    - Semantic: `relationship_key = "{entity_id}:{verb}:{fact_id}"`, then `point_id = hash(tenant_id, relationship_key)` (or UUIDv5).

## B) Multi-Tenancy Enforcement (match existing FastAPI + AGE approach)

- **Tenant resolution already exists (`TenantInfo`)**
  - Graph isolation is achieved by passing `tenant_info.graph_name` into `AgeRepository`.
  - **Plan action:** Mirror this in vectors:
    - Construct the vector repo with `tenant_id`.
    - Enforce `tenant_id` filtering in _every_ Qdrant search (not optional).

## C) Embedding Provider / Defaults (make the plan match actual stack)

- **Embedding model choice should match dependencies**
  - Current dependencies include `langchain-google-genai`; the plan's default `text-embedding-3-small` implies OpenAI.
  - **Decision:** Use Google embeddings via `langchain-google-genai` with `gemini-embedding-001` (**768 dims**).
  - **Plan action:** Treat `embedding_dim=768` as the Qdrant collection `vector_size` and fail fast if config and collection schema disagree.

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
  - Checks if `semantic_memory` collection exists.
  - If not, creates it with `Cosine` distance.
  - **Critical:** Creates payload indexes on `tenant_id`, `entity_id` for fast filtering.

## Step 3: Repository Layer (`apps/api/app/features/graph/repositories/`)

Create `vector_repository.py` to abstract the Qdrant client. This ensures `tenant_id` is _always_ injected.

```python
class VectorRepository:
    def __init__(self, client, tenant_id: str):
        self.client = client
        self.tenant_id = tenant_id

    async def add_semantic(self, entity_id: UUID, fact: Fact, verb: str):
        # relationship_key must uniquely represent the assertion in the graph:
        # f"{entity_id}:{verb}:{fact.fact_id}"
        # Construct text: f"The entity {verb} {fact.type}: {fact.name}"
        # Embed text
        # Upsert to 'semantic_memory' collection
        # Payload includes: tenant_id, entity_id, fact_id, verb, relationship_key
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
    await self.vector_repo.add_semantic(
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
from qdrant_client.models import Distance, VectorParams

@pytest_asyncio.fixture(scope="function")
async def qdrant_client(test_settings: Settings) -> AsyncGenerator[AsyncQdrantClient, None]:
    """Provide Qdrant client for vector operations tests.

    Creates a fresh client for each test and cleans up the semantic_memory collection after.
    """
    client = AsyncQdrantClient(
        host=test_settings.qdrant_host,
        port=test_settings.qdrant_port,
    )

    # Ensure collection exists for tests
    collection_name = "semantic_memory_test"
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
        collection_name="semantic_memory_test",
    )


@pytest.fixture
def test_fact() -> Fact:
    """Test fact for vector operations."""
    return Fact(name="Paris", type="Location")


class TestVectorRepositoryAddSemantic:
    """Integration tests for VectorRepository.add_semantic method."""

    @pytest.mark.asyncio
    async def test_add_semantic_basic(
        self,
        vector_repository: VectorRepository,
        test_fact: Fact,
    ) -> None:
        """Test basic semantic vector addition."""
        entity_id = uuid.uuid4()

        # Act
        result = await vector_repository.add_semantic(
            entity_id=entity_id,
            fact=test_fact,
            verb="lives_in",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_add_semantic_is_idempotent(
        self,
        vector_repository: VectorRepository,
        test_fact: Fact,
    ) -> None:
        """Test that adding the same semantic vector is idempotent."""
        entity_id = uuid.uuid4()

        # Add twice
        await vector_repository.add_semantic(entity_id, test_fact, "lives_in")
        await vector_repository.add_semantic(entity_id, test_fact, "lives_in")

        # Assert: Should have only one point (due to deterministic ID)
        # Verify by searching
        results = await vector_repository.search_semantic(
            entity_id=entity_id,
            query_text="Where does the entity live?",
            top_k=10,
        )
        assert len(results) == 1


class TestVectorRepositorySearchSemantic:
    """Integration tests for VectorRepository.search_semantic method."""

    @pytest.mark.asyncio
    async def test_search_semantic_finds_relevant_fact(
        self,
        vector_repository: VectorRepository,
    ) -> None:
        """Test that semantic search finds relevant facts."""
        entity_id = uuid.uuid4()

        # Add multiple facts
        await vector_repository.add_semantic(
            entity_id, Fact(name="Paris", type="Location"), "lives_in"
        )
        await vector_repository.add_semantic(
            entity_id, Fact(name="Software Engineering", type="Profession"), "works_as"
        )
        await vector_repository.add_semantic(
            entity_id, Fact(name="Hiking", type="Hobby"), "enjoys"
        )

        # Search for location-related query
        results = await vector_repository.search_semantic(
            entity_id=entity_id,
            query_text="Where does this person live?",
            top_k=3,
        )

        # The top result should be the location fact
        assert len(results) > 0
        assert results[0]["fact_id"] == "Location:Paris"

    @pytest.mark.asyncio
    async def test_search_semantic_respects_tenant_isolation(
        self,
        qdrant_client: AsyncQdrantClient,
    ) -> None:
        """Test that search only returns results for the current tenant."""
        entity_id = uuid.uuid4()

        # Create repos for two different tenants
        repo_tenant_a = VectorRepository(
            client=qdrant_client,
            tenant_id="tenant_a",
            collection_name="semantic_memory_test",
        )
        repo_tenant_b = VectorRepository(
            client=qdrant_client,
            tenant_id="tenant_b",
            collection_name="semantic_memory_test",
        )

        # Add fact from tenant A
        await repo_tenant_a.add_semantic(
            entity_id, Fact(name="Paris", type="Location"), "lives_in"
        )

        # Search from tenant B - should NOT find tenant A's data
        results = await repo_tenant_b.search_semantic(
            entity_id=entity_id,
            query_text="location",
            top_k=10,
        )

        assert len(results) == 0


class TestVectorRepositoryDeleteSemantic:
    """Integration tests for VectorRepository.delete_semantic method."""

    @pytest.mark.asyncio
    async def test_delete_semantic_removes_vector(
        self,
        vector_repository: VectorRepository,
        test_fact: Fact,
    ) -> None:
        """Test that deleting a semantic vector removes it from the collection."""
        entity_id = uuid.uuid4()

        # Add then delete
        await vector_repository.add_semantic(entity_id, test_fact, "lives_in")
        await vector_repository.delete_semantic(
            entity_id=entity_id,
            fact_id=test_fact.fact_id,
            verb="lives_in",
        )

        # Search should return nothing
        results = await vector_repository.search_semantic(
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
        collection_name="semantic_memory_test",
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
        search_results = await vector_repo.search_semantic(
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
        search_results = await vector_repo.search_semantic(
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
