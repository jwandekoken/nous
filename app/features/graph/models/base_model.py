"""Base models for graph database entities.

This module defines the base configuration and common functionality
for all graph database models.
"""

from pydantic import BaseModel, ConfigDict


# Base configuration for all models
class GraphBaseModel(BaseModel):
    """Base model for all graph entities with common functionality."""

    model_config = ConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        from_attributes=True,
    )
