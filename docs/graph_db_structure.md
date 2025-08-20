# KùzuDB Graph Schema Documentation

This document outlines the KùzuDB graph schema designed to function as a flexible and scalable knowledge graph. It captures facts about specific entities derived from textual sources.

## Schema Definition (DDL)

```cypher
-- The canonical Entity node, identified by a system-managed UUID
CREATE NODE TABLE Entity (
    id UUID,
    created_at TIMESTAMPLTZ,
    metadata MAP(STRING, STRING),
    PRIMARY KEY (id)
);

-- A dedicated node for external identifiers like emails or phone numbers
CREATE NODE TABLE Identifier (
    value STRING,
    type STRING,
    PRIMARY KEY (value)
);

CREATE NODE TABLE Fact (
  name STRING,
  type STRING,
  PRIMARY KEY (name, type)
);

CREATE NODE TABLE Source (
  id UUID,
  content STRING,
  timestamp TIMESTAMPLTZ,
  PRIMARY KEY (id)
);

-- Connects an Entity to its various external Identifiers
CREATE REL TABLE HAS_IDENTIFIER (
    FROM Entity TO Identifier,
    is_primary BOOLEAN,
    created_at TIMESTAMPLTZ
);

CREATE REL TABLE HAS_FACT (
  FROM Entity TO Fact,
  verb STRING,
  confidence_score DOUBLE,
  created_at TIMESTAMPLTZ
);

CREATE REL TABLE DERIVED_FROM (
  FROM Fact TO Source
);
```

## Schema Rationale

The schema is designed around principles of robust identity management, clarity, traceability, and query performance.

### Core Design Principle: Identity Management

A key feature of this schema is the separation of the canonical `Entity` from its external `Identifier`(s). Instead of using a user-provided email or phone number as the primary key for an `Entity`, we use a stable, internal UUID. External identifiers are stored as separate `Identifier` nodes and linked to the `Entity`.

- **Benefit**: This approach solves the "split brain" problem by allowing a single, canonical `Entity` to be associated with multiple identifiers (e.g., an email _and_ a phone number). This prevents duplicate entity profiles and provides a flexible foundation for identity resolution.

### Core Design Principle: Natural vs. System Keys

This schema deliberately uses two different approaches for primary keys, depending on the node's purpose.

- **Natural Keys**: For nodes like `Identifier` and `Fact`, the primary key is based on their "natural" real-world properties (e.g., the identifier's `value`, or the fact's `name` and `type`). This is because the identity of these nodes _is_ their data. This is a graph best practice for nodes that represent unique concepts and are typically found or created using the `MERGE` command.
- **System Keys**: For nodes like `Entity` and `Source` that lack a stable, natural identifier, we use a system-generated `UUID` as the primary key. This provides a reliable, unchanging internal anchor, even if the node's other properties change.

### Node Tables

#### `Entity`

- **Purpose**: The abstract, central subject of the graph (e.g., a user). It acts as the canonical anchor for all related facts and identifiers.
- **Rationale**:
  - `id` is a system-controlled `PRIMARY KEY`, ensuring the entity's reference is stable and independent of changing external identifiers.
  - `metadata MAP(STRING, STRING)` provides a flexible "catch-all" for semi-structured data, avoiding frequent schema alterations.

#### `Identifier`

- **Purpose**: Represents an external, real-world identifier for an entity.
- **Rationale**:
  - Modeling identifiers as distinct nodes allows a one-to-many relationship with an `Entity`.
  - The `value` (e.g., "user@example.com") is a natural `PRIMARY KEY` for extremely fast lookups.

#### `Fact`

- **Purpose**: A discrete piece of knowledge or a named entity (e.g., a location, company, or hobby).
- **Rationale**:
  - The composite `PRIMARY KEY (name, type)` is a natural key that uniquely identifies a fact, distinguishing between concepts with the same name but different types (e.g., "Paris" as a `Location` vs. "Paris" as a `Person`).

#### `Source`

- **Purpose**: The origin of the information (e.g., a chat message, email, or document).
- **Rationale**:
  - **Traceability**: Modeled as a node to be a "first-class citizen," enabling queries about data provenance.
  - **Efficiency**: Avoids data duplication by allowing multiple `Fact` nodes to link to a single `Source`.

### Relationship Tables

#### `HAS_IDENTIFIER`

- **Purpose**: A directed relationship connecting an `Entity` to its `Identifier`.
- **Rationale**: This link formally associates the abstract `Entity` with its real-world identifier(s). Properties like `is_primary` can add valuable context.

#### `HAS_FACT`

- **Purpose**: A directed relationship connecting an `Entity` to a `Fact` it possesses.
- **Rationale**:
  - Properties like `verb` and `confidence_score` add rich semantic context directly to the connection itself, describing _how_ the entity and fact are related.

#### `DERIVED_FROM`

- **Purpose**: A directed relationship linking a `Fact` back to the `Source` where it was found.
- **Rationale**:
  - This relationship is the cornerstone of traceability, making it possible to answer the critical question: **"How do we know this fact?"**

### Core Design Principle: Timestamps

A crucial design choice is the deliberate distinction between timestamp fields:

- **`Source.timestamp`**: This is the **real-world event time**. It records when the original message was sent or the event occurred.
- **`created_at`**: This is the **system's internal audit time**. It records when a node or relationship was created _in our database_.

This separation allows for accurate contextual queries ("What did the user say on Monday?") while also enabling system-level auditing ("What new facts did the system learn today?").
