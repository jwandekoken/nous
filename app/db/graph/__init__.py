"""Graph database connection and utilities.
This example uses Neo4j as the graph database.
"""

from contextlib import asynccontextmanager
from typing import Any

from app.core.settings import get_settings

# Note: You would install neo4j driver with: uv add neo4j
# For now, we'll create a placeholder implementation


class GraphDB:
    """Graph database connection manager.
    This is a placeholder implementation for Neo4j.
    """

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: Any | None = None

    async def connect(self) -> None:
        """Connect to the graph database."""
        # In a real implementation, you would:
        # from neo4j import AsyncGraphDatabase
        # self._driver = AsyncGraphDatabase.driver(
        #     self.uri, auth=(self.user, self.password)
        # )
        print(f"Connected to graph database at {self.uri}")

    async def disconnect(self) -> None:
        """Disconnect from the graph database."""
        if self._driver:
            # await self._driver.close()
            print("Disconnected from graph database")

    @asynccontextmanager
    async def session(self):
        """Get a database session."""
        # In a real implementation:
        # async with self._driver.session() as session:
        #     yield session
        yield MockSession()

    async def execute_query(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> Any:
        """Execute a Cypher query."""
        async with self.session():
            # In a real implementation:
            # result = await session.run(query, parameters or {})
            # return await result.data()
            print(f"Executing query: {query} with params: {parameters}")
            return []


class MockSession:
    """Mock session for development."""

    async def run(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Mock query execution."""
        return MockResult()


class MockResult:
    """Mock result for development."""

    async def data(self) -> list[Any]:
        """Mock data return."""
        return []


# Global graph database instance
_graph_db: GraphDB | None = None


async def get_graph_db() -> GraphDB:
    """Get the graph database instance."""
    global _graph_db
    if _graph_db is None:
        settings = get_settings()
        _graph_db = GraphDB(
            uri=settings.graph_uri,
            user=settings.graph_user,
            password=settings.graph_password,
        )
        await _graph_db.connect()

    return _graph_db


async def close_graph_db() -> None:
    """Close the graph database connection."""
    global _graph_db
    if _graph_db:
        await _graph_db.disconnect()
        _graph_db = None
