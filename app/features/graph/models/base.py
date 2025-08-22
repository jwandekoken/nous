"""Base models for graph database entities.

This module defines the base configuration and common functionality
for all graph database models.
"""

from pydantic import BaseModel, ConfigDict

# def datetime_encoder(dt: datetime | None) -> str | None:
#     """Encode datetime to ISO format string."""
#     return dt.isoformat() if dt else None


# Base configuration for all models
class GraphBaseModel(BaseModel):
    """Base model for all graph entities with common functionality."""

    model_config = ConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        from_attributes=True,
        # json_encoders={
        #     datetime: datetime_encoder,
        #     UUID: str,
        # },
    )
