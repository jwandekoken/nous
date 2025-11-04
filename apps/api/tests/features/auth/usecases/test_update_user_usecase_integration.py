"""Integration tests for the UpdateUserUseCase."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import AuthenticatedUser, UserRole
from app.features.auth.dtos import UpdateUserRequest
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.update_user_usecase import (
    PasswordHasher,
    UpdateUserUseCaseImpl,
)

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestUpdateUserUseCase:
    """Test suite for the UpdateUserUseCase."""

    async def test_update_user_email_successfully(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test successfully updating a user's email."""
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
            email="old@example.com",
            hashed_password="hash_user",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = UpdateUserRequest(email="new@example.com")

        # Act
        response = await use_case.execute(target_user.id, request, admin_user)

        # Assert
        assert response.message == "User updated successfully"
        assert response.user_id == str(target_user.id)

        # Verify database state
        user = (
            await db_session.execute(select(User).filter_by(id=target_user.id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.email == "new@example.com"

    async def test_update_user_is_active_status(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test successfully updating a user's is_active status."""
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
            is_active=True,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = UpdateUserRequest(is_active=False)

        # Act
        response = await use_case.execute(target_user.id, request, admin_user)

        # Assert
        assert response.message == "User updated successfully"

        # Verify database state
        user = (
            await db_session.execute(select(User).filter_by(id=target_user.id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.is_active is False

    async def test_update_user_role(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test successfully updating a user's role."""
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

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = UpdateUserRequest(role=UserRole.TENANT_ADMIN)

        # Act
        response = await use_case.execute(target_user.id, request, admin_user)

        # Assert
        assert response.message == "User updated successfully"

        # Verify database state
        user = (
            await db_session.execute(select(User).filter_by(id=target_user.id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.role == UserRole.TENANT_ADMIN

    async def test_update_user_password_reset(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test successfully resetting a user's password."""
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
            hashed_password="old_hash",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        old_password_hash = target_user.hashed_password

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = UpdateUserRequest(password="new_password")

        # Act
        response = await use_case.execute(target_user.id, request, admin_user)

        # Assert
        assert response.message == "User updated successfully"

        # Verify database state
        user = (
            await db_session.execute(select(User).filter_by(id=target_user.id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.hashed_password != old_password_hash
        # Verify the password was actually hashed (argon2id is the default)
        assert user.hashed_password.startswith("$argon2id$")

    async def test_update_user_multiple_fields(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test updating multiple fields at once."""
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
            email="old@example.com",
            hashed_password="old_hash",
            tenant_id=tenant.id,
            role=UserRole.TENANT_USER,
            is_active=True,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        request = UpdateUserRequest(
            email="new@example.com",
            is_active=False,
            role=UserRole.TENANT_ADMIN,
        )

        # Act
        response = await use_case.execute(target_user.id, request, admin_user)

        # Assert
        assert response.message == "User updated successfully"

        # Verify database state
        user = (
            await db_session.execute(select(User).filter_by(id=target_user.id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.email == "new@example.com"
        assert user.is_active is False
        assert user.role == UserRole.TENANT_ADMIN

    async def test_update_user_not_found(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that updating a non-existent user raises 404."""
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

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        fake_user_id = "00000000-0000-0000-0000-000000000000"
        request = UpdateUserRequest(email="new@example.com")

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(fake_user_id, request, admin_user)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "User not found"

    async def test_update_user_from_different_tenant(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test 404 when trying to update user from different tenant."""
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

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin_tenant1.id,
            email=admin_tenant1.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant1.id,
        )

        request = UpdateUserRequest(email="new@example.com")

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(user_tenant2.id, request, admin_user)
        assert excinfo.value.status_code == 404
        assert excinfo.value.detail == "User not found"

    async def test_update_user_duplicate_email(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that updating to an existing email fails."""
        # Arrange - Create two users
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

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Try to update user2 to have the same email as user1
        request = UpdateUserRequest(email="user1@example.com")

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(user2.id, request, admin_user)
        assert excinfo.value.status_code == 400
        assert excinfo.value.detail == "User with this email already exists"

    async def test_update_user_partial_update(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that partial updates only change the provided fields."""
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
            is_active=True,
        )

        db_session.add_all([admin, target_user])
        await db_session.commit()

        original_email = target_user.email
        original_role = target_user.role
        original_password = target_user.hashed_password

        use_case = UpdateUserUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        admin_user = AuthenticatedUser(
            user_id=admin.id,
            email=admin.email,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        # Only update is_active
        request = UpdateUserRequest(is_active=False)

        # Act
        response = await use_case.execute(target_user.id, request, admin_user)

        # Assert
        assert response.message == "User updated successfully"

        # Verify database state - only is_active should change
        user = (
            await db_session.execute(select(User).filter_by(id=target_user.id))
        ).scalar_one_or_none()
        assert user is not None
        assert user.is_active is False  # Changed
        assert user.email == original_email  # Unchanged
        assert user.role == original_role  # Unchanged
        assert user.hashed_password == original_password  # Unchanged

