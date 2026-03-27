#!/usr/bin/env bash
set -e

echo "=== Cognee Knowledge Graph Memory ==="
echo "Graph backend: ${COGNEE_GRAPH_BACKEND:-networkx}"
echo "Vector store: ${COGNEE_VECTOR_STORE:-lancedb}"

# Install cognee
pip install --quiet cognee[server] 2>&1 | tail -1

# Start the Cognee server
echo "Starting Cognee server on port 8000..."
exec python -m cognee.api.server --host 0.0.0.0 --port 8000
