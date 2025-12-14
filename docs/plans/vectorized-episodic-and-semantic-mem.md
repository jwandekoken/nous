Here is the finalized implementation plan for adding **Vectorized Episodic** and **Vectorized Semantic** memory to your project. This strategy ensures strict linking between your Vector Store (Qdrant) and your Graph Store (Apache AGE) using the UUIDs and identifiers you have already defined.

### 1\. High-Level Architecture: The "Anchor & Link" Strategy

The core principle is **"Vectors are Entry Points; Graphs are the Truth."**

- **Qdrant** is used to find the _ID_ of a node based on fuzzy meaning.
- **Apache AGE** is used to retrieve the actual trusted data using that ID.

---

### 2\. Strategy A: Vectorized Episodic Memory (The Context)

This memory allows the agent to recall _what happened_ and _how it was said_.

- **The Data:** Sliding window of conversation text.
- **The Vector:** Embedding of `"{Previous_Turn}\n{Current_Turn}"`.
- **The Linkage:**
  - **Graph Anchor:** The `Source` node in AGE.
  - **Link:** The Qdrant payload stores the `source_id` (UUID) of the `Source` node created in AGE.
- **Implementation Logic:**
  1.  **Input:** User sends `content="I love hiking"`, `history=["Hi, I'm John"]`.
  2.  **Graph Action:** Create `Source` node. Get `source.id` (UUID).
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

### 3\. Strategy B: Vectorized Semantic Memory (The Facts)

This memory allows the agent to find specific facts based on vague queries (e.g., query "outdoor activities" -\> finds fact "Hiking").

- **The Data:** Extracted atomic facts (Subject, Verb, Object).
- **The Vector:** Embedding of a **synthetic sentence** representation of the fact. Embedding just the word "Paris" is weak; embedding "The entity lives in Paris" is strong.
- **The Linkage:**
  - **Graph Anchor:** The `Fact` node in AGE.
  - **Link:** The Qdrant payload stores the `fact_id` (Synthetic ID like `Location:Paris`) from AGE.
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
          "type": "semantic"
        }
        ```

---

### 4\. Implementation Plan

Here is the step-by-step code integration plan.

#### Step 1: Configuration (`apps/api/app/core/settings.py`)

Add the Qdrant connection details.

```python
# ... existing settings ...
    # Qdrant
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")
    embedding_model: str = Field(default="text-embedding-3-small", description="Model name")
```

#### Step 2: Database Layer (`apps/api/app/db/qdrant/`)

Create the connection and initialization logic.

- `connection.py`: Returns a singleton `AsyncQdrantClient`.
- `init_db.py`:
  - Checks if `episodic_memory` and `semantic_memory` collections exist.
  - If not, creates them with `Cosine` distance.
  - **Critical:** Creates payload indexes on `tenant_id`, `entity_id`, and `type` for fast filtering.

#### Step 3: Repository Layer (`apps/api/app/features/graph/repositories/`)

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
        # Construct text: f"{verb} {fact.type}: {fact.name}"
        # Embed text
        # Upsert to 'semantic_memory' collection
        # Payload includes: tenant_id, entity_id, fact_id
```

#### Step 4: Use Case Integration (`assimilate_knowledge_usecase.py`)

Update the `execute` method to call the vector repository.

```python
# ... inside execute method ...

# 1. (Existing) Create/Find Entity
# 2. (Existing) Create Source in Graph
source = Source(...)

# 3. [NEW] Add to Episodic Memory
# Construct window from history + current content
window_text = self._construct_window(request.history, request.content)
await self.vector_repo.add_episodic(entity.id, source.id, window_text)

# 4. (Existing) Extract Facts
extracted_facts = await self.fact_extractor.extract_facts(...)

for fact_data in extracted_facts:
    # 5. (Existing) Add to Graph
    result = await self.repository.add_fact_to_entity(...)

    # 6. [NEW] Add to Semantic Memory
    # We use the fact data returned from the repository to ensure IDs match
    await self.vector_repo.add_semantic(
        entity_id=entity.id,
        fact=result["fact"],
        verb=result["has_fact_relationship"].verb
    )
```
