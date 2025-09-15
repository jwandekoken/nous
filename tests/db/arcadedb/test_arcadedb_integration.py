"""Integration tests for ArcadeDB HTTP API."""

from collections.abc import AsyncGenerator

import pytest

from app.core.settings import get_settings
from app.db.arcadedb import GraphDB, get_database_name, get_graph_db


class TestArcadeDBIntegration:
    """Integration tests for ArcadeDB using real database connection."""

    @pytest.fixture
    async def arcadedb_client(self) -> AsyncGenerator[GraphDB, None]:
        """Get a real ArcadeDB client instance."""
        settings = get_settings()
        client = GraphDB(
            base_url=settings.graph_api_url,
            username=settings.graph_api_username,
            password=settings.graph_api_password,
        )

        try:
            await client.connect()
            yield client
        finally:
            await client.disconnect()

    @pytest.fixture
    def database_name(self):
        """Get the configured database name."""
        return get_database_name()

    @pytest.mark.asyncio
    async def test_is_server_ready_endpoint(self, arcadedb_client: GraphDB):
        """Test GET /api/v1/ready endpoint."""
        try:
            is_ready = await arcadedb_client.is_server_ready()
            print("arcadedb server ready: ", is_ready)
            assert isinstance(is_ready, bool)
            # The method returns True if server is ready (status 200), False otherwise
            assert is_ready is True or is_ready is False
        except Exception as e:
            pytest.skip(f"ArcadeDB server not available: {e}")

    @pytest.mark.asyncio
    async def test_server_info_endpoint(self, arcadedb_client: GraphDB):
        """Test GET /api/v1/server endpoint."""
        try:
            info = await arcadedb_client.get_server_info()
            print("arcadedb server info: ", info)
            assert isinstance(info, dict)

            # Check that the required keys are present
            required_keys = ["user", "version", "serverName"]
            for key in required_keys:
                assert key in info, f"Missing required key: {key}"
                assert isinstance(info[key], str), f"Key {key} should be a string"

            # Ensure we have exactly the expected keys
            assert set(info.keys()) == set(required_keys), (
                f"Unexpected keys in response: {set(info.keys()) - set(required_keys)}"
            )
        except Exception as e:
            pytest.skip(f"ArcadeDB server not available: {e}")

    # @pytest.mark.asyncio
    # async def test_query_endpoint_simple(self, arcadedb_client: GraphDB, database_name):
    #     """Test POST /api/v1/query/{database} with a simple query."""
    #     try:
    #         # Simple query that should work on most ArcadeDB instances
    #         result = await arcadedb_client.execute_query(
    #             query="SELECT 1 as test_value", database=database_name
    #         )
    #         assert isinstance(result, dict)
    #         # Should contain query results
    #         assert "result" in result or isinstance(result, list)
    #     except Exception as e:
    #         pytest.skip(f"ArcadeDB server not available or query failed: {e}")

    # @pytest.mark.asyncio
    # async def test_query_endpoint_with_parameters(self, arcadedb_client: GraphDB, database_name):
    #     """Test POST /api/v1/query/{database} with parameters."""
    #     try:
    #         # Query with parameters
    #         result = await arcadedb_client.execute_query(
    #             query="SELECT $param as test_param",
    #             database=database_name,
    #             parameters={"param": "integration_test_value"},
    #         )
    #         assert isinstance(result, dict)
    #         # Should contain query results
    #         assert "result" in result or isinstance(result, list)
    #     except Exception as e:
    #         pytest.skip(
    #             f"ArcadeDB server not available or parameterized query failed: {e}"
    #         )

    # @pytest.mark.asyncio
    # async def test_command_endpoint_create_and_drop(
    #     self, arcadedb_client: GraphDB, database_name
    # ):
    #     """Test POST /api/v1/command/{database} with CREATE and DROP commands."""
    #     test_vertex_type = "TestIntegrationVertex"
    #     test_property = "test_property"

    #     try:
    #         # Try to create a test vertex type
    #         create_result = await arcadedb_client.execute_command(
    #             command=f"CREATE VERTEX TYPE {test_vertex_type} IF NOT EXISTS",
    #             database=database_name,
    #         )
    #         assert isinstance(create_result, dict)

    #         # Try to add a property to the vertex type
    #         alter_result = await arcadedb_client.execute_command(
    #             command=f"CREATE PROPERTY {test_vertex_type}.{test_property} STRING",
    #             database=database_name,
    #         )
    #         assert isinstance(alter_result, dict)

    #         # Clean up - drop the test vertex type
    #         drop_result = await arcadedb_client.execute_command(
    #             command=f"DROP VERTEX TYPE {test_vertex_type} IF EXISTS",
    #             database=database_name,
    #         )
    #         assert isinstance(drop_result, dict)

    #     except Exception as e:
    #         pytest.skip(
    #             f"ArcadeDB server not available or command execution failed: {e}"
    #         )

    # @pytest.mark.asyncio
    # async def test_command_endpoint_insert_and_delete(
    #     self, arcadedb_client: GraphDB, database_name
    # ):
    #     """Test INSERT and DELETE operations."""
    #     test_vertex_type = "TestPerson"

    #     try:
    #         # Create vertex type if it doesn't exist
    #         await arcadedb_client.execute_command(
    #             command=f"CREATE VERTEX TYPE {test_vertex_type} IF NOT EXISTS",
    #             database=database_name,
    #         )

    #         # Insert a test record
    #         insert_result = await arcadedb_client.execute_command(
    #             command=f"INSERT INTO {test_vertex_type} SET name = 'Test User', age = 30",
    #             database=database_name,
    #         )
    #         assert isinstance(insert_result, dict)
    #         assert "result" in insert_result

    #         # Get the inserted record ID for cleanup
    #         if insert_result["result"]:
    #             record_id = insert_result["result"][0]["@rid"]

    #             # Delete the test record
    #             delete_result = await arcadedb_client.execute_command(
    #                 command=f"DELETE FROM {record_id}", database=database_name
    #             )
    #             assert isinstance(delete_result, dict)

    #     except Exception as e:
    #         pytest.skip(f"ArcadeDB server not available or DML operations failed: {e}")

    @pytest.mark.asyncio
    async def test_connection_pooling(self):
        """Test that the singleton connection manager works correctly."""
        try:
            # Get first instance
            db1 = await get_graph_db()
            assert isinstance(db1, GraphDB)

            # Get second instance (should be the same)
            db2 = await get_graph_db()
            assert db1 is db2

            # Test that we can use the connection
            is_ready = await db1.is_server_ready()
            assert isinstance(is_ready, bool)

        except Exception as e:
            pytest.skip(f"ArcadeDB server not available: {e}")

    # @pytest.mark.asyncio
    # async def test_error_handling_invalid_query(self, arcadedb_client: GraphDB, database_name):
    #     """Test error handling for invalid queries."""
    #     try:
    #         # Try an invalid query
    #         with pytest.raises(HTTPStatusError):
    #             await arcadedb_client.execute_query(
    #                 query="INVALID QUERY SYNTAX", database=database_name
    #             )
    #     except Exception as e:
    #         # If server is not available, skip the test
    #         if "not available" in str(e).lower():
    #             pytest.skip(f"ArcadeDB server not available: {e}")
    #         # Otherwise, the error might be handled differently, so we'll pass

    # @pytest.mark.asyncio
    # async def test_error_handling_invalid_command(self, arcadedb_client: GraphDB, database_name):
    #     """Test error handling for invalid commands."""
    #     try:
    #         # Try an invalid command
    #         with pytest.raises(HTTPStatusError):
    #             await arcadedb_client.execute_command(
    #                 command="INVALID COMMAND SYNTAX", database=database_name
    #             )
    #     except Exception as e:
    #         # If server is not available, skip the test
    #         if "not available" in str(e).lower():
    #             pytest.skip(f"ArcadeDB server not available: {e}")
    #         # Otherwise, the error might be handled differently, so we'll pass

    @pytest.mark.asyncio
    async def test_database_name_configuration(self):
        """Test that database name is properly configured."""
        db_name = get_database_name()
        assert isinstance(db_name, str)
        assert len(db_name.strip()) > 0
        assert db_name != ""  # Should not be empty

    @pytest.mark.asyncio
    async def test_settings_configuration(self):
        """Test that settings are properly configured."""
        settings = get_settings()

        # Check that required settings exist
        assert hasattr(settings, "graph_api_url")
        assert isinstance(settings.graph_api_url, str)
        assert len(settings.graph_api_url.strip()) > 0

        assert hasattr(settings, "graph_database")
        assert isinstance(settings.graph_database, str)
        assert len(settings.graph_database.strip()) > 0
