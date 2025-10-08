"""ArcadeDB connection management."""

from app.core.settings import get_settings

from .client import ArcadeDB

# Global ArcadeDB instance
_arcadedb: ArcadeDB | None = None


async def get_graph_db() -> ArcadeDB:
    """Get the graph database client as a dependency."""
    global _arcadedb
    if _arcadedb is None:
        settings = get_settings()
        _arcadedb = ArcadeDB(
            base_url=settings.arcadedb_url,
            username=settings.arcadedb_user,
            password=settings.arcadedb_password,
        )
        await _arcadedb.connect()
    elif not _arcadedb.is_connected:
        # Reconnect if client was closed
        await _arcadedb.connect()

    return _arcadedb


def get_database_name() -> str:
    """Get the configured ArcadeDB database name."""
    settings = get_settings()
    return settings.arcadedb_database


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
