# Delete Entity with Cascading Cleanup Implementation Plan

This document outlines the implementation plan for enhancing the `delete_entity_by_id` method in `GraphRepository` to perform proper cascading cleanup of orphan resources.

## Current State

Currently, `delete_entity_by_id` only deletes the Entity vertex. Connected edges are automatically removed by ArcadeDB, but connected vertices (identifiers, facts, sources) remain in the database as orphans, potentially causing data inconsistency.

## Target Implementation

The enhanced `delete_entity_by_id` method should perform cascading cleanup:

1. **Find the entity to be deleted** - Verify the entity exists and get its internal RID
2. **Find connected identifiers** - Query all Identifier vertices connected to this entity
3. **Delete orphan identifiers** - Only delete identifiers that are not connected to other entities
4. **Delete the entity** - Remove the entity vertex itself

## Step-by-Step Implementation

### Step 1: Find the Entity to be Deleted

```python
# Check if entity exists and get its RID for subsequent queries
entity_query = f"SELECT @rid FROM Entity WHERE id = '{entity_id}'"
entity_result = await self.db.execute_command(
    entity_query, database_name, language="sql"
)

if not entity_result or not entity_result.get("result"):
    return False  # Entity not found

entity_rid = entity_result["result"][0]["@rid"]
```

### Step 2: Find Connected Identifiers

```python
# Find all identifiers connected to this entity via HAS_IDENTIFIER edges
connected_identifiers_query = f"""
SELECT @rid FROM Identifier
WHERE @rid IN (SELECT in FROM HAS_IDENTIFIER WHERE out = '{entity_rid}')
"""
identifiers_result = await self.db.execute_command(
    connected_identifiers_query, database_name, language="sql"
)
```

### Step 3: Identify Orphan Identifiers

For each connected identifier, check if it has connections to other entities (excluding the one being deleted):

```python
identifiers_to_delete = []
if identifiers_result and identifiers_result.get("result"):
    for identifier in identifiers_result["result"]:
        identifier_rid = identifier["@rid"]

        # Check if this identifier is connected to other entities
        other_connections_query = f"""
        SELECT FROM HAS_IDENTIFIER
        WHERE in = '{identifier_rid}' AND out != '{entity_rid}'
        LIMIT 1
        """
        connections_result = await self.db.execute_command(
            other_connections_query, database_name, language="sql"
        )

        # If no other connections exist, this identifier is an orphan
        if not connections_result or not connections_result.get("result"):
            identifiers_to_delete.append(identifier_rid)
```

### Step 4: Delete Orphan Identifiers

```python
# Delete each orphan identifier
for identifier_rid in identifiers_to_delete:
    delete_identifier_query = f"DELETE VERTEX FROM `{identifier_rid}`"
    await self.db.execute_command(delete_identifier_query, database_name, language="sql")
```

### Step 5: Delete the Entity

```python
# Finally, delete the entity itself
delete_entity_query = f"DELETE VERTEX FROM `{entity_rid}`"
delete_result = await self.db.execute_command(
    delete_entity_query, database_name, language="sql"
)

return bool(
    delete_result
    and delete_result.get("result")
    and delete_result["result"][0].get("count", 0) > 0
)
```

## Key Considerations

### SQL Query Safety

- Use parameterized queries where possible to prevent injection
- Escape RID values properly in queries
- Handle ArcadeDB's specific SQL syntax requirements

### Orphan Detection Logic

- An identifier is an orphan if it has no HAS_IDENTIFIER edges to entities other than the one being deleted
- Use `LIMIT 1` for efficiency when checking for existence
- Compare RIDs directly for precision

### Transaction Integrity

- While ArcadeDB doesn't support full transactions for this operation, the sequence ensures data consistency
- If any step fails, the method raises an exception to prevent partial cleanup

### Performance Considerations

- Minimize the number of database round trips
- Use efficient queries that leverage ArcadeDB's indexing
- Consider batching deletes if many orphans exist

## Future Extensions

This implementation can be extended to handle Facts and Sources:

1. **Facts Cleanup**: After deleting orphan identifiers, check for orphan facts using similar logic with HAS_FACT edges
2. **Sources Cleanup**: For each orphan fact, check for orphan sources using DERIVED_FROM edges
3. **Batch Operations**: If many resources need deletion, consider batching the DELETE operations

## Testing Strategy

The implementation should be tested with:

1. **Basic deletion**: Entity with unique identifiers (all should be deleted)
2. **Shared identifiers**: Entity with identifiers shared by other entities (identifiers should be preserved)
3. **Non-existent entity**: Should return False without error
4. **Edge cases**: Empty entity_id, malformed RIDs, etc.
