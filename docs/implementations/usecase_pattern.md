Of course. You are absolutely correct. To properly refactor your code into the Usecase pattern, we will create two new layers: the **Repository** layer for all database interactions and the **Usecase** layer for all business logic.

This is an excellent architectural decision that will make your application much more scalable, testable, and maintainable.

Here is a comprehensive, step-by-step plan to transform your current router file into a clean, three-layer architecture.

### **Phase 1: Create the Repository Layer**

First, we will extract all database logic into a single `GraphRepository` class. This class will be the only part of your application that knows how to write and execute Cypher queries.

**Action:** Create a new file: `app/features/graph/repository.py`.

```python
# app/features/graph/repository.py

from typing import Any
from uuid import UUID
from app.db.graph import GraphDB
from app.features.graph.graph_models import Entity, Identifier, HasIdentifier, Fact, Source, HasFact

class GraphRepository:
    """Handles all direct database interactions for the graph."""
    def __init__(self, db: GraphDB):
        self.db = db

    async def create_entity(self, entity: Entity, identifier: Identifier, rel: HasIdentifier) -> bool:
        query = """
        MERGE (i:Identifier {value: $id_val}) ON CREATE SET i.type = $id_type
        CREATE (e:Entity {id: $e_id, created_at: $e_cat, metadata: $e_meta})
        CREATE (e)-[:HAS_IDENTIFIER {is_primary: $is_p, created_at: $rel_cat}]->(i)
        RETURN e.id
        """
        params = {
            "id_val": identifier.value, "id_type": identifier.type,
            "e_id": str(entity.id), "e_cat": entity.created_at, "e_meta": entity.metadata,
            "is_p": rel.is_primary, "rel_cat": rel.created_at,
        }
        result = await self.db.execute_query(query, params)
        return result.get("success", False)

    async def find_entity_by_id(self, entity_id: UUID) -> dict[str, Any] | None:
        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[:HAS_IDENTIFIER]->(i:Identifier)
        OPTIONAL MATCH (e)-[hf:HAS_FACT]->(f:Fact)
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        RETURN e,
               collect(DISTINCT i) as identifiers,
               collect(DISTINCT {fact: f, source: s, relationship: hf}) as facts_with_sources
        """
        result = await self.db.execute_query(query, {"entity_id": str(entity_id)})
        return result["data"][0] if result.get("data") else None

    async def add_fact_to_entity(self, entity_id: UUID, fact: Fact, source: Source, has_fact: HasFact) -> bool:
        query = """
        MATCH (e:Entity {id: $entity_id})
        MERGE (f:Fact {fact_id: $fact_id}) ON CREATE SET f.name = $fact_name, f.type = $fact_type
        MERGE (s:Source {id: $source_id}) ON CREATE SET s.content = $source_content, s.timestamp = $source_timestamp
        CREATE (e)-[hf:HAS_FACT {verb: $verb, confidence_score: $cs, created_at: $hf_cat}]->(f)
        CREATE (f)-[:DERIVED_FROM]->(s)
        RETURN hf
        """
        params = {
            "entity_id": str(entity_id),
            "fact_id": fact.fact_id, "fact_name": fact.name, "fact_type": fact.type,
            "source_id": str(source.id), "source_content": source.content, "source_timestamp": source.timestamp,
            "verb": has_fact.verb, "cs": has_fact.confidence_score, "hf_cat": has_fact.created_at,
        }
        result = await self.db.execute_query(query, params)
        return result.get("success", False)

    async def find_entities(self, identifier_value: str | None, identifier_type: str | None, limit: int) -> list[dict[str, Any]]:
        if identifier_value:
            query = f"""
            MATCH (e:Entity)-[:HAS_IDENTIFIER]->(i:Identifier {{value: $id_val}})
            { "WHERE i.type = $id_type" if identifier_type else "" }
            RETURN e, collect(i) as identifiers LIMIT $limit
            """
            params = {"id_val": identifier_value, "limit": limit}
            if identifier_type:
                params["identifier_type"] = identifier_type
        else:
            query = """
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[:HAS_IDENTIFIER]->(i:Identifier)
            RETURN e, collect(i) as identifiers LIMIT $limit
            """
            params = {"limit": limit}
        result = await self.db.execute_query(query, params)
        return result.get("data", [])

    async def find_fact_by_id(self, fact_id: str) -> dict[str, Any] | None:
        query = """
        MATCH (f:Fact {fact_id: $fact_id})
        OPTIONAL MATCH (f)-[:DERIVED_FROM]->(s:Source)
        OPTIONAL MATCH (e:Entity)-[:HAS_FACT]->(f)
        RETURN f, s, collect(e) as entities
        """
        result = await self.db.execute_query(query, {"fact_id": fact_id})
        return result["data"][0] if result.get("data") else None
```

### **Phase 2: Create the Usecase Layer**

Now, create a dedicated class for each business operation. This makes your logic modular and easy to test.

**Action:** Create a new directory `app/features/graph/usecases/`. Inside it, create a file for each usecase. We'll start with `create_entity.py` and `add_fact.py`.

```python
# app/features/graph/usecases/create_entity.py

from typing import Any
from app.features.graph.repository import GraphRepository
from app.features.graph.graph_models import Entity, Identifier, create_entity_with_identifier

class CreateEntityUsecase:
    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(self, value: str, type: str, meta: dict | None) -> tuple[Entity, Identifier]:
        entity, identifier, rel = create_entity_with_identifier(value, type, meta)
        success = await self.repo.create_entity(entity, identifier, rel)
        if not success:
            raise ValueError("Failed to persist entity in the database.")
        return entity, identifier

# You would create similar files for other usecases, e.g., get_entity.py
# app/features/graph/usecases/add_fact.py

from uuid import UUID
from datetime import datetime
from app.features.graph.repository import GraphRepository
from app.features.graph.graph_models import Fact, Source, HasFact, create_fact_with_source

class AddFactUsecase:
    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def execute(self, entity_id: UUID, name: str, type: str, verb: str, content: str, score: float, timestamp: datetime | None):
        fact, source, _ = create_fact_with_source(name, type, content, timestamp)
        has_fact = HasFact(from_entity_id=entity_id, to_fact_id=fact.fact_id, verb=verb, confidence_score=score)
        success = await self.repo.add_fact_to_entity(entity_id, fact, source, has_fact)
        if not success:
            raise ValueError("Failed to add fact to entity.")
        return fact, source, has_fact
```

### **Phase 3: Update Pydantic Models for API Contracts**

To make your API robust and self-documenting, define explicit request and response models.

**Action:** Update your `app/features/graph/graph_models.py` file.

```python
# app/features/graph/graph_models.py

# ... keep all your existing models ...

# Add these new models for API input/output
class CreateEntityRequest(BaseModel):
    identifier_value: str
    identifier_type: str
    metadata: dict[str, Any] | None = None

class CreateEntityResponse(GraphBaseModel):
    entity: Entity
    primary_identifier: Identifier

class AddFactRequest(BaseModel):
    fact_name: str
    fact_type: str
    verb: str
    source_content: str
    confidence_score: float = 1.0
    source_timestamp: datetime | None = None

class AddFactResponse(GraphBaseModel):
    message: str = "Fact added successfully"
    fact: Fact
    source: Source
    relationship: HasFact

# ... add other response models as needed, e.g., GetEntityResponse
```

### **Phase 4: Refactor the Router Layer**

Finally, simplify your router file. Its only job is to handle HTTP concerns and call the appropriate usecase.

**Action:** Replace the content of your router file with this refactored version.

```python
# app/features/graph/routes.py (the refactored version)

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.db.graph import GraphDB, get_graph_db
from app.features.graph.repository import GraphRepository
from app.features.graph.usecases.create_entity import CreateEntityUsecase
from app.features.graph.usecases.add_fact import AddFactUsecase
# ... import other usecases as you create them
from app.features.graph.graph_models import (
    CreateEntityRequest, CreateEntityResponse,
    AddFactRequest, AddFactResponse,
)

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

# --- Dependency Injection Setup ---
async def get_graph() -> GraphDB:
    return await get_graph_db()

def get_repository(graph: GraphDB = Depends(get_graph)) -> GraphRepository:
    return GraphRepository(db=graph)

def get_create_entity_usecase(repo: GraphRepository = Depends(get_repository)) -> CreateEntityUsecase:
    return CreateEntityUsecase(repo=repo)

def get_add_fact_usecase(repo: GraphRepository = Depends(get_repository)) -> AddFactUsecase:
    return AddFactUsecase(repo=repo)
# ... add dependency providers for other usecases

# --- Endpoints ---
@router.post("/entities", status_code=status.HTTP_201_CREATED, response_model=CreateEntityResponse)
async def create_entity(
    request: CreateEntityRequest,
    usecase: CreateEntityUsecase = Depends(get_create_entity_usecase),
) -> CreateEntityResponse:
    try:
        entity, identifier = await usecase.execute(
            value=request.identifier_value,
            type=request.identifier_type,
            meta=request.metadata,
        )
        return CreateEntityResponse(entity=entity, primary_identifier=identifier)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/entities/{entity_id}/facts", status_code=status.HTTP_201_CREATED, response_model=AddFactResponse)
async def add_fact_to_entity(
    entity_id: UUID,
    request: AddFactRequest,
    usecase: AddFactUsecase = Depends(get_add_fact_usecase),
) -> AddFactResponse:
    try:
        fact, source, rel = await usecase.execute(
            entity_id=entity_id,
            name=request.fact_name,
            type=request.fact_type,
            verb=request.verb,
            content=request.source_content,
            score=request.confidence_score,
            timestamp=request.source_timestamp,
        )
        return AddFactResponse(fact=fact, source=source, relationship=rel)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

# ... refactor other endpoints (GET, SEARCH) following the same pattern ...
```

This plan provides a clear path to a much cleaner and more professional application structure. You can now continue this pattern for the remaining `GET` endpoints.
