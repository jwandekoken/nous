"""Graph database API routes - main router that includes all entity-specific route modules."""

from fastapi import APIRouter, Depends

from app.db.arcadedb.connection import get_graph_db
from app.features.graph.dtos.knowledge_dto import (
    AssimilateKnowledgeRequest,
    AssimilateKnowledgeResponse,
)
from app.features.graph.repositories import ArcadedbRepository
from app.features.graph.usecases import (
    AssimilateKnowledgeUseCase,
    AssimilateKnowledgeUseCaseImpl,
)

router = APIRouter(prefix="/graph", tags=["graph"])


async def get_assimilate_knowledge_use_case() -> AssimilateKnowledgeUseCase:
    """Dependency injection for the assimilate knowledge use case."""

    # TODO: Replace with actual fact extractor service
    class StubFactExtractor:
        async def extract_facts(self, content: str) -> list[dict[str, str]]:
            """Stub implementation - returns empty list for now."""
            return []

    db = await get_graph_db()
    return AssimilateKnowledgeUseCaseImpl(
        repository=ArcadedbRepository(db), fact_extractor=StubFactExtractor()
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
