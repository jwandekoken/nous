import argparse
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.authentication import get_password_hash
from app.core.schemas import UserRole
from app.core.settings import get_settings
from app.db.postgres.auth_session import Base
from app.features.auth.models import User


async def create_super_admin(email, password):
    """Creates the first super admin user."""
    if not email or not password:
        print("Email and password cannot be empty.")
        return

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        async with conn.begin():
            session = AsyncSession(engine)

            result = await session.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                print(f"User with email {email} already exists.")
                return

            hashed_password = get_password_hash(password)
            super_admin = User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=hashed_password,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                tenant_id=None,
            )
            session.add(super_admin)
            await session.commit()
            print(f"Super admin {email} created successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a super admin user.")
    parser.add_argument("--email", required=True, help="Email for the super admin.")
    parser.add_argument(
        "--password", required=True, help="Password for the super admin."
    )
    args = parser.parse_args()

    asyncio.run(create_super_admin(args.email, args.password))
