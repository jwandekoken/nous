# Token usage tracking (Gemini + embeddings)

## Goal

Track **LLM/embedding token usage** (and related usage metadata) per **tenant** (and optionally per user / API key) across the Nous API, so we can:

- attribute spend to tenants/features/endpoints
- build dashboards/alerts/quotas later
- debug runaway usage

Non-goals for the first iteration:

- enforcing quotas/limits (we’ll design for it, but not block requests yet)
- billing/invoicing flows
- perfect token counts when the provider doesn’t return them (we’ll store “unknown” and add fallbacks later)

---

## Where tokens are consumed today (current call sites)

In our API, “token consumption” is happening in the **graph feature** via LangChain + Google Gemini:

- **LLM calls**

  - `apps/api/app/features/graph/services/langchain_fact_extractor.py`
    - `LangChainFactExtractor.extract_facts()` calls `self.chain.ainvoke(...)` (Gemini chat model)
  - `apps/api/app/features/graph/services/langchain_data_summarizer.py`
    - `LangChainDataSummarizer.summarize()` calls `self.chain.ainvoke(...)` (Gemini chat model)

- **Embedding calls (used for RAG / Qdrant)**
  - `apps/api/app/features/graph/services/embedding_service.py`
    - `EmbeddingService.embed_text()` → `GoogleGenerativeAIEmbeddings.aembed_query(...)`
    - `EmbeddingService.embed_texts()` → `GoogleGenerativeAIEmbeddings.aembed_documents(...)`
  - These are used by:
    - `apps/api/app/features/graph/repositories/qdrant_repository.py`
      - `add_semantic_memory()` (embeds synthetic sentence)
      - `search_semantic_memory()` (embeds the query)

Those services are invoked through:

- `apps/api/app/features/graph/routes/assimilate.py` → `AssimilateKnowledgeUseCaseImpl` → `FactExtractor` (+ optional `VectorRepository`)
- `apps/api/app/features/graph/routes/lookup.py`
  - `GetEntityUseCaseImpl` (optional RAG → embeddings)
  - `GetEntitySummaryUseCaseImpl` (summary → LLM)

---

## Constraints from the current app shape

- Tenant identity is resolved via `get_tenant_info()` (used as a router-level dependency in `apps/api/app/features/graph/router.py`).
- Graph services (`LangChainFactExtractor`, `LangChainDataSummarizer`) are instantiated at **module import time** in the route modules (singletons).
- DB migrations exist via Alembic for the **auth Postgres DB** (`apps/api/migrations/*`) with models in `apps/api/app/features/auth/models.py`.

Implication: token tracking should be:

- request-scoped (tenant/user/api-key attribution)
- safe with module-level singleton services (no global mutable state leaking across requests)

---

## Proposed architecture

### High-level design

Add a new feature module: `app/features/usage/` (name bikeshed: `usage`, `billing`, `telemetry`).

It provides:

- **Request usage context**

  - `contextvars` to store `request_id`, `tenant_id`, `actor_type`, `actor_id`, `path`, etc.
  - a small FastAPI middleware to create `request_id` and timing metadata
  - a hook in `get_tenant_info()` (or a wrapper dependency) to populate tenant/actor context once auth succeeds

- **A TokenUsageTracker service**

  - an interface like `TokenUsageRecorder` / `TokenUsageRepository`
  - a default **Noop** implementation when disabled (or missing DB)
  - a Postgres-backed implementation writing to the auth DB

- **LangChain integration (recommended)**

  - implement a LangChain callback handler (`BaseCallbackHandler` / `AsyncCallbackHandler`)
  - attach it per invocation: `await chain.ainvoke(input, config={"callbacks": [handler]})`
  - in `on_llm_end`, extract provider usage metadata and call `TokenUsageTracker.record(...)`

- **Embedding tracking**
  - wrap `EmbeddingService.embed_text(s)` calls with a lightweight “span”:
    - input size (chars) always
    - token counts if/when the provider returns them (varies by SDK)
  - store `usage_kind="embedding"` events separately from `usage_kind="chat"`

This gets us coverage without changing business logic and keeps tracking centralized.

---

## Data model (auth Postgres DB)

### Table: `token_usage_events` (append-only)

Store one row per “provider call” (LLM or embedding), to preserve fidelity for later aggregation.

Suggested columns:

- **identity**

  - `id` UUID PK
  - `created_at` timestamptz default now()
  - `request_id` UUID (from middleware)
  - `tenant_id` UUID (required)
  - `actor_type` text enum-ish (`"api_key" | "user" | "unknown"`)
  - `actor_id` UUID nullable (api_key id or user id if available)

- **what happened**

  - `feature` text (e.g. `"graph"`)
  - `operation` text (e.g. `"fact_extract" | "entity_summary" | "rag_query_embed" | "semantic_memory_embed"`)
  - `endpoint` text (HTTP path template if available; otherwise raw path)

- **provider/model**

  - `provider` text (e.g. `"google"`)
  - `model` text (`gemini-2.5-flash`, `models/gemini-embedding-001`, etc.)

- **counts**

  - `prompt_tokens` int nullable
  - `completion_tokens` int nullable
  - `total_tokens` int nullable
  - `input_chars` int nullable (fallback metric)
  - `output_chars` int nullable (fallback metric)

- **outcome**
  - `status` text (`"ok" | "error"`)
  - `error_type` text nullable

Notes:

- Keeping token columns nullable is important because Gemini/LangChain may not always surface usage in a stable field.
- We can add a second table later for rollups (`token_usage_daily`) if/when we need cheap queries.

### Refactor: Rename `auth_session.py` to general-purpose session

The current `apps/api/app/db/postgres/auth_session.py` is named for auth-specific use, but it's evolving into the **general Postgres session provider** for the app (used by auth, usage, and future features).

**Rename the file and its contents:**

| Current                                    | New                                   |
| ------------------------------------------ | ------------------------------------- |
| `apps/api/app/db/postgres/auth_session.py` | `apps/api/app/db/postgres/session.py` |
| `init_auth_db_session()`                   | `init_db_session()`                   |
| `get_auth_db_session()`                    | `get_db_session()`                    |

**Update the module docstring** to reflect broader usage:

> _"SQLAlchemy database session management for the Postgres database. Provides async sessions for all features requiring structured data persistence (auth, usage, etc.)."_

**Update all import sites** that reference the old names (search for `auth_session` and `get_auth_db_session`).

---

### ORM + migrations

- Add a SQLAlchemy model in `apps/api/app/features/usage/models.py`.
  - Ensure Alembic discovers the model by importing it in `migrations/env.py`.
- Create a new Alembic migration under `apps/api/migrations/versions/`.

---

## Request context propagation

### Middleware: request id + timing

Add a middleware in `apps/api/app/main.py` (or a dedicated `app/core/middleware.py`) that:

- generates a `request_id` UUID for every request
- stores it in a contextvar
- optionally adds it to response headers (`X-Request-Id`)

### Tenant + actor attribution

Update `app/core/authorization.py:get_tenant_info()` (or wrap it) to also set contextvars:

- `tenant_id` and `graph_name`
- `actor_type`:
  - `"user"` if resolved from cookie/JWT
  - `"api_key"` if resolved from `X-API-Key`
- `actor_id` if we can cheaply access it (optional for v1)

This works well because graph routes already depend on `get_tenant_info` at router-level.

---

## LangChain/Gemini usage extraction strategy

We should treat “usage extraction” as adapter logic because the exact fields differ across providers and LangChain versions.

Plan:

- Implement `extract_usage_from_langchain_result(result) -> TokenCounts | None`
  - check for known locations:
    - `response.llm_output` (common in LC)
    - `response.generations[*].message.usage_metadata` (Gemini adapters often attach this)
    - message `response_metadata` / `usage_metadata` keys
- If present:
  - compute/store `prompt_tokens`, `completion_tokens`, `total_tokens`
- If not present:
  - store only fallback metrics (`input_chars`, `output_chars`) and set token fields `NULL`

---

## Integration points (minimal code changes later)

### 1) Fact extraction

In `LangChainFactExtractor.extract_facts()`:

- pass callbacks into `ainvoke`:
  - `await self.chain.ainvoke(inputs, config={"callbacks": [TokenUsageCallbackHandler(operation="fact_extract")]})`

### 2) Entity summary

In `LangChainDataSummarizer.summarize()`:

- same as above with `operation="entity_summary"`

### 3) Embeddings (RAG)

In `EmbeddingService.embed_text(s)`:

- wrap calls with `TokenUsageTracker.record_embedding(...)`
- operations:
  - `semantic_memory_embed` (from `add_semantic_memory`)
  - `rag_query_embed` (from `search_semantic_memory`)

We can pass the operation down from the caller (QdrantRepository) or infer it (less ideal).

---

## Optional API surface (for later visibility)

Add a new router `app/features/usage/router.py` under `/api/v1/usage` to expose:

- `GET /usage/tokens/summary?from=...&to=...`
  - tenant-scoped totals grouped by day and/or operation
- `GET /usage/tokens/events?...` (admin-only) for debugging

Initial implementation can skip this and only store events, depending on urgency.

---

## Testing strategy

- **Unit tests**

  - usage extraction adapter: ensure it can parse multiple “shapes” of LangChain outputs
  - callback handler calls repository with correct context + operation

- **Integration tests (fast)**
  - for graph routes, mock the LangChain chain `.ainvoke` to return a response object containing usage metadata
  - assert we persist `token_usage_events` rows with correct tenant attribution

---

## Rollout plan

- Add a `Settings` flag, e.g. `token_usage_enabled: bool = False`.
- When disabled, `TokenUsageTracker` is Noop (zero overhead beyond a couple of `if`s).
- When enabled, persist events.
- Add lightweight logging/metrics only if needed.

---

## Implementation checklist (next steps)

- Create `app/features/usage/` module:
  - context (`contextvars`)
  - repository (auth DB)
  - tracker service
  - LangChain callback handler + usage extractor adapter
- Add Alembic migration + model for `token_usage_events`
- Add request-id middleware + tenant/actor context in `get_tenant_info`
- Wire callbacks into:
  - `LangChainFactExtractor.extract_facts`
  - `LangChainDataSummarizer.summarize`
  - `EmbeddingService` (+ optionally `QdrantRepository` passes operation)
- Add tests
