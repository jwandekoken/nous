# Plan: `AgeRepository` Implementation and Integration Tests

This plan outlines the steps to implement `AgeRepository`, a PostgreSQL/AGE-based graph repository, and create a corresponding integration test suite. The new repository will conform to the `GraphRepository` protocol defined in `app/features/graph/repositories/base.py`.

## 1. `AgeRepository` Implementation

**File:** `app/features/graph/repositories/age_repository.py`

### 1.1. Class Definition

- Create a class `AgeRepository` that implements the `GraphRepository` protocol.
- The constructor will accept an `asyncpg.Pool` for database connections and store it as an instance variable.
- It will retrieve the AGE graph name from the application settings.

### 1.2. Helper for Cypher Execution

- A private helper method `_execute_cypher` will be created to simplify running queries.
- This helper will handle:
  - Acquiring a connection from the pool.
  - Setting up the transaction block.
  - Executing `LOAD 'age';` and `SET search_path = ag_catalog, "$user", public;`.
  - Executing the main Cypher query with parameters.
  - Formatting results from AGE's `agtype` format into standard Python types.
  - Releasing the connection.

### 1.3. Method Implementations

All methods from the `GraphRepository` protocol will be implemented using Cypher queries.

- **`create_entity`**:
  - Use `MERGE` on the `Identifier` node to ensure it's unique.
  - Use `CREATE` for the `Entity` node.
  - Use `CREATE` to establish the `HAS_IDENTIFIER` relationship.
  - It will be idempotent; if an entity with the identifier already exists, it will return the existing one.
- **`find_entity_by_identifier`**:
  - Use `MATCH` to find an `Entity` connected to a specific `Identifier`.
  - Use `OPTIONAL MATCH` to gather all associated `Fact` and `Source` nodes.
  - Aggregate the results into the `FindEntityResult` structure.
- **`find_entity_by_id`**:
  - Use `MATCH` to find an entity by its `id` property.
  - Use `OPTIONAL MATCH` to gather associated identifiers, facts, and sources.
- **`delete_entity_by_id`**:
  - Use `MATCH (e:Entity {id: $entity_id}) DETACH DELETE e` to remove the entity and all its relationships.
- **`add_fact_to_entity`**:
  - `MATCH` the existing `Entity`.
  - `MERGE` the `Fact` and `Source` nodes to avoid duplicates.
  - `CREATE` the `HAS_FACT` and `DERIVED_FROM` relationships. This operation will be idempotent.
- **`find_fact_by_id`**:
  - `MATCH` a `Fact` node by its `fact_id`.
  - `OPTIONAL MATCH` its connected `Source` node.

## 2. Integration Test Suite

**File:** `tests/features/graph/repositories/test_age_repository_integration.py`

### 2.1. Test Structure

- The test file will mirror the structure of `test_arcadedb_repository_integration.py`.
- A `TestAgeRepositoryIntegration` class will contain test cases for each repository method.

### 2.2. Fixtures

- **`postgres_pool`**: An `async` fixture to provide a database connection pool for the tests.
- **`age_repository`**: A fixture that instantiates `AgeRepository` with the `postgres_pool`.
- **`clean_graph_db`**: An `autouse=True` fixture that runs before each test to clear the graph, ensuring test isolation. It will execute `MATCH (n) DETACH DELETE n;`.
- **Test Data Fixtures**: Reuse existing fixtures like `test_entity`, `test_identifier`, etc., from `test_arcadedb_repository_integration.py`.

### 2.3. Test Cases

- Implement comprehensive tests for each method in `AgeRepository`.
- **`create_entity`**: Test basic creation and idempotency.
- **`find_entity_by_identifier`**: Test finding an existing entity and handling a non-existent one.
- **`find_entity_by_id`**: Test retrieval by ID and handling of non-existent IDs.
- **`delete_entity_by_id`**: Test successful deletion and attempting to delete a non-existent entity.
- **`add_fact_to_entity`**: Test adding a single fact, multiple facts, and idempotency.
- **`find_fact_by_id`**: Test finding an existing fact and handling a non-existent one.

## 3. Dependency Injection (Future Step)

- The dependency injection mechanism in `app/features/graph/router.py` will be updated to allow selecting the graph repository (`ArcadedbRepository` or `AgeRepository`) based on an environment variable in the settings. This will not be part of the initial implementation but is a necessary follow-up step.
