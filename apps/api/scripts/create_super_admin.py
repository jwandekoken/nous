import asyncio
import getpass
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.authentication import get_password_hash
from app.core.schemas import UserRole
from app.core.settings import get_settings
from app.db.postgres.auth_session import Base
from app.features.auth.models import User


async def create_super_admin(email: str, password: str):
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


def get_user_input():
    """Get email and password from user interactively."""
    email = input("Enter email for super admin: ").strip()

    if not email:
        print("Email cannot be empty.")
        return None, None

    password = getpass.getpass("Enter password for super admin: ")
    if not password:
        print("Password cannot be empty.")
        return None, None

    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        print("Passwords do not match.")
        return None, None

    return email, password


if __name__ == "__main__":
    print("Create Super Admin User")
    print("=" * 25)

    email, password = get_user_input()
    if not email or not password:
        exit(1)

    asyncio.run(create_super_admin(email, password))
