<!-- SCOPE: both -->
---
name: cognee-integration
description: >
  Configure and use Cognee for knowledge graph memory.
  Provides structured knowledge extraction, graph-based retrieval, and MCP server integration.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: topoteretes/cognee
  tool-license: Apache-2.0
  tool-ring: ADOPT
  tool-score: 8.20
audience: os-dev
summary_line: Configure and use Cognee for knowledge graph memory.

---

## Purpose

Integrate Cognee as a knowledge graph memory layer that complements Engram. While Engram provides flat observation-based memory, Cognee adds relationship-aware knowledge graphs with semantic search, enabling agents to understand connections between concepts, decisions, and patterns.

## Invocation

`/cognee-setup` — Initial configuration
`/cognee-add <source>` — Add knowledge from a source (file, URL, text)
`/cognee-search <query>` — Search the knowledge graph

## Setup

### Prerequisites
- Python 3.10+
- `pip install cognee`
- Graph database backend: Neo4j (recommended) or NetworkX (lightweight)
- Vector store: Qdrant, Weaviate, or pgvector

### Configuration

Add to `cognitive-os.yaml` services section:
```yaml
services:
  cognee:
    mode: on_demand
    idle_timeout_minutes: 15
    config:
      graph_backend: "${COGNEE_GRAPH_BACKEND:-networkx}"  # networkx | neo4j
      vector_store: "${COGNEE_VECTOR_STORE:-lancedb}"
      llm_provider: "${COGNEE_LLM_PROVIDER:-anthropic}"
      mcp_enabled: true
      mcp_port: 8100
```

### Environment Variables
```
COGNEE_GRAPH_BACKEND=networkx     # or neo4j
COGNEE_VECTOR_STORE=lancedb       # or qdrant, weaviate, pgvector
COGNEE_LLM_PROVIDER=anthropic
COGNEE_LLM_MODEL=claude-sonnet-4-5-20250514
```

## What to Do

### Step 1: Add Knowledge

Process documents, code, or text through the ECL pipeline:
```python
import cognee

# Add source
await cognee.add("path/to/document.md")

# Process (Extract → Cognify → Load)
await cognee.cognify()
```

### Step 2: Search Knowledge Graph

Query relationships and semantic connections:
```python
results = await cognee.search("How does the auth middleware handle JWT tokens?")
# Returns: nodes, relationships, and semantic matches
```

### Step 3: MCP Server Integration

Cognee provides an MCP server that Claude Code agents can use directly:
```bash
# Start Cognee MCP server
cognee mcp serve --port 8100
```

Register in Claude Code settings for direct agent access.

## Architecture: Engram + Cognee

```
Agent Query
    ├─ Engram (flat observations)
    │   └─ "What did we decide about X?" → topic-key lookup
    │
    └─ Cognee (knowledge graph)
        └─ "How does X relate to Y?" → graph traversal + semantic search
```

| Use Case | Engram | Cognee |
|----------|--------|--------|
| Decision recall | ✅ Best | ⚠️ Possible |
| Relationship discovery | ❌ | ✅ Best |
| Codebase understanding | ⚠️ Limited | ✅ Best |
| Convention tracking | ✅ Best | ⚠️ Possible |
| Cross-project patterns | ⚠️ Namespace isolation | ✅ Graph traversal |

## Rules

- Cognee complements Engram — it does NOT replace it
- Use Engram for: decisions, conventions, feedback, project state
- Use Cognee for: relationships, codebase understanding, knowledge synthesis
- Default to lightweight backend (NetworkX + LanceDB) for evaluation
- Upgrade to Neo4j + Qdrant only when graph size exceeds local capacity
- MCP server runs on-demand, not always-on (save resources)
