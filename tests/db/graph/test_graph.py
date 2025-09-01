"""Tests for the KuzuDB graph database connection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import BasicAuth

from app.core.settings import Settings
from app.db.graph import GraphDB, close_graph_db, get_graph_db


class TestGraphDB:
    """Test cases for GraphDB class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.graph_api_url = "http://localhost:8000"
        settings.graph_api_username = None
        settings.graph_api_password = None
        return settings

    @pytest.fixture
    def graph_db(self):
        """Create a GraphDB instance for testing."""
        return GraphDB(base_url="http://localhost:8000", username=None, password=None)

    @pytest.fixture
    def graph_db_with_auth(self):
        """Create a GraphDB instance with authentication for testing."""
        return GraphDB(
            base_url="http://localhost:8000", username="testuser", password="testpass"
        )

    @pytest.mark.asyncio
    async def test_connect_without_auth(self, graph_db):
        """Test connecting to KuzuDB API server without authentication."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "version": "0.3.1"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await graph_db.connect()

            # Verify AsyncClient was created with correct parameters
            mock_client_class.assert_called_once_with(
                base_url="http://localhost:8000", timeout=30.0, auth=None
            )

            # Verify connection test was made
            mock_client.get.assert_called_once_with("/")

    @pytest.mark.asyncio
    async def test_connect_with_auth(self, graph_db_with_auth):
        """Test connecting to KuzuDB API server with authentication."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "version": "0.3.1"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await graph_db_with_auth.connect()

            # Verify AsyncClient was created with authentication
            call_args = mock_client_class.call_args
            assert call_args[1]["base_url"] == "http://localhost:8000"
            assert call_args[1]["timeout"] == 30.0
            assert isinstance(call_args[1]["auth"], BasicAuth)
            # Verify BasicAuth was created with correct credentials
            auth_header = call_args[1]["auth"]._auth_header
            assert (
                auth_header == "Basic dGVzdHVzZXI6dGVzdHBhc3M="
            )  # base64 encoded "testuser:testpass"

    @pytest.mark.asyncio
    async def test_disconnect(self, graph_db):
        """Test disconnecting from KuzuDB API server."""
        mock_client = AsyncMock()
        graph_db._client = mock_client

        await graph_db.disconnect()

        mock_client.aclose.assert_called_once()
        assert graph_db._client is None

    @pytest.mark.asyncio
    async def test_disconnect_without_client(self, graph_db):
        """Test disconnecting when no client is connected."""
        graph_db._client = None

        # Should not raise any exception
        await graph_db.disconnect()

    @pytest.mark.asyncio
    async def test_get_server_status(self, graph_db):
        """Test getting server status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "version": "0.3.1"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        graph_db._client = mock_client

        result = await graph_db.get_server_status()

        assert result == {"status": "ok", "version": "0.3.1"}
        mock_client.get.assert_called_once_with("/")

    @pytest.mark.asyncio
    async def test_get_server_status_without_client(self, graph_db):
        """Test getting server status when not connected."""
        graph_db._client = None

        with pytest.raises(RuntimeError, match="Not connected to KuzuDB API server"):
            await graph_db.get_server_status()

    @pytest.mark.asyncio
    async def test_get_graph_db_singleton(self, mock_settings):
        """Test that get_graph_db returns a singleton instance."""
        with (
            patch("app.db.graph.connection.get_settings", return_value=mock_settings),
            patch.object(GraphDB, "connect", new_callable=AsyncMock),
        ):
            # First call should create a new instance
            db1 = await get_graph_db()
            assert isinstance(db1, GraphDB)
            assert db1.base_url == "http://localhost:8000"
            assert db1.username is None
            assert db1.password is None

            # Second call should return the same instance
            db2 = await get_graph_db()
            assert db1 is db2

    @pytest.mark.asyncio
    async def test_close_graph_db(self, mock_settings):
        """Test closing the graph database connection."""
        mock_db = AsyncMock()
        mock_db.disconnect = AsyncMock()

        with (
            patch("app.db.graph.connection.get_settings", return_value=mock_settings),
            patch("app.db.graph.connection._graph_db", mock_db),
        ):
            await close_graph_db()

            mock_db.disconnect.assert_called_once()
            # Check that the global instance is reset to None
            from app.db.graph.connection import _graph_db

            assert _graph_db is None

    @pytest.mark.asyncio
    async def test_close_graph_db_without_instance(self):
        """Test closing when no graph database instance exists."""
        with patch("app.db.graph.connection._graph_db", None):
            # Should not raise any exception
            await close_graph_db()
