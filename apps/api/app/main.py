"""Main FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.db.postgres.auth_session import init_db_session
from app.db.postgres.graph_connection import close_db_pool, get_db_pool
from app.features.auth.router import router as auth_router
from app.features.graph.router import router as graph_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database connections
    init_db_session()
    print("Auth database session initialized.")
    _ = await get_db_pool()
    print("Graph database connection pool created.")

    yield

    # Shutdown
    print("Shutting down application")
    await close_db_pool()
    print("Database connection pool closed.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="FastAPI application with modular architecture",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )
