"""Integration tests for the ListUsersUseCase."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import AuthenticatedUser, UserRole
from app.features.auth.dtos import ListUsersRequest
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.users.list_users_usecase import ListUsersUseCaseImpl

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestListUsersUseCase:
    """Test suite for the ListUsersUseCase."""

    async def test_list_users_successfully(
        self,
        db_session: AsyncSession,
    ):
        """Test the successful listing of users with pagination."""
        # Arrange - Create a tenant and some users
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        user1 = User(
            email="alice@example.com",
            hashed_password="hash1",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        user2 = User(
            email="bob@example.com",
            hashed_password="hash2",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        user3 = User(
            email="charlie@example.com",
            hashed_password="hash3",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([user1, user2, user3])
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=user1.id,
            email=user1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = ListUsersRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="email",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 3
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1
        assert len(response.users) == 3

        # Check ordering by email ascending
        assert response.users[0].email == "alice@example.com"
        assert response.users[0].role == UserRole.TENANT_ADMIN
        assert response.users[1].email == "bob@example.com"
        assert response.users[1].role == UserRole.TENANT_USER
        assert response.users[2].email == "charlie@example.com"

    async def test_list_users_with_pagination(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users with pagination."""
        # Arrange - Create a tenant and 5 users
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        users = []
        for i in range(5):
            user = User(
                email=f"user{i:02d}@example.com",
                hashed_password=f"hash{i}",
                tenant_id=tenant.id,
                role=UserRole.TENANT_USER,
            )
            users.append(user)
            db_session.add(user)
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=users[0].id,
            email=users[0].email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Test page 1 with page_size 2
        request = ListUsersRequest(
            page=1,
            page_size=2,
            search=None,
            sort_by="email",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 5
        assert response.page == 1
        assert response.page_size == 2
        assert response.total_pages == 3  # ceil(5/2) = 3
        assert len(response.users) == 2
        assert response.users[0].email == "user00@example.com"
        assert response.users[1].email == "user01@example.com"

    async def test_list_users_with_search(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users with search filtering."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        user1 = User(
            email="alice@example.com",
            hashed_password="hash1",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        user2 = User(
            email="bob@example.com",
            hashed_password="hash2",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        user3 = User(
            email="alice@other.com",
            hashed_password="hash3",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([user1, user2, user3])
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=user1.id,
            email=user1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Search for "alice"
        request = ListUsersRequest(
            page=1,
            page_size=10,
            search="alice",
            sort_by="email",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 2
        assert len(response.users) == 2
        assert response.users[0].email == "alice@example.com"
        assert response.users[1].email == "alice@other.com"

    async def test_list_users_with_sorting_desc(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users with descending sort order."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        user1 = User(
            email="alice@example.com",
            hashed_password="hash1",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        user2 = User(
            email="bob@example.com",
            hashed_password="hash2",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        user3 = User(
            email="charlie@example.com",
            hashed_password="hash3",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([user1, user2, user3])
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=user1.id,
            email=user1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = ListUsersRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="email",
            sort_order="desc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 3
        assert len(response.users) == 3
        assert response.users[0].email == "charlie@example.com"
        assert response.users[1].email == "bob@example.com"
        assert response.users[2].email == "alice@example.com"

    async def test_list_users_sort_by_created_at(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users sorted by creation date."""
        # Arrange - Create users with a small delay to ensure different timestamps
        import asyncio

        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.commit()

        user1 = User(
            email="first@example.com",
            hashed_password="hash1",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        db_session.add(user1)
        await db_session.commit()
        await asyncio.sleep(0.01)  # Small delay

        user2 = User(
            email="second@example.com",
            hashed_password="hash2",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        db_session.add(user2)
        await db_session.commit()
        await asyncio.sleep(0.01)  # Small delay

        user3 = User(
            email="third@example.com",
            hashed_password="hash3",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        db_session.add(user3)
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=user1.id,
            email=user1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = ListUsersRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="created_at",
            sort_order="desc",  # Most recent first
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 3
        assert len(response.users) == 3
        assert response.users[0].email == "third@example.com"  # Most recent
        assert response.users[1].email == "second@example.com"
        assert response.users[2].email == "first@example.com"  # Oldest

    async def test_list_users_tenant_scoping(
        self,
        db_session: AsyncSession,
    ):
        """Test that users from other tenants are not visible."""
        # Arrange - Create two tenants with users
        tenant1 = Tenant(name="tenant-1", age_graph_name="graph_1")
        tenant2 = Tenant(name="tenant-2", age_graph_name="graph_2")
        db_session.add_all([tenant1, tenant2])
        await db_session.flush()

        # Users in tenant 1
        user1 = User(
            email="user1@tenant1.com",
            hashed_password="hash1",
            tenant_id=tenant1.id,
            role=UserRole.TENANT_ADMIN,
        )
        user2 = User(
            email="user2@tenant1.com",
            hashed_password="hash2",
            tenant_id=tenant1.id,
            role=UserRole.TENANT_USER,
        )

        # Users in tenant 2
        user3 = User(
            email="user3@tenant2.com",
            hashed_password="hash3",
            tenant_id=tenant2.id,
            role=UserRole.TENANT_USER,
        )
        user4 = User(
            email="user4@tenant2.com",
            hashed_password="hash4",
            tenant_id=tenant2.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([user1, user2, user3, user4])
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Admin from tenant 1
        admin_user = AuthenticatedUser(
            user_id=user1.id,
            email=user1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant1.id,
        )

        request = ListUsersRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="email",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert - Should only see users from tenant 1
        assert response.total == 2
        assert len(response.users) == 2
        assert all("tenant1" in user.email for user in response.users)

    async def test_list_users_empty_result(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users when no users match the search."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        user1 = User(
            email="alice@example.com",
            hashed_password="hash1",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        user2 = User(
            email="bob@example.com",
            hashed_password="hash2",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([user1, user2])
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=user1.id,
            email=user1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Search for non-existent user
        request = ListUsersRequest(
            page=1,
            page_size=10,
            search="nonexistent",
            sort_by="email",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 0
        assert len(response.users) == 0
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 0

    async def test_list_users_no_users_in_tenant(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users when tenant has no users."""
        # Arrange - Create tenant without users
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.commit()

        use_case = ListUsersUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Create a fake admin user (not in DB)
        admin_user = AuthenticatedUser(
            user_id="00000000-0000-0000-0000-000000000000",
            email="admin@example.com",
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = ListUsersRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="email",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request, admin_user)

        # Assert
        assert response.total == 0
        assert len(response.users) == 0
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 0
