# ADR-001: Modular Architecture

**Status:** Accepted

**Date:** 2025-08-19

## Context

We need a scalable and maintainable structure for our growing FastAPI application. The architecture must support multiple databases (PostgreSQL and a graph DB) and promote clear separation of concerns.

## Decision

We will adopt a modular, feature-based architecture with **inline tests**. Test files will be co-located with the source code they verify. The project will be organized by business domains (e.g., `users`, `items`), with each module containing its own routes, logic, models, and tests.

## Development Environment

Dependency management will be handled by `uv`, with dependencies specified in `pyproject.toml`.

Tests will be run by pointing `pytest` to the application source directory: `uv run pytest app/`.

## Architecture Overview

```plaintext
/my_fastapi_project/
|
|-- /app/
|   |-- main.py
|   |-- /core/
|   |   |-- security.py
|   |   `-- test_security.py      # Test co-located with code
|   |
|   |-- /db/
|   |   |-- /postgres/
|   |   `-- /graph/
|   |
|   `-- /features/
|       `-- /users/               # Example feature module
|           |-- router.py
|           |-- test_router.py    # Test for the router
|           |-- service.py
|           |-- test_service.py   # Test for the service
|           |-- schemas.py
|           |-- models.py
|           `-- graph_models.py
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

| Component         | Responsibility                                                                                |
| :---------------- | :-------------------------------------------------------------------------------------------- |
| `main.py`         | Creates and configures the main `FastAPI` instance.                                           |
| `core/`           | App-wide concerns (settings, security).                                                       |
| `db/`             | Contains isolated connection logic for each database.                                         |
| `router.py`       | **API Layer:** Handles HTTP requests and responses.                                           |
| `service.py`      | **Logic Layer:** Implements business rules.                                                   |
| `schemas.py`      | **Data Layer:** Defines pure Pydantic models for API I/O (when separate from DB models).      |
| `models.py`       | **Persistence Layer:** Defines SQLModel classes that serve as both DB tables and API schemas. |
| `graph_models.py` | **Persistence Layer:** Defines graph DB node/edge models.                                     |
| `test_*.py`       | **Testing Layer:** Verifies the correctness of a module.                                      |

## Consequences

### Positive

- **High Cohesion:** Feature-specific code and its tests are grouped together.
- **Test Proximity:** Locating tests next to source code improves discoverability and encourages consistent testing.
- **Polyglot Persistence:** Natively supports using the right database for the right task.
- **Scalability:** Adding new features is straightforward.
- **Unified Data Models:** SQLModel eliminates duplication between database models and API schemas, ensuring consistency and reducing maintenance overhead.
- **Type Safety:** Full type checking across database operations and API serialization.

### Negative

- **Source Directory Clutter:** Production and test code are mixed within the `app` directory.
- **Increased Complexity:** Managing services across multiple databases is inherently complex.
- **Packaging:** Requires explicit configuration to exclude test files from a production build artifact.
