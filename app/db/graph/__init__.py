"""Graph database connection and utilities.
This implementation uses KuzuDB through the KuzuDB API server.
"""

from collections.abc import Mapping
from typing import Any

import httpx
from httpx import BasicAuth

from app.core.settings import get_settings


class GraphDB:
    """Graph database connection manager.
    This implementation connects to KuzuDB through the KuzuDB API server.
    """

    def __init__(
        self, base_url: str, username: str | None = None, password: str | None = None
    ):
        self.base_url: str = base_url.rstrip("/")
        self.username: str | None = username
        self.password: str | None = password
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Connect to the KuzuDB API server."""
        # Configure authentication if credentials are provided
        auth = None
        if self.username and self.password:
            auth = BasicAuth(self.username, self.password)

        self._client = httpx.AsyncClient(
            base_url=self.base_url, timeout=30.0, auth=auth
        )
        # Test the connection by getting server status
        _ = await self.get_server_status()
        auth_status = " with authentication" if auth else " without authentication"
        print(f"Connected to KuzuDB API server at {self.base_url}{auth_status}")

    async def disconnect(self) -> None:
        """Disconnect from the KuzuDB API server."""
        if self._client:
            await self._client.aclose()
            self._client = None
            print("Disconnected from KuzuDB API server")

    async def get_server_status(self) -> Any:
        """Get the status of the KuzuDB API server."""
        if not self._client:
            raise RuntimeError("Not connected to KuzuDB API server")

        response = await self._client.get("/")
        _ = response.raise_for_status()  # Validate response status
        return response.json()

    async def get_schema(self) -> Any:
        """Get the schema of the database."""
        if not self._client:
            raise RuntimeError("Not connected to KuzuDB API server")

        response = await self._client.get("/schema")
        _ = response.raise_for_status()  # Validate response status
        return response.json()

    async def execute_query(
        self,
        query: str,
        parameters: Any | None = None,
    ) -> Any:
        """Execute a Cypher query and get the result."""
        if not self._client:
            raise RuntimeError("Not connected to KuzuDB API server")

        request_data: dict[str, str | Mapping[str, str | int | float | bool | None]] = {
            "query": query
        }
        if parameters:
            request_data["params"] = parameters

        response = await self._client.post(
            "/cypher", json=request_data, headers={"Content-Type": "application/json"}
        )

        _ = response.raise_for_status()  # Validate response status
        response_json = response.json()
        return response_json


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

    return _graph_db


async def close_graph_db() -> None:
    """Close the graph database connection."""
    global _graph_db
    if _graph_db:
        await _graph_db.disconnect()
        _graph_db = None
