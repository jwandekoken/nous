"""API keys data transfer objects."""

from datetime import datetime

from pydantic import BaseModel


class CreateApiKeyRequest(BaseModel):
    """Request model for creating an API key."""

    name: str


class CreateApiKeyResponse(BaseModel):
    """Response model for successful API key creation."""

    message: str
    api_key: str
    key_prefix: str
    expires_at: str | None


class ApiKeyInfo(BaseModel):
    """Information about an API key."""

    id: str
    name: str
    key_prefix: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None


class ListApiKeysResponse(BaseModel):
    """Response model for listing API keys."""

    api_keys: list[ApiKeyInfo]
