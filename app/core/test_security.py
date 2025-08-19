"""Tests for security utilities."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.settings import get_settings


def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = get_password_hash(password)

    # Hash should be different from original password
    assert hashed != password

    # Should verify correctly
    assert verify_password(password, hashed) is True

    # Should not verify incorrect password
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    # Token should be a string
    assert isinstance(token, str)

    # Token should have 3 parts (header.payload.signature)
    assert len(token.split(".")) == 3


def test_create_access_token_with_expiration():
    """Test JWT token creation with custom expiration."""
    data = {"sub": "123"}
    expires_delta = timedelta(minutes=15)
    token = create_access_token(data, expires_delta)

    # Decode token to check expiration
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    # Check that expiration is set
    assert "exp" in payload

    # Check that expiration is approximately 15 minutes from now
    exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
    expected_time = datetime.now(UTC) + expires_delta

    # Allow 1 minute tolerance
    assert abs((exp_time - expected_time).total_seconds()) < 60


def test_verify_token_valid():
    """Test token verification with valid token."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    payload = verify_token(token)

    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload


def test_verify_token_invalid():
    """Test token verification with invalid token."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        verify_token("invalid.token.here")

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)
