# Nous API Tests

This directory contains the test suite for the Nous API.

## Test Types

Tests are organized into two main categories:

| Type            | File Suffix                  | Marker                     | Description                                                                   |
| --------------- | ---------------------------- | -------------------------- | ----------------------------------------------------------------------------- |
| **Unit**        | `test_<name>.py`             | `@pytest.mark.unit`        | Isolated tests with mocked dependencies. Fast, no external services required. |
| **Integration** | `test_<name>_integration.py` | `@pytest.mark.integration` | Tests that require external services (PostgreSQL, Qdrant, Google API).        |

## Running Tests

### All Tests

```bash
uv run pytest
```

### Only Integration Tests

```bash
uv run pytest -m integration
```

### Only Unit Tests

```bash
uv run pytest -m unit
```

### Exclude Integration Tests (faster)

```bash
uv run pytest -m "not integration"
```

### Run a Specific Test Module

```bash
uv run pytest tests/features/graph/usecases/test_get_entity_summary.py
```

### Run a Specific Test

```bash
uv run pytest tests/features/graph/usecases/test_get_entity_summary.py::TestGetEntitySummaryUseCase::test_returns_summary
```

## Directory Structure

```
tests/
├── conftest.py              # Shared fixtures (DB, Qdrant, etc.)
├── core/                    # Core module tests
├── db/                      # Database-level tests
│   └── postgres/            # PostgreSQL integration tests
├── features/                # Feature-specific tests
│   ├── auth/                # Authentication tests
│   │   └── usecases/        # Use case tests for auth
│   ├── graph/               # Knowledge graph tests
│   │   ├── repositories/    # Repository tests
│   │   ├── routes/          # HTTP endpoint tests
│   │   ├── services/        # Service layer tests
│   │   └── usecases/        # Use case tests
│   └── usage/               # Token usage tracking tests
└── utils/                   # Test utilities
```

## Prerequisites

Integration tests require the following services:

1. **PostgreSQL with Apache AGE** - Graph database
2. **Qdrant** - Vector database
3. **Google API Key** - For embedding and LLM calls

Configure via environment variables or `.env` file:

```bash
POSTGRES_HOST=localhost
POSTGRES_DB=test_db
QDRANT_URL=http://localhost:6333
GOOGLE_API_KEY=your-api-key
```

## Writing New Tests

### Integration Test Template

```python
"""Integration tests for MyFeature."""

import pytest

pytestmark = pytest.mark.integration

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_something(self, db_session, ...):
        ...
```

### Unit Test Template

```python
"""Unit tests for MyFeature."""

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

class TestMyFeature:
    def test_something(self):
        mock_repo = AsyncMock()
        ...
```

## Markers Reference

| Marker        | Description                           |
| ------------- | ------------------------------------- |
| `integration` | Requires external services (DB, APIs) |
| `unit`        | Isolated tests with mocks             |
| `slow`        | Long-running tests                    |
| `asyncio`     | Async tests (auto-detected)           |
