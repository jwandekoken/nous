"""User API routes and endpoints with SQLModel."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.postgres import get_db
from app.features.users.models import User, UserCreate, UserUpdate
from app.features.users.schemas import Token

router = APIRouter(prefix="/users", tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Create a new user - PLACEHOLDER."""
    # TODO: Implement user creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User creation endpoint not implemented yet",
    )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user information - PLACEHOLDER."""
    # TODO: Implement current user info
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Current user info endpoint not implemented yet",
    )


@router.get("/", response_model=list[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[User]:
    """Get list of users - PLACEHOLDER."""
    # TODO: Implement get users list
    return []


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> User:
    """Get user by ID - PLACEHOLDER."""
    # TODO: Implement get user by ID
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get user by ID endpoint not implemented yet",
    )


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> User:
    """Update user information - PLACEHOLDER."""
    # TODO: Implement user update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update user endpoint not implemented yet",
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Delete user - PLACEHOLDER."""
    # TODO: Implement user deletion
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete user endpoint not implemented yet",
    )


# Authentication routes
auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """OAuth2 compatible token login - PLACEHOLDER."""
    # TODO: Implement authentication
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication endpoint not implemented yet",
    )


# Include auth router in main router
router.include_router(auth_router)
