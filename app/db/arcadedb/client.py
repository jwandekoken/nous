"""Graph database client implementation."""

from collections.abc import Mapping
from typing import Any, TypedDict

import httpx
from httpx import BasicAuth


class ServerInfo(TypedDict):
    """Server information structure."""

    user: str
    version: str
    serverName: str


class GraphDB:
    """Graph database connection manager.
    This implementation connects to ArcadeDB through the ArcadeDB HTTP API.
    """

    def __init__(
        self, base_url: str, username: str | None = None, password: str | None = None
    ):
        self.base_url: str = base_url.rstrip("/")
        self.username: str | None = username
        self.password: str | None = password
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Connect to the ArcadeDB HTTP API server."""
        # Configure authentication if credentials are provided
        auth = None
        if self.username and self.password:
            auth = BasicAuth(self.username, self.password)

        self._client = httpx.AsyncClient(
            base_url=self.base_url, timeout=30.0, auth=auth
        )
        # Test the connection by getting server status
        is_ready = await self.is_server_ready()
        if not is_ready:
            raise RuntimeError("ArcadeDB server is not ready")

        auth_status = " with authentication" if auth else " without authentication"
        print(f"Connected to ArcadeDB HTTP API at {self.base_url}{auth_status}")

    async def disconnect(self) -> None:
        """Disconnect from the ArcadeDB HTTP API server."""
        if self._client:
            await self._client.aclose()
            self._client = None
            print("Disconnected from ArcadeDB HTTP API")

    async def is_server_ready(self) -> bool:
        """Get the status of the ArcadeDB server."""
        if not self._client:
            raise RuntimeError("Not connected to ArcadeDB HTTP API")

        response = await self._client.get("/api/v1/ready")

        if response.status_code == 204:
            return True
        else:
            return False

    async def get_server_info(self) -> ServerInfo:
        """Get the server information from ArcadeDB."""
        if not self._client:
            raise RuntimeError("Not connected to ArcadeDB HTTP API")

        response = await self._client.get("/api/v1/server?mode=basic")
        _ = response.raise_for_status()  # Validate response status

        # Handle different response formats
        try:
            data: dict[str, Any] = response.json()
            # Extract the required fields from the server response
            return {
                "user": data.get("user", ""),
                "version": data.get("version", ""),
                "serverName": data.get("serverName", ""),
            }
        except Exception:
            # If not JSON or parsing fails, return empty values
            return {"user": "", "version": "", "serverName": ""}

    async def execute_query(
        self,
        query: str,
        database: str,
        parameters: Any | None = None,
        language: str = "sql",
    ) -> Any:
        """Execute a query using ArcadeDB HTTP API.

        Args:
            query: The command/query to execute
            database: The database name
            parameters: Optional map of parameters to pass to the query engine
            language: The query language used (default: "sql")
                     Supported values: "sql", "sqlscript", "graphql", "cypher", "gremlin", "mongo"
                     and any other language supported by ArcadeDB and available at runtime.
        """

        if not self._client:
            raise RuntimeError("Not connected to ArcadeDB HTTP API")

        request_data: dict[str, str | Mapping[str, str | int | float | bool | None]] = {
            "language": language,
            "command": query,
            "params": parameters if parameters else {},
        }

        response = await self._client.post(
            f"/api/v1/query/{database}",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        _ = response.raise_for_status()  # Validate response status

        # Handle different response formats
        try:
            response_json = response.json()
            return response_json
        except Exception:
            # If not JSON, return the text response
            return {"result": response.text}

    async def execute_command(
        self,
        command: str,
        database: str,
        parameters: Any | None = None,
    ) -> Any:
        """Execute a database command (CREATE, UPDATE, DELETE, etc.) using ArcadeDB HTTP API."""

        if not self._client:
            raise RuntimeError("Not connected to ArcadeDB HTTP API")

        request_data: dict[str, str | Mapping[str, str | int | float | bool | None]] = {
            "command": command
        }
        if parameters:
            request_data["params"] = parameters

        response = await self._client.post(
            f"/api/v1/command/{database}",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        _ = response.raise_for_status()  # Validate response status

        # Handle different response formats
        try:
            response_json = response.json()
            return response_json
        except Exception:
            # If not JSON, return the text response
            return {"result": response.text}
