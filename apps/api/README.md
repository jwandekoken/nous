# Nous - FastAPI Modular Architecture

A FastAPI application built with a modular, feature-based architecture supporting PostgreSQL AGE Graph Database.

## Architecture

This project follows a modular architecture, with tests properly separated from application code in a dedicated `tests/` directory.

## Project Structure

```plaintext
apps/api/
├── app/                          # Application source code
│   ├── main.py                    # FastAPI app instance
│   ├── core/                      # App-wide concerns
│   │   ├── security.py           # Authentication & security
│   │   └── settings.py           # Configuration
│   ├── db/                       # Database connections
│   │   ├── postgres/             # PostgreSQL AGE connection
│   └── features/                 # Feature modules
│       └── auth/                 # Example feature: Auth
│           ├── dtos/             # Data Transfer Objects (Request/Response)
│           ├── models.py         # Database models
│           ├── router.py         # Main feature router
│           ├── routes/           # API route handlers
│           └── usecases/         # Business logic (Clean Architecture)
├── tests/                        # Test suite (mirrors app structure)
│   ├── core/
│   ├── db/
│   ├── features/
│       └── auth/
│           └── usecases/
│               └── test_signup_tenant_usecase.py
└── pyproject.toml                # Dependencies & config
```

## Features

- ✅ **Modular Architecture**: Feature-based organization with Clean Architecture patterns (Use Cases)
- ✅ **Graph Database Support**: PostgreSQL AGE Graph Database
- ✅ **Database Integration**: PostgreSQL AGE accessed via native SQL queries
- ✅ **Authentication**: Cookie-based auth with password hashing
- ✅ **Test Suite**: Comprehensive test coverage with separated test directory
- ✅ **Modern Python**: Type hints, async/await, Pydantic v2, SQLAlchemy
- ✅ **Development Tools**: Ruff linting/formatting, basedpyright type checking, pytest

## Database Setup

For database setup (PostgreSQL with AGE extension), please refer to the [root README](../../README.md#how-to-start-the-database).

### Database Migrations

This project uses Alembic for database schema management. See the [migration documentation](migrations/README.md) for detailed instructions on creating, applying, and managing database migrations.

## Development

This project is part of a monorepo. For instructions on how to run the application, please refer to the [root README](../../README.md).

### Adding New Features

The project follows a Clean Architecture approach using **Use Cases**.

1. **Create feature directory**:

   ```bash
   mkdir -p app/features/your_feature
   ```

2. **Add the standard structure**:

   - `dtos/` - Pydantic models for Requests and Responses
   - `models.py` - Database models (SQLAlchemy/SQLModel)
   - `router.py` - Main router that includes sub-routers from `routes/`
   - `routes/` - API route handlers. These should be thin wrappers that delegate to Use Cases.
   - `usecases/` - Business logic implementations.

3. **Implement the Use Case Pattern**:

   - Define a **Protocol** for your use case in the route file or a separate interface file.
   - Implement the use case in `usecases/`.
   - Inject the use case into the route handler using FastAPI's `Depends`.

   **Example Route (`routes/items.py`)**:

   ```python
   from typing import Protocol
   from fastapi import APIRouter, Depends
   from app.features.your_feature.dtos import CreateItemRequest, ItemResponse

   class CreateItemUseCase(Protocol):
       async def execute(self, request: CreateItemRequest) -> ItemResponse: ...

   async def get_create_item_use_case() -> CreateItemUseCase:
       return CreateItemUseCaseImpl(...)

   @router.post("/items")
   async def create_item(
       request: CreateItemRequest,
       use_case: CreateItemUseCase = Depends(get_create_item_use_case)
   ):
       return await use_case.execute(request)
   ```

4. **Include router in main app**:
   ```python
   from app.features.your_feature.router import router
   app.include_router(router, prefix="/api/v1")
   ```

### Testing

The test suite uses a dedicated test database to ensure complete isolation from your development database.

#### Running Tests

You can run tests from the root of the monorepo using `pnpm turbo test`, or directly from this directory using `uv`:

Run all tests:

```bash
uv run pytest tests/
```

Run tests with coverage:

```bash
uv run pytest tests/ --cov=app --cov-report=html
```

Run specific test file:

```bash
uv run pytest tests/features/auth/usecases/test_signup_tenant_usecase_integration.py -v
```

Run only integration tests:

```bash
uv run pytest tests/ -m asyncio -v
```

#### Integration Tests

Integration tests use real database connections and test the full stack:

```bash
# Run all graph repository integration tests
uv run pytest tests/features/graph/repositories/test_age_repository_integration.py -v

# Run auth integration tests
uv run pytest tests/features/auth/usecases/test_signup_tenant_usecase_integration.py -v

# Run specific test with detailed output
uv run pytest tests/features/graph/usecases/test_assimilate_knowledge_usecase_integration.py::TestAssimilateKnowledgeUseCaseIntegration::test_assimilate_knowledge_basic -v -s
```

**How It Works**:

- Shared fixtures in `tests/conftest.py` manage the test database lifecycle
- Each test gets a clean graph (AGE) state via autouse fixtures
- Tables are created once per test session from models
- Test database is automatically dropped after all tests complete

#### Test Database Isolation

Tests use a separate PostgreSQL database (`multimodel_db_test` by default) with the following features:

- **Automatic setup**: Test database is created automatically when tests run
- **Schema sync**: Tables are created from SQLAlchemy models (no migrations needed)
- **AGE support**: AGE extension is installed and configured automatically
- **Clean slate**: All data is cleaned between tests
- **Safe teardown**: Test database is dropped after tests complete

### Development Tools

**Format and lint code**:

```bash
uv run ruff format app/
uv run ruff check app/ tests/
```

**Type checking**:

```bash
uv run basedpyright app/ tests/
```

## Contributing

1. Follow the naming conventions in [docs/naming_convention.md](docs/naming_convention.md)
2. Write tests for new features in the `tests/` directory (mirroring the `app/` structure)
3. Use type hints for all functions
4. Follow the modular architecture patterns
5. Use `uv` for dependency management
