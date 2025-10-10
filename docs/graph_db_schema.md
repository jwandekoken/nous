# Conceptual Graph Schema for a Knowledge Graph

This document outlines the conceptual data model for a flexible and scalable knowledge graph. It is designed to be implementation-agnostic and can be adapted to various graph database technologies. The schema's purpose is to capture facts about specific entities derived from textual sources.

## Core Components

The schema consists of four primary node (vertex) types and three primary relationship (edge) types.

### Node Types

#### 1. Entity

- **Purpose**: Represents the abstract, central subject of the graph (e.g., a person, an organization, a concept). It serves as the canonical anchor for all related information.
- **Key Properties**:
  - `id`: A unique, application-managed identifier (e.g., a UUID) that is stable and portable.
  - `created_at`: A timestamp indicating when the entity was created in the system.
  - `metadata`: A flexible container for additional, semi-structured properties related to the entity.

#### 2. Identifier

- **Purpose**: Represents an external, real-world identifier for an `Entity`.
- **Key Properties**:
  - `value`: The value of the identifier (e.g., "user@example.com", "+15551234567"). This should be unique across all identifiers.
  - `type`: The type of the identifier (e.g., "email", "phone_number").

#### 3. Fact

- **Purpose**: Represents a discrete piece of knowledge or a named entity (e.g., a location, a company, a hobby).
- **Key Properties**:
  - `fact_id`: A unique, application-generated identifier for the fact (e.g., a composite key of its type and name).
  - `name`: The name or value of the fact (e.g., "Paris", "Acme Corp").
  - `type`: The category of the fact (e.g., "Location", "Company").

#### 4. Source

- **Purpose**: Represents the origin of the information (e.g., a chat message, an email, a document).
- **Key Properties**:
  - `id`: A unique, application-managed identifier for the source.
  - `content`: The original content from which facts were derived.
  - `timestamp`: The real-world timestamp of when the source was created (e.g., when an email was sent).

### Relationship Types

#### 1. `HAS_IDENTIFIER`

- **Purpose**: A directed relationship connecting an `Entity` to its `Identifier`.
- **Direction**: `(Entity) -[HAS_IDENTIFIER]-> (Identifier)`
- **Key Properties**:
  - `is_primary`: A boolean flag to indicate if this is the primary identifier for the entity.
  - `created_at`: A timestamp for when the relationship was established.

#### 2. `HAS_FACT`

- **Purpose**: A directed relationship connecting an `Entity` to a `Fact` it possesses.
- **Direction**: `(Entity) -[HAS_FACT]-> (Fact)`
- **Key Properties**:
  - `verb`: Describes the relationship between the entity and the fact (e.g., "lives in", "works at").
  - `confidence_score`: A numerical value indicating the confidence in the validity of the fact.
  - `created_at`: A timestamp for when the relationship was established.

#### 3. `DERIVED_FROM`

- **Purpose**: A directed relationship linking a `Fact` back to the `Source` from which it was extracted.
- **Direction**: `(Fact) -[DERIVED_FROM]-> (Source)`
- **Rationale**: This relationship is the cornerstone of data traceability and provenance, answering the question: "How do we know this fact?"

## Schema Rationale and Design Principles

### Identity Management

The separation of the canonical `Entity` from its external `Identifier`(s) is a core design principle. This allows a single `Entity` to be associated with multiple identifiers, preventing duplicate profiles and providing a flexible foundation for identity resolution.

### Traceability

Every `Fact` should be traceable to a `Source`. The `DERIVED_FROM` relationship ensures that the provenance of all information in the graph is maintained.

### Timestamps

A clear distinction is made between two types of timestamps:

- **Event Time (`Source.timestamp`)**: The real-world time an event occurred.
- **System Time (`created_at`)**: The internal audit time when a record or relationship was created in our system.

This separation allows for accurate contextual queries alongside system-level auditing.
