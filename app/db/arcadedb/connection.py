"""ArcadeDB connection management."""

from app.core.settings import get_settings

from .client import GraphDB

# Global ArcadeDB instance
_arcadedb: GraphDB | None = None


async def get_graph_db() -> GraphDB:
    """Get the ArcadeDB instance."""
    global _arcadedb
    if _arcadedb is None:
        settings = get_settings()
        _arcadedb = GraphDB(
            base_url=settings.graph_api_url,
            username=settings.graph_api_username,
            password=settings.graph_api_password,
        )
        await _arcadedb.connect()
    elif _arcadedb._client is None:  # type: ignore[attr-defined]
        # Reconnect if client was closed
        await _arcadedb.connect()

    return _arcadedb


def get_database_name() -> str:
    """Get the configured ArcadeDB database name."""
    settings = get_settings()
    return settings.graph_database


async def close_graph_db() -> None:
    """Close the ArcadeDB connection."""
    global _arcadedb
    if _arcadedb:
        await _arcadedb.disconnect()
        _arcadedb = None


async def reset_graph_db() -> None:
    """Reset the ArcadeDB connection for testing purposes."""
    global _arcadedb
    if _arcadedb:
        try:
            await _arcadedb.disconnect()
        except Exception:
            pass  # Ignore errors during reset
        _arcadedb = None
