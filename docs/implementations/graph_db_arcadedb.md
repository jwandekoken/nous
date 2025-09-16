# ArcadeDB Graph Schema for a Knowledge Graph

This document outlines a graph schema for ArcadeDB, designed to function as a flexible and scalable knowledge graph. It captures facts about specific entities derived from textual sources.

## Schema Definition (ArcadeDB SQL)

The following Data Definition Language (DDL) commands are written in ArcadeDB's SQL dialect.

```sql
-- The canonical Entity vertex, identified by an application-managed UUID
CREATE VERTEX TYPE Entity;
CREATE PROPERTY Entity.id STRING (mandatory true);
CREATE PROPERTY Entity.created_at DATETIME (mandatory true, default "sysdate()");
CREATE PROPERTY Entity.metadata MAP;
CREATE INDEX ON Entity (id) UNIQUE;

-- A dedicated vertex for external identifiers like emails or phone numbers
CREATE VERTEX TYPE Identifier;
CREATE PROPERTY Identifier.value STRING (mandatory true);
CREATE PROPERTY Identifier.type STRING;
CREATE INDEX ON Identifier (value) UNIQUE;

-- A Fact vertex, representing a piece of knowledge.
-- A synthetic key `fact_id` is created by the application (e.g., "type:name")
-- to ensure the uniqueness of each fact.
CREATE VERTEX TYPE Fact;
CREATE PROPERTY Fact.fact_id STRING (mandatory true);
CREATE PROPERTY Fact.name STRING;
CREATE PROPERTY Fact.type STRING;
CREATE INDEX ON Fact (fact_id) UNIQUE;

-- The Source vertex, representing the origin of the information
CREATE VERTEX TYPE Source;
CREATE PROPERTY Source.id STRING (mandatory true);
CREATE PROPERTY Source.content STRING;
CREATE PROPERTY Source.timestamp DATETIME;
CREATE INDEX ON Source (id) UNIQUE;

-- Connects an Entity to its various external Identifiers
CREATE EDGE TYPE HAS_IDENTIFIER;
CREATE PROPERTY HAS_IDENTIFIER.is_primary BOOLEAN;
CREATE PROPERTY HAS_IDENTIFIER.created_at DATETIME (default "sysdate()");

-- Connects an Entity to a Fact it possesses
CREATE EDGE TYPE HAS_FACT;
CREATE PROPERTY HAS_FACT.verb STRING;
CREATE PROPERTY HAS_FACT.confidence_score DOUBLE;
CREATE PROPERTY HAS_FACT.created_at DATETIME (default "sysdate()");

-- Connects a Fact to the Source it was derived from
CREATE EDGE TYPE DERIVED_FROM;
```

## Schema Rationale

The schema is designed around principles of robust identity management, clarity, traceability, and query performance, tailored to ArcadeDB's capabilities.

### Core Design Principle: Identity Management

A key feature of this schema is the separation of the canonical `Entity` from its external `Identifier`(s). Instead of using a user-provided email or phone number as the primary identifier for an `Entity`, we use a stable, internal UUID stored in a dedicated property. External identifiers are stored as separate `Identifier` vertices and linked to the `Entity` via edges.[1]

- **Benefit**: This approach solves the "split brain" problem by allowing a single, canonical `Entity` to be associated with multiple identifiers (e.g., an email _and_ a phone number). This prevents duplicate entity profiles and provides a flexible foundation for identity resolution.

### Core Design Principle: Natural vs. System Keys

This schema deliberately uses two different approaches for unique identification, depending on the vertex's purpose. In ArcadeDB, uniqueness is enforced by creating a `UNIQUE` index on a `mandatory` property.[1]

- **Natural & Synthetic Keys**: For vertices like `Identifier` and `Fact`, the unique index is based on their real-world properties.
  - `Identifier` uses a **natural key** (`value`), as the identifier itself is unique.
  - `Fact` uses a **synthetic key** (`fact_id`), which is constructed by the application (e.g., by concatenating `type` and `name`). This ensures that each fact vertex is unique.
- **System Keys**: For vertices like `Entity` and `Source` that lack a stable, natural identifier, we use an application-generated `UUID` stored in a `STRING` property as the unique identifier. This provides a reliable, unchanging internal anchor for lookups.

### Vertex Types

#### `Entity`

- **Purpose**: The abstract, central subject of the graph (e.g., a user). It acts as the canonical anchor for all related facts and identifiers.
- **Rationale**:
  - The `id` property, combined with a `UNIQUE` index, ensures the entity's reference is stable and lookups are fast.[1]
  - `metadata MAP` provides a flexible "catch-all" for semi-structured data without needing to pre-define every possible property.[1]

#### `Identifier`

- **Purpose**: Represents an external, real-world identifier for an entity.
- **Rationale**:
  - Modeling identifiers as distinct vertices allows a one-to-many relationship with an `Entity`.
  - The `value` (e.g., "user@example.com") is a natural unique key, enabling extremely fast lookups via its index.

#### `Fact`

- **Purpose**: A discrete piece of knowledge or a named entity (e.g., a location, company, or hobby).
- **Rationale**:
  - The `fact_id` is a synthetic unique key (e.g., "Location:Paris") created by the application to enforce uniqueness.

#### `Source`

- **Purpose**: The origin of the information (e.g., a chat message, email, or document).
- **Rationale**:
  - **Traceability**: Modeled as a vertex to be a "first-class citizen," enabling queries about data provenance.
  - **Efficiency**: Avoids data duplication by allowing multiple `Fact` vertices to link to a single `Source` via an edge.

### Edge Types

#### `HAS_IDENTIFIER`

- **Purpose**: A directed edge connecting an `Entity` to its `Identifier`.
- **Rationale**: This link formally associates the abstract `Entity` with its real-world identifier(s). In ArcadeDB, edges are first-class citizens and can hold properties like `is_primary`.[1]

#### `HAS_FACT`

- **Purpose**: A directed edge connecting an `Entity` to a `Fact` it possesses.
- **Rationale**:
  - Properties like `verb` add rich semantic context to the connection, a core feature of property graphs.[1]

#### `DERIVED_FROM`

- **Purpose**: A directed edge linking a `Fact` back to the `Source` where it was found.
- **Rationale**:
  - This relationship is the cornerstone of traceability, answering the question: **"How do we know this fact?"**

### Core Design Principle: Timestamps

A crucial design choice is the deliberate distinction between timestamp fields, using ArcadeDB's `DATETIME` type [1]:

- **`Source.timestamp`**: This is the **real-world event time**.
- **`created_at`**: This is the **system's internal audit time**, automatically populated using `default "sysdate()"` when a record is created.

This separation allows for accurate contextual queries ("What did the user say on Monday?") while also enabling system-level auditing ("What new facts did the system learn today?").
