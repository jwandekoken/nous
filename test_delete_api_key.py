#!/usr/bin/env python3
"""Test script to verify API key deletion functionality."""

import asyncio
import uuid

from app.db.postgres.auth_session import get_auth_db_session
from app.features.auth.models import ApiKey
from app.features.auth.usecases.delete_api_key_usecase import DeleteApiKeyUseCaseImpl
from sqlalchemy import select


async def test_delete_api_key():
    """Test the delete API key functionality."""
    # Create a test API key first
    test_tenant_id = uuid.uuid4()

    async with get_auth_db_session() as session:
        # Create a test API key
        test_api_key = ApiKey(
            name="test_key",
            key_prefix="test123",
            hashed_key="hashed_test_key",
            tenant_id=test_tenant_id,
        )
        session.add(test_api_key)
        await session.commit()
        await session.refresh(test_api_key)

        api_key_id = str(test_api_key.id)
        print(f"Created test API key with ID: {api_key_id}")

        # Verify it exists
        result = await session.execute(
            select(ApiKey).where(ApiKey.id == test_api_key.id)
        )
        existing_key = result.scalar_one_or_none()
        print(f"API key exists before deletion: {existing_key is not None}")

    # Now try to delete it using the use case
    use_case = DeleteApiKeyUseCaseImpl(get_db_session=get_auth_db_session)

    try:
        result = await use_case.execute(api_key_id, test_tenant_id)
        print(f"Delete result: {result}")
    except Exception as e:
        print(f"Delete failed with error: {e}")

    # Verify it was actually deleted
    async with get_auth_db_session() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.id == test_api_key.id)
        )
        deleted_key = result.scalar_one_or_none()
        print(f"API key exists after deletion: {deleted_key is not None}")

        # Clean up
        if deleted_key:
            session.delete(deleted_key)
            await session.commit()
            print("Cleaned up remaining test API key")


if __name__ == "__main__":
    asyncio.run(test_delete_api_key())
