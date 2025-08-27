# KuzuDB Integration Guide

This document describes the integration between our application and KuzuDB, including the challenges encountered and the solutions implemented.

## Overview

KuzuDB is a high-performance graph database that uses Cypher as its query language. Our application integrates with KuzuDB through its HTTP API server to manage graph entities, relationships, and associated metadata.

## Issues Discovered and Solutions

### 1. Primary Key Requirement

#### Issue

KuzuDB requires the primary key (`id`) to be provided when creating Entity nodes. Unlike some databases that auto-generate primary keys during insertion, KuzuDB's `MERGE` operation expects the primary key value to be known upfront.

#### Original Problematic Code

```cypher
MERGE (e:Entity)-[r:HAS_IDENTIFIER]->(i)
ON CREATE SET
    e.id = $entity_id,  -- This fails because KuzuDB doesn't know the primary key
    ...
```

#### Solution

Provide the UUID directly in the `MERGE` clause using the `uuid()` function:

```cypher
MERGE (e:Entity {id: uuid('550e8400-e29b-41d4-a716-446655440000')})
ON CREATE SET
    e.created_at = timestamp('2025-08-27 10:03:43'),
    ...
```

### 2. Timestamp Format Handling

#### Issue

KuzuDB's HTTP API is strict about data type conversions and doesn't automatically convert ISO timestamp strings to TIMESTAMP types. This results in "Implicit cast is not supported" errors.

#### Original Problematic Code

```cypher
e.created_at = $created_at,  -- Passing ISO string directly
```

#### Solution

Use KuzuDB's `timestamp()` function to explicitly convert string to TIMESTAMP:

```cypher
e.created_at = timestamp('2025-08-27 10:03:43'),
```

**Format Requirements:**

- Use format: `YYYY-MM-DD HH:MM:SS`
- No milliseconds or timezone offsets in the string
- Function handles conversion to KuzuDB's internal TIMESTAMP format

### 3. MAP vs STRUCT Data Types

#### Issue

KuzuDB distinguishes between `STRUCT` and `MAP` data types:

- **STRUCT**: Fixed schema with named fields, created with `{key: value}` syntax
- **MAP**: Variable schema key-value pairs, created with `map([keys], [values])` function

When Python dictionaries are sent via HTTP API parameters, they get serialized as JSON objects, which KuzuDB interprets as STRUCT rather than MAP, causing type mismatch errors.

#### Original Problematic Code

```cypher
e.metadata = $metadata,  -- Python dict serialized as STRUCT
```

#### Solution

Convert Python dictionaries to KuzuDB MAP format using the `map()` function:

```python
# Python code to convert dict to MAP syntax
keys = list(entity.metadata.keys())
values = list(entity.metadata.values())
keys_str = ", ".join([f"'{k}'" for k in keys])
values_str = ", ".join([f"'{v}'" for v in values])
metadata_clause = f"e.metadata = map([{keys_str}], [{values_str}])"
```

```cypher
-- Resulting Cypher query
e.metadata = map(['key1', 'key2'], ['value1', 'value2']),
```

**MAP Format:**

- `map([keys_array], [values_array])`
- Keys and values must be arrays of the same length
- All keys must be the same type (typically STRING)
- All values must be the same type (typically STRING for metadata)

## Data Type Mapping

| Python Type      | KuzuDB Type           | Conversion Method                |
| ---------------- | --------------------- | -------------------------------- |
| `UUID`           | `UUID`                | `uuid('string')` function        |
| `datetime`       | `TIMESTAMP`           | `timestamp('string')` function   |
| `dict[str, str]` | `MAP(STRING, STRING)` | `map([keys], [values])` function |
| `str`            | `STRING`              | Direct parameter passing         |
| `bool`           | `BOOLEAN`             | Direct parameter passing         |

## Best Practices

1. **Always provide primary keys explicitly** when using `MERGE` operations
2. **Use KuzuDB type conversion functions** instead of relying on implicit casting
3. **Convert Python dicts to MAP syntax** when working with key-value metadata
4. **Handle empty collections properly** (e.g., `map([], [])` for empty metadata)
5. **Test queries directly** against KuzuDB to verify type compatibility

## References

- [KuzuDB Data Types Documentation](https://docs.kuzudb.com/cypher/data-types/)
- [KuzuDB MAP Functions](https://docs.kuzudb.com/cypher/expressions/map-functions/)
- [KuzuDB Timestamp Documentation](https://docs.kuzudb.com/cypher/data-types/#timestamp)

## Future Considerations

- Monitor KuzuDB updates for changes in type handling behavior
- Consider implementing connection pooling for better performance
- Evaluate the need for custom serializers for complex data types
- Investigate KuzuDB's native Python client as an alternative to HTTP API
