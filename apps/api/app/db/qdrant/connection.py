"""Qdrant vector database connection management.

This module provides a singleton AsyncQdrantClient for vector operations.
Used primarily by the graph features for semantic memory operations.
"""

from qdrant_client import AsyncQdrantClient

from app.core.settings import get_settings

_client: AsyncQdrantClient | None = None


async def get_qdrant_client() -> AsyncQdrantClient:
    """Get the Qdrant client singleton.

    Returns:
        AsyncQdrantClient: The singleton Qdrant client instance.
    """
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )

    return _client


async def close_qdrant_client() -> None:
    """Close the Qdrant client connection."""
    global _client
    if _client:
        await _client.close()
        _client = None


async def reset_qdrant_client() -> None:
    """Reset the Qdrant client for testing purposes."""
    global _client
    if _client:
        try:
            await _client.close()
        except Exception:
            pass  # Ignore errors during reset
        _client = None
