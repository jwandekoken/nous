"""Integration tests for the SetupAdminUseCase."""

import asyncpg
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.schemas import UserRole
from app.features.auth.dtos import CreateTenantRequest, SetupAdminRequest
from app.features.auth.models import User
from app.features.auth.usecases.setup.setup_admin_usecase import (
    PasswordHasher,
    SetupAdminUseCaseImpl,
)
from app.features.auth.usecases.tenants.signup_tenant_usecase import (
    SignupTenantUseCaseImpl,
)


@pytest.mark.asyncio
class TestSetupAdminUseCase:
    """Test suite for the SetupAdminUseCase."""

    async def test_setup_admin_successfully(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test the successful creation of the first super admin."""
        # Arrange
        use_case = SetupAdminUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )
        request = SetupAdminRequest(
            email="admin@example.com",
            password="securepassword",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.message == "Super admin created successfully."
        assert response.email == "admin@example.com"

        # Verify database
        result = await db_session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.role == UserRole.SUPER_ADMIN

    async def test_setup_admin_already_exists(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that setup fails if a super admin already exists."""
        # Arrange - Create first admin
        use_case = SetupAdminUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )
        await use_case.execute(
            SetupAdminRequest(
                email="admin1@example.com",
                password="password",
            )
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(
                SetupAdminRequest(
                    email="admin2@example.com",
                    password="password",
                )
            )

        assert excinfo.value.status_code == 403
        assert excinfo.value.detail == "Setup has already been completed."

    async def test_setup_admin_email_conflict(
        self,
        db_session: AsyncSession,
        postgres_pool: asyncpg.Pool,
        password_hasher: PasswordHasher,
    ):
        """Test that setup fails if the email is already taken by a non-admin."""
        # Arrange - Create a tenant user with the target email
        signup_use_case = SignupTenantUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
            get_db_pool=lambda: postgres_pool,
        )
        await signup_use_case.execute(
            CreateTenantRequest(
                name="tenant1",
                email="conflict@example.com",
                password="password",
            )
        )

        # Setup use case
        setup_use_case = SetupAdminUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await setup_use_case.execute(
                SetupAdminRequest(
                    email="conflict@example.com",
                    password="password",
                )
            )

        assert excinfo.value.status_code == 400
        assert excinfo.value.detail == "User with this email already exists."
