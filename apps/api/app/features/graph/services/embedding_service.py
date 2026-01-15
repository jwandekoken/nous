"""Embedding service using Google's Gemini embedding model.

This module provides text embedding functionality for semantic memory operations,
using the google-genai SDK directly for full usage metadata access.
"""

from dataclasses import dataclass

from google import genai
from google.genai import types

from app.core.settings import Settings
from app.features.usage.pricing import cost_usd_for_embedding
from app.features.usage.tracker import (
    TokenUsageRecord,
    TokenUsageTracker,
    get_token_usage_tracker,
)


@dataclass
class EmbeddingUsageMetadata:
    """Usage metadata from embedding API call."""

    prompt_token_count: int | None = None
    total_token_count: int | None = None
    billable_character_count: int | None = None


@dataclass
class EmbeddingResult:
    """Result of a single embedding operation with usage metadata."""

    embedding: list[float]
    usage_metadata: EmbeddingUsageMetadata | None = None


@dataclass
class EmbeddingBatchResult:
    """Result of batch embedding operation with usage metadata."""

    embeddings: list[list[float]]
    usage_metadata: EmbeddingUsageMetadata | None = None


class EmbeddingService:
    """Service for generating text embeddings using Google's Gemini model.

    This service uses the google-genai SDK directly to access usage metadata
    for token tracking.
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the embedding service.

        Args:
            settings: Optional settings instance. If not provided, a new one will be created.

        Raises:
            ValueError: If GOOGLE_API_KEY is not set.
        """
        self._settings = settings or Settings()
        if not self._settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        self._client: genai.Client = genai.Client(api_key=self._settings.google_api_key)

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension for this service.

        Returns:
            The embedding vector dimension (default 768, configurable via settings).
        """
        return self._settings.embedding_dim

    async def embed_text(
        self,
        text: str,
        *,
        operation: str = "embed",
        tracker: TokenUsageTracker | None = None,
    ) -> EmbeddingResult:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed.
            operation: Operation name for usage tracking (e.g., "semantic_memory_embed").
            tracker: Optional usage tracker. If None and usage tracking is enabled,
                     uses the default tracker.

        Returns:
            EmbeddingResult containing the embedding vector and usage metadata.
        """
        config = types.EmbedContentConfig(
            output_dimensionality=self._settings.embedding_dim,
        )

        response = await self._client.aio.models.embed_content(
            model=self._settings.embedding_model,
            contents=text,
            config=config,
        )

        # Extract usage metadata if available
        usage_metadata = self._extract_usage_metadata(response)

        # Record usage if tracker provided
        await self._record_usage(
            tracker=tracker,
            operation=operation,
            usage_metadata=usage_metadata,
            input_chars=len(text),
            status="ok",
        )

        # Extract embedding values
        embedding = response.embeddings[0].values if response.embeddings else []

        return EmbeddingResult(
            embedding=list(embedding) if embedding else [],
            usage_metadata=usage_metadata,
        )

    async def embed_texts(
        self,
        texts: list[str],
        *,
        operation: str = "embed_batch",
        tracker: TokenUsageTracker | None = None,
    ) -> EmbeddingBatchResult:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: The list of texts to embed.
            operation: Operation name for usage tracking.
            tracker: Optional usage tracker.

        Returns:
            EmbeddingBatchResult containing embedding vectors and usage metadata.
        """
        if not texts:
            return EmbeddingBatchResult(embeddings=[], usage_metadata=None)

        config = types.EmbedContentConfig(
            output_dimensionality=self._settings.embedding_dim,
        )

        response = await self._client.aio.models.embed_content(
            model=self._settings.embedding_model,
            contents=texts,
            config=config,
        )

        # Extract usage metadata
        usage_metadata = self._extract_usage_metadata(response)

        # Record usage
        await self._record_usage(
            tracker=tracker,
            operation=operation,
            usage_metadata=usage_metadata,
            input_chars=sum(len(t) for t in texts),
            status="ok",
        )

        # Extract all embeddings
        embeddings = [
            list(emb.values) if emb.values else []
            for emb in (response.embeddings or [])
        ]

        return EmbeddingBatchResult(
            embeddings=embeddings,
            usage_metadata=usage_metadata,
        )

    def _extract_usage_metadata(
        self, response: types.EmbedContentResponse
    ) -> EmbeddingUsageMetadata | None:
        """Extract usage metadata from the API response."""
        if response.metadata is None:
            return None

        return EmbeddingUsageMetadata(
            billable_character_count=response.metadata.billable_character_count,
        )

    async def _record_usage(
        self,
        *,
        tracker: TokenUsageTracker | None,
        operation: str,
        usage_metadata: EmbeddingUsageMetadata | None,
        input_chars: int,
        status: str,
        error_type: str | None = None,
    ) -> None:
        """Record embedding usage event."""
        # Resolve tracker if not provided
        if tracker is None:
            tracker = get_token_usage_tracker()

        # Extract token counts from usage metadata
        prompt_tokens = usage_metadata.prompt_token_count if usage_metadata else None
        total_tokens = usage_metadata.total_token_count if usage_metadata else None

        # Compute cost
        cost_usd = None
        model_pricing = self._settings.model_pricing.get(self._settings.embedding_model)
        if model_pricing and "per_1m_tokens" in model_pricing:
            cost_usd = cost_usd_for_embedding(
                total_tokens=total_tokens,
                per_1m_tokens=model_pricing.get("per_1m_tokens", 0.0),
            )

        try:
            await tracker.record(
                TokenUsageRecord(
                    feature="graph",
                    operation=operation,
                    provider="google",
                    model=self._settings.embedding_model,
                    prompt_tokens=prompt_tokens,
                    total_tokens=total_tokens,
                    input_chars=input_chars,
                    cost_usd=cost_usd,
                    status=status,
                    error_type=error_type,
                )
            )
        except Exception:
            # Never let usage tracking fail the main request
            pass
