"""Integration tests for the DeleteUserUseCase."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import AuthenticatedUser, UserRole
from app.features.auth.models import RefreshToken, Tenant, User
from app.features.auth.usecases.delete_user_usecase import DeleteUserUseCaseImpl

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestDeleteUserUseCase:
    """Test suite for the DeleteUserUseCase."""

    async def test_delete_user_successfully(
        self,
        db_session: AsyncSession,
    ):
        """Test the successful deletion of a user."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        target_user = User(
            email="user@example.com",
            hashed_password="hash_user",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        user_id = target_user.id

        use_case = DeleteUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Act
        response = await use_case.execute(user_id, admin_user)

        # Assert
        assert response.message == "User deleted successfully"
        assert response.user_id == str(user_id)

        # Verify user is deleted from database
        user = (
            await db_session.execute(select(User).filter_by(id=user_id))
        ).scalar_one_or_none()
        assert user is None

    async def test_delete_user_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test that deleting a non-existent user raises 404."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        db_session.add(admin)
        await db_session.commit()

        use_case = DeleteUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        fake_user_id = "00000000-0000-0000-0000-000000000000"

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(fake_user_id, admin_user)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "User not found"

    async def test_delete_user_from_different_tenant(
        self,
        db_session: AsyncSession,
    ):
        """Test 404 when trying to delete user from different tenant."""
        # Arrange - Create two tenants
        tenant1 = Tenant(name="tenant-1", age_graph_name="graph_1")
        tenant2 = Tenant(name="tenant-2", age_graph_name="graph_2")
        db_session.add_all([tenant1, tenant2])
        await db_session.flush()

        admin_tenant1 = User(
            email="admin@tenant1.com",
            hashed_password="hash_admin",
            tenant_id=tenant1.id,
            role=UserRole.TENANT_ADMIN,
        )
        user_tenant2 = User(
            email="user@tenant2.com",
            hashed_password="hash_user",
            tenant_id=tenant2.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin_tenant1, user_tenant2])
        await db_session.commit()

        use_case = DeleteUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin_tenant1.id,
            email=admin_tenant1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant1.id,
        )

        # Act & Assert - Try to delete user from tenant 2
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(user_tenant2.id, admin_user)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "User not found"

    async def test_delete_user_cascades_to_refresh_tokens(
        self,
        db_session: AsyncSession,
    ):
        """Test that deleting a user also deletes all associated refresh tokens."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        target_user = User(
            email="user@example.com",
            hashed_password="hash_user",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin, target_user])
        await db_session.flush()

        # Create refresh tokens for the target user
        from datetime import datetime, timedelta, timezone

        refresh_token1 = RefreshToken(
            token_hash="hash_token1",
            user_id=target_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        refresh_token2 = RefreshToken(
            token_hash="hash_token2",
            user_id=target_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        db_session.add_all([refresh_token1, refresh_token2])
        await db_session.commit()

        user_id = target_user.id

        # Verify refresh tokens exist
        tokens_before = (
            (await db_session.execute(select(RefreshToken).filter_by(user_id=user_id)))
            .scalars()
            .all()
        )
        assert len(tokens_before) == 2

        use_case = DeleteUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Act
        await use_case.execute(user_id, admin_user)

        # Assert - Verify refresh tokens are deleted
        tokens_after = (
            (await db_session.execute(select(RefreshToken).filter_by(user_id=user_id)))
            .scalars()
            .all()
        )
        assert len(tokens_after) == 0

    async def test_delete_user_actually_removes_from_database(
        self,
        db_session: AsyncSession,
    ):
        """Test that the user is actually removed from the database."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        target_user = User(
            email="user@example.com",
            hashed_password="hash_user",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        user_id = target_user.id

        # Verify user exists before deletion
        user_before = (
            await db_session.execute(select(User).filter_by(id=user_id))
        ).scalar_one_or_none()
        assert user_before is not None

        use_case = DeleteUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Act
        await use_case.execute(user_id, admin_user)

        # Assert - Verify user is gone
        user_after = (
            await db_session.execute(select(User).filter_by(id=user_id))
        ).scalar_one_or_none()
        assert user_after is None

        # Also verify we can't find it by email
        user_by_email = (
            await db_session.execute(
                select(User).filter_by(email="user@example.com")
            )
        ).scalar_one_or_none()
        assert user_by_email is None

    async def test_delete_user_multiple_users_in_tenant(
        self,
        db_session: AsyncSession,
    ):
        """Test deleting one user doesn't affect other users in the same tenant."""
        # Arrange
        tenant = Tenant(name="test-tenant", age_graph_name="graph_test")
        db_session.add(tenant)
        await db_session.flush()

        admin = User(
            email="admin@example.com",
            hashed_password="hash_admin",
            tenant_id=tenant.id,
            role=UserRole.TENANT_ADMIN,
        )
        user1 = User(
            email="user1@example.com",
            hashed_password="hash_user1",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )
        user2 = User(
            email="user2@example.com",
            hashed_password="hash_user2",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin, user1, user2])
        await db_session.commit()

        use_case = DeleteUserUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Act - Delete user1
        await use_case.execute(user1.id, admin_user)

        # Assert - user1 is deleted, but user2 and admin remain
        deleted_user = (
            await db_session.execute(select(User).filter_by(id=user1.id))
        ).scalar_one_or_none()
        assert deleted_user is None

        user2_still_exists = (
            await db_session.execute(select(User).filter_by(id=user2.id))
        ).scalar_one_or_none()
        assert user2_still_exists is not None
        assert user2_still_exists.email == "user2@example.com"

        admin_still_exists = (
            await db_session.execute(select(User).filter_by(id=admin.id))
        ).scalar_one_or_none()
        assert admin_still_exists is not None
        assert admin_still_exists.email == "admin@example.com"

