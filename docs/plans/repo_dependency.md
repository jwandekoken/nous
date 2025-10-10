# Repository Dependency Inversion Plan

This document outlines the plan to invert dependencies for the repository layer, decoupling the use cases from the concrete implementation of the `ArcadedbRepository`.

## Step 1: Rename `GraphDB` to `ArcadeDB` and Introduce a DB Client Interface

1.  **Rename `GraphDB`:** In `app/db/arcadedb/client.py`, rename the `GraphDB` class to `ArcadeDB` to reflect its specific implementation.
2.  **Create DB Client Protocol:** Create a new file `app/db/base.py` and define a `DatabaseClient` protocol. This protocol will define the common methods for a database client, like `execute_command` and `execute_query`.
3.  **Implement Protocol:** Make the `ArcadeDB` class implement the `DatabaseClient` protocol.

## Step 2: Create a Generic Repository Interface

1.  **Create Repository Types:** Create a new file `app/features/graph/repositories/types.py`. Move all the `TypedDict` definitions (e.g., `CreateEntityResult`, `FindEntityResult`) from `app/features/graph/repositories/arcadedb_repository.py` into this new file. This will allow the interface to use them without depending on the concrete repository.
2.  **Create Repository Protocol:** Create a new file `app/features/graph/repositories/base.py` and define a `GraphRepository` protocol. This interface will declare all the public methods currently in `ArcadedbRepository` (e.g., `create_entity`, `find_entity_by_identifier`, `add_fact_to_entity`).
3.  **Implement Protocol:** Make `ArcadedbRepository` implement the `GraphRepository` protocol.

## Step 3: Update Use Cases to Depend on the Repository Interface

1.  **Update `AssimilateKnowledgeUseCaseImpl`:** In `app/features/graph/usecases/assimilate_knowledge_usecase.py`, change the type hint for the `repository` parameter in the `__init__` method from `ArcadedbRepository` to `GraphRepository`.
2.  **Update `GetEntityUseCaseImpl`:** In `app/features/graph/usecases/get_entity_usecase.py`, change the type hint for the `repository` parameter in the `__init__` method from `ArcadedbRepository` to `GraphRepository`.

## Step 4: Adjust Dependency Injection in `router.py`

1.  **Update `get_assimilate_knowledge_use_case`:** In `app/features/graph/router.py`, the dependency injection function for the assimilate use case will still instantiate `ArcadedbRepository`, but the use case it's injected into will now expect the `GraphRepository` interface. No significant code change is needed here, but it's an important part of the flow.
2.  **Update `get_get_entity_use_case`:** Similarly, the dependency injection for the get entity use case will continue to work as is, providing the concrete repository to a use case that now depends on the abstraction.
