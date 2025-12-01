import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_password_hash
from app.core.schemas import UserRole
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.dtos import (
    SetupAdminRequest,
    SetupAdminResponse,
    SetupRequiredResponse,
)
from app.features.auth.models import User

router = APIRouter()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide a database session."""
    async with get_auth_db_session() as session:
        yield session


@router.get("/setup-required", response_model=SetupRequiredResponse)
async def check_setup_required(
    session: AsyncSession = Depends(get_session),
) -> SetupRequiredResponse:
    """Check if the application requires initial setup (no super admin exists)."""
    query = (
        select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
    )
    result = await session.execute(query)
    count = result.scalar_one()

    return SetupRequiredResponse(setup_required=count == 0)


@router.post("/setup-admin", response_model=SetupAdminResponse)
async def setup_admin(
    request: SetupAdminRequest,
    session: AsyncSession = Depends(get_session),
) -> SetupAdminResponse:
    """Create the first super admin user. Only allowed if no super admin exists."""
    # Double check to prevent race conditions or unauthorized usage
    query = (
        select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
    )
    result = await session.execute(query)
    count = result.scalar_one()

    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup has already been completed.",
        )

    # Check if email already exists (though unlikely given the check above, good practice)
    email_check = await session.execute(select(User).where(User.email == request.email))
    if email_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    hashed_password = get_password_hash(request.password)
    super_admin = User(
        id=uuid.uuid4(),
        email=request.email,
        hashed_password=hashed_password,
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        tenant_id=None,
    )
    session.add(super_admin)
    await session.commit()

    return SetupAdminResponse(
        message="Super admin created successfully.",
        email=super_admin.email,
    )
