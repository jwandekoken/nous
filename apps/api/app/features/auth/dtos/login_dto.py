"""Login data transfer objects."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing access token."""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Response model for successful token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
