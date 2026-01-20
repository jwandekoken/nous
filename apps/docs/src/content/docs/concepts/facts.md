---
title: Facts
description: Discrete pieces of knowledge that power your knowledge graph
---

A **Fact** represents a discrete piece of knowledge or a named entity in your knowledge graph. Facts can be locations (Paris), companies (Acme Corp), skills (Python), relationships, or any structured piece of information about an entity.

## What is a Fact?

Facts are the "knowledge atoms" in Nous—small, reusable pieces of information that can be associated with entities. Unlike unstructured notes, facts are structured and semantic, making them queryable and analyzable.

### Key Characteristics

- **Discrete**: Each fact represents one piece of knowledge
- **Typed**: Every fact has a category (Location, Company, Skill, etc.)
- **Reusable**: Multiple entities can share the same fact
- **Traceable**: Every fact links back to its source

## Fact Properties

| Property  | Type   | Required | Description                                       |
|-----------|--------|----------|---------------------------------------------------|
| `name`    | string | Yes      | The value of the fact (e.g., "Paris", "Python")   |
| `type`    | string | Yes      | The category (e.g., "Location", "Skill")          |
| `fact_id` | string | Auto     | Synthetic key combining type and name             |

### The fact_id Synthetic Key

Facts use a composite key rather than a UUID:

```
fact_id = "{type}:{name}"
```

**Examples:**
- `Location:Paris`
- `Company:Acme Corp`
- `Skill:Python`
- `Hobby:Photography`

This design allows the same fact to be reused across multiple entities. If 100 people live in Paris, they all reference the same `Location:Paris` fact node rather than creating 100 duplicate fact nodes.

### Example Fact Structure

```json
{
  "name": "Paris",
  "type": "Location",
  "fact_id": "Location:Paris"
}
```

## The HAS_FACT Relationship

Facts connect to entities through the `HAS_FACT` relationship, which provides semantic context:

```
(Entity) -[HAS_FACT]-> (Fact)
```

### Relationship Properties

| Property          | Type     | Description                                    |
|-------------------|----------|------------------------------------------------|
| `from_entity_id`  | UUID     | The entity that possesses this fact            |
| `to_fact_id`      | string   | The fact being connected                       |
| `verb`            | string   | Semantic relationship (e.g., "lives_in")       |
| `confidence_score`| float    | Confidence level (0.0 to 1.0)                  |
| `created_at`      | datetime | When this relationship was established         |

### The Verb: Semantic Context

The `verb` property is crucial—it describes HOW the entity relates to the fact:

```json
// Alice lives in Paris
{
  "from_entity_id": "uuid-alice",
  "to_fact_id": "Location:Paris",
  "verb": "lives_in",
  "confidence_score": 0.95
}

// Alice works at Acme Corp
{
  "from_entity_id": "uuid-alice",
  "to_fact_id": "Company:Acme Corp",
  "verb": "works_at",
  "confidence_score": 1.0
}

// Alice knows Python
{
  "from_entity_id": "uuid-alice",
  "to_fact_id": "Skill:Python",
  "verb": "knows",
  "confidence_score": 0.8
}
```

The same fact (`Location:Paris`) can have different verbs depending on the relationship:
- `lives_in` - Person's residence
- `visited` - Past travel
- `born_in` - Birthplace
- `wants_to_visit` - Future intention

### Confidence Scores

Every fact has a confidence score from 0.0 to 1.0, representing how certain you are about the information:

| Score Range | Meaning                | Use Case                              |
|-------------|------------------------|---------------------------------------|
| 0.9 - 1.0   | Very High Confidence   | Verified information, official records |
| 0.7 - 0.9   | High Confidence        | Clear statements, reliable sources    |
| 0.5 - 0.7   | Moderate Confidence    | Implied information, indirect sources |
| 0.3 - 0.5   | Low Confidence         | Uncertain, requires verification      |
| 0.0 - 0.3   | Very Low Confidence    | Speculation, rumors, weak signals     |

**Example:**

```python
# Direct statement: "I live in Paris"
confidence_score = 1.0

# Implied information: "I love the croissants here in Paris"
confidence_score = 0.85

# Unclear: "I might move to Paris next year"
confidence_score = 0.4
```

## Fact Extraction

Facts are typically extracted automatically from unstructured text during the assimilation process:

### Input Text
```
"Alice moved to Paris last month and started working at Acme Corp as a Senior Engineer."
```

### Extracted Facts

```json
[
  {
    "name": "Paris",
    "type": "Location",
    "fact_id": "Location:Paris",
    "verb": "lives_in",
    "confidence_score": 0.95
  },
  {
    "name": "Acme Corp",
    "type": "Company",
    "fact_id": "Company:Acme Corp",
    "verb": "works_at",
    "confidence_score": 0.95
  },
  {
    "name": "Senior Engineer",
    "type": "JobTitle",
    "fact_id": "JobTitle:Senior Engineer",
    "verb": "has_title",
    "confidence_score": 0.95
  }
]
```

## Fact Reusability

One of the most powerful features of facts is reusability. Consider:

```
Alice -[lives_in]-> Location:Paris
Bob   -[lives_in]-> Location:Paris
Carol -[visited]->  Location:Paris
```

All three people reference the same `Location:Paris` fact node. This enables:

1. **Efficient Storage**: One fact node, many relationships
2. **Rich Querying**: "Find all entities living in Paris"
3. **Network Analysis**: Understand connections through shared facts
4. **Consistency**: Update "Paris" in one place

## Common Fact Types

While Nous doesn't restrict fact types, here are common categories:

| Type         | Examples                          | Common Verbs                    |
|--------------|-----------------------------------|---------------------------------|
| Location     | Paris, New York, Tokyo            | lives_in, visited, born_in      |
| Company      | Acme Corp, Google, Microsoft      | works_at, worked_at, founded    |
| Skill        | Python, JavaScript, Design        | knows, learning, expert_in      |
| JobTitle     | Engineer, Manager, Designer       | has_title, had_title            |
| Hobby        | Photography, Hiking, Gaming       | enjoys, practices               |
| Interest     | AI, Blockchain, Climate Change    | interested_in, researching      |
| Person       | John Smith, Jane Doe              | knows, reports_to, friends_with |
| Product      | iPhone, Tesla Model 3             | owns, uses, developing          |

## Use Cases

### 1. Personal AI Memory

Track what the AI learns about users:

```
User Entity:
  -[lives_in]-> Location:San Francisco
  -[works_at]-> Company:Startup XYZ
  -[knows]-> Skill:Python
  -[interested_in]-> Interest:AI
```

The AI can recall: "You live in San Francisco, work at Startup XYZ, know Python, and are interested in AI."

### 2. Organization Network

Map relationships between people and organizations:

```
Alice -[works_at]-> Company:Acme Corp
Bob   -[works_at]-> Company:Acme Corp
Carol -[worked_at]-> Company:Acme Corp (confidence: 0.7)
```

Query: "Who currently works at Acme Corp?" (filter by verb="works_at" and high confidence)

### 3. Skill Inventory

Track team capabilities:

```
Alice -[expert_in]-> Skill:Python (confidence: 0.95)
Bob   -[knows]-> Skill:Python (confidence: 0.7)
Carol -[learning]-> Skill:Python (confidence: 0.5)
```

Query: "Who are our Python experts?" (filter by verb="expert_in")

### 4. Research Knowledge Graph

Track concepts and their relationships:

```
Paper_123 -[discusses]-> Concept:Neural Networks
Paper_123 -[discusses]-> Concept:Transformers
Paper_456 -[discusses]-> Concept:Transformers
```

Query: "What papers discuss Transformers?"

## Best Practices

### Choose Descriptive Fact Types

Use specific, consistent type names:

```json
// Good
{ "type": "Location", "name": "Paris" }
{ "type": "Company", "name": "Acme Corp" }
{ "type": "Skill", "name": "Python" }

// Bad (too generic)
{ "type": "Thing", "name": "Paris" }
{ "type": "Entity", "name": "Acme Corp" }
```

### Use Consistent Verb Naming

Standardize your verbs to enable querying:

```json
// Good (consistent tense and format)
"lives_in", "works_at", "knows", "enjoys"

// Bad (inconsistent)
"living_in", "workAt", "Knows", "is_enjoying"
```

**Recommendations:**
- Use snake_case (lives_in, not livesIn or lives-in)
- Use present tense for current facts (works_at, not worked_at)
- Use past tense for historical facts (worked_at, visited)
- Use consistent verbs across similar relationships

### Set Appropriate Confidence Scores

Don't default everything to 1.0:

```python
# Explicit statement → high confidence
"I live in Paris" → 1.0

# Implied but clear → moderate-high confidence
"I love the weather here in Paris" → 0.85

# Ambiguous or future → lower confidence
"I might move to Paris" → 0.4
```

Lower confidence scores help:
- Prioritize reliable information
- Flag facts that need verification
- Enable confidence-based filtering

### Normalize Fact Names

Keep fact names consistent:

```json
// Good (consistent casing and format)
{ "type": "Location", "name": "Paris" }
{ "type": "Location", "name": "New York" }

// Bad (inconsistent casing)
{ "type": "Location", "name": "paris" }
{ "type": "Location", "name": "NEW YORK" }
```

This prevents duplicate facts like `Location:Paris` and `Location:paris`.

## Querying Facts

### Find All Facts for an Entity

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@example.com
```

Returns all facts associated with Alice's entity.

### Filter by Fact Type

```cypher
# Apache AGE query example
SELECT * FROM cypher('nous', $$
  MATCH (e:Entity)-[r:HAS_FACT]->(f:Fact)
  WHERE f.type = 'Location'
  RETURN e, r, f
$$) as (entity agtype, relation agtype, fact agtype);
```

### Filter by Confidence

```cypher
# Find high-confidence facts only
SELECT * FROM cypher('nous', $$
  MATCH (e:Entity)-[r:HAS_FACT]->(f:Fact)
  WHERE r.confidence_score >= 0.8
  RETURN e, r, f
$$) as (entity agtype, relation agtype, fact agtype);
```

## Fact Provenance

Every fact traces back to its source through the `DERIVED_FROM` relationship:

```
(Fact) -[DERIVED_FROM]-> (Source)
```

This enables:
- **Auditability**: "Where did this fact come from?"
- **Trust**: Evaluate facts based on source reliability
- **Debugging**: Track down incorrect information
- **Compliance**: Maintain data lineage for regulations

[Learn more about Sources →](/concepts/sources)

## Common Questions

### Can a fact belong to multiple entities?

Yes! That's the power of the fact model. The same fact node (e.g., `Location:Paris`) can have many `HAS_FACT` relationships pointing to it from different entities.

### How do I update a fact?

Facts themselves are immutable. If information changes:
1. The fact node stays the same (`Location:Paris`)
2. Update the `HAS_FACT` relationship (change verb, confidence score)
3. Or remove the old relationship and create a new one

### Can facts reference other facts?

Not directly in the current schema. Facts are designed to be atomic pieces of knowledge. Complex relationships should be modeled through entities.

### Should I create a fact for every piece of information?

No. Facts work best for:
- Discrete, reusable information
- Knowledge that needs to be queried
- Information shared across entities

For entity-specific notes or metadata, consider using the entity's metadata field or creating a more specific fact type.

## Related Concepts

- [Entities](/concepts/entities) - The subjects that possess facts
- [Sources](/concepts/sources) - Where facts originate from
- [Overview](/concepts/overview) - How facts fit into the knowledge graph
