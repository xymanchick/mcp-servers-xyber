# Qdrant MCP Server Configuration

This document explains how Qdrant search works and how to configure it for optimal performance.

## How Qdrant Search Works

Qdrant provides **4 levels** of search performance, from basic to advanced:

### 1. Basic Search (No Filters)
Pure semantic search across all documents in a collection.
```python
qdrant_find(query="machine learning", collection_name="docs")
```
**Performance**: Fast for small collections, slower as data grows.

### 2. Basic Filtering (No Indexes)
Search with payload filters, but no indexes configured.
```python
qdrant_find(
    query="machine learning",
    collection_name="docs",
    filters={"metadata.category": "ai"}
)
```
**Performance**: Qdrant scans all documents to apply filters. Slow for large datasets.

### 3. Advanced Filtering (Payload Indexes)
Search with filters on indexed fields.
```python
qdrant_find(
    query="machine learning",
    collection_name="docs",
    filters={"metadata.category": "ai", "metadata.priority": 10}
)
```
**Performance**: Very fast filtering using indexes. Recommended for production.

### 4. Tenant-Based Filtering (Fastest)
Multi-tenant setup with dedicated per-tenant indexes.
```python
qdrant_find(
    query="machine learning",
    collection_name="docs",
    filters={"metadata.user_id": "alice"}  # tenant field
)
```
**Performance**: Extremely fast. Data is partitioned by tenant for optimal isolation and speed.

## Filter Processing & Performance

**Important**: Qdrant applies filters **DURING** vector search, not before or after. Based on the official documentation:

> "We do filtering **during** the vector search... we check conditions dynamically during the traversal of HNSW graph."

### Qdrant's Smart Filtering Strategy:
Qdrant's query planner chooses different strategies based on filter selectivity:

```python
# High selectivity (restrictive filters):
# → Uses payload index directly, then re-scores by similarity

# Low selectivity (broad filters):
# → Uses filterable HNSW with dynamic condition checking during search
```

### Key Benefits:
- ✅ **Adaptive**: Automatically chooses optimal strategy based on filter cardinality
- ✅ **Dynamic**: Checks conditions during graph traversal, not all documents
- ✅ **Efficient**: Limits condition checks by orders of magnitude
- ✅ **Accurate**: Maintains search quality while filtering

## Configuration Examples

Configure your MCP server using environment variables:

### Basic Setup (No Indexes)
```bash
# No additional configuration needed
# Uses default Qdrant settings
```

### Advanced Setup (Payload Indexes)
```bash
# Create indexes for fast filtering
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__FIELD_NAME=metadata.category
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__INDEX_TYPE=keyword

QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__1__FIELD_NAME=metadata.priority
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__1__INDEX_TYPE=integer
```

### Multi-Tenant Setup (Fastest)
```bash
# Disable global index, enable per-tenant partitioning
QDRANT_COLLECTION_CONFIG__HNSW_CONFIG__M=0
QDRANT_COLLECTION_CONFIG__HNSW_CONFIG__PAYLOAD_M=16

# Configure tenant field (user_id) with special tenant indexing
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__FIELD_NAME=metadata.user_id
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__INDEX_TYPE=keyword
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__IS_TENANT=true

# Additional indexes for other fields
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__1__FIELD_NAME=metadata.category
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__1__INDEX_TYPE=keyword
```

## Index Types

| Type | Use Case | Example |
|------|----------|---------|
| `keyword` | Exact string matching | user IDs, categories, tags |
| `integer` | Numeric values | priorities, counts, years |
| `float` | Decimal numbers | scores, ratings, prices |
| `bool` | True/false values | flags, status |

## Multi-Tenant Rules

- **Only one field** can have `IS_TENANT=true`
- **Tenant field must be `keyword` type**
- When using tenants: set `M=0` and `PAYLOAD_M=16`

## Performance Comparison

| Setup | Write Speed | Search Speed | Tenant Filtering | Memory Usage |
|-------|-------------|--------------|------------------|--------------|
| Basic | Fast | Slow (large data) | Slow | Low |
| Indexed | Medium | Fast | Fast | Medium |
| Multi-Tenant | Very Fast | Very Fast | Extremely Fast | High |

## Quick Start

1. **Start simple**: Use basic search first
2. **Add indexes**: When you need faster filtering, add payload indexes
3. **Enable multi-tenancy**: When you have user-specific data that needs isolation

Example progression:
```bash
# Step 1: Basic (no config needed)

# Step 2: Add indexes for your common filters
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__FIELD_NAME=metadata.category
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__INDEX_TYPE=keyword

# Step 3: Enable multi-tenancy for user isolation
QDRANT_COLLECTION_CONFIG__HNSW_CONFIG__M=0
QDRANT_COLLECTION_CONFIG__HNSW_CONFIG__PAYLOAD_M=16
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__FIELD_NAME=metadata.user_id
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__INDEX_TYPE=keyword
QDRANT_COLLECTION_CONFIG__PAYLOAD_INDEXES__0__IS_TENANT=true
```

## Checking Your Configuration

Use `qdrant_get_collection_info` to verify your setup:
```python
info = await qdrant_get_collection_info("my_collection")
print(info["payload_schema"])  # Shows your configured indexes
```

**Note**: Configuration only applies to **new collections**. Delete existing collections to apply new settings.
