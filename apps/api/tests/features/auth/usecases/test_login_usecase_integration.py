"""Integration tests for the LoginUseCase."""

from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

from app.core.authentication import pwd_context
from app.features.auth.dtos.auth_dto import LoginRequest, LoginResponse
from app.features.auth.models import Tenant, User
from app.features.auth.usecases.login_usecase import LoginUseCaseImpl


class PasswordVerifierImpl:
    """Wrapper for password verification to match protocol."""

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


class TokenCreatorImpl:
    """Wrapper for token creation to match protocol."""

    def __init__(self):
        self.created_tokens = []

    def __call__(self, data: dict[str, str | int], expires_delta=None) -> str:
        """Create an access token."""
        # Store the data for verification in tests
        self.created_tokens.append(data)
        # Return a mock token for testing
        return f"mock_token_{len(self.created_tokens)}"


def create_session_factory(session):
    """Create a session factory that returns the same session."""

    @asynccontextmanager
    async def get_session():
        yield session

    return get_session


@pytest.mark.asyncio
class TestLoginUseCase:
    """Test suite for the LoginUseCase."""

    async def test_login_successful(
        self,
        db_session,
        password_hasher,
    ):
        """Test successful user login."""
        # Arrange - Create a tenant and user
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        hashed_password = password_hasher.hash("correctpassword")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            failed_login_attempts=0,
            locked_until=None,
        )
        db_session.add(user)
        await db_session.commit()

        # Create use case
        token_creator = TokenCreatorImpl()
        use_case = LoginUseCaseImpl(
            password_verifier=PasswordVerifierImpl(),
            token_creator=token_creator,
            get_db_session=create_session_factory(db_session),
        )

        request = LoginRequest(
            email="test@example.com",
            password="correctpassword",
        )

        # Act
        response = await use_case.execute(request.email, request.password)

        # Assert
        assert isinstance(response, LoginResponse)
        assert response.access_token.startswith("mock_token_")
        assert response.token_type == "bearer"
        assert response.expires_in == 1800  # 30 minutes in seconds

        # Verify token data
        assert len(token_creator.created_tokens) == 1
        token_data = token_creator.created_tokens[0]
        assert token_data["sub"] == str(user.id)
        assert token_data["tenant_id"] == str(tenant.id)
        assert token_data["role"] == user.role.value

        # Verify user state was updated
        await db_session.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    async def test_login_user_not_found(
        self,
        db_session,
    ):
        """Test login with non-existent email."""
        # Arrange
        token_creator = TokenCreatorImpl()
        use_case = LoginUseCaseImpl(
            password_verifier=PasswordVerifierImpl(),
            token_creator=token_creator,
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute("nonexistent@example.com", "password")

        assert excinfo.value.status_code == 401
        assert "Incorrect email or password" in excinfo.value.detail

    async def test_login_wrong_password(
        self,
        db_session,
        password_hasher,
    ):
        """Test login with wrong password."""
        # Arrange - Create a tenant and user
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        hashed_password = password_hasher.hash("correctpassword")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            failed_login_attempts=0,
            locked_until=None,
        )
        db_session.add(user)
        await db_session.commit()

        # Create use case
        token_creator = TokenCreatorImpl()
        use_case = LoginUseCaseImpl(
            password_verifier=PasswordVerifierImpl(),
            token_creator=token_creator,
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute("test@example.com", "wrongpassword")

        assert excinfo.value.status_code == 401
        assert "Incorrect email or password" in excinfo.value.detail

        # Verify no token was created
        assert len(token_creator.created_tokens) == 0

    async def test_login_account_locked(
        self,
        db_session,
        password_hasher,
    ):
        """Test login when account is temporarily locked."""
        # Arrange - Create a tenant and user with locked account
        from datetime import UTC, datetime, timedelta

        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        hashed_password = password_hasher.hash("correctpassword")
        locked_until = datetime.now(UTC) + timedelta(minutes=30)
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            failed_login_attempts=3,
            locked_until=locked_until,
        )
        db_session.add(user)
        await db_session.commit()

        # Create use case
        token_creator = TokenCreatorImpl()
        use_case = LoginUseCaseImpl(
            password_verifier=PasswordVerifierImpl(),
            token_creator=token_creator,
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute("test@example.com", "correctpassword")

        assert excinfo.value.status_code == 401
        assert "Account is temporarily locked" in excinfo.value.detail

        # Verify no token was created
        assert len(token_creator.created_tokens) == 0

    async def test_login_account_inactive(
        self,
        db_session,
        password_hasher,
    ):
        """Test login when account is disabled."""
        # Arrange - Create a tenant and inactive user
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        hashed_password = password_hasher.hash("correctpassword")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=False,  # Account is inactive
            failed_login_attempts=0,
            locked_until=None,
        )
        db_session.add(user)
        await db_session.commit()

        # Create use case
        token_creator = TokenCreatorImpl()
        use_case = LoginUseCaseImpl(
            password_verifier=PasswordVerifierImpl(),
            token_creator=token_creator,
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute("test@example.com", "correctpassword")

        assert excinfo.value.status_code == 401
        assert "Account is disabled" in excinfo.value.detail

        # Verify no token was created
        assert len(token_creator.created_tokens) == 0

    async def test_login_resets_failed_attempts_on_success(
        self,
        db_session,
        password_hasher,
    ):
        """Test that successful login resets failed login attempts counter."""
        # Arrange - Create a tenant and user with some failed attempts
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        hashed_password = password_hasher.hash("correctpassword")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            failed_login_attempts=2,  # Had some failed attempts
            locked_until=None,
        )
        db_session.add(user)
        await db_session.commit()

        # Create use case
        token_creator = TokenCreatorImpl()
        use_case = LoginUseCaseImpl(
            password_verifier=PasswordVerifierImpl(),
            token_creator=token_creator,
            get_db_session=create_session_factory(db_session),
        )

        # Act
        await use_case.execute("test@example.com", "correctpassword")

        # Assert - Verify failed attempts were reset
        await db_session.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
