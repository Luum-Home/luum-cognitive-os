# GPU Sandbox (Jupyter MCP)

## Overview

The GPU Sandbox provides a Jupyter compute runtime accessible via MCP for executing Python code in compute-heavy tasks: ML inference, data processing, financial calculations, and analytics.

## Architecture

```
Claude Agent
    │ (MCP protocol)
    ▼
Jupyter MCP Server (uvx jupyter-mcp-server)
    │ (Jupyter REST API)
    ▼
Jupyter Kernel (local Docker / Colab / remote)
```

## Configuration

### MCP Config (`.mcp.json`)

```json
{
  "jupyter": {
    "command": "uvx",
    "args": ["jupyter-mcp-server"],
    "env": { "JUPYTER_URL": "http://localhost:8888" }
  }
}
```

### Self-Hosted (Docker)

Optional Jupyter container in `docker-compose.cognitive-os.yml`:

```yaml
jupyter:
  image: jupyter/scipy-notebook
  container_name: cognitive-os-jupyter
  ports:
    - "8888:8888"
  environment:
    JUPYTER_TOKEN: "cognitive-os-dev"
```

Start with: `docker-compose -f docker-compose.cognitive-os.yml up -d jupyter`

### Local (without Docker)

```bash
pip install jupyter jupyterlab
jupyter notebook --port=8888 --NotebookApp.token='cognitive-os-dev' --no-browser
```

## Usage

Invoke via `/gpu-sandbox` or use the Jupyter MCP tools directly when the server is running.

### Use Cases

| Task | Example |
|------|---------|
| Financial risk | Monte Carlo simulations, VaR calculations |
| Data processing | Transaction analysis, CSV/parquet processing |
| ML inference | Fraud detection models, anomaly detection |
| Analytics | Charts, dashboards, reporting |

## Port Reservation

Port **8888** is reserved for Jupyter in the cognitive-os stack. This does not conflict with existing project services.

## Notes

- The Jupyter kernel maintains state between executions (variables persist)
- For GPU access, use `jupyter/tensorflow-notebook` or `jupyter/pytorch-notebook` images
- Default dev token: `cognitive-os-dev`
- The MCP server (`jupyter-mcp-server`) is installed on-demand via `uvx` (no global install needed)
