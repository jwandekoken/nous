# Apache AGE Graph Schema for a Knowledge Graph

This document outlines the graph schema for Apache AGE, a PostgreSQL extension for graph databases. It is designed to implement the conceptual model defined in `graph_db_schema.md`.

Apache AGE follows a dynamic schema approach, meaning vertex and edge labels (types) do not need to be explicitly defined before use. They are created automatically when the first vertex or edge with that label is created. However, for data integrity and query performance, it is crucial to define unique constraints and indexes on key properties.

## 1. Initial Setup

Before creating any data, you must load the AGE extension and create a graph.

```sql
-- Load the AGE extension
LOAD 'age';

-- Set the search path to include the graph
SET search_path = ag_catalog, "$user", public;

-- Create the graph (if it doesn't exist)
SELECT create_graph('knowledge_graph');
```

## 2. Schema Definition (Constraints and Indexes)

The following commands should be run to enforce the schema's integrity and ensure efficient lookups. These are written in a mix of SQL and Cypher, as executed through AGE's functions.

### Vertex Labels

#### `Entity`

- **Purpose**: The canonical subject of the graph.
- **Commands**:

  ```sql
  -- Although the label is created on first use, we must create a UNIQUE constraint on the 'id' property.
  -- This requires creating at least one node first.
  SELECT * FROM cypher('knowledge_graph', $$
      CREATE (:Entity {id: 'temp'})
  $$) AS (v agtype);

  CREATE UNIQUE INDEX ON entity ((properties->>'id'));

  -- Clean up the temporary node
  SELECT * FROM cypher('knowledge_graph', $$
      MATCH (e:Entity {id: 'temp'}) DELETE e
  $$) AS (v agtype);
  ```

#### `Identifier`

- **Purpose**: An external identifier for an entity.
- **Commands**:

  ```sql
  -- Create a temporary node to establish the label
  SELECT * FROM cypher('knowledge_graph', $$
      CREATE (:Identifier {value: 'temp'})
  $$) AS (v agtype);

  CREATE UNIQUE INDEX ON identifier ((properties->>'value'));

  -- Clean up the temporary node
  SELECT * FROM cypher('knowledge_graph', $$
      MATCH (i:Identifier {value: 'temp'}) DELETE i
  $$) AS (v agtype);
  ```

#### `Fact`

- **Purpose**: A discrete piece of knowledge.
- **Commands**:

  ```sql
  -- Create a temporary node to establish the label
  SELECT * FROM cypher('knowledge_graph', $$
      CREATE (:Fact {fact_id: 'temp'})
  $$) AS (v agtype);

  CREATE UNIQUE INDEX ON fact ((properties->>'fact_id'));

  -- Clean up the temporary node
  SELECT * FROM cypher('knowledge_graph', $$
      MATCH (f:Fact {fact_id: 'temp'}) DELETE f
  $$) AS (v agtype);
  ```

#### `Source`

- **Purpose**: The origin of the information.
- **Commands**:

  ```sql
  -- Create a temporary node to establish the label
  SELECT * FROM cypher('knowledge_graph', $$
      CREATE (:Source {id: 'temp'})
  $$) AS (v agtype);

  CREATE UNIQUE INDEX ON source ((properties->>'id'));

  -- Clean up the temporary node
  SELECT * FROM cypher('knowledge_graph', $$
      MATCH (s:Source {id: 'temp'}) DELETE s
  $$) AS (v agtype);
  ```

### Edge Labels

Edge labels (`HAS_IDENTIFIER`, `HAS_FACT`, `DERIVED_FROM`) are created implicitly when an edge with that label is first created. There are no constraints or indexes applied to edges in this schema.

## 3. Example Cypher Queries for Data Creation

The following `CREATE` queries demonstrate how to insert data that conforms to this schema. Executing these queries will implicitly create the labels if they don't already exist.

```cypher
-- Create an Entity
CREATE (e:Entity {
    id: 'entity-uuid-123',
    created_at: '2023-10-27T10:00:00Z',
    metadata: {
        source_system: 'CRM'
    }
});

-- Create an Identifier and link it to the Entity
CREATE (i:Identifier {
    value: 'user@example.com',
    type: 'email'
});
MATCH (e:Entity {id: 'entity-uuid-123'}), (i:Identifier {value: 'user@example.com'})
CREATE (e)-[:HAS_IDENTIFIER {is_primary: true, created_at: '2023-10-27T10:00:00Z'}]->(i);

-- Create a Fact, a Source, and link them
CREATE (f:Fact {
    fact_id: 'Location:Paris',
    name: 'Paris',
    type: 'Location'
});
CREATE (s:Source {
    id: 'source-uuid-456',
    content: 'User mentioned they live in Paris.',
    timestamp: '2023-10-26T18:30:00Z'
});
MATCH (f:Fact {fact_id: 'Location:Paris'}), (s:Source {id: 'source-uuid-456'})
CREATE (f)-[:DERIVED_FROM]->(s);

-- Link the Fact to the Entity
MATCH (e:Entity {id: 'entity-uuid-123'}), (f:Fact {fact_id: 'Location:Paris'})
CREATE (e)-[:HAS_FACT {verb: 'lives in', confidence_score: 0.95, created_at: '2023-10-27T10:01:00Z'}]->(f);
```
