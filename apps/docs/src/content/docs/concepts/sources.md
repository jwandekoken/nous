---
title: Sources
description: Tracking the provenance and origin of knowledge in your graph
---

A **Source** represents the origin of information in your knowledge graph. Sources capture where facts came from—a chat message, email, document, API call, or any piece of content from which knowledge was extracted.

## What is a Source?

In Nous, every fact must be traceable back to its origin. Sources provide this traceability, answering the critical question: "How do we know this?"

### Key Characteristics

- **Provenance Tracking**: Every fact links back to a source
- **Content Preservation**: Stores the original text or data
- **Temporal Context**: Records when the source was created
- **Audit Trail**: Enables verification and debugging

## Source Properties

| Property    | Type     | Required | Description                                    |
|-------------|----------|----------|------------------------------------------------|
| `id`        | UUID     | Auto     | Unique system identifier                       |
| `content`   | string   | Yes      | The original content/source text               |
| `timestamp` | datetime | Auto     | Real-world timestamp when source was created   |

### Example Source Structure

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "content": "Alice moved to Paris last month and started working at Acme Corp.",
  "timestamp": "2025-01-15T14:30:00Z"
}
```

## Why Track Sources?

### 1. Auditability

When facts conflict or need verification, sources provide the evidence:

```
Fact: Alice lives in Paris
  ↓ DERIVED_FROM
Source (Jan 15): "Alice moved to Paris last month"

Fact: Alice lives in London
  ↓ DERIVED_FROM
Source (Dec 10): "Alice is settling into her new flat in London"
```

By comparing sources and timestamps, you can determine:
- Which information is more recent?
- Which source is more authoritative?
- Whether facts need updating or reconciliation

### 2. Trust and Confidence

Not all sources are equally reliable. Sources enable trust-based reasoning:

```
Source A: Official company announcement → High trust
Source B: Social media rumor → Lower trust
Source C: Direct message from the person → Highest trust
```

You can adjust fact confidence scores based on source reliability.

### 3. Debugging and Correction

When you discover incorrect information:
1. Trace the fact back to its source
2. Identify why the extraction was wrong
3. Fix the root cause (extraction logic, source quality)
4. Re-process or update the fact

### 4. Compliance and Regulations

Many industries require data lineage:
- **Healthcare**: Track where patient information originated
- **Finance**: Audit trail for financial data
- **Legal**: Chain of custody for evidence
- **GDPR**: Know where personal data came from

## The DERIVED_FROM Relationship

Facts connect to sources through the `DERIVED_FROM` relationship:

```
(Fact) -[DERIVED_FROM]-> (Source)
```

### Relationship Properties

| Property       | Type   | Description                           |
|----------------|--------|---------------------------------------|
| `from_fact_id` | string | The fact that was derived             |
| `to_source_id` | UUID   | The source where fact originated      |

### Example Relationship

```json
{
  "from_fact_id": "Location:Paris",
  "to_source_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

This links the fact `Location:Paris` to the source containing "Alice moved to Paris last month."

## Understanding Timestamps

Sources use a **real-world timestamp** (`timestamp`) that represents when the original event occurred:

```json
{
  "timestamp": "2025-01-15T14:30:00Z"  // When the message was sent
}
```

This is different from system timestamps like `created_at` on entities and relationships, which track when records were added to Nous.

### Event Time vs System Time

| Time Type    | Field        | Meaning                                 |
|--------------|--------------|------------------------------------------|
| Event Time   | `timestamp`  | When the real-world event happened       |
| System Time  | `created_at` | When Nous recorded the information       |

**Example:**

```
User sends a message on Jan 15 at 2:00 PM
  → Source.timestamp = "2025-01-15T14:00:00Z"

Message is processed by Nous on Jan 16 at 10:00 AM
  → Entity.created_at = "2025-01-16T10:00:00Z"
```

This separation enables:
- **Temporal Queries**: "What did we know about Alice in December?"
- **Historical Analysis**: Reconstruct the state of knowledge at any point in time
- **Audit Trails**: Distinguish when events occurred vs. when they were recorded

## Source Types and Metadata

While the source model is flexible, different sources have different characteristics. Consider using the entity metadata pattern for source categorization:

### Common Source Types

```json
// Chat message
{
  "content": "Alice: I just moved to Paris!",
  "timestamp": "2025-01-15T14:30:00Z",
  "metadata": {
    "type": "chat_message",
    "channel": "slack",
    "user_id": "U12345"
  }
}

// Email
{
  "content": "Subject: New Address\n\nHi team, my new address is...",
  "timestamp": "2025-01-10T09:00:00Z",
  "metadata": {
    "type": "email",
    "from": "alice@example.com",
    "subject": "New Address"
  }
}

// Document
{
  "content": "Employee record updated: Alice Smith, Location: Paris",
  "timestamp": "2025-01-15T16:00:00Z",
  "metadata": {
    "type": "document",
    "document_id": "doc-123",
    "file_type": "pdf"
  }
}

// API Call
{
  "content": "{\"user\": \"alice\", \"location\": \"Paris\"}",
  "timestamp": "2025-01-15T14:35:00Z",
  "metadata": {
    "type": "api_response",
    "endpoint": "/users/alice",
    "source_system": "crm"
  }
}
```

Note: The current schema doesn't include a metadata field on sources, but you can extend it or encode metadata in the content field.

## Working with Sources

### Creating Sources During Assimilation

Sources are typically created automatically during the assimilation process:

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
1. Create a new source with the content
2. Extract facts from the content
3. Link facts to the source via `DERIVED_FROM`
4. Associate facts with the entity

### Retrieving Sources for Facts

When you look up an entity, sources are included in the response:

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@example.com
```

Response includes:
- The entity
- All facts
- All sources for those facts

This provides complete transparency: "Here's what we know about Alice and where we learned it."

## Use Cases

### 1. Conversational AI Memory

Track conversation history:

```
Source 1 (Jan 5): "I love hiking in the mountains"
  → Fact: Hobby:Hiking

Source 2 (Jan 12): "I'm planning a trip to Colorado"
  → Fact: Location:Colorado (verb: planning_to_visit)

Source 3 (Jan 20): "Just got back from an amazing hike in Rocky Mountain National Park"
  → Fact: Location:Colorado (verb: visited)
```

The AI can say: "Last time we talked on January 12th, you were planning a trip to Colorado. How was it?"

### 2. Customer Support Context

Build a timeline of customer interactions:

```
Source A (Dec 1): "My account is locked"
  → Fact: Issue:Account Locked

Source B (Dec 2): Support ticket resolved
  → Fact: Status:Resolved

Source C (Jan 5): "Same issue again!"
  → Fact: Issue:Account Locked (second occurrence)
```

Support agents can see: "This is the second time this month the customer has reported this issue."

### 3. Research Knowledge Management

Track the lineage of research findings:

```
Paper A (2023): Claims X is true
  → Fact: Claim:X (confidence: 0.8)

Paper B (2024): Confirms X with additional evidence
  → Same Fact: Claim:X (confidence: 0.95)

Paper C (2025): Disputes X
  → Conflicting Fact: Claim:Not-X (confidence: 0.7)
```

Researchers can see: "Claim X has support from Papers A and B but is disputed in Paper C."

### 4. Data Lineage for Compliance

Demonstrate where personal data came from:

```
Source: User registration form (2024-01-15)
  → Fact: Email:alice@example.com
  → Fact: Location:Paris

Source: Customer support chat (2024-03-20)
  → Fact: Phone:+1-555-0123

Source: Account settings update (2024-06-10)
  → Fact: Location:London (updated)
```

For GDPR requests, you can provide: "Here's all data we collected about you and when we collected it."

## Best Practices

### Preserve Original Content

Always store the complete, original source text:

```json
// Good
{
  "content": "User: I just moved to Paris last week! Loving it so far."
}

// Bad (information lost)
{
  "content": "Moved to Paris"
}
```

Original content enables:
- Re-processing with improved extraction logic
- Human review when facts conflict
- Context for ambiguous information

### Use Accurate Timestamps

Set the `timestamp` to when the event occurred, not when you processed it:

```python
# Good
source.timestamp = message.sent_at  # When the user sent the message

# Bad
source.timestamp = datetime.now()  # When you're processing it
```

### Don't Delete Sources Prematurely

Even after facts are extracted, keep sources for:
- Audit trails
- Re-extraction with improved models
- Human verification

Only delete sources when:
- Legal requirements mandate it (GDPR deletion requests)
- Storage constraints absolutely require it
- Facts have been thoroughly verified through other means

### Consider Source Authority

When facts conflict, source authority matters:

```python
# High authority
official_document_source → confidence = 1.0

# Medium authority
user_statement_source → confidence = 0.85

# Low authority
third_party_rumor_source → confidence = 0.5
```

You can encode authority in:
- The fact's confidence score
- Source metadata (if extended)
- Your fact extraction logic

## Querying Sources

### Find All Sources for an Entity

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@example.com
```

Returns entity with all facts and their sources.

### Trace a Specific Fact to Sources

```cypher
# Apache AGE query example
SELECT * FROM cypher('nous', $$
  MATCH (f:Fact {fact_id: 'Location:Paris'})-[d:DERIVED_FROM]->(s:Source)
  RETURN f, d, s
  ORDER BY s.timestamp DESC
$$) as (fact agtype, relation agtype, source agtype);
```

### Find Sources by Time Range

```cypher
SELECT * FROM cypher('nous', $$
  MATCH (s:Source)
  WHERE s.timestamp >= '2025-01-01T00:00:00Z'
    AND s.timestamp < '2025-02-01T00:00:00Z'
  RETURN s
  ORDER BY s.timestamp
$$) as (source agtype);
```

## Source Validation

Sources validate their content to prevent errors:

**Content Validation:**
- Cannot be empty or whitespace-only
- Automatically trimmed of leading/trailing spaces

```python
# Valid
Source(content="Alice moved to Paris")

# Invalid (raises ValueError)
Source(content="")
Source(content="   ")
```

## Common Questions

### Can multiple facts come from the same source?

Yes! A single source often produces multiple facts:

```
Source: "Alice moved to Paris and started working at Acme Corp"
  ↓ DERIVED_FROM
  ├── Fact: Location:Paris
  ├── Fact: Company:Acme Corp
  └── Fact: JobTitle:Employee
```

### Can a fact have multiple sources?

Yes! The same fact can be confirmed by multiple sources:

```
Fact: Location:Paris
  ↓ DERIVED_FROM (from multiple sources)
  ├── Source A: "Alice lives in Paris"
  ├── Source B: "Sent from Paris, France"
  └── Source C: "Alice's Paris office"
```

This increases confidence in the fact.

### Should I create a source for manually entered facts?

Yes. Even for manual entries, create a source to maintain provenance:

```json
{
  "content": "Admin manually verified: Alice works at Acme Corp",
  "timestamp": "2025-01-15T10:00:00Z"
}
```

This documents who added the information and when.

### How do I handle sources that contain multiple entities?

One source can mention multiple entities:

```
Source: "Alice and Bob both moved to Paris"
  ↓ DERIVED_FROM
  ├── Entity (Alice) → Fact: Location:Paris
  └── Entity (Bob) → Fact: Location:Paris
```

The same source produces facts for different entities.

## Related Concepts

- [Facts](/concepts/facts) - The knowledge derived from sources
- [Entities](/concepts/entities) - The subjects facts are about
- [Overview](/concepts/overview) - How sources fit into the knowledge graph
