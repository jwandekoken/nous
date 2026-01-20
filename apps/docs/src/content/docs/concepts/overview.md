---
title: Overview
description: Understanding the four core concepts that power Nous
---

Nous is built around four fundamental concepts that work together to create a flexible and traceable knowledge graph. Understanding these concepts is essential to using Nous effectively.

## The Four Core Concepts

### 1. Entity

The **Entity** is the canonical anchor in your knowledge graph. It represents a real-world subject—a person, organization, concept, or any central subject you want to remember facts about.

- **Stable Identity**: Each entity has a unique UUID that never changes
- **Identifier-Agnostic**: The entity exists independently of external identifiers
- **Central Hub**: All facts and identifiers connect to the entity

[Learn more about Entities →](/concepts/entities)

### 2. Identifier

An **Identifier** is an external, real-world handle that points to an entity. Examples include email addresses, phone numbers, usernames, or any external ID.

- **Multiple Per Entity**: A single entity can have many identifiers
- **Prevents Duplicates**: Helps resolve identity across different sources
- **Real-World Mapping**: Connects your internal entity to external systems

[Learn more about Identifiers →](/concepts/identifiers)

### 3. Fact

A **Fact** is a discrete piece of knowledge associated with an entity. Facts can represent locations, companies, skills, relationships, or any named piece of information.

- **Semantic Context**: Each fact has a verb describing the relationship (e.g., "lives_in", "works_at")
- **Confidence Scores**: Track certainty levels for each fact
- **Reusable**: Multiple entities can share the same fact (e.g., "Location:Paris")

[Learn more about Facts →](/concepts/facts)

### 4. Source

A **Source** represents the origin of information—a chat message, email, document, or any content from which facts were extracted.

- **Provenance Tracking**: Every fact traces back to its source
- **Auditability**: Know exactly where each piece of information came from
- **Temporal Context**: Sources capture the real-world timestamp of events

[Learn more about Sources →](/concepts/sources)

## How They Connect

The four concepts form a connected graph structure:

```
┌─────────────┐
│   Entity    │ (Canonical subject with stable UUID)
└─────┬───┬───┘
      │   │
      │   └──────────────────┐
      │                      │
      ▼                      ▼
┌─────────────┐        ┌─────────────┐
│ Identifier  │        │    Fact     │
│             │        │             │
│ HAS_        │        │ HAS_FACT    │
│ IDENTIFIER  │        │ relationship│
└─────────────┘        └──────┬──────┘
                              │
                              │ DERIVED_FROM
                              │
                              ▼
                        ┌─────────────┐
                        │   Source    │
                        └─────────────┘
```

### Key Relationships

1. **Entity → Identifier** (`HAS_IDENTIFIER`)
   - An entity can have multiple identifiers
   - One identifier can be marked as primary

2. **Entity → Fact** (`HAS_FACT`)
   - Links an entity to knowledge about it
   - Includes a verb and confidence score

3. **Fact → Source** (`DERIVED_FROM`)
   - Traces each fact back to its origin
   - Ensures data provenance and traceability

## Design Principles

### Identity Resolution

By separating the canonical **Entity** from its external **Identifiers**, Nous prevents duplicate profiles. When you encounter a new identifier (like a second email for the same person), you can link it to the existing entity rather than creating a duplicate.

### Traceability

Every fact in Nous can answer the question: "How do we know this?" The `DERIVED_FROM` relationship ensures complete data provenance from fact to source.

### Temporal Awareness

Nous distinguishes between two types of time:
- **Event Time** (`Source.timestamp`): When something actually happened in the real world
- **System Time** (`created_at`): When it was recorded in Nous

This allows accurate contextual queries alongside system auditing.

## Quick Reference

| Concept    | Primary Key | Purpose                           |
|------------|-------------|-----------------------------------|
| Entity     | UUID        | Canonical anchor for all information |
| Identifier | value       | External handle to find an entity |
| Fact       | fact_id     | Discrete piece of knowledge       |
| Source     | UUID        | Origin of information             |

## Next Steps

Ready to dive deeper? Start with [Entities](/concepts/entities) to understand the foundation of the knowledge graph.
