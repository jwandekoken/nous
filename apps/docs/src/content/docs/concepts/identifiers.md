---
title: Identifiers
description: External handles that connect the real world to your knowledge graph
---

An **Identifier** is an external, real-world handle that points to an entity in your knowledge graph. Examples include email addresses, phone numbers, usernames, or any external ID used to reference a subject.

## What is an Identifier?

While entities use stable internal UUIDs, the real world doesn't work with UUIDs. People use emails, phone numbers, usernames, and other identifiers. Identifiers bridge this gap—they're the external "addresses" that map to your internal entity system.

### Key Characteristics

- **External References**: Real-world handles like emails, phones, usernames
- **Many-to-One**: Multiple identifiers can point to the same entity
- **Unique Values**: Each identifier value must be unique across the system
- **Typed**: Each identifier has a type (email, phone, username, etc.)

## Identifier Properties

| Property | Type   | Required | Description                                      |
|----------|--------|----------|--------------------------------------------------|
| `value`  | string | Yes      | The identifier value (e.g., "alice@example.com") |
| `type`   | string | Yes      | Type of identifier (see supported types below)   |

### Supported Identifier Types

Nous validates identifier types to ensure consistency:

- `email` - Email addresses
- `phone` - Phone numbers
- `username` - Username handles
- `uuid` - External system UUIDs
- `social_id` - Social media identifiers

### Example Identifier Structure

```json
{
  "value": "alice@example.com",
  "type": "email"
}
```

## Why Use Identifiers?

### The Identity Resolution Problem

Consider these interactions:

1. **Monday**: Someone emails you from `alice@company.com`
2. **Wednesday**: You get a call from `+1-555-0123`
3. **Friday**: You receive a Slack message from `@alice.smith`

Are these three different people or the same person? Identifiers help you resolve this:

```
alice@company.com  ──┐
                     ├──> Entity (UUID: 550e8400...)
+1-555-0123        ──┤
                     │
@alice.smith       ──┘
```

All three identifiers point to the same canonical entity.

### Benefits

1. **Prevent Duplicate Profiles**: Link new identifiers to existing entities
2. **Flexible Lookup**: Find entities using any identifier they're associated with
3. **Cross-Platform Integration**: Different systems can use different identifiers for the same entity
4. **Historical Tracking**: Keep old identifiers even after someone changes their email or phone

## The HAS_IDENTIFIER Relationship

Identifiers connect to entities through the `HAS_IDENTIFIER` relationship:

```
(Entity) -[HAS_IDENTIFIER]-> (Identifier)
```

### Relationship Properties

| Property     | Type     | Description                                |
|--------------|----------|--------------------------------------------|
| `from_entity_id` | UUID | The entity that owns this identifier    |
| `to_identifier_value` | string | The identifier being connected    |
| `is_primary` | boolean  | Whether this is the primary identifier     |
| `created_at` | datetime | When this relationship was established     |

### Primary Identifiers

You can mark one identifier as "primary" to serve as the default or preferred identifier for an entity:

```json
{
  "from_entity_id": "550e8400-e29b-41d4-a716-446655440000",
  "to_identifier_value": "alice@example.com",
  "is_primary": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

This is useful for:
- Display names in UIs
- Default contact methods
- Prioritizing identifiers when multiple exist

## Working with Identifiers

### Looking Up Entities by Identifier

The most common operation is finding an entity using one of its identifiers:

```bash
GET /entities/lookup?identifier_type=email&identifier_value=alice@example.com
```

This returns the complete entity profile, including:
- The entity UUID
- All associated identifiers
- All facts
- All sources

### Adding New Identifiers

When you discover a new identifier for an existing entity, you can link it:

```bash
# During assimilation, if the identifier already exists,
# Nous will add facts to the existing entity
POST /entities/assimilate
{
  "identifier": {
    "type": "phone",
    "value": "+1-555-0123"
  },
  "content": "Alice called to confirm her address in Paris."
}
```

If `+1-555-0123` doesn't exist yet, this creates it and potentially merges with an existing entity (based on your identity resolution logic).

### Identifier Validation

Nous validates identifiers to prevent errors:

**Value Validation:**
- Cannot be empty or whitespace-only
- Automatically trimmed of leading/trailing spaces

**Type Validation:**
- Must be one of the supported types
- Invalid types are rejected with an error

## Use Cases

### 1. Multi-Channel Customer Support

Track a customer across channels:

```
customer@email.com    ──┐
                        ├──> Customer Entity
+1-555-HELP          ──┤
                        │
@customer_twitter    ──┘
```

Support agents can look up the customer by any identifier and see the complete interaction history.

### 2. User Migration

When migrating users between systems:

```
old_system_id: "12345"  ──┐
                          ├──> User Entity
new_system_id: "uuid-..."──┘
```

Keep both identifiers linked during the transition period.

### 3. Privacy-Compliant Deletion

When a user requests identifier deletion (GDPR, etc.):
- Delete the specific identifier
- Keep the entity and other identifiers intact
- Maintain data lineage without the deleted identifier

## Best Practices

### Always Use the Correct Type

Don't store all identifiers as generic strings. Use the appropriate type:

```json
// Good
{ "type": "email", "value": "alice@example.com" }
{ "type": "phone", "value": "+1-555-0123" }

// Bad
{ "type": "identifier", "value": "alice@example.com" }
{ "type": "identifier", "value": "+1-555-0123" }
```

This enables:
- Validation at creation time
- Type-specific querying
- Better analytics and reporting

### Normalize Values Before Storage

Standardize identifier values:

- **Emails**: Lowercase, trimmed
- **Phone numbers**: Use E.164 format (`+1-555-0123`)
- **Usernames**: Lowercase, no whitespace

This prevents duplicate identifiers like `Alice@example.com` and `alice@example.com`.

### Use Primary Flags Wisely

Only mark one identifier as primary per entity. If you need multiple "preferred" identifiers:
- Use one primary identifier for display
- Store preferences in entity metadata or as facts

### Don't Store Sensitive Data in Identifiers

Identifiers should be references, not containers for sensitive information. For example:
- ✅ Store `identifier: "user123"`
- ❌ Don't store `identifier: "ssn:123-45-6789"`

Use facts with appropriate security measures for sensitive data.

## Identity Resolution Strategies

When you encounter a new identifier, you face a key decision: does this identifier belong to an existing entity or a new one?

### Strategy 1: Always Create New

The simplest approach—every new identifier creates a new entity:

```
alice@work.com    ──> Entity A
alice@personal.com ──> Entity B
```

Later, you can manually merge Entity A and Entity B if you discover they're the same person.

### Strategy 2: Rule-Based Matching

Use business logic to link identifiers:
- Same email domain + same first name → same entity
- Same phone number → same entity
- Explicit user confirmation → same entity

### Strategy 3: Explicit Linking API

Provide an API for manually linking identifiers:

```bash
POST /entities/{entity_id}/identifiers
{
  "type": "email",
  "value": "alice@personal.com",
  "is_primary": false
}
```

This gives you full control over identity resolution.

## Common Questions

### Can two entities share the same identifier?

No. Each identifier value must be unique across the entire system. This ensures deterministic lookups—given an identifier, you can always find exactly one entity.

### What happens if I try to create a duplicate identifier?

The system will reject it with a validation error. You should first check if the identifier exists and link to that entity if appropriate.

### Can I change an identifier's value?

Identifiers are meant to be immutable references. If someone's email changes, don't update the identifier—instead:
1. Create a new identifier with the new email
2. Optionally mark it as primary
3. Keep the old identifier for historical reference

### How do I handle temporary identifiers?

For temporary identifiers (session IDs, one-time tokens), consider:
- Using a different storage mechanism (cache, session store)
- Using facts with expiration metadata instead
- Only creating identifiers for persistent, long-lived references

## Related Concepts

- [Entities](/concepts/entities) - The canonical subject that identifiers point to
- [Facts](/concepts/facts) - Knowledge associated with entities
- [Overview](/concepts/overview) - How all concepts fit together
