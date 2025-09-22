# API Implementation Plan: Assimilate Knowledge

This document outlines the design for a high-level API endpoint responsible for processing textual content, extracting facts, and associating them with an entity in the knowledge graph.

## Proposed API Endpoint

A `POST` endpoint is proposed to encapsulate the action of assimilating new knowledge for a given entity.

- **HTTP Method:** `POST`
- **Path:** `/api/v1/graph/entities/assimilate`
- **File Location:** `app/features/graph/router.py`

### Rationale

- **`POST` Method**: This operation creates new resources in the database (Facts, Sources, and their relationships) and is not idempotent, making `POST` the appropriate HTTP method.
- **Path**: The path `/entities/assimilate` clearly communicates that the action is performed on the collection of entities. The verb "assimilate" accurately describes the process of absorbing new information into the knowledge graph.

---

## API Contract (Data Models)

Pydantic models will be defined to ensure a clear and validated API contract. These models will be located in a new file: `app/features/graph/dtos/knowledge_dto.py`.

### Request Body

The request payload will contain the identifier for the entity and the content to be processed.

```python
# app/features/graph/dtos/knowledge_dto.py

from pydantic import BaseModel, Field
from datetime import datetime

class IdentifierPayload(BaseModel):
    """Payload for identifying an entity via an external identifier."""
    type: str = Field(..., description="Type of identifier (e.g., 'email', 'phone')")
    value: str = Field(..., description="The identifier value (e.g., 'user@example.com')")

class AssimilateKnowledgeRequest(BaseModel):
    """Request to process content and associate facts with an entity."""
    identifier: IdentifierPayload = Field(..., description="The entity's external identifier.")
    content: str = Field(..., description="The textual content to process.")
    timestamp: datetime | None = Field(
        default_factory=datetime.utcnow,
        description="The real-world timestamp of the content's creation."
    )
```

### Success Response

The response payload will confirm the successful operation by returning the entity, the source of the information, and the list of facts that were extracted.

```python
# app/features/graph/dtos/knowledge_dto.py (continued)
# EntityDto and FactDto are defined in this same file

class SourceDto(BaseModel):
    """DTO for a Source."""
    id: UUID
    content: str
    timestamp: datetime

class AssimilateKnowledgeResponse(BaseModel):
    """Response after successfully assimilating knowledge."""
    entity: EntityDto = Field(..., description="The entity the knowledge was assimilated for.")
    source: SourceDto = Field(..., description="The source created from the content.")
    extracted_facts: list[FactDto] = Field(..., description="A list of facts extracted and stored.")
```

---

## High-Level Workflow

The use case logic triggered by this endpoint will perform the following steps:

1.  **Find or Create Entity**: Use the provided `identifier` to look up an existing `Entity`. If no entity is found, create a new one.
2.  **Create Source**: Create a `Source` vertex from the `content` and `timestamp` provided in the request. This preserves the original context and ensures data provenance.
3.  **Extract Facts (NLP/AI Step)**: Pass the `content` to a fact-extraction service. This service will be responsible for identifying key pieces of information (e.g., using a large language model to extract subject-verb-object triplets).
4.  **Create and Link Facts**: For each piece of information extracted:
    - Create or retrieve the corresponding `Fact` vertex (e.g., `Fact(type='Location', name='Paris')`).
    - Create a `HasFact` edge to link the `Entity` to the new `Fact`.
    - Create a `DerivedFrom` edge to link the `HasFact` relationship back to the `Source`, providing clear traceability.
5.  **Return Response**: Construct and return the `AssimilateKnowledgeResponse` with DTOs representing the newly created or affected graph elements.
