use uv# ArcadeDB Integration Implementation Plan

## Overview

This document outlines the implementation plan for refactoring the `app/db/arcadedb/` package to use ArcadeDB's HTTP API instead of KuzuDB.

## Current State

The current implementation in `app/db/arcadedb/` is designed for KuzuDB API server with the following structure:

- `client.py`: GraphDB class with HTTP client for KuzuDB API
- `connection.py`: Global connection management
- `__init__.py`: Package exports

## Target Architecture

### ArcadeDB HTTP API Endpoints

We need to implement support for the following ArcadeDB HTTP API endpoints:

1. **Get server status** - `GET /api/v1/ready`

   - Returns server readiness status
   - Used for health checks and connection validation

2. **Get server information** - `GET /api/v1/server`

   - Returns detailed server information
   - Replaces current `get_schema()` functionality

3. **Execute a query** - `POST /api/v1/query/{database}`

   - Executes read-only queries (SELECT, MATCH, etc.)
   - Accepts query parameters and returns results

4. **Execute database command** - `POST /api/v1/command/{database}`
   - Executes write operations (CREATE, UPDATE, DELETE, etc.)
   - Used for data manipulation operations

## Implementation Plan

### Phase 1: Core Refactoring

#### 1.1 Update GraphDB Client Class

- **File**: `app/db/arcadedb/client.py`
- **Changes**:
  - Update docstrings to reference ArcadeDB instead of KuzuDB
  - Replace KuzuDB-specific endpoints with ArcadeDB HTTP API endpoints
  - Update `get_server_status()` to use `GET /api/v1/ready`
  - Update `get_schema()` to use `GET /api/v1/server`
  - Update `execute_query()` to use `POST /api/v1/query/{database}`
  - Add new method for command execution using `POST /api/v1/command/{database}`
  - Add database name parameter support for query/command endpoints

#### 1.2 Update Connection Management

- **File**: `app/db/arcadedb/connection.py`
- **Changes**:
  - Add database name configuration from settings
  - Update initialization to include database parameter
  - Ensure proper handling of database-specific endpoints

#### 1.3 Update Package Interface

- **File**: `app/db/arcadedb/__init__.py`
- **Changes**:
  - Update docstrings to reference ArcadeDB
  - Ensure all necessary exports remain available

### Phase 2: Configuration Updates

#### 2.1 Settings Configuration

- **File**: `app/core/settings.py`
- **Changes**:
  - Add `arcadedb_database` setting for database name
  - Update existing graph database settings to be ArcadeDB-specific
  - Ensure backward compatibility if needed

### Phase 3: Testing and Validation

#### 3.1 Unit Tests

- Update existing tests to work with ArcadeDB API
- Add tests for new command execution method
- Mock ArcadeDB HTTP responses for testing

#### 3.2 Integration Tests

- Update integration tests to use ArcadeDB endpoints
- Validate query and command execution
- Test error handling and authentication

### Phase 4: Migration and Deployment

#### 4.1 Data Migration

- Document any schema changes needed
- Provide migration scripts if necessary
- Update database initialization procedures

#### 4.2 Environment Configuration

- Update Docker/Kubernetes configurations
- Update environment variables documentation
- Provide ArcadeDB-specific deployment guides

## API Changes Summary

### New Methods

```python
async def execute_command(
    self,
    command: str,
    database: str,
    parameters: Any | None = None,
) -> Any:
    """Execute a database command (CREATE, UPDATE, DELETE, etc.)"""
```

### Updated Methods

```python
async def get_server_status(self) -> Any:
    """Get server status from /api/v1/ready"""

async def get_server_info(self) -> Any:
    """Get server information from /api/v1/server"""

async def execute_query(
    self,
    query: str,
    database: str,
    parameters: Any | None = None,
) -> Any:
    """Execute a query using /api/v1/query/{database}"""
```

## Configuration Requirements

### Environment Variables

```bash
ARCADEDB_API_URL=http://localhost:2480
ARCADEDB_DATABASE=graphdb
ARCADEDB_USERNAME=admin
ARCADEDB_PASSWORD=admin
```

### Settings Class Updates

```python
@dataclass
class Settings:
    # Existing fields...
    arcadedb_api_url: str = Field(default="http://localhost:2480")
    arcadedb_database: str = Field(default="graphdb")
    arcadedb_username: str | None = Field(default=None)
    arcadedb_password: str | None = Field(default=None)
```

## Error Handling

### HTTP Status Codes

- 200: Success
- 400: Bad Request (invalid query/command)
- 401: Unauthorized
- 403: Forbidden
- 404: Database not found
- 500: Internal Server Error

### Exception Handling

- Wrap HTTP errors in custom exceptions
- Provide meaningful error messages
- Handle connection timeouts and retries

## Security Considerations

- Ensure proper authentication handling
- Validate input parameters to prevent injection
- Use HTTPS in production environments
- Implement proper timeout configurations

## Performance Considerations

- Connection pooling for HTTP client
- Query result pagination for large datasets
- Caching strategies for frequently accessed data
- Monitoring and logging of API calls

## Rollback Plan

1. Keep old KuzuDB implementation as backup
2. Use feature flags to switch between implementations
3. Have database backup/restore procedures ready
4. Monitor application performance post-migration

## Success Criteria

- [ ] All ArcadeDB HTTP API endpoints implemented
- [ ] Existing functionality preserved
- [ ] Tests pass with new implementation
- [ ] Performance meets or exceeds current benchmarks
- [ ] Error handling robust and informative
- [ ] Documentation updated and accurate
