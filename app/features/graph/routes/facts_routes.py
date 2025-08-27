"""Fact-related API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.graph import GraphDB, get_graph_db
from app.features.graph.dtos import GetFactResponse
from app.features.graph.repositories import FactRepository
from app.features.graph.usecases.get_fact_usecase import GetFactUsecase

router = APIRouter()


# Dependency Injection Setup
async def get_graph() -> GraphDB:
    """Dependency to get the graph database connection."""
    return await get_graph_db()


def get_fact_repository(graph: GraphDB = Depends(get_graph)) -> FactRepository:  # pyright: ignore[reportCallInDefaultInitializer]
    """Dependency to get the fact repository."""
    return FactRepository(db=graph)


def get_get_fact_usecase(
    repo: FactRepository = Depends(get_fact_repository),  # pyright: ignore[reportCallInDefaultInitializer]
) -> GetFactUsecase:
    """Dependency to get the get fact usecase."""
    return GetFactUsecase(repo=repo)


@router.get("/facts/{fact_id}", response_model=GetFactResponse)
async def get_fact(
    fact_id: str,
    usecase: GetFactUsecase = Depends(get_get_fact_usecase),  # pyright: ignore[reportCallInDefaultInitializer]
) -> GetFactResponse:
    """Get a fact with its source information."""
    try:
        fact_data = await usecase.execute(fact_id)

        if not fact_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fact {fact_id} not found",
            )

        # For now, return the raw data structure - we'll improve this with proper models later
        return GetFactResponse(**fact_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving fact: {str(e)}",
        )
