<!-- ca250ada-87c4-43ce-bba9-252d0e84ee3c 3c1bc412-8f58-446a-889b-43b1ca821d03 -->

# Plan: Implement Get Entity Endpoint

Here is the plan to create the new endpoint for fetching entity information.

### 1. Create Data Transfer Objects (DTOs)

I'll start by creating the necessary Pydantic models for the API response in `app/features/graph/dtos/knowledge_dto.py`. These DTOs will mirror the structure of `FindEntityResult` from the repository layer, ensuring a consistent and well-defined API contract.

```python:app/features/graph/dtos/knowledge_dto.py
class IdentifierDto(BaseModel):
    """DTO for an Identifier."""
    value: str = Field(..., description="The identifier value (e.g., 'user@example.com')")
    type: str = Field(..., description="Type of identifier (e.g., 'email', 'phone', 'username')")

class HasIdentifierDto(BaseModel):
    """DTO for the relationship between an Entity and an Identifier."""
    is_primary: bool = Field(..., description="Whether this is the primary identifier for the entity")
    created_at: datetime = Field(..., description="When this relationship was established")

class IdentifierWithRelationshipDto(BaseModel):
    """DTO grouping an identifier with its relationship to the entity."""
    identifier: IdentifierDto
    relationship: HasIdentifierDto

class FactWithSourceDto(BaseModel):
    """DTO grouping a fact with its relationship and source."""
    fact: FactDto
    relationship: HasFactDto
    source: SourceDto | None = Field(None, description="The source of the fact, if available.")

class GetEntityResponse(BaseModel):
    """Response for getting an entity by identifier."""
    entity: EntityDto
    identifier: IdentifierWithRelationshipDto
    facts: list[FactWithSourceDto]
```

### 2. Implement the "Get Entity" Use Case

Next, I will create a new use case to handle the business logic. I'll create a new file `app/features/graph/usecases/get_entity_usecase.py`. This use case will:

- Receive an identifier type and value.
- Call the `find_entity_by_identifier` method in `ArcadedbRepository`.
- If the entity is not found, it will raise an appropriate HTTP exception (404 Not Found).
- If the entity is found, it will map the repository's result into the `GetEntityResponse` DTO.

### 3. Add the Endpoint to the Router

Finally, I'll expose this functionality by adding a new endpoint to `app/features/graph/router.py`.

- The endpoint will be `GET /graph/entities/lookup`.
- It will use query parameters `type` and `value` for the identifier.
- I will add a dependency injection provider for the `GetEntityUseCase`.

This approach reuses existing data-fetching logic, maintains a clean separation of concerns, and provides a robust and well-defined API for clients.
