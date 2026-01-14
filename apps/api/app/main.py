"""Main FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.middleware import request_context_middleware
from app.core.settings import get_settings
from app.db.postgres.graph_connection import close_graph_db_pool, get_graph_db_pool
from app.db.postgres.session import init_db_session
from app.db.qdrant import close_qdrant_client, get_qdrant_client, init_qdrant_db
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
    print("Database session initialized.")
    _ = await get_graph_db_pool()
    print("Graph database connection pool created.")

    # Initialize Qdrant vector database
    qdrant_client = await get_qdrant_client()
    await init_qdrant_db(qdrant_client)
    print("Qdrant vector database initialized.")

    yield

    # Shutdown
    print("Shutting down application")
    await close_graph_db_pool()
    print("Graph database connection pool closed.")
    await close_qdrant_client()
    print("Qdrant client closed.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Nous API - The Knowledge Graph Memory Brain",
        lifespan=lifespan,
    )

    # Request context middleware (request_id, timing, etc.)
    _ = app.middleware("http")(request_context_middleware)

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
