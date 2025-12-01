from pydantic import BaseModel, EmailStr


class SetupRequiredResponse(BaseModel):
    """Response model for setup required check."""

    setup_required: bool


class SetupAdminRequest(BaseModel):
    """Request model for creating the first admin."""

    email: EmailStr
    password: str


class SetupAdminResponse(BaseModel):
    """Response model for successful admin creation."""

    message: str
    email: str
