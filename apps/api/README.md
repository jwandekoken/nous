# Nous API - The Semantic Memory Brain

The core intelligence layer of Nous, built with FastAPI and modular architecture. This service manages the Knowledge Graph (Apache AGE) and Vector Embeddings (Qdrant).

For setup and running instructions, please see the [Root README](../../README.md).

---

## Architecture

This project is built on two key architectural principles:

### 1. Modular / Feature-Based

Code is organized by **feature** rather than by technical layer.

- **Good:** `app/features/auth`, `app/features/graph`
- **Bad:** `app/controllers`, `app/services`

### 2. Clean Architecture

We strictly separate concerns using the Use Case pattern:

- **Routes** (`routes/`): Thin entry points. They validate input and call Use Cases.
- **Use Cases** (`usecases/`): Pure business logic. They do not know about HTTP or SQL.
- **Repositories** (`repositories/`): Data access. They hide the DB implementation details.

---

## Project Structure

```plaintext
apps/api/
├── app/
│   ├── main.py                    # FastAPI entrypoint
│   ├── core/                      # Shared utilities (Security, Config)
│   ├── db/                        # Database connections (Postgres, Qdrant)
│   └── features/                  # FEATURE MODULES
│       ├── auth/                  # Feature: Authentication
│       └── graph/                 # Feature: Knowledge Graph (The Core)
│           ├── dtos/              # Pydantic schemas (Input/Output)
│           ├── router.py          # Feature-level router
│           ├── routes/            # API Endpoints
│           ├── usecases/          # Business Logic
│           └── repositories/      # Data Access (AGE, Qdrant)
├── tests/                         # Mirrored test structure
└── pyproject.toml                 # Dependencies (managed by uv)
```

---

## Development

### Adding New Features

To add a new feature (e.g., `billing`):

1.  **Create the Directory:**

    ```bash
    mkdir -p app/features/billing
    ```

2.  **Add Standard Layers:**

    - `dtos/`: Request/Response models.
    - `routes/`: FastAPI endpoints.
    - `usecases/`: Business logic.
    - `router.py`: Expose routes to the main app.

3.  **Dependency Injection:**
    Inject Use Cases into Routes using FastAPI's `Depends`. This makes testing easy by allowing us to mock Use Cases.

### Testing

The test suite uses a dedicated test database to ensure complete isolation from your development database.

#### Running Tests

You can run tests from the root of the monorepo using `pnpm turbo test`, or directly from this directory using `uv`.

**Run all tests:**

```bash
uv run pytest tests/
```

**Run only integration tests (async):**

```bash
uv run pytest tests/ -m asyncio
```

_(Note: Most integration tests are async, so this marker effectively selects them.)_

**Run specific test file:**

```bash
uv run pytest tests/features/auth/usecases/test_signup_tenant_usecase_integration.py -v
```

**Run specific test case:**

```bash
uv run pytest tests/features/graph/usecases/test_assimilate_knowledge_usecase_integration.py::TestAssimilateKnowledgeUseCaseIntegration::test_assimilate_knowledge_basic -v -s
```

#### How It Works

- **Shared Fixtures:** `tests/conftest.py` manages the test database lifecycle.
- **Clean State:** Each test gets a clean graph (AGE) state via autouse fixtures.
- **Automatic Tables:** Tables are created once per test session from SQLAlchemy models.
- **Teardown:** The test database is automatically dropped after all tests complete.

#### Test Database Isolation

Tests use a separate PostgreSQL database (`multimodel_db_test` by default) to prevent data clashes with your development environment.

### Tools

We use modern Python tooling for code quality:

```bash
# Linting & Formatting
uv run ruff check app/
uv run ruff format app/

# Type Checking
uv run basedpyright app/
```
