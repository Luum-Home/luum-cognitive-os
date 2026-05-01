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
| COGNEE_LLM_PROVIDER | ollama | LLM for knowledge extraction (`ollama`, `openai`, `gemini`, `anthropic`, `custom`) |
| COGNEE_LLM_MODEL | llama3.1:8b | Local Ollama model for extraction |
| COGNEE_LLM_ENDPOINT | http://host.docker.internal:11434/v1 | Docker-to-host Ollama endpoint |
| COGNEE_EMBEDDING_PROVIDER | fastembed | Local embedding backend; avoids OpenAI fallback |
| COGNEE_EMBEDDING_MODEL | sentence-transformers/all-MiniLM-L6-v2 | Fastembed model |
| COGNEE_LLM_API_KEY | ollama | Placeholder required by the client for Ollama; not a cloud key |


## Provider Policy

The reference Docker profile defaults to a local Ollama + Fastembed setup so
starting `--profile memory` does not require or propagate `ANTHROPIC_API_KEY`.
Use Anthropic only as an explicit Cognee override:

```bash
COGNEE_LLM_PROVIDER=anthropic \
COGNEE_LLM_MODEL=claude-sonnet-4-5-20250514 \
COGNEE_LLM_API_KEY="$ANTHROPIC_API_KEY" \
docker compose -f docker-compose.cognitive-os.yml --profile memory up -d cognee
```

Cognee's current docs require configuring both LLM and embeddings for local
operation; otherwise embeddings may fall back to OpenAI.
