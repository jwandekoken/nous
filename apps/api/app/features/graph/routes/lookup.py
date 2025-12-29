"""Entity lookup route handler."""

from typing import Protocol

from fastapi import APIRouter, Depends

from app.core.authorization import TenantInfo, get_tenant_info
from app.db.postgres.graph_connection import get_graph_db_pool
from app.features.graph.dtos.knowledge_dto import (
    GetEntityResponse,
    GetEntitySummaryResponse,
)
from app.features.graph.repositories.age_repository import AgeRepository
from app.features.graph.services.langchain_data_summarizer import (
    LangChainDataSummarizer,
)
from app.features.graph.usecases import GetEntityUseCaseImpl
from app.features.graph.usecases.get_entity_summary import (
    GetEntitySummaryUseCaseImpl,
)


class GetEntityUseCase(Protocol):
    """Protocol for the get entity use case."""

    async def execute(
        self,
        identifier_value: str,
        identifier_type: str,
        rag_query: str | None = None,
        rag_top_k: int = 10,
        rag_min_score: float | None = None,
        rag_expand_hops: int = 0,
        rag_debug: bool = False,
    ) -> GetEntityResponse:
        """Retrieve entity information by identifier."""
        ...


class GetEntitySummaryUseCase(Protocol):
    """Protocol for the get entity summary use case."""

    async def execute(
        self, identifier_value: str, identifier_type: str, lang: str | None = None
    ) -> GetEntitySummaryResponse:
        """Generate a natural language summary of entity data."""
        ...


async def get_get_entity_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> GetEntityUseCase:
    """Dependency injection for the get entity use case."""

    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    return GetEntityUseCaseImpl(repository=repository)


# Create the data summarizer instance at module level
_data_summarizer = LangChainDataSummarizer()


async def get_entity_summary_use_case(
    tenant_info: TenantInfo = Depends(get_tenant_info),
) -> GetEntitySummaryUseCase:
    """Dependency injection for the entity summary use case."""
    pool = await get_graph_db_pool()
    repository = AgeRepository(pool, graph_name=tenant_info.graph_name)
    get_entity_use_case = GetEntityUseCaseImpl(repository=repository)
    return GetEntitySummaryUseCaseImpl(
        get_entity_use_case=get_entity_use_case, data_summarizer=_data_summarizer
    )


router = APIRouter()


@router.get("/entities/lookup", response_model=GetEntityResponse)
async def get_entity(
    type: str,
    value: str,
    rag_query: str | None = None,
    rag_top_k: int = 10,
    rag_min_score: float | None = None,
    rag_expand_hops: int = 0,
    rag_debug: bool = False,
    use_case: GetEntityUseCase = Depends(get_get_entity_use_case),
) -> GetEntityResponse:
    """Retrieve entity information by identifier.

    This endpoint looks up an entity using an external identifier (e.g., email, phone)
    and returns the entity details along with all associated facts and their sources.

    Args:
        type: The identifier type (e.g., 'email', 'phone')
        value: The identifier value (e.g., 'user@example.com')
        rag_query: Optional conversational query for semantic search
        rag_top_k: Number of vector candidates to retrieve (default: 10)
        rag_min_score: Optional similarity threshold for filtering vector hits
        rag_expand_hops: Optional graph expansion depth (default: 0)
        rag_debug: Whether to return debug metadata (default: False)
    """

    return await use_case.execute(
        identifier_value=value,
        identifier_type=type,
        rag_query=rag_query,
        rag_top_k=rag_top_k,
        rag_min_score=rag_min_score,
        rag_expand_hops=rag_expand_hops,
        rag_debug=rag_debug,
    )


@router.get("/entities/lookup/summary", response_model=GetEntitySummaryResponse)
async def get_entity_summary(
    type: str,
    value: str,
    lang: str | None = None,
    use_case: GetEntitySummaryUseCase = Depends(get_entity_summary_use_case),
) -> GetEntitySummaryResponse:
    """Generate a natural language summary of entity data.

    This endpoint looks up an entity using an external identifier (e.g., email, phone)
    and returns a concise textual summary of all known facts and relationships.
    The summary is optimized for consumption by Large Language Models.

    Args:
        type: The identifier type (e.g., 'email', 'phone')
        value: The identifier value (e.g., 'user@example.com')
        lang: Optional language code for the summary (e.g., 'pt-br', 'es', 'fr'). Defaults to English.
    """
    return await use_case.execute(
        identifier_value=value, identifier_type=type, lang=lang
    )
