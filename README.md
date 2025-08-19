# Nous - FastAPI Modular Architecture

A FastAPI application built with a modular, feature-based architecture supporting multiple databases (PostgreSQL and KuzuDB Graph Database).

## Architecture

This project follows the modular architecture defined in [ADR-001](docs/architecture/adr_001_project_architecture.md), with inline tests co-located with source code.

## Project Structure

```plaintext
/nous-api/
├── app/
│   ├── main.py                    # FastAPI app instance
│   ├── core/                      # App-wide concerns
│   │   ├── security.py           # Authentication & security
│   │   ├── test_security.py      # Security tests
│   │   └── settings.py           # Configuration
│   ├── db/                       # Database connections
│   │   ├── postgres/             # PostgreSQL connection
│   │   └── graph/                # KuzuDB HTTP API client
│   └── features/                 # Feature modules
│       └── users/                # User feature
│           ├── router.py         # API endpoints
│           ├── test_router.py    # Router tests
│           ├── service.py        # Business logic
│           ├── test_service.py   # Service tests
│           ├── schemas.py        # Pydantic models
│           ├── models.py         # PostgreSQL models
│           └── graph_models.py   # KuzuDB models
└── pyproject.toml                # Dependencies & config
```

## Features

- ✅ **Modular Architecture**: Feature-based organization
- ✅ **Dual Database Support**: PostgreSQL + KuzuDB Graph Database
- ✅ **HTTP API Integration**: KuzuDB accessed via REST API calls using httpx
- ✅ **Authentication**: JWT-based auth with password hashing
- ✅ **Inline Tests**: Tests co-located with source code
- ✅ **Modern Python**: Type hints, async/await, Pydantic v2, SQLModel
- ✅ **Development Tools**: Ruff linting/formatting, basedpyright type checking, pytest

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL (optional, for full functionality)
- KuzuDB (optional, for graph features)
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

Run all tests:

```bash
uv run pytest app/
```

Run tests with coverage:

```bash
uv run pytest app/ --cov=app --cov-report=html
```

Run specific test file:

```bash
uv run pytest app/features/users/test_router.py -v
```

### Development Tools

**Format and lint code**:

```bash
uv run ruff format app/
uv run ruff check app/
```

**Fix linting issues automatically**:

```bash
uv run ruff check app/ --fix
```

**Type checking**:

```bash
uv run basedpyright app/
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

### PostgreSQL

1. **Create database**:

   ```sql
   CREATE DATABASE nous;
   ```

2. **Update connection settings in `.env`**:
   ```env
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_DB=nous
   ```

### KuzuDB Graph Database

1. **Setup KuzuDB** (optional):

   KuzuDB integration uses HTTP API calls, so no additional Python dependencies are required beyond `httpx` (already included).

   ```bash
   # Install KuzuDB server (follow official KuzuDB installation guide)
   # Or use KuzuDB cloud service
   ```

2. **Update connection settings in `.env`**:
   ```env
   KUZU_API_URL=http://localhost:8080
   KUZU_API_KEY=your_api_key
   KUZU_DATABASE=your_database_name
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
   - `graph_models.py` - KuzuDB models (if needed)

3. **Add inline tests**:

   - `test_router.py`
   - `test_service.py`

4. **Include router in main app**:
   ```python
   from app.features.your_feature.router import router
   app.include_router(router, prefix="/api/v1")
   ```

### Environment Variables

All configuration is handled through environment variables. See `.env.example` for available options.

## Contributing

1. Follow the naming conventions in [docs/naming_convention.md](docs/naming_convention.md)
2. Write tests for new features (inline with source code)
3. Use type hints for all functions
4. Follow the modular architecture patterns
5. Use `uv` for dependency management
