"""Use case for signing up a new tenant with user and graph database."""

from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.features.auth.dtos import SignupRequest, SignupResponse
from app.features.auth.models import Tenant, User


class PasswordHasher(Protocol):
    """Protocol for password hashing operations."""

    def hash(self, secret: str | bytes, **kwargs) -> str:
        """Hash a password or secret."""
        ...


class SignupTenantUseCaseImpl:
    """Implementation of the signup tenant use case."""

    def __init__(
        self,
        password_hasher: PasswordHasher,
        get_db_session,
        get_db_pool,
    ):
        """Initialize the use case with dependencies.

        Args:
            password_hasher: Service for hashing passwords
            get_db_session: Function to get database session
            get_db_pool: Function to get graph database pool
        """
        self.password_hasher = password_hasher
        self.get_auth_db_session = get_db_session
        self.get_graph_db_pool = get_db_pool

    async def execute(self, request: SignupRequest) -> SignupResponse:
        """Create a new tenant with an initial user and AGE graph.

        Args:
            request: The signup request containing tenant details

        Returns:
            Response with success message and IDs

        Raises:
            ValueError: If validation fails or creation fails
        """
        # Validate input
        if len(request.name) < 3 or len(request.name) > 50:
            raise ValueError("Tenant name must be between 3 and 50 characters")

        if not request.name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Tenant name can only contain alphanumeric characters, hyphens, and underscores"
            )

        if len(request.password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        async with self.get_auth_db_session() as session:
            async with session.begin():
                try:
                    # Generate unique graph name
                    graph_name = self._generate_unique_graph_name()

                    # Create tenant
                    tenant = Tenant(name=request.name, age_graph_name=graph_name)
                    session.add(tenant)
                    await session.flush()  # Get the tenant ID

                    # Hash password
                    hashed_password = self.password_hasher.hash(request.password)

                    # Create user
                    user = User(
                        email=request.email,
                        hashed_password=hashed_password,
                        tenant_id=tenant.id,
                    )
                    session.add(user)
                    await session.flush()

                    # Create AGE graph
                    pool = await self.get_graph_db_pool()
                    async with pool.acquire() as conn:
                        await conn.execute("LOAD 'age';")
                        await conn.execute(
                            "SET search_path = ag_catalog, '$user', public;"
                        )
                        await conn.execute("SELECT create_graph($1)", graph_name)

                    return SignupResponse(
                        message="Tenant created successfully",
                        tenant_id=str(tenant.id),
                        user_id=str(user.id),
                    )

                except IntegrityError as e:
                    await session.rollback()
                    raise ValueError("Tenant name or email already exists") from e
                except Exception as e:
                    await session.rollback()
                    # Log the error (in production, use proper logging)
                    print(f"Signup error: {e}")
                    raise ValueError("Failed to create tenant") from e

    def _generate_unique_graph_name(self) -> str:
        """Generate a unique graph name for a tenant."""
        return f"nous_graph_{uuid4().hex}"
