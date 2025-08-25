"""Entity-related API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.graph import GraphDB, get_graph_db
from app.features.graph.models import (
    CreateEntityRequest,
    CreateEntityResponse,
    GetEntityResponse,
    SearchEntitiesResponse,
)
from app.features.graph.repositories import EntityRepository
from app.features.graph.usecases.create_entity import CreateEntityUsecase
from app.features.graph.usecases.get_entity import GetEntityUsecase
from app.features.graph.usecases.search_entities import SearchEntitiesUsecase

router = APIRouter()


# Dependency Injection Setup
async def get_graph() -> GraphDB:
    """Dependency to get the graph database connection."""
    return await get_graph_db()


def get_entity_repository(graph: GraphDB = Depends(get_graph)) -> EntityRepository:
    """Dependency to get the entity repository."""
    return EntityRepository(db=graph)


def get_create_entity_usecase(
    repo: EntityRepository = Depends(get_entity_repository),
) -> CreateEntityUsecase:
    """Dependency to get the create entity usecase."""
    return CreateEntityUsecase(repo=repo)


def get_get_entity_usecase(
    repo: EntityRepository = Depends(get_entity_repository),
) -> GetEntityUsecase:
    """Dependency to get the get entity usecase."""
    return GetEntityUsecase(repo=repo)


def get_search_entities_usecase(
    repo: EntityRepository = Depends(get_entity_repository),
) -> SearchEntitiesUsecase:
    """Dependency to get the search entities usecase."""
    return SearchEntitiesUsecase(repo=repo)


@router.post(
    "/entities",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateEntityResponse,
)
async def create_entity(
    request: CreateEntityRequest,
    usecase: CreateEntityUsecase = Depends(get_create_entity_usecase),
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
    usecase: GetEntityUsecase = Depends(get_get_entity_usecase),
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
    usecase: SearchEntitiesUsecase = Depends(get_search_entities_usecase),
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
