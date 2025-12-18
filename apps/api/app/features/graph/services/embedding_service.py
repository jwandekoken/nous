"""Embedding service using Google's Gemini embedding model.

This module provides text embedding functionality for semantic memory operations,
wrapping the langchain-google-genai embeddings for async usage.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr

from app.core.settings import Settings


class EmbeddingService:
    """Service for generating text embeddings using Google's Gemini model.

    This service wraps the GoogleGenerativeAIEmbeddings from langchain-google-genai
    and provides an async interface for embedding text.
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

        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=self._settings.embedding_model,
            google_api_key=SecretStr(self._settings.google_api_key),
        )

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension for this service.

        Returns:
            The embedding vector dimension (768 for gemini-embedding-001).
        """
        return self._settings.embedding_dim

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector (768 dimensions).
        """
        # GoogleGenerativeAIEmbeddings.aembed_query is the async method
        embedding = await self._embeddings.aembed_query(text)
        return embedding

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: The list of texts to embed.

        Returns:
            A list of embedding vectors.
        """
        # GoogleGenerativeAIEmbeddings.aembed_documents is the async batch method
        embeddings = await self._embeddings.aembed_documents(texts)
        return embeddings
