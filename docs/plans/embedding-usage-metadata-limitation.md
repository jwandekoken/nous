# Embedding API Usage Metadata Limitation

## Problem

The Google Embedding API (`gemini-embedding-001`) via the `google-genai` SDK **does not return usage metadata** (token counts) when using the AI Studio API endpoint. This differs from the Chat models which do return `prompt_tokens`, `completion_tokens`, and `total_tokens`.

### Evidence

When calling `client.aio.models.embed_content()`, the response structure shows:

```python
EmbedContentResponse(
    embeddings=[ContentEmbedding(values=[...])],
    metadata=None  # <-- Always None for AI Studio
)
```

This is a known limitation of the AI Studio (non-Vertex) endpoint. The Vertex AI endpoint may return metadata, but we're using AI Studio.

## Impact

- **Token tracking**: We cannot accurately track `prompt_tokens` or `total_tokens` for embedding calls.
- **Cost calculation**: Since cost is computed from token counts, `cost_usd` is always `None` for embeddings.
- **Usage analytics**: Embedding usage is underrepresented in usage reports.

## Current Behavior

The `EmbeddingService._record_usage()` currently records:

- ✅ `input_chars` — Character count of input text
- ✅ `operation`, `provider`, `model`, `status`
- ❌ `prompt_tokens` — Always None
- ❌ `total_tokens` — Always None
- ❌ `cost_usd` — Always None (depends on token counts)

---

## Proposed Solutions

### Option 1: Estimate Tokens from Characters (Recommended)

Most tokenizers use approximately **4 characters per token** on average for English text. We can estimate:

```python
estimated_tokens = max(1, input_chars // 4)
```

**Pros:**

- Simple to implement
- Provides reasonable cost estimates for billing purposes
- No external dependencies

**Cons:**

- Not exact — can vary by language and content type
- May over/underestimate by 10-30%

**Implementation:**

```python
def _record_usage(self, ..., input_chars: int, ...):
    # Estimate tokens if not provided by API
    prompt_tokens = usage_metadata.prompt_token_count if usage_metadata else None
    if prompt_tokens is None and input_chars:
        prompt_tokens = max(1, input_chars // 4)  # ~4 chars per token estimate

    total_tokens = usage_metadata.total_token_count if usage_metadata else prompt_tokens

    # Now cost can be computed...
```

---

### Option 2: Use Google's Tokenizer Library

Google provides `google-genai` tokenization via `client.models.count_tokens()`:

```python
response = await self._client.aio.models.count_tokens(
    model=self._settings.embedding_model,
    contents=text,
)
token_count = response.total_tokens
```

**Pros:**

- Exact token count
- Official Google implementation

**Cons:**

- Requires an extra API call per embedding request (doubles latency)
- Additional API quota usage
- More complex implementation

---

### Option 3: Use `billable_character_count`

The Vertex AI endpoint returns `billable_character_count` in metadata. For Vertex pricing, embeddings are billed per character, not per token.

**Pros:**

- Accurate for Vertex billing
- No estimation needed

**Cons:**

- Only available on Vertex AI, not AI Studio
- Different billing model (characters vs tokens)

---

### Option 4: Record Without Token Counts

Accept that embedding usage cannot have accurate token counts and update tests/analytics accordingly.

**Pros:**

- No estimation errors
- Honest data

**Cons:**

- Incomplete usage tracking
- Cost analytics are incomplete

---

## Recommendation

**Implement Option 1 (Estimate from Characters)** as the primary solution:

1. Simple and sufficient for cost tracking purposes
2. Provides reasonable accuracy for analytics
3. No additional API calls or dependencies
4. Can be refined later if needed

If exact counts become critical, Option 2 (tokenizer API) can be added as an opt-in feature.

## Action Items

- [ ] Update `EmbeddingService._record_usage()` to estimate tokens from `input_chars`
- [ ] Update tests to verify estimated tokens are recorded
- [ ] Document the estimation approach in code comments
- [ ] Consider adding a `tokens_estimated: bool` field to distinguish estimated vs actual counts
