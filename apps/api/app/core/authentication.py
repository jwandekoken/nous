"""Authentication utilities for JWT token validation and user retrieval."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.schemas import AuthenticatedUser, UserRole
from app.core.settings import get_settings

# Password hashing - using argon2 as bcrypt has issues.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

security = HTTPBearer()


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthenticatedUser:
    """Get current user from JWT token with tenant information."""
    token = credentials.credentials
    payload = verify_token(token)

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")  # This can be None
    role_str = payload.get("role")

    if user_id is None or role_str is None:  # tenant_id can be None, but role cannot
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required user or role information",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return AuthenticatedUser(
            user_id=UUID(str(user_id)),
            tenant_id=UUID(str(tenant_id)) if tenant_id else None,
            role=UserRole(role_str),  # <-- Validate and cast role
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user, tenant, or role format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
