"""Authentication token schemas."""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    """Token payload data schema."""

    user_id: str | None = Field(None, description="User ID from token")
