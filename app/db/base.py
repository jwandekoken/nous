"""Base classes and protocols for database clients."""

from typing import Any, Protocol


class DatabaseClient(Protocol):
    """Protocol for a generic database client."""

    async def connect(self) -> None:
        """Connect to the database server."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the database server."""
        ...

    async def execute_query(
        self,
        query: str,
        database: str,
        parameters: dict[str, str | int | float | bool | None] | None = None,
        language: str = "sql",
    ) -> Any:
        """Execute a query."""
        ...

    async def execute_command(
        self,
        command: str,
        database: str,
        parameters: dict[str, Any] | None = None,
        language: str = "sql",
    ) -> Any:
        """Execute a command."""
        ...
