"""Entity-related API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.graph import GraphDB, get_graph_db
from app.features.graph.dtos import (
    AddFactRequest,
    AddFactResponse,
    CreateEntityRequest,
    CreateEntityResponse,
    GetEntityResponse,
    SearchEntitiesResponse,
)
from app.features.graph.repositories import EntityRepository, FactRepository
from app.features.graph.usecases.add_fact_usecase import AddFactUsecase
from app.features.graph.usecases.create_entity_usecase import CreateEntityUsecase
from app.features.graph.usecases.get_entity_usecase import GetEntityUsecase
from app.features.graph.usecases.search_entities_usecase import SearchEntitiesUsecase

router = APIRouter()


# Dependency Injection Setup
async def get_graph() -> GraphDB:
    """Dependency to get the graph database connection."""
    return await get_graph_db()


def get_entity_repository(graph: GraphDB = Depends(get_graph)) -> EntityRepository:  # pyright: ignore[reportCallInDefaultInitializer]
    """Dependency to get the entity repository."""
    return EntityRepository(db=graph)


def get_create_entity_usecase(
    repo: EntityRepository = Depends(get_entity_repository),  # pyright: ignore[reportCallInDefaultInitializer]
) -> CreateEntityUsecase:
    """Dependency to get the create entity usecase."""
    return CreateEntityUsecase(repo=repo)


def get_get_entity_usecase(
    repo: EntityRepository = Depends(get_entity_repository),  # pyright: ignore[reportCallInDefaultInitializer]
) -> GetEntityUsecase:
    """Dependency to get the get entity usecase."""
    return GetEntityUsecase(repo=repo)


def get_search_entities_usecase(
    repo: EntityRepository = Depends(get_entity_repository),  # pyright: ignore[reportCallInDefaultInitializer]
) -> SearchEntitiesUsecase:
    """Dependency to get the search entities usecase."""
    return SearchEntitiesUsecase(repo=repo)


def get_fact_repository(graph: GraphDB = Depends(get_graph)) -> FactRepository:  # pyright: ignore[reportCallInDefaultInitializer]
    """Dependency to get the fact repository."""
    return FactRepository(db=graph)


def get_add_fact_usecase(
    repo: FactRepository = Depends(get_fact_repository),  # pyright: ignore[reportCallInDefaultInitializer]
) -> AddFactUsecase:
    """Dependency to get the add fact usecase."""
    return AddFactUsecase(repo=repo)


@router.post(
    "/entities",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateEntityResponse,
)
async def create_entity(
    request: CreateEntityRequest,
    usecase: CreateEntityUsecase = Depends(get_create_entity_usecase),  # pyright: ignore[reportCallInDefaultInitializer]
) -> CreateEntityResponse:
    """Create a new entity with an identifier.

    This creates the canonical entity, its identifier, and the relationship between them.
    """
    try:
        entity, identifier = await usecase.execute(
            identifier_value=request.identifier_value,
            identifier_type=request.identifier_type,
            metadata=request.metadata,
        )

        return CreateEntityResponse(
            entity=entity, identifiers=[identifier], primary_identifier=identifier
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating entity: {str(e)}",
        )


@router.get("/entities/{entity_id}", response_model=GetEntityResponse)
async def get_entity(
    entity_id: UUID,
    usecase: GetEntityUsecase = Depends(get_get_entity_usecase),  # pyright: ignore[reportCallInDefaultInitializer]
) -> GetEntityResponse:
    """Get an entity with all its identifiers and facts."""
    try:
        entity_data = await usecase.execute(entity_id)

        if not entity_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        # For now, return the raw data structure - we'll improve this with proper models later
        return GetEntityResponse(**entity_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity: {str(e)}",
        )


@router.get("/entities", response_model=SearchEntitiesResponse)
async def search_entities(
    identifier_value: str | None = None,
    identifier_type: str | None = None,
    limit: int = 50,
    usecase: SearchEntitiesUsecase = Depends(get_search_entities_usecase),  # pyright: ignore[reportCallInDefaultInitializer]
) -> SearchEntitiesResponse:
    """Search for entities by identifier."""
    try:
        entities = await usecase.execute(
            identifier_value=identifier_value,
            identifier_type=identifier_type,
            limit=limit,
        )

        return SearchEntitiesResponse(entities=entities, total_count=len(entities))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching entities: {str(e)}",
        )


@router.post("/entities/{entity_id}/facts", response_model=AddFactResponse)
async def add_fact_to_entity(
    entity_id: UUID,
    request: AddFactRequest,
    usecase: AddFactUsecase = Depends(get_add_fact_usecase),  # pyright: ignore[reportCallInDefaultInitializer]
) -> AddFactResponse:
    """Add a fact to an existing entity with source information."""
    try:
        source_timestamp = None
        if request.source_timestamp:
            source_timestamp = datetime.fromisoformat(request.source_timestamp)

        fact, source, relationship = await usecase.execute(
            entity_id=entity_id,
            fact_name=request.fact_name,
            fact_type=request.fact_type,
            verb=request.verb,
            source_content=request.source_content,
            confidence_score=request.confidence_score,
            source_timestamp=source_timestamp,
        )

        return AddFactResponse(fact=fact, source=source, relationship=relationship)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding fact to entity: {str(e)}",
        )
