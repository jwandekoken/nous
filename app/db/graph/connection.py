"""Graph database connection management."""

from app.core.settings import get_settings

from .client import GraphDB

# Global graph database instance
_graph_db: GraphDB | None = None


async def get_graph_db() -> GraphDB:
    """Get the graph database instance."""
    global _graph_db
    if _graph_db is None:
        settings = get_settings()
        _graph_db = GraphDB(
            base_url=settings.graph_api_url,
            username=settings.graph_api_username,
            password=settings.graph_api_password,
        )
        await _graph_db.connect()
    elif _graph_db._client is None:
        # Reconnect if client was closed
        await _graph_db.connect()

    return _graph_db


async def close_graph_db() -> None:
    """Close the graph database connection."""
    global _graph_db
    if _graph_db:
        await _graph_db.disconnect()
        _graph_db = None


async def reset_graph_db() -> None:
    """Reset the graph database connection for testing purposes."""
    global _graph_db
    if _graph_db:
        try:
            await _graph_db.disconnect()
        except Exception:
            pass  # Ignore errors during reset
        _graph_db = None
