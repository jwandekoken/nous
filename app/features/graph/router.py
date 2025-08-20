"""User API routes and endpoints with SQLModel."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db

router = APIRouter(prefix="/entities", tags=["entities"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/{entity_id}/facts", status_code=status.HTTP_200_OK)
async def ingest_fact(
    entity_id: str,
    fact: Fact,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Create a new user - PLACEHOLDER."""
    # TODO: Implement user creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User creation endpoint not implemented yet",
    )
