"""Graph database API routes - main router that includes all entity-specific route modules."""

from fastapi import APIRouter, Depends

from app.db.arcadedb.connection import get_graph_db
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
)
from app.features.graph.repositories import ArcadedbRepository
from app.features.graph.services.fact_extractor import LangChainFactExtractor
from app.features.graph.usecases import (
    AssimilateKnowledgeUseCase,
    AssimilateKnowledgeUseCaseImpl,
)

router = APIRouter(prefix="/graph", tags=["graph"])


# Create the fact extractor instance at module level to avoid instantiation issues
_fact_extractor = LangChainFactExtractor()


async def get_assimilate_knowledge_use_case() -> AssimilateKnowledgeUseCaseImpl:
    """Dependency injection for the assimilate knowledge use case."""

    db = await get_graph_db()
    return AssimilateKnowledgeUseCaseImpl(
        repository=ArcadedbRepository(db), fact_extractor=_fact_extractor
    )


@router.post("/entities/assimilate", response_model=AssimilateKnowledgeResponse)
async def assimilate_knowledge(
    request: AssimilateKnowledgeRequest,
    use_case: AssimilateKnowledgeUseCase = Depends(get_assimilate_knowledge_use_case),
) -> AssimilateKnowledgeResponse:
    """Assimilate knowledge by processing content and associating facts with an entity.

    This endpoint processes textual content, extracts facts, and associates them
    with the specified entity in the knowledge graph.
    """
    print(f"request: {request}")

    return await use_case.execute(request)
