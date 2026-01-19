---
title: Introduction
description: Introduction to Nous - Knowledge Graph Memory for AI Agents
---

Nous is a knowledge graph memory system designed to give AI agents persistent, structured memory.

## The Problem

Imagine having a conversation with someone who forgets everything you said five minutes ago. That's essentially how most AI agents work today.

Large Language Models are **stateless** — they have no persistent memory. Each conversation starts from scratch, and even within a conversation, they're limited by context windows. Most agents today suffer from "short-term amnesia," operating with sliding context windows that only remember the last few messages.

This creates a fundamental limitation: **agents can't truly know you**. They can't remember your preferences, your history, or the context that makes interactions meaningful.

## Current Approaches and Their Limitations

Several approaches exist to give agents memory, but each has significant drawbacks:

| Approach | How It Works | Limitation |
|----------|--------------|------------|
| **Prompt Stuffing** | Include entire conversation history in the prompt | Expensive, hits context limits quickly |
| **Summarization** | Compress past conversations into summaries | Loses important details |
| **Vector Search (RAG)** | Store and retrieve by semantic similarity | No structured relationships |
| **Knowledge Graphs** | Store entities and relationships | No semantic/fuzzy search |

The key insight is that **human memory doesn't work just by similarity — it works by connection**. When you learn that "Alice moved to Berlin," you don't just create a floating data point. You update your mental model of Alice with a new attribute. It's a graph, not a list.

## The Nous Approach

Nous (Greek for "intellect" or "mind") combines the best of both worlds:

- **Graph Database** — Stores entities and their relationships in a structured way
- **Vector Database** — Enables semantic search and fuzzy matching

This hybrid approach means you get both the **structural reasoning** of a knowledge graph and the **semantic flexibility** of vector search.

## How It Works

Nous provides two core operations:

### Assimilate (Write)

When you send text to Nous, it:
1. Extracts atomic facts from the content using an LLM
2. Identifies or creates relevant entities
3. Stores the facts in the graph with their relationships
4. Creates vector embeddings for semantic search

```
Input: "João lives in Curitiba and works as a data engineer.
        He loves playing chess on weekends."

Result:
  Entity: João
  Facts:
    - lives_in: Curitiba
    - works_as: Data Engineer
    - enjoys: Chess
```

### Lookup (Read)

When you need to retrieve information:
1. Query by entity, semantic search, or both
2. Get structured facts with their sources
3. Receive context optimized for LLM consumption

This allows your agent to answer questions like "Where does this person live?" or "What are their hobbies?" with accurate, sourced information.

## Use Cases

- **Personal Assistants** — Remember user preferences and context
- **Intelligent CRM** — Track customer interaction history
- **AI Tutors** — Remember student progress and learning style
- **Health Assistants** — Maintain contextualized medical history
- **Sales Agents** — Build deep knowledge of each customer

## Next Steps

Ready to get started? Head to the [Installation](/getting-started/installation/) guide to set up Nous.
