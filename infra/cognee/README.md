# Cognee — Knowledge Graph Memory

## Quick Start

```bash
docker compose -f docker-compose.cognitive-os.yml --profile memory up -d
```

## Architecture

- **cognee**: Python FastAPI server with knowledge graph + vector search
- Default backends: NetworkX (graph) + LanceDB (vectors)
- Production: Neo4j + Qdrant

## Python SDK

```bash
pip install cognee
```

```python
import cognee
await cognee.add("document.md")
await cognee.cognify()
results = await cognee.search("query")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| COGNEE_PORT | 8100 | Server port |
| COGNEE_GRAPH_BACKEND | networkx | Graph DB (networkx/neo4j) |
| COGNEE_VECTOR_STORE | lancedb | Vector store (lancedb/qdrant/weaviate) |
| COGNEE_LLM_PROVIDER | anthropic | LLM for knowledge extraction |
| ANTHROPIC_API_KEY | — | Required for knowledge extraction |
