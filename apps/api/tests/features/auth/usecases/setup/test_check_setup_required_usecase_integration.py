"""Integration tests for the CheckSetupRequiredUseCase."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dtos import SetupAdminRequest
from app.features.auth.usecases.setup.check_setup_required_usecase import (
    CheckSetupRequiredUseCaseImpl,
)
from app.features.auth.usecases.setup.setup_admin_usecase import (
    PasswordHasher,
    SetupAdminUseCaseImpl,
)

# All fixtures are now provided by tests/conftest.py


@pytest.mark.asyncio
class TestCheckSetupRequiredUseCase:
    """Test suite for the CheckSetupRequiredUseCase."""

    async def test_setup_required_true_initially(
        self,
        db_session: AsyncSession,
    ):
        """Test that setup is required when no super admin exists."""
        # Arrange
        use_case = CheckSetupRequiredUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Act
        response = await use_case.execute()

        # Assert
        assert response.setup_required is True

    async def test_setup_required_false_after_setup(
        self,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ):
        """Test that setup is not required after a super admin is created."""
        # Arrange - Create a super admin
        setup_use_case = SetupAdminUseCaseImpl(
            password_hasher=password_hasher,
            get_db_session=lambda: db_session,
        )
        await setup_use_case.execute(
            SetupAdminRequest(
                email="admin@example.com",
                password="securepassword",
            )
        )

        check_use_case = CheckSetupRequiredUseCaseImpl(
            get_db_session=lambda: db_session,
        )

        # Act
        response = await check_use_case.execute()

        # Assert
        assert response.setup_required is False
