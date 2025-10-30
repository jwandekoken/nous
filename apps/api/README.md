# Nous - FastAPI Modular Architecture

A FastAPI application built with a modular, feature-based architecture supporting PostgreSQL AGE Graph Database.

## Architecture

This project follows the modular architecture defined in [Project-architecture](docs/project_architecture.md), with tests properly separated from application code in a dedicated `tests/` directory.

## Project Structure

```plaintext
/nous-api/
├── app/                          # Application source code
│   ├── main.py                    # FastAPI app instance
│   ├── core/                      # App-wide concerns
│   │   ├── security.py           # Authentication & security
│   │   └── settings.py           # Configuration
│   ├── db/                       # Database connections
│   │   ├── postgres/             # PostgreSQL AGE connection
│   └── features/                 # Feature modules
│       └── graph/                # Graph feature
│           ├── models/           # Domain models
│           ├── repositories/     # Data access layer
│           ├── routes/           # API endpoints
│           └── usecases/         # Business logic
├── tests/                        # Test suite (mirrors app structure)
│   ├── core/
│   │   └── test_security.py      # Security tests
│   ├── db/
│   │   └── graph/
│   │       └── test_graph.py     # Graph database tests
│   └── features/
│       └── graph/
│           └── repositories/
│               └── test_entity_repository_integration.py
└── pyproject.toml                # Dependencies & config
```

## Features

- ✅ **Modular Architecture**: Feature-based organization
- ✅ **Graph Database Support**: PostgreSQL AGE Graph Database
- ✅ **Database Integration**: PostgreSQL AGE accessed via native SQL queries
- ✅ **Authentication**: JWT-based auth with password hashing
- ✅ **Test Suite**: Comprehensive test coverage with separated test directory
- ✅ **Modern Python**: Type hints, async/await, Pydantic v2, SQLModel
- ✅ **Development Tools**: Ruff linting/formatting, basedpyright type checking, pytest

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL with AGE extension (required, for graph database features)
- `uv` package manager

### Installation

1. **Clone and setup**:

   ```bash
   git clone <repository>
   cd nous-api
   ```

2. **Install dependencies using uv**:

   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

### Running the Application

**Development server (recommended)**:

```bash
uv run fastapi dev app/main.py
```

**Alternative methods**:

```bash
# Using uvicorn directly
uv run uvicorn app.main:app --reload

# Using the main module
uv run python -m app.main
```

The API will be available at:

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Testing

The test suite uses a dedicated test database to ensure complete isolation from your development database. Tests automatically create and tear down the test database, making them safe to run at any time.

#### Test Database Isolation

Tests use a separate PostgreSQL database (`multimodel_db_test` by default) with the following features:

- **Automatic setup**: Test database is created automatically when tests run
- **Schema sync**: Tables are created from SQLAlchemy models (no migrations needed)
- **AGE support**: AGE extension is installed and configured automatically
- **Clean slate**: All data is cleaned between tests
- **Safe teardown**: Test database is dropped after tests complete

Your development database (`multimodel_db`) is never touched by tests.

#### Configuration

The test database is configured via environment variables or settings:

```bash
# Optional: Create .env.test for custom test configuration
TESTING=true
POSTGRES_DB=multimodel_db_test
POSTGRES_USER=admin
POSTGRES_PASSWORD=supersecretpassword
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

The `TESTING=true` flag automatically switches to the test database.

#### Running Tests

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

### Development Tools

**Format and lint code**:

```bash
uv run ruff format app/
uv run ruff check app/ tests/
```

**Fix linting issues automatically**:

```bash
uv run ruff check app/ tests/ --fix
```

**Type checking**:

```bash
uv run basedpyright app/ tests/
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/token` - Login and get access token

### Users

- `POST /api/v1/users/` - Create new user
- `GET /api/v1/users/me` - Get current user info
- `GET /api/v1/users/` - List users (authenticated)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user
- `POST /api/v1/users/{user_id}/friends/{friend_id}` - Add friend
- `GET /api/v1/users/{user_id}/friends` - Get user's friends

### Health

- `GET /health` - Health check

## Database Setup

### PostgreSQL AGE Graph Database

1. **Setup PostgreSQL with AGE extension** (required):

   The application uses PostgreSQL with the AGE extension for graph database functionality.

   ```bash
   # Install PostgreSQL and AGE extension (see compose/postgres/ for Docker setup)
   # Or use a PostgreSQL service with AGE extension installed
   ```

2. **Database Migrations**:

   This project uses Alembic for database schema management. See the [migration documentation](migrations/README.md) for detailed instructions on creating, applying, and managing database migrations.

3. **Update connection settings in `.env`**:
   ```env
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=supersecretpassword
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=multimodel_db
   AGE_GRAPH_NAME=nous
   ```

## Development

### Adding New Features

1. **Create feature directory**:

   ```bash
   mkdir -p app/features/your_feature
   ```

2. **Add the standard files**:

   - `router.py` - API endpoints
   - `service.py` - Business logic
   - `schemas.py` - Pydantic models
   - `models.py` - SQLModel database models
   - `graph_models.py` - PostgreSQL AGE models (if needed)

3. **Add corresponding tests in `tests/` directory**:

   Create the test directory structure:

   ```bash
   mkdir -p tests/features/your_feature
   ```

   Add test files:

   - `tests/features/your_feature/test_router.py`
   - `tests/features/your_feature/test_service.py`

4. **Include router in main app**:
   ```python
   from app.features.your_feature.router import router
   app.include_router(router, prefix="/api/v1")
   ```

### Environment Variables

All configuration is handled through environment variables. See `.env.example` for available options.

## Contributing

1. Follow the naming conventions in [docs/naming_convention.md](docs/naming_convention.md)
2. Write tests for new features in the `tests/` directory (mirroring the `app/` structure)
3. Use type hints for all functions
4. Follow the modular architecture patterns
5. Use `uv` for dependency management
