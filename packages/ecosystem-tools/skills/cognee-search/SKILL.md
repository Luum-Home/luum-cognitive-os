---
name: cognee-search
version: 1.0.0
description: Semantic knowledge graph search via Cognee — complements Engram FTS5
  with relationship-aware retrieval
triggers:
- semantic search
- knowledge graph
- deep search
- relationship search
- cognee
tags:
- memory
- search
- knowledge-graph
requires:
- COGNEE_ENABLED=true
- Cognee container running (docker compose --profile memory)
audience: project
summary_line: Semantic knowledge graph search via Cognee — complements Engram FTS5
  with…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bcognee[- ]?search\b
  confidence: 0.95
- pattern: \bsearch\s+(via\s+)?cognee\b
  confidence: 0.85
- pattern: \bcognee\s+(knowledge|graph)\b
  confidence: 0.75
routing_intents:
- intent: cognee_search_request
  description: User asks to semantic knowledge graph search via Cognee — complements
    Engram FTS5 with relationship-aware retrieval.
  confidence: 0.85
---
<!-- SCOPE: both -->
# Cognee Search

## Purpose

Provides deep semantic search across codebase knowledge using Cognee's knowledge graph.
While Engram uses FTS5 (keyword-based full-text search), Cognee builds a graph of
entities and relationships, enabling queries like "how does service A relate to service B"
or "what patterns are used across the auth layer."

## When to Use

- When Engram FTS5 search returns no results for a conceptual query
- When you need relationship-aware results (entity connections, dependency chains)
- When searching for architectural patterns across multiple files/services
- When the query is semantic rather than keyword-based

## When NOT to Use

- For exact keyword matches (Engram FTS5 is faster and sufficient)
- For session-specific context (use `mem_context` instead)
- When Cognee is not running (gracefully returns empty results)

## Prerequisites

1. Cognee container must be running: `docker compose --profile memory up cognee`
2. Environment: `COGNEE_ENABLED=true`
3. Knowledge must be ingested first via `add_knowledge` or the cognify pipeline

## Steps

### 1. Check Availability

```python
from lib.cognee_client import is_cognee_available, is_cognee_enabled

if not is_cognee_enabled():
    print("Cognee not enabled. Set COGNEE_ENABLED=true")
    # Fall back to Engram search
elif not is_cognee_available():
    print("Cognee container not running")
    # Fall back to Engram search
```

### 2. Ingest Knowledge (if needed)

```python
from lib.cognee_client import CogneeClient

client = CogneeClient()

# Add codebase context
client.add_knowledge(
    text="The auth service validates JWT tokens using RS256...",
    source="internal/auth/jwt_validator.go",
)

# Build knowledge graph
client.cognify()
```

### 3. Search

```python
results = client.search("how does authentication work", limit=5)
for r in results:
    print(r.get("content", ""), r.get("score", 0))
```

### 4. Graceful Fallback

```python
from lib.cognee_client import search_graceful

# Returns empty list if Cognee is unavailable — never raises
results = search_graceful("JWT token validation", limit=5)
if not results:
    # Fall back to Engram
    # mem_search(query="JWT token validation", project="my-project")
    pass
```

## Search Types

| Type | Description | Use Case |
|------|-------------|----------|
| `INSIGHTS` | Graph-based semantic search (default) | Conceptual queries |
| `CHUNKS` | Vector similarity on text chunks | Exact content retrieval |
| `GRAPH_COMPLETION` | Graph traversal from entities | Relationship exploration |

## Integration with Engram

The recommended search strategy is layered:

1. **First**: Engram `mem_search` (fast FTS5 keyword search)
2. **If no results**: Cognee `search` (semantic graph search)
3. **If still no results**: Cognee `search` with `CHUNKS` type (vector similarity)

This ensures fast results for known terms while falling back to semantic
understanding for conceptual queries.
