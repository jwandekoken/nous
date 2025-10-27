"""Integration tests for the ListApiKeysUseCase."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import UserRole
from app.features.auth.dtos import CreateApiKeyRequest
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.create_api_key_usecase import CreateApiKeyUseCaseImpl
from app.features.auth.usecases.list_api_keys_usecase import ListApiKeysUseCaseImpl
from app.features.auth.usecases.signup_tenant_usecase import PasswordHasher

# All fixtures are now provided by tests/conftest.py


class TestListApiKeysUseCase:
    """Test suite for the ListApiKeysUseCase."""

    async def test_list_api_keys_empty(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test listing API keys for a tenant with no keys returns empty list."""

        # Arrange - Create a tenant and user first (no API keys)
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_123")
            db_session.add(tenant)
            await db_session.flush()

            user_model = User(
                email="user@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add(user_model)
            await db_session.flush()

        use_case = ListApiKeysUseCaseImpl(get_db_session=lambda: db_session)

        # Act
        response = await use_case.execute(tenant.id)

        # Assert
        assert response.api_keys == []

    async def test_list_api_keys_populated(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test listing API keys for a tenant with multiple keys."""

        # Arrange - Create a tenant and user first
        async with db_session.begin():
            tenant = Tenant(name="test-tenant", age_graph_name="test_graph_456")
            db_session.add(tenant)
            await db_session.flush()

            user_model = User(
                email="user@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add(user_model)
            await db_session.flush()

        # Create multiple API keys using the create use case
        create_use_case = CreateApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        api_key_names = ["key1", "key2", "key3"]
        created_keys = []

        for name in api_key_names:
            request = CreateApiKeyRequest(name=name)
            response = await create_use_case.execute(request, tenant.id)
            created_keys.append(response)

        list_use_case = ListApiKeysUseCaseImpl(get_db_session=lambda: db_session)

        # Act
        response = await list_use_case.execute(tenant.id)

        # Assert
        assert len(response.api_keys) == 3

        # Check that all created keys are in the response
        response_names = {key.name for key in response.api_keys}
        assert response_names == set(api_key_names)

        response_prefixes = {key.key_prefix for key in response.api_keys}
        created_prefixes = {key.key_prefix for key in created_keys}
        assert response_prefixes == created_prefixes

        # Check that all keys have required fields
        for api_key_info in response.api_keys:
            assert api_key_info.id is not None
            assert api_key_info.name is not None
            assert api_key_info.key_prefix is not None
            assert api_key_info.created_at is not None
            # expires_at and last_used_at can be None

    async def test_list_api_keys_tenant_isolation(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that tenants only see their own API keys."""

        # Arrange - Create two tenants and users
        async with db_session.begin():
            tenant1 = Tenant(name="tenant1", age_graph_name="test_graph_789")
            tenant2 = Tenant(name="tenant2", age_graph_name="test_graph_101")
            db_session.add_all([tenant1, tenant2])
            await db_session.flush()

            user1_model = User(
                email="user1@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant1.id,
                role=UserRole.TENANT_USER,
            )
            user2_model = User(
                email="user2@example.com",
                hashed_password=password_hasher.hash("userpass"),
                tenant_id=tenant2.id,
                role=UserRole.TENANT_USER,
            )
            db_session.add_all([user1_model, user2_model])
            await db_session.flush()

        # Create API keys for both tenants
        create_use_case = CreateApiKeyUseCaseImpl(get_db_session=lambda: db_session)

        # Create keys for tenant1
        request1 = CreateApiKeyRequest(name="tenant1-key")
        await create_use_case.execute(request1, tenant1.id)

        # Create keys for tenant2
        request2a = CreateApiKeyRequest(name="tenant2-key-a")
        request2b = CreateApiKeyRequest(name="tenant2-key-b")
        await create_use_case.execute(request2a, tenant2.id)
        await create_use_case.execute(request2b, tenant2.id)

        list_use_case = ListApiKeysUseCaseImpl(get_db_session=lambda: db_session)

        # Act - List keys for tenant1
        response1 = await list_use_case.execute(tenant1.id)

        # List keys for tenant2
        response2 = await list_use_case.execute(tenant2.id)

        # Assert - tenant1 should only see their 1 key
        assert len(response1.api_keys) == 1
        assert response1.api_keys[0].name == "tenant1-key"

        # tenant2 should only see their 2 keys
        assert len(response2.api_keys) == 2
        response2_names = {key.name for key in response2.api_keys}
        assert response2_names == {"tenant2-key-a", "tenant2-key-b"}
