"""Fact extraction service using LangChain and Google's Gemini model."""

from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.core.settings import Settings
from app.features.graph.dtos.knowledge_dto import IdentifierPayload


class ExtractedFact(BaseModel):
    """A single, discrete fact extracted from a text."""

    name: str = Field(
        ...,
        description="The name or value of the fact (e.g., 'Paris', 'Software Engineer')",
    )
    type: str = Field(
        ...,
        description="The category of the fact (e.g., 'Location', 'Profession', 'Hobby')",
    )
    verb: str = Field(
        ...,
        description="The semantic verb connecting the entity to the fact (e.g., 'lives_in', 'works_at', 'is_a')",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="The confidence score of the extracted fact, from 0.0 to 1.0",
    )


class FactList(BaseModel):
    """A list of facts extracted from a text."""

    facts: list[ExtractedFact]


class LangChainFactExtractor:
    """Extracts facts from text content using LangChain and Gemini."""

    def __init__(self):
        """Initialize the fact extractor with LangChain and Gemini model."""
        # Create settings that will read from current environment
        settings = Settings()
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        # Create the prompt template for fact extraction
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at extracting key facts about a specific entity from text.
The text is a turn in a conversation. Your task is to identify discrete, meaningful facts from the provided text that are relevant to the entity identified by: {entity_identifier}.
You may also be provided with the history of the conversation for context.

Guidelines:
- Extract facts that are specific and verifiable, but also sentiments or opinions if they are stated as facts by the entity (e.g., 'likes chocolate', 'dislikes flying').
- For each fact, provide a 'verb' that describes the relationship from the entity to the fact (e.g., 'lives_in', 'works_at', 'is_a', 'likes', 'dislikes').
- Use clear, concise names and appropriate categories for each fact.
- Provide a confidence score (0.0 to 1.0) indicating how certain you are about the extracted fact.
- Focus on facts that would be useful for building a knowledge graph about the entity's preferences, statements, and characteristics.
- If the text contains no new facts about the entity, return an empty list.
- Avoid extracting subjective opinions or interpretations from *other* people in the conversation, focus on the identified entity.
- Ignore generic statements, meta-comments, or information that isn't a specific characteristic, preference, or action of the entity. For example, from 'This is a test entity with minimal information.', no facts should be extracted.

Example 1:
If the entity is 'email:john.doe@example.com' and the text is 'I really enjoy hiking on weekends.', the output should be:
[
    {{ "name": "Hiking", "type": "Hobby", "verb": "enjoys", "confidence_score": 1.0 }}
]

Example 2:
If the entity is 'email:jane.doe@example.com' and the text is 'I think that new project is a bad idea.', the output could be:
[
    {{ "name": "new project", "type": "Opinion", "verb": "considers_bad_idea", "confidence_score": 0.9 }}
]""",
                ),
                ("human", "{history_section}Here is the text to analyze:\n\n{content}"),
            ]
        )

        # Initialize the Gemini model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=settings.google_api_key,
        )

        # Create structured output chain
        structured_llm = llm.with_structured_output(FactList)
        self.chain = prompt | structured_llm

    async def extract_facts(
        self,
        content: str,
        entity_identifier: IdentifierPayload,
        history: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extracts facts and converts them to the required dictionary format.

        Args:
            content: The text content to extract facts from
            entity_identifier: The entity identifier payload
            history: Optional list of previous conversational turns for context.

        Returns:
            List of dictionaries containing fact name, type, verb and confidence
        """
        history_section = ""
        if history:
            history_section = (
                "For context, here is the preceding conversation:\n"
                + "\n".join(history)
                + "\n\n"
            )

        response: FactList = cast(
            FactList,
            await self.chain.ainvoke(
                {
                    "content": content,
                    "entity_identifier": f"{entity_identifier.type}:{entity_identifier.value}",
                    "history_section": history_section,
                }
            ),
        )
        return [fact.model_dump() for fact in response.facts]
