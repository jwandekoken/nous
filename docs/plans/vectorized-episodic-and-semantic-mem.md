Here is the finalized implementation plan for adding **Vectorized Episodic** and **Vectorized Semantic** memory to your project. This strategy ensures strict linking between your Vector Store (Qdrant) and your Graph Store (Apache AGE) using the UUIDs and identifiers you have already defined.

---

# 0\. Repo Discoveries, Criticisms, and Suggestions (Addendum)

This section captures implementation-relevant discoveries from the current codebase, plus suggested corrections to this plan to ensure it matches what’s already implemented (AGE schema/repository patterns, DTO shapes, multi-tenancy, and expected runtime behavior).

## A) Source Persistence (Episodic memory requires a real Source anchor)

- **A `Source` object can exist in the response but not be persisted unless at least one Fact is written**
  - Current graph write flow creates the `Source` node as a side-effect of `add_fact_to_entity`.
  - If fact extraction returns 0 facts, there may be no `Source` node to anchor episodic vectors.
  - **Decision (Option B):** Persist a `Source` **iff** we write an **episodic vector** for that content.
    - If we don't store an episodic vector, we don't persist the `Source` (avoid retaining useless/raw content).
    - If we do store an episodic vector, we must persist the `Source` so the vector hit can be verified/expanded in AGE (“Vectors are Entry Points; Graphs are the Truth.”).
  - **Plan action:** Add a dedicated graph operation to persist a `Source` (upsert by `source.id`) and call it immediately before writing episodic memory. Then link Facts (if any) to that same Source.

## B) Qdrant Collection Design (dimensions, versioning, and idempotency)

- **Collection creation must know vector dimension up-front**

  - Qdrant requires `vector_size` at collection creation time.
  - **Decision:** Standardize on `gemini-embedding-001` with **768** dimensions (`embedding_dim = 768`).
  - **Plan action:** Add settings for `embedding_model` and `embedding_dim` (single source of truth) and a migration rule when models/dims change:
    - Fail fast and require a manual migration, or
    - Create versioned collections (e.g., `semantic_memory_v2`) and route reads/writes accordingly.

- **Make vector writes idempotent**
  - **Plan action:** Use deterministic Qdrant point IDs:
    - Episodic: `point_id = hash(tenant_id, source_id, window_index)` (or a UUIDv5 derived from those fields).
    - Semantic: `relationship_key = "{entity_id}:{verb}:{fact_id}"`, then `point_id = hash(tenant_id, relationship_key)` (or UUIDv5).

## C) Multi-Tenancy Enforcement (match existing FastAPI + AGE approach)

- **Tenant resolution already exists (`TenantInfo`)**
  - Graph isolation is achieved by passing `tenant_info.graph_name` into `AgeRepository`.
  - **Plan action:** Mirror this in vectors:
    - Construct the vector repo with `tenant_id`.
    - Enforce `tenant_id` filtering in _every_ Qdrant search (not optional).

## D) Embedding Provider / Defaults (make the plan match actual stack)

- **Embedding model choice should match dependencies**
  - Current dependencies include `langchain-google-genai`; the plan’s default `text-embedding-3-small` implies OpenAI.
  - **Decision:** Use Google embeddings via `langchain-google-genai` with `gemini-embedding-001` (**768 dims**).
  - **Plan action:** Treat `embedding_dim=768` as the Qdrant collection `vector_size` and fail fast if config and collection schema disagree.

## E) Retrieval Workflows (Anchor & Expand is missing from the step plan)

- This plan currently covers ingestion; it should also specify retrieval:
  1. Embed query → Qdrant search (filtered by `tenant_id` **and `entity_id`**, and optionally `type`)
  2. Convert hits → AGE anchor IDs:
     - Episodic: `source_id`
     - Semantic: `fact_id` + `verb` (or `relationship_key`)
  3. Graph verification + traversal (“expand”):
     - Semantic results MUST be resolved in AGE by following only the relationship for the same entity:
       - Match `(Entity {id = entity_id}) -[verb]-> (Fact {fact_id = fact_id})`
       - Do not return the same `fact_id` from a different entity
     - Return a compact graph-context bundle for LLM consumption
  - **Plan action:** Add a new step for retrieval endpoints/usecases (e.g., “search memories” and “expand from anchors”).

### E.1) API Retrieval Contract (Option A: opt-in params, no breaking changes)

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

#### E.1.1) Query params

- **`rag_query: str | None`**

  - Conversational user turn (free text).
  - If omitted/empty → identical behavior to today.

- **`rag_top_k: int`** (default: 10)

  - Number of vector candidates to retrieve before graph verification.

- **`rag_min_score: float | None`**

  - Optional similarity threshold for filtering vector hits before graph verification.

- **`rag_mode: "semantic" | "episodic" | "hybrid"`** (default: `"semantic"`)

  - Controls which vector collection(s) are searched.
  - **Important**: regardless of mode, the public API remains **fact-only** (see below).

- **`rag_expand_hops: int`** (default: 0)
  - Optional graph expansion depth starting from verified anchors.
  - `0` returns only matched facts; `1` may include adjacent facts depending on expansion rules.

#### E.1.2) Fact-only response semantics (episodic is a selector, not a returned object)

We will **not** return episodic windows/sources as first-class objects in lookup responses at this stage.

- **Semantic mode**:

  - Qdrant hits return `relationship_key` / (`fact_id`, `verb`)
  - AGE verification ensures the relationship exists for the resolved entity
  - Response `facts[]` is filtered to verified hits (plus any optional expansion)

- **Episodic mode (selector-only)**:

  - Qdrant hits return `source_id`
  - AGE resolves facts attached to those sources (scoped to the resolved entity)
  - Response still returns **facts only**; episodic windows are not returned directly

- **Hybrid mode**:
  - Union semantic-selected facts + episodic-selected facts (dedupe by `relationship_key` / (`fact_id`, `verb`))
  - Apply `rag_expand_hops` if enabled

#### E.1.3) Optional RAG debug metadata (opt-in, does not change default behavior)

We may add an **optional** field to the response DTO(s) to surface retrieval provenance when requested.

- **DTO field**: `rag_debug: RagDebugDto | None = None`
- **Enabled by**: a query param like `rag_debug=true` (default false)
- **Contains** (suggested minimal shape):
  - `mode`, `top_k`, `min_score`
  - `vector_hits`: list of `{collection, score, anchor_type, anchor_id, relationship_key?}`
  - `verified_anchors`: list of anchors that passed AGE verification
  - `timings_ms` (optional): `{vector_search, graph_verify, graph_fetch}`

## F) Docker / Runtime Gotchas

- When running under Docker Compose, Qdrant host will typically be `qdrant` (service name), not `localhost`.
- **Plan action:** Document environment-specific defaults (`localhost` for local dev outside compose; `qdrant` inside compose).

# 1\. High-Level Architecture: The "Anchor & Link" Strategy

The core principle is **"Vectors are Entry Points; Graphs are the Truth."**

- **Qdrant** is used to find the _ID_ of a node based on fuzzy meaning.
- **Apache AGE** is used to retrieve the actual trusted data using that ID.

---

# 2\. Strategy A: Vectorized Episodic Memory (The Context)

This memory allows the agent to recall _what happened_ and _how it was said_.

- **The Data:** Sliding window of conversation text.
- **The Vector:** Embedding of `"{Previous_Turn}\n{Current_Turn}"`.
- **The Linkage:**
  - **Graph Anchor:** The `Source` node in AGE.
  - **Link:** The Qdrant payload stores the `source_id` (UUID) of the `Source` node persisted in AGE.
- **Implementation Logic:**
  1.  **Input:** User sends `content="I love hiking"`, `history=["Hi, I'm John"]`.
  2.  **Graph Action (Option B):** Persist `Source` node **only if** we are writing an episodic vector for this content. Get `source.id` (UUID).
  3.  **Vector Action:**
      - Text to Embed: `"User: Hi, I'm John\nUser: I love hiking"`
      - Payload:
        ```json
        {
          "tenant_id": "...",    // For isolation
          "entity_id": "...",    // UUID of the Entity
          "source_id": "...",    // UUID of the Source Node
          "type": "episodic",
          "timestamp": 171562... // Unix epoch
        }
        ```

---

# 3\. Strategy B: Vectorized Semantic Memory (The Facts)

This memory allows the agent to find specific facts based on vague queries (e.g., query "outdoor activities" -\> finds fact "Hiking").

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

# 4\. Implementation Plan

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
  - Checks if `episodic_memory` and `semantic_memory` collections exist.
  - If not, creates them with `Cosine` distance.
  - **Critical:** Creates payload indexes on `tenant_id`, `entity_id`, and `type` for fast filtering.

## Step 3: Repository Layer (`apps/api/app/features/graph/repositories/`)

Create `vector_repository.py` to abstract the Qdrant client. This ensures `tenant_id` is _always_ injected.

```python
class VectorRepository:
    def __init__(self, client, tenant_id: str):
        self.client = client
        self.tenant_id = tenant_id

    async def add_episodic(self, entity_id: UUID, source_id: UUID, text: str):
        # Embed text (using OpenAI or local model)
        # Upsert to 'episodic_memory' collection
        # Payload includes: tenant_id, entity_id, source_id

    async def add_semantic(self, entity_id: UUID, fact: Fact, verb: str):
        # relationship_key must uniquely represent the assertion in the graph:
        # f"{entity_id}:{verb}:{fact.fact_id}"
        # Construct text: f"The entity {verb} {fact.type}: {fact.name}"
        # Embed text
        # Upsert to 'semantic_memory' collection
        # Payload includes: tenant_id, entity_id, fact_id, verb, relationship_key
```

## Step 4: Use Case Integration (`assimilate_knowledge_usecase.py`)

Update the `execute` method to call the vector repository.

```python
# ... inside execute method ...

# 1. (Existing) Create/Find Entity
# 2. (New; Option B) Create Source object (in-memory)
source = Source(...)

# 3. [NEW] Persist Source in Graph (only if we write episodic memory)
await self.repository.upsert_source(source)

# 4. [NEW] Add to Episodic Memory
# Construct window from history + current content
window_text = self._construct_window(request.history, request.content)
await self.vector_repo.add_episodic(entity.id, source.id, window_text)

# 5. (Existing) Extract Facts
extracted_facts = await self.fact_extractor.extract_facts(...)

for fact_data in extracted_facts:
    # 6. (Existing) Add to Graph
    result = await self.repository.add_fact_to_entity(...)

    # 7. [NEW] Add to Semantic Memory
    # We use the fact data returned from the repository to ensure IDs match
    await self.vector_repo.add_semantic(
        entity_id=entity.id,
        fact=result["fact"],
        verb=result["has_fact_relationship"].verb
    )
```
