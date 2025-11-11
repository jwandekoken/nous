"""Entity data summarization service using LangChain and Google's Gemini model."""

import json
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.settings import Settings
from app.features.graph.dtos.knowledge_dto import GetEntityResponse


class SummaryOutput(BaseModel):
    """Structured output from the LLM containing the entity summary."""

    summary: str


class LangChainDataSummarizer:
    """Summarizes entity data into natural language using LangChain and Gemini.

    This service converts structured entity data (facts, relationships, sources)
    into concise natural language summaries optimized for LLM consumption.
    """

    chain: Runnable[dict[str, Any], Any]

    def __init__(self):
        """Initialize the data summarizer with LangChain and Gemini model."""
        # Create settings that will read from current environment
        settings = Settings()
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        # Create the prompt template for data summarization
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a specialized assistant that converts structured entity data into natural language summaries.
Your summaries are designed to be consumed by Large Language Models (LLMs) for context-aware interactions.

Guidelines:
- Generate a concise, coherent summary (2-4 paragraphs maximum)
- Organize information logically by category
- Include confidence qualifiers when appropriate:
  - confidence >= 0.9: state facts directly
  - confidence 0.7-0.9: use "likely" or "probably"
  - confidence < 0.7: use "possibly" or "appears to"
- Mention source timestamps when relevant for temporal context
- Use clear, unambiguous language suitable for LLM interpretation
- Avoid redundancy and generic statements
- Note: You will always receive at least one fact (empty facts are handled before LLM call)

Input Format:
You will receive a JSON object with:
- entity: Contains id, created_at, and optional metadata
- identifier: The primary identifier (type:value)
- facts: Array of facts with name, type, verb, confidence_score, and optional source

Output:
Generate a natural language summary that a Large Language Model can easily understand and use for context.""",
                ),
                ("human", "{entity_data}"),
            ]
        )

        # Initialize the Gemini model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=settings.google_api_key,
        )

        # Create structured output chain
        structured_llm = llm.with_structured_output(SummaryOutput)
        self.chain = prompt | structured_llm

    async def summarize(
        self, entity_data: GetEntityResponse, lang: str | None = None
    ) -> str:
        """Generate a natural language summary of entity data.

        Args:
            entity_data: The complete entity data including facts and relationships
            lang: Optional language code (e.g., 'pt-br', 'es', 'fr'). Defaults to English.

        Returns:
            A natural language summary string optimized for LLM consumption
        """
        # Convert entity data to dict for template
        entity_dict = entity_data.model_dump(mode="json")

        # Format the data as JSON for the LLM
        entity_json = json.dumps(entity_dict, indent=2, default=str)

        # Build the complete human message with optional language instruction
        human_message = ""
        if lang:
            human_message += f"Generate the summary in the language: {lang}.\n\n"
        human_message += f"Here is the entity data to summarize:\n\n{entity_json}"

        # Call the LLM chain
        response: SummaryOutput = cast(
            SummaryOutput,
            await self.chain.ainvoke({"entity_data": human_message}),
        )

        return response.summary
