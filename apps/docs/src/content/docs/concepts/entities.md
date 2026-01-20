---
title: Entities
description: The canonical anchor point for all knowledge in Nous
---

An **Entity** is the central subject in your knowledge graph. It represents a real-world entity—a person, organization, concept, or any subject you want to remember information about.

## What is an Entity?

Think of an entity as the canonical "profile" or "identity" for a subject in your system. Unlike traditional databases where you might identify a user by their email, Nous uses a stable UUID that never changes—even if all the person's contact information changes.

### Key Characteristics

- **Stable Identity**: Each entity has a unique UUID that persists forever
- **Identifier-Agnostic**: The entity exists independently of external identifiers like emails or usernames
- **Relationship Hub**: All facts and identifiers connect through the entity
- **Flexible Metadata**: Can store additional semi-structured information as needed

## Entity Properties

| Property     | Type                 | Description                                    |
|--------------|----------------------|------------------------------------------------|
| `id`         | UUID                 | Unique system identifier, auto-generated       |
| `created_at` | datetime             | When this entity was created in the system     |
| `metadata`   | dict[str, str] or {} | Flexible key-value pairs for additional data   |

### Example Entity Structure

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-15T10:30:00Z",
  "metadata": {
    "type": "person",
    "source_system": "crm"
  }
}
```

## Why Separate Entities from Identifiers?

A common question: why not just use an email address as the primary key?

### The Problem with External Identifiers

Consider this scenario:
1. Alice signs up with `alice@company.com`
2. She changes jobs and starts using `alice@newcompany.com`
3. She also has a personal email `alice.smith@gmail.com`
4. You receive a message from her phone number `+1-555-0123`

**Without entities**: You might create 4 separate profiles, fragmenting Alice's information.

**With entities**: All four identifiers point to the same canonical entity UUID. Her complete history stays connected.

### Benefits of Entity-Based Design

1. **Identity Resolution**: Merge profiles when you discover two identifiers belong to the same person
2. **Future-Proof**: New identifier types (social handles, crypto addresses) can be added without schema changes
3. **Cross-System Integration**: Different systems can use different identifiers while referencing the same entity
4. **Privacy-Friendly**: The entity UUID can persist even if external identifiers are deleted

## Entity Lifecycle

### 1. Creation

Entities are typically created during the **assimilation** process when you first encounter a new identifier:

```bash
POST /entities/assimilate
{
  "identifier": {
    "type": "email",
    "value": "alice@example.com"
  },
  "content": "Alice moved to Paris and started working at Acme Corp."
}
```

This will:
- Create a new entity with a unique UUID
- Link the `alice@example.com` identifier to the entity
- Extract and associate facts with the entity

### 2. Lookup

Retrieve an entity and all its associated data using any of its identifiers:

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@example.com
```

Returns the entity with all identifiers, facts, and sources.

### 3. Updating

Entities themselves are immutable (the UUID never changes), but you can:
- Add new identifiers to an entity
- Add new facts to an entity
- Update metadata fields

## Entity Relationships

### Has Identifiers

An entity connects to its external identifiers through `HAS_IDENTIFIER` relationships:

```
(Entity) -[HAS_IDENTIFIER]-> (Identifier)
```

**Relationship Properties:**
- `is_primary`: Boolean flag marking the primary identifier
- `created_at`: When the identifier was linked

### Has Facts

An entity connects to knowledge about itself through `HAS_FACT` relationships:

```
(Entity) -[HAS_FACT]-> (Fact)
```

**Relationship Properties:**
- `verb`: Semantic relationship (e.g., "lives_in", "works_at")
- `confidence_score`: Confidence level (0.0 to 1.0)
- `created_at`: When the fact was linked

[Learn more about Facts →](/concepts/facts)

## Use Cases

### 1. Customer Profiles

Track a customer across multiple touchpoints:
- Email conversations
- Phone support calls
- Social media interactions
- In-app behavior

All unified under a single entity UUID.

### 2. AI Agent Memory

Give your AI agent a persistent memory of users:
- Remember preferences across sessions
- Maintain conversation history
- Build context over time

### 3. Research Knowledge Bases

Track entities in research:
- Organizations and their relationships
- People and their affiliations
- Concepts and their connections

## Best Practices

### Use Metadata Sparingly

The `metadata` field is flexible, but overusing it can make querying difficult. Reserve it for:
- System integration data (e.g., `source_system: "salesforce"`)
- Lightweight type hints (e.g., `entity_type: "organization"`)

Store structured data as Facts instead.

### Don't Reuse Entity UUIDs

Once an entity UUID is created, never reuse it for a different subject. If you need to merge entities, create a new entity and migrate the relationships.

### Use Primary Identifiers

Mark one identifier as `is_primary` to serve as the default display name or contact method for the entity.

## Common Questions

### Can I create an entity without an identifier?

Technically yes, but it's not recommended. Entities without identifiers are unreachable through the standard lookup API. Always link at least one identifier when creating an entity.

### Can entities have relationships with other entities?

Not directly in the current schema. Entity-to-entity relationships can be modeled through shared facts or by creating custom fact types that reference other entities.

### How do I delete an entity?

Nous currently focuses on write and read operations. Entity deletion would require cascading deletion of all related identifiers, facts, and relationships—something to implement carefully based on your data retention policies.

## Related Concepts

- [Identifiers](/concepts/identifiers) - External handles that point to entities
- [Facts](/concepts/facts) - Knowledge associated with entities
- [Sources](/concepts/sources) - Origin of information about entities
