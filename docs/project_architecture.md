# Modular Architecture

## Context

We need a scalable and maintainable structure for our growing FastAPI application. The architecture must support multiple databases (PostgreSQL and a graph DB) and promote clear separation of concerns.

## Decision

We have implemented a modular, feature-based architecture with **inline tests** and **entity-specific separation**. The project is organized by business domains (e.g., `users`, `graph`), with each feature containing its own routes, logic, models, repositories, and tests. We follow the **Clean Architecture** principles with clear separation between:

- **Presentation Layer** (Routes/APIs)
- **Application Layer** (Use Cases/Business Logic)
- **Domain Layer** (Models/Entities)
- **Infrastructure Layer** (Repositories/Databases)

## Development Environment

Dependency management will be handled by `uv`, with dependencies specified in `pyproject.toml`.

Tests will be run by pointing `pytest` to the application source directory: `uv run pytest app/`.

## Architecture Overview

```plaintext
/nous-api/
|
|-- /app/
|   |-- main.py                    # FastAPI app factory & router inclusion
|   |-- /core/
|   |   |-- security.py
|   |   `-- test_security.py       # Test co-located with code
|   |
|   |-- /db/
|   |   |-- /postgres/             # PostgreSQL connection logic
|   |   `-- /graph/                # Graph DB connection logic
|   |
|   `-- /features/
|       |-- /users/                # User management feature
|       |   |-- router.py
|       |   |-- test_router.py     # Test co-located with code
|       |   |-- service.py
|       |   |-- models.py
|       |   `-- schemas.py
|       |
|       `-- /graph/                # Graph database feature (IMPLEMENTED)
|           |-- router.py          # Main router including all entity routes
|           |-- /models/           # Domain models (Entity, Fact, etc.)
|           |-- /repositories/     # Entity-specific repositories
|           |   |-- entity.py      # EntityRepository
|           |   |-- fact.py        # FactRepository
|           |   |-- identifier.py  # IdentifierRepository
|           |   `-- source.py      # SourceRepository
|           |-- /routes/           # Entity-specific route modules
|           |   |-- entities.py    # Entity CRUD routes
|           |   |-- facts.py       # Fact retrieval routes
|           |   |-- entity_facts.py # Entity-Fact relationship routes
|           |   `-- __init__.py    # Route exports
|           `-- /usecases/         # Business logic use cases
|               |-- create_entity.py
|               |-- get_entity.py
|               |-- add_fact.py
|               `-- ...
|
`-- pyproject.toml
```

### Data Layer Architecture with SQLModel

This project uses **SQLModel**, which unifies database models and API schemas into single class definitions. SQLModel classes serve dual purposes:

1. **Database Tables**: When defined with `table=True`, they create SQLAlchemy table models
2. **API Schemas**: The same classes automatically work as Pydantic models for FastAPI serialization

This approach reduces code duplication and ensures consistency between database structure and API contracts.

**File Usage Patterns:**

- `models.py`: Contains SQLModel classes that serve as both database tables and API schemas
- `schemas.py`: Contains pure Pydantic models for cases where you need API-only schemas (e.g., authentication tokens, complex validation models)

### Component Responsibilities

| Component         | Responsibility                                                                     |
| :---------------- | :--------------------------------------------------------------------------------- |
| `main.py`         | Creates and configures the main `FastAPI` instance with router inclusion.          |
| `core/`           | App-wide concerns (settings, security).                                            |
| `db/`             | Contains isolated connection logic for each database.                              |
| `router.py`       | **Main Router:** Orchestrates entity-specific route modules.                       |
| `routes/`         | **API Layer:** Entity-specific route modules handling HTTP requests/responses.     |
| `usecases/`       | **Application Layer:** Business logic use cases with validation and rules.         |
| `repositories/`   | **Infrastructure Layer:** Entity-specific database operations and queries.         |
| `models/`         | **Domain Layer:** Core business entities, relationships, and domain models.        |
| `schemas.py`      | **Data Layer:** Pure Pydantic models for API I/O (when separate from DB models).   |
| `models.py`       | **Persistence Layer:** SQLModel classes serving as both DB tables and API schemas. |
| `graph_models.py` | **Persistence Layer:** Graph DB node/edge models.                                  |
| `test_*.py`       | **Testing Layer:** Verifies the correctness of each module.                        |

### API Structure

```
FastAPI Application
├── /api/v1/graph/
│   ├── POST /entities           # Create entity with identifier
│   ├── GET /entities/{id}       # Get entity by ID
│   ├── GET /entities            # Search entities by identifier
│   ├── GET /facts/{id}          # Get fact by ID
│   └── POST /entities/{id}/facts # Add fact to entity
└── /health                      # Health check endpoint
```
