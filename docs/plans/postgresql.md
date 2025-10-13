### \#\# 🚀 Implementation Plan: PostgreSQL + AGE + PGVector

Here is a step-by-step plan to integrate the new database while leveraging your existing repository protocol.

### \#\#\# Step 1: Project Scaffolding

First, create the necessary files and directories for the new PostgreSQL connection logic, mirroring the existing `arcadedb` structure.

1.  **Create the PostgreSQL DB directory**:

    ```bash
    mkdir -p app/db/postgres
    ```

2.  **Create the connection files**:

    ```bash
    touch app/db/postgres/__init__.py
    touch app/db/postgres/connection.py
    ```

    - The `connection.py` file will manage the `asyncpg` connection pool.

3.  **Create the new repository file**:

    ```bash
    touch app/features/graph/repositories/age_repository.py
    ```

4.  **Create the new schema setup script**:

    ```bash
    touch scripts/setup_postgres_schema.py
    ```

### \#\#\# Step 2: Implement the Database Connection

You'll need an asynchronous driver for PostgreSQL. **`asyncpg`** is the recommended choice for its performance with FastAPI.

1.  **Add `asyncpg` to your dependencies** in `pyproject.toml`:

    ```toml
    # pyproject.toml

    [project]
    dependencies = [
        # ... other dependencies
        "asyncpg>=0.30.0",
    ]
    ```

    Then run `uv sync` to install it.

2.  **Update `app/core/settings.py`** with PostgreSQL-specific connection settings.

3.  **Implement `app/db/postgres/connection.py`** to manage a connection pool. This will replace the logic from `app/db/arcadedb/connection.py`.

    ```python
    # app/db/postgres/connection.py
    import asyncpg
    from app.core.settings import get_settings

    _pool: asyncpg.Pool | None = None

    async def get_db_pool() -> asyncpg.Pool:
        """Get the database connection pool as a dependency."""
        global _pool
        if _pool is None:
            settings = get_settings()
            _pool = await asyncpg.create_pool(
                dsn=settings.postgres_dsn, # Add POSTGRES_DSN to your Settings
                min_size=5,
                max_size=20
            )
        return _pool

    async def close_db_pool() -> None:
        """Close the database connection pool."""
        global _pool
        if _pool:
            await _pool.close()
            _pool = None
    ```

### \#\#\# Step 3: Create the Schema Setup Script

This script will initialize the database, create the necessary extensions, and set up the graph schema as defined in your `docs/graph_db_schema_age.md`.

- In `scripts/setup_postgres_schema.py`, write a script that connects using `asyncpg` and executes the following commands:
  1.  `CREATE EXTENSION IF NOT EXISTS age;`
  2.  `CREATE EXTENSION IF NOT EXISTS vector;`
  3.  `LOAD 'age';`
  4.  `SET search_path = ag_catalog, "$user", public;`
  5.  `SELECT create_graph('knowledge_graph');`
  6.  Execute the `CREATE UNIQUE INDEX` commands from your `graph_db_schema_age.md` documentation to define constraints on your vertices.

### \#\#\# Step 4: Implement the `AgeRepository`

This is the core of the work. The goal is to create `AgeRepository` that perfectly implements the `GraphRepository` protocol from `app/features/graph/repositories/base.py`. This ensures you can swap it in without changing any of the use case logic.

In `app/features/graph/repositories/age_repository.py`:

```python
# app/features/graph/repositories/age_repository.py
import asyncpg
from app.features.graph.models import Entity, Fact, ...
from app.features.graph.repositories.base import GraphRepository
from app.features.graph.repositories.types import CreateEntityResult, ...

class AgeRepository(GraphRepository):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.graph_name = "knowledge_graph" # Or from settings

    async def create_entity(
        self, entity: Entity, identifier: Identifier, relationship: HasIdentifier
    ) -> CreateEntityResult:
        async with self.pool.acquire() as conn:
            # Use AGE's cypher() function within a SQL query
            # Use parameterized queries ($1, $2) to prevent SQL injection
            cypher_query = """
                CREATE (e:Entity {id: $1, created_at: $2, metadata: $3}),
                       (i:Identifier {value: $4, type: $5}),
                       (e)-[:HAS_IDENTIFIER {is_primary: $6, created_at: $7}]->(i)
            """
            await conn.fetchval(
                f"SELECT * FROM cypher('{self.graph_name}', $1, $2) as (v agtype);",
                cypher_query,
                # Parameters passed as a JSON string for agtype
                f'{{
                    "p1": "{entity.id}", "p2": "{entity.created_at}", ...
                }}'
            )
            # Return the created models...

    # ... implement all other methods from the GraphRepository protocol ...
```

**PGVector Integration**:
To use pgvector, you would add a `vector` property to your `Fact` or `Source` vertices in the schema script:

```sql
-- In your setup script
SELECT * FROM cypher('knowledge_graph', $$
    MATCH (f:Fact) SET f.vector = <some_vector_value>
$$) AS (v agtype);
```

Your repository could then have methods for vector similarity search using standard SQL and pgvector operators like `<->`.

### \#\#\# Step 5: Update Dependency Injection

Now, simply tell your application to use the new `AgeRepository`.

In `app/features/graph/router.py`, update the dependency injection functions to provide the `AgeRepository` instead of the `ArcadedbRepository`.

```python
# app/features/graph/router.py

# --- BEFORE ---
# from app.features.graph.repositories.arcadedb_repository import ArcadedbRepository
# async def get_assimilate_knowledge_use_case() -> AssimilateKnowledgeUseCase:
#     db = await get_graph_db()
#     return AssimilateKnowledgeUseCaseImpl(
#         repository=ArcadedbRepository(db), ...
#     )

# --- AFTER ---
from app.db.postgres.connection import get_db_pool
from app.features.graph.repositories.age_repository import AgeRepository # Import the new repo

async def get_assimilate_knowledge_use_case() -> AssimilateKnowledgeUseCase:
    """Dependency injection for the assimilate knowledge use case."""
    pool = await get_db_pool() # Get the new connection pool
    return AssimilateKnowledgeUseCaseImpl(
        repository=AgeRepository(pool), fact_extractor=_fact_extractor
    )

async def get_get_entity_use_case() -> GetEntityUseCase:
    """Dependency injection for the get entity use case."""
    pool = await get_db_pool() # Get the new connection pool
    return GetEntityUseCaseImpl(repository=AgeRepository(pool))

```

### \#\#\# Step 6: Test the New Implementation

1.  **Create New Integration Tests**: Create `tests/features/graph/repositories/test_age_repository_integration.py` by copying and adapting `test_arcadedb_repository_integration.py`. The tests should verify the same behaviors against the PostgreSQL database.
2.  **Run Existing Use Case Tests**: Because you only swapped the repository implementation behind a consistent protocol, your high-level use case integration tests in `tests/features/graph/usecases/` should pass with minimal to no changes. This validates the power of your current architecture\!

### \#\#\# Step 7: Final Cleanup

Once all tests are passing and you have fully migrated:

1.  Delete the `app/db/arcadedb/` directory.
2.  Delete `app/features/graph/repositories/arcadedb_repository.py`.
3.  Delete the corresponding tests for the ArcadeDB repository.
4.  Update your `README.md` and any other documentation to reflect the new PostgreSQL/AGE setup.
