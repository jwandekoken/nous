from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.core.authentication import AuthenticatedUser, get_password_hash
from app.core.authorization import is_tenant_admin
from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.models import User, UserRole

router = APIRouter()


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: UserRole = UserRole.TENANT_USER


class UserResponse(BaseModel):
    id: str
    email: str
    role: UserRole


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_user(
    request: CreateUserRequest,
    admin_user: AuthenticatedUser = Depends(is_tenant_admin),
    get_db_session_func=Depends(get_auth_db_session),
):
    """
    Allows a TENANT_ADMIN to create a new user within their own tenant.
    """
    if admin_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Admin has no tenant")

    if request.role == UserRole.TENANT_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot create another admin")

    if request.role == UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot create a super admin")

    hashed_password = get_password_hash(request.password)
    new_user = User(
        email=request.email,
        hashed_password=hashed_password,
        tenant_id=admin_user.tenant_id,
        role=request.role,
    )

    async with get_db_session_func() as session:
        try:
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return UserResponse(
                id=str(new_user.id), email=new_user.email, role=new_user.role
            )
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists in the tenant",
            )
