"""Integration tests for the RefreshTokenUseCase."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import refresh_token_context
from app.features.auth.dtos.auth_dto import RefreshTokenResponse
from app.features.auth.models import RefreshToken, Tenant, User
from app.features.auth.usecases.login.refresh_token_usecase import (
    RefreshTokenUseCaseImpl,
)


class TokenCreatorImpl:
    """Wrapper for token creation to match protocol."""

    def __init__(self):
        self.created_tokens = []

    def __call__(self, data: dict[str, str | int], expires_delta=None) -> str:
        """Create an access token."""
        # Store the data for verification in tests
        self.created_tokens.append(data)
        # Return a mock token for testing
        return f"mock_access_token_{len(self.created_tokens)}"


class RefreshTokenCreatorImpl:
    """Wrapper for refresh token creation to match protocol."""

    def __init__(self):
        self.created_tokens = []

    def create(self) -> str:
        """Create a refresh token."""
        token = f"new_refresh_token_{len(self.created_tokens) + 1}"
        self.created_tokens.append(token)
        return token

    def hash(self, token: str) -> str:
        """Hash a refresh token."""
        return refresh_token_context.hash(token)


class RefreshTokenVerifierImpl:
    """Wrapper for refresh token verification to match protocol."""

    def verify(self, plain_token: str, hashed_token: str) -> bool:
        """Verify a refresh token against its hash."""
        return refresh_token_context.verify(plain_token, hashed_token)


def create_session_factory(session):
    """Create a session factory that returns the same session."""

    @asynccontextmanager
    async def get_session():
        yield session

    return get_session


@pytest.mark.asyncio
class TestRefreshTokenUseCase:
    """Test suite for the RefreshTokenUseCase."""

    async def test_refresh_token_successful(
        self,
        db_session: AsyncSession,
        password_hasher,
    ):
        """Test successful token refresh."""
        # Arrange - Create a tenant, user, and refresh token
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        hashed_password = password_hasher.hash("password")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            failed_login_attempts=0,
            locked_until=None,
        )
        db_session.add(user)
        await db_session.flush()

        # Create a valid refresh token
        plain_token = "valid_refresh_token"
        token_hash = refresh_token_context.hash(plain_token)
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked=False,
        )
        db_session.add(refresh_token)
        await db_session.commit()

        # Create use case
        token_creator = TokenCreatorImpl()
        refresh_token_creator = RefreshTokenCreatorImpl()
        refresh_token_verifier = RefreshTokenVerifierImpl()
        use_case = RefreshTokenUseCaseImpl(
            token_creator=token_creator,
            refresh_token_creator=refresh_token_creator,
            refresh_token_verifier=refresh_token_verifier,
            get_db_session=create_session_factory(db_session),
        )

        # Act
        response = await use_case.execute(plain_token)

        # Assert
        assert isinstance(response, RefreshTokenResponse)
        assert response.access_token.startswith("mock_access_token_")
        assert response.refresh_token.startswith("new_refresh_token_")
        assert response.token_type == "bearer"
        assert response.expires_in == 1800

        # Verify access token data
        assert len(token_creator.created_tokens) == 1
        token_data = token_creator.created_tokens[0]
        assert token_data["sub"] == str(user.id)
        assert token_data["tenant_id"] == str(tenant.id)
        assert token_data["role"] == user.role.value

        # Verify new refresh token was created
        assert len(refresh_token_creator.created_tokens) == 1

        # Verify old token was revoked
        await db_session.refresh(refresh_token)
        assert refresh_token.revoked is True
        assert refresh_token.replaced_by_id is not None

    async def test_refresh_token_expired(
        self,
        db_session: AsyncSession,
        password_hasher,
    ):
        """Test refresh with expired token."""
        # Arrange - Create user with expired refresh token
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            email="test@example.com",
            hashed_password=password_hasher.hash("password"),
            tenant_id=tenant.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create an expired refresh token
        plain_token = "expired_refresh_token"
        token_hash = refresh_token_context.hash(plain_token)
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
            revoked=False,
        )
        db_session.add(refresh_token)
        await db_session.commit()

        # Create use case
        use_case = RefreshTokenUseCaseImpl(
            token_creator=TokenCreatorImpl(),
            refresh_token_creator=RefreshTokenCreatorImpl(),
            refresh_token_verifier=RefreshTokenVerifierImpl(),
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(plain_token)

        assert excinfo.value.status_code == 401
        assert "expired" in excinfo.value.detail.lower()

    async def test_refresh_token_revoked(
        self,
        db_session: AsyncSession,
        password_hasher,
    ):
        """Test refresh with already revoked token."""
        # Arrange - Create user with revoked refresh token
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            email="test@example.com",
            hashed_password=password_hasher.hash("password"),
            tenant_id=tenant.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create a revoked refresh token
        plain_token = "revoked_refresh_token"
        token_hash = refresh_token_context.hash(plain_token)
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked=True,  # Already revoked
        )
        db_session.add(refresh_token)
        await db_session.commit()

        # Create use case
        use_case = RefreshTokenUseCaseImpl(
            token_creator=TokenCreatorImpl(),
            refresh_token_creator=RefreshTokenCreatorImpl(),
            refresh_token_verifier=RefreshTokenVerifierImpl(),
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(plain_token)

        assert excinfo.value.status_code == 401
        assert "Invalid refresh token" in excinfo.value.detail

    async def test_refresh_token_invalid(
        self,
        db_session: AsyncSession,
    ):
        """Test refresh with non-existent token."""
        # Arrange - No refresh token in database
        use_case = RefreshTokenUseCaseImpl(
            token_creator=TokenCreatorImpl(),
            refresh_token_creator=RefreshTokenCreatorImpl(),
            refresh_token_verifier=RefreshTokenVerifierImpl(),
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute("non_existent_token")

        assert excinfo.value.status_code == 401
        assert "Invalid refresh token" in excinfo.value.detail

    async def test_refresh_token_rotation(
        self,
        db_session: AsyncSession,
        password_hasher,
    ):
        """Test that old token cannot be reused after refresh."""
        # Arrange - Create user and refresh token
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            email="test@example.com",
            hashed_password=password_hasher.hash("password"),
            tenant_id=tenant.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        plain_token = "rotation_test_token"
        token_hash = refresh_token_context.hash(plain_token)
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked=False,
        )
        db_session.add(refresh_token)
        await db_session.commit()

        # Create use case
        use_case = RefreshTokenUseCaseImpl(
            token_creator=TokenCreatorImpl(),
            refresh_token_creator=RefreshTokenCreatorImpl(),
            refresh_token_verifier=RefreshTokenVerifierImpl(),
            get_db_session=create_session_factory(db_session),
        )

        # Act - First refresh (should succeed)
        response = await use_case.execute(plain_token)
        assert response.access_token.startswith("mock_access_token_")

        # Try to use the same token again (should fail)
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(plain_token)

        assert excinfo.value.status_code == 401
        assert "Invalid refresh token" in excinfo.value.detail

    async def test_refresh_token_user_inactive(
        self,
        db_session: AsyncSession,
        password_hasher,
    ):
        """Test refresh fails when user account is inactive."""
        # Arrange - Create inactive user with refresh token
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            email="test@example.com",
            hashed_password=password_hasher.hash("password"),
            tenant_id=tenant.id,
            is_active=False,  # Inactive account
        )
        db_session.add(user)
        await db_session.flush()

        plain_token = "inactive_user_token"
        token_hash = refresh_token_context.hash(plain_token)
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked=False,
        )
        db_session.add(refresh_token)
        await db_session.commit()

        # Create use case
        use_case = RefreshTokenUseCaseImpl(
            token_creator=TokenCreatorImpl(),
            refresh_token_creator=RefreshTokenCreatorImpl(),
            refresh_token_verifier=RefreshTokenVerifierImpl(),
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(plain_token)

        assert excinfo.value.status_code == 401
        assert "Account is disabled" in excinfo.value.detail

    async def test_refresh_token_user_locked(
        self,
        db_session: AsyncSession,
        password_hasher,
    ):
        """Test refresh fails when user account is locked."""
        # Arrange - Create locked user with refresh token
        tenant = Tenant(name="test-tenant", age_graph_name="test_tenant_graph")
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            email="test@example.com",
            hashed_password=password_hasher.hash("password"),
            tenant_id=tenant.id,
            is_active=True,
            locked_until=datetime.now(UTC) + timedelta(hours=1),  # Locked
        )
        db_session.add(user)
        await db_session.flush()

        plain_token = "locked_user_token"
        token_hash = refresh_token_context.hash(plain_token)
        refresh_token = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked=False,
        )
        db_session.add(refresh_token)
        await db_session.commit()

        # Create use case
        use_case = RefreshTokenUseCaseImpl(
            token_creator=TokenCreatorImpl(),
            refresh_token_creator=RefreshTokenCreatorImpl(),
            refresh_token_verifier=RefreshTokenVerifierImpl(),
            get_db_session=create_session_factory(db_session),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await use_case.execute(plain_token)

        assert excinfo.value.status_code == 401
        assert "Account is temporarily locked" in excinfo.value.detail
