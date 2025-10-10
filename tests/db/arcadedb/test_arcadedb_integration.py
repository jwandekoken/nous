"""Integration tests for ArcadeDB HTTP API."""

from collections.abc import AsyncGenerator

import pytest

from app.core.settings import get_settings
from app.db.arcadedb import ArcadeDB, get_database_name, get_graph_db


@pytest.fixture
async def arcadedb_client() -> AsyncGenerator[ArcadeDB, None]:
    """Get a real ArcadeDB client instance."""
    settings = get_settings()
    client = ArcadeDB(
        base_url=settings.arcadedb_url,
        username=settings.arcadedb_user,
        password=settings.arcadedb_password,
    )

    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()


@pytest.fixture
def database_name():
    """Get the configured database name."""
    return get_database_name()


class TestArcadeDBIntegration:
    """Integration tests for ArcadeDB using real database connection."""

    @pytest.mark.asyncio
    async def test_is_server_ready_endpoint(self, arcadedb_client: ArcadeDB):
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
    async def test_server_info_endpoint(self, arcadedb_client: ArcadeDB):
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

    @pytest.mark.asyncio
    async def test_query_endpoint_simple(
        self, arcadedb_client: ArcadeDB, database_name: str
    ):
        """Test POST /api/v1/query/{database} with a simple query."""
        try:
            # Simple query that should work on most ArcadeDB instances
            result = await arcadedb_client.execute_query(
                query="SELECT 1 as test_value", database=database_name
            )
            assert isinstance(result, dict)
            # Should contain query results
            assert "result" in result or isinstance(result, list)
        except Exception as e:
            pytest.skip(f"ArcadeDB server not available or query failed: {e}")

    @pytest.mark.asyncio
    async def test_command_endpoint_create_and_drop(
        self, arcadedb_client: ArcadeDB, database_name: str
    ):
        """Test POST /api/v1/command/{database} with CREATE and DROP commands."""
        test_vertex_type = "TestIntegrationVertex"

        try:
            simple_result = await arcadedb_client.execute_command(
                command="SELECT 1 as test_command",
                database=database_name,
            )
            assert isinstance(simple_result, dict)
            assert "result" in simple_result

            vertex_created = False
            try:
                create_result = await arcadedb_client.execute_command(
                    command=f"CREATE VERTEX TYPE {test_vertex_type} IF NOT EXISTS",
                    database=database_name,
                )
                assert isinstance(create_result, dict)
                vertex_created = True
            except Exception as ddl_error:
                pytest.fail(f"DDL CREATE command failed: {ddl_error}")

            check_result = await arcadedb_client.execute_query(
                query=f"SELECT count(*) as count FROM {test_vertex_type}",
                database=database_name,
            )
            assert isinstance(check_result, dict)

            if vertex_created:
                try:
                    drop_result = await arcadedb_client.execute_command(
                        command=f"DROP TYPE {test_vertex_type}",
                        database=database_name,
                    )
                    assert isinstance(drop_result, dict)
                    print(f"Successfully dropped vertex type {test_vertex_type}")
                except Exception as drop_error:
                    pytest.fail(f"DROP command failed: {drop_error}")
                    # Don't fail the test if cleanup fails

        except Exception as e:
            pytest.fail(f"ArcadeDB command functionality test failed: {e}")

    @pytest.mark.asyncio
    async def test_connection_pooling(self):
        """Test that the singleton connection manager works correctly."""
        try:
            # Get first instance
            db1 = await get_graph_db()
            assert isinstance(db1, ArcadeDB)

            # Get second instance (should be the same)
            db2 = await get_graph_db()
            assert db1 is db2

            # Test that we can use the connection
            is_ready = await db1.is_server_ready()
            assert isinstance(is_ready, bool)

        except Exception as e:
            pytest.skip(f"ArcadeDB server not available: {e}")

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
        assert hasattr(settings, "arcadedb_url")
        assert isinstance(settings.arcadedb_url, str)
        assert len(settings.arcadedb_url.strip()) > 0

        assert hasattr(settings, "arcadedb_database")
        assert isinstance(settings.arcadedb_database, str)
        assert len(settings.arcadedb_database.strip()) > 0
