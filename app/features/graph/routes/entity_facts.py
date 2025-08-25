"""Entity-Fact relationship API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.graph import GraphDB, get_graph_db
from app.features.graph.models import AddFactRequest, AddFactResponse
from app.features.graph.repositories import FactRepository
from app.features.graph.usecases.add_fact import AddFactUsecase

router = APIRouter()


# Dependency Injection Setup
async def get_graph() -> GraphDB:
    """Dependency to get the graph database connection."""
    return await get_graph_db()


def get_fact_repository(graph: GraphDB = Depends(get_graph)) -> FactRepository:
    """Dependency to get the fact repository."""
    return FactRepository(db=graph)


def get_add_fact_usecase(
    repo: FactRepository = Depends(get_fact_repository),
) -> AddFactUsecase:
    """Dependency to get the add fact usecase."""
    return AddFactUsecase(repo=repo)


@router.post("/entities/{entity_id}/facts", response_model=AddFactResponse)
async def add_fact_to_entity(
    entity_id: UUID,
    request: AddFactRequest,
    usecase: AddFactUsecase = Depends(get_add_fact_usecase),
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
