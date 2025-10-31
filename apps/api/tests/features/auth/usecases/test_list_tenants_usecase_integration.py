"""Integration tests for the ListTenantsUseCase."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dtos import ListTenantsRequest
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.list_tenants_usecase import ListTenantsUseCaseImpl

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestListTenantsUseCase:
    """Test suite for the ListTenantsUseCase."""

    async def test_list_tenants_successfully(
        self,
        db_session: AsyncSession,
    ):
        """Test the successful listing of tenants with pagination."""
        # Arrange - Create some test tenants
        tenant1 = Tenant(name="alpha-tenant", age_graph_name="graph_alpha")
        tenant2 = Tenant(name="beta-tenant", age_graph_name="graph_beta")
        tenant3 = Tenant(name="gamma-tenant", age_graph_name="graph_gamma")

        db_session.add_all([tenant1, tenant2, tenant3])
        await db_session.flush()

        # Create users for the tenants
        user1 = User(
            email="user1@alpha.com", hashed_password="hash1", tenant_id=tenant1.id
        )
        user2 = User(
            email="user2@beta.com", hashed_password="hash2", tenant_id=tenant2.id
        )
        user3 = User(
            email="user3@beta.com", hashed_password="hash3", tenant_id=tenant2.id
        )  # beta has 2 users
        user4 = User(
            email="user4@gamma.com", hashed_password="hash4", tenant_id=tenant3.id
        )

        db_session.add_all([user1, user2, user3, user4])
        await db_session.commit()

        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        request = ListTenantsRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="name",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 3
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1
        assert len(response.tenants) == 3

        # Check ordering by name ascending
        assert response.tenants[0].name == "alpha-tenant"
        assert response.tenants[0].user_count == 1
        assert response.tenants[1].name == "beta-tenant"
        assert response.tenants[1].user_count == 2
        assert response.tenants[2].name == "gamma-tenant"
        assert response.tenants[2].user_count == 1

    async def test_list_tenants_with_pagination(
        self,
        db_session: AsyncSession,
    ):
        """Test listing tenants with pagination."""
        # Arrange - Create 5 test tenants
        tenants = []
        for i in range(5):
            tenant = Tenant(name=f"tenant-{i:02d}", age_graph_name=f"graph_{i}")
            tenants.append(tenant)
            db_session.add(tenant)
        await db_session.commit()

        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Test page 1 with page_size 2
        request = ListTenantsRequest(
            page=1,
            page_size=2,
            search=None,
            sort_by="name",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 5
        assert response.page == 1
        assert response.page_size == 2
        assert response.total_pages == 3  # ceil(5/2) = 3
        assert len(response.tenants) == 2
        assert response.tenants[0].name == "tenant-00"
        assert response.tenants[1].name == "tenant-01"

    async def test_list_tenants_with_search(
        self,
        db_session: AsyncSession,
    ):
        """Test listing tenants with search filtering."""
        # Arrange
        tenant1 = Tenant(name="alpha-tenant", age_graph_name="graph_alpha")
        tenant2 = Tenant(name="beta-tenant", age_graph_name="graph_beta")
        tenant3 = Tenant(name="other-tenant", age_graph_name="graph_other")

        db_session.add_all([tenant1, tenant2, tenant3])
        await db_session.commit()

        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Search for "beta"
        request = ListTenantsRequest(
            page=1,
            page_size=10,
            search="beta",
            sort_by="name",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 1
        assert len(response.tenants) == 1
        assert response.tenants[0].name == "beta-tenant"

    async def test_list_tenants_with_sorting_desc(
        self,
        db_session: AsyncSession,
    ):
        """Test listing tenants with descending sort order."""
        # Arrange
        tenant1 = Tenant(name="alpha-tenant", age_graph_name="graph_alpha")
        tenant2 = Tenant(name="beta-tenant", age_graph_name="graph_beta")
        tenant3 = Tenant(name="gamma-tenant", age_graph_name="graph_gamma")

        db_session.add_all([tenant1, tenant2, tenant3])
        await db_session.commit()

        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        request = ListTenantsRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="name",
            sort_order="desc",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 3
        assert len(response.tenants) == 3
        assert response.tenants[0].name == "gamma-tenant"
        assert response.tenants[1].name == "beta-tenant"
        assert response.tenants[2].name == "alpha-tenant"

    async def test_list_tenants_sort_by_created_at(
        self,
        db_session: AsyncSession,
    ):
        """Test listing tenants sorted by creation date."""
        # Arrange - Create tenants with a small delay to ensure different timestamps
        import asyncio

        tenant1 = Tenant(name="first-tenant", age_graph_name="graph_first")
        db_session.add(tenant1)
        await db_session.commit()
        await asyncio.sleep(0.01)  # Small delay

        tenant2 = Tenant(name="second-tenant", age_graph_name="graph_second")
        db_session.add(tenant2)
        await db_session.commit()
        await asyncio.sleep(0.01)  # Small delay

        tenant3 = Tenant(name="third-tenant", age_graph_name="graph_third")
        db_session.add(tenant3)
        await db_session.commit()

        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        request = ListTenantsRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="created_at",
            sort_order="desc",  # Most recent first
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 3
        assert len(response.tenants) == 3
        assert response.tenants[0].name == "third-tenant"  # Most recent
        assert response.tenants[1].name == "second-tenant"
        assert response.tenants[2].name == "first-tenant"  # Oldest

    async def test_list_tenants_empty_result(
        self,
        db_session: AsyncSession,
    ):
        """Test listing tenants when no tenants match the search."""
        # Arrange - Create some tenants
        tenant1 = Tenant(name="alpha-tenant", age_graph_name="graph_alpha")
        tenant2 = Tenant(name="beta-tenant", age_graph_name="graph_beta")

        db_session.add_all([tenant1, tenant2])
        await db_session.commit()

        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Search for non-existent tenant
        request = ListTenantsRequest(
            page=1,
            page_size=10,
            search="nonexistent",
            sort_by="name",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 0
        assert len(response.tenants) == 0
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 0

    async def test_list_tenants_no_tenants(
        self,
        db_session: AsyncSession,
    ):
        """Test listing tenants when database is empty."""
        use_case = ListTenantsUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        request = ListTenantsRequest(
            page=1,
            page_size=10,
            search=None,
            sort_by="name",
            sort_order="asc",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.total == 0
        assert len(response.tenants) == 0
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 0
