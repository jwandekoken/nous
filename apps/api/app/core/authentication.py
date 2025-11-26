"""Authentication utilities for JWT token validation and user retrieval."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.schemas import AuthenticatedUser, UserRole
from app.core.settings import get_settings

# Password hashing - using argon2 as bcrypt has issues.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Refresh token hashing context - using argon2
refresh_token_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_token(token: str) -> dict[str, str | int]:
    """Verify and decode a JWT token."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, str | UUID | datetime], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token() -> str:
    """Generate a cryptographically secure random refresh token.

    Returns:
        A 64-character hexadecimal string (256 bits of entropy)
    """
    return secrets.token_hex(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for secure storage in database.

    Args:
        token: The plain refresh token to hash

    Returns:
        The hashed token
    """
    return refresh_token_context.hash(token)


def verify_refresh_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a plain refresh token against its hash.

    Args:
        plain_token: The plain refresh token from the request
        hashed_token: The hashed token from the database

    Returns:
        True if the token matches, False otherwise
    """
    return refresh_token_context.verify(plain_token, hashed_token)


async def verify_auth(
    access_token: str | None = Cookie(None, alias="access_token"),
) -> AuthenticatedUser:
    """Verify authentication from cookie.

    Returns:
        AuthenticatedUser with user_id, tenant_id, and role

    Raises:
        HTTPException 401 if not authenticated or token is invalid
    """

    # Try cookie (web app authentication)
    if access_token:
        payload = verify_token(access_token)

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role_str = payload.get("role")

        if user_id is None or role_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required user or role information",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            return AuthenticatedUser(
                user_id=UUID(str(user_id)),
                tenant_id=UUID(str(tenant_id)) if tenant_id else None,
                role=UserRole(role_str),
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user, tenant, or role format in token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # No authentication credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
