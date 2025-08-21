# KùzuDB Graph Schema Documentation

This document outlines the KùzuDB graph schema designed to function as a flexible and scalable knowledge graph. It captures facts about specific entities derived from textual sources.

## Schema Definition (DDL)

```cypher
-- The canonical Entity node, identified by a system-managed UUID
CREATE NODE TABLE Entity (
    id UUID,
    created_at TIMESTAMP,
    metadata MAP(STRING, STRING),
    PRIMARY KEY (id)
);

-- A dedicated node for external identifiers like emails or phone numbers
CREATE NODE TABLE Identifier (
    value STRING,
    type STRING,
    PRIMARY KEY (value)
);

-- Note: KùzuDB does not support composite primary keys.
-- A synthetic key `fact_id` is created by the application (e.g., "type:name")
-- to ensure the uniqueness of each fact.
CREATE NODE TABLE Fact (
  fact_id STRING,
  name STRING,
  type STRING,
  PRIMARY KEY (fact_id)
);

CREATE NODE TABLE Source (
  id UUID,
  content STRING,
  timestamp TIMESTAMP,
  PRIMARY KEY (id)
);

-- Connects an Entity to its various external Identifiers
CREATE REL TABLE HAS_IDENTIFIER (
    FROM Entity TO Identifier,
    is_primary BOOLEAN,
    created_at TIMESTAMP
);

CREATE REL TABLE HAS_FACT (
  FROM Entity TO Fact,
  verb STRING,
  confidence_score DOUBLE,
  created_at TIMESTAMP
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

- **Natural & Synthetic Keys**: For nodes like `Identifier` and `Fact`, the primary key is based on their real-world properties.
  - `Identifier` uses a **natural key** (`value`), as the identifier itself is unique.
  - `Fact` uses a **synthetic key** (`fact_id`), which is constructed by the application (e.g., by concatenating `type` and `name`). This is a workaround for KùzuDB's lack of composite key support and ensures that each fact node is unique.
- **System Keys**: For nodes like `Entity` and `Source` that lack a stable, natural identifier, we use a system-generated `UUID` as the primary key. This provides a reliable, unchanging internal anchor.

### Node Tables

#### `Entity`

- **Purpose**: The abstract, central subject of the graph (e.g., a user). It acts as the canonical anchor for all related facts and identifiers.
- **Rationale**:
  - `id` is a system-controlled `PRIMARY KEY`, ensuring the entity's reference is stable.
  - `metadata MAP(STRING, STRING)` provides a flexible "catch-all" for semi-structured data.

#### `Identifier`

- **Purpose**: Represents an external, real-world identifier for an entity.
- **Rationale**:
  - Modeling identifiers as distinct nodes allows a one-to-many relationship with an `Entity`.
  - The `value` (e.g., "user@example.com") is a natural `PRIMARY KEY` for extremely fast lookups.

#### `Fact`

- **Purpose**: A discrete piece of knowledge or a named entity (e.g., a location, company, or hobby).
- **Rationale**:
  - The `fact_id` is a synthetic `PRIMARY KEY` (e.g., "Location:Paris") created by the application to enforce uniqueness, as composite keys are not supported.

#### `Source`

- **Purpose**: The origin of the information (e.g., a chat message, email, or document).
- **Rationale**:
  - **Traceability**: Modeled as a node to be a "first-class citizen," enabling queries about data provenance.
  - **Efficiency**: Avoids data duplication by allowing multiple `Fact` nodes to link to a single `Source`.

### Relationship Tables

#### `HAS_IDENTIFIER`

- **Purpose**: A directed relationship connecting an `Entity` to its `Identifier`.
- **Rationale**: This link formally associates the abstract `Entity` with its real-world identifier(s).

#### `HAS_FACT`

- **Purpose**: A directed relationship connecting an `Entity` to a `Fact` it possesses.
- **Rationale**:
  - Properties like `verb` add rich semantic context to the connection.

#### `DERIVED_FROM`

- **Purpose**: A directed relationship linking a `Fact` back to the `Source` where it was found.
- **Rationale**:
  - This relationship is the cornerstone of traceability, answering the question: **"How do we know this fact?"**

### Core Design Principle: Timestamps

A crucial design choice is the deliberate distinction between timestamp fields:

- **`Source.timestamp`**: This is the **real-world event time**.
- **`created_at`**: This is the **system's internal audit time**.

This separation allows for accurate contextual queries ("What did the user say on Monday?") while also enabling system-level auditing ("What new facts did the system learn today?").
