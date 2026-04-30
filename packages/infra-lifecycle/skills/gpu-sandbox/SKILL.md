<!-- SCOPE: both -->
---
name: gpu-sandbox
description: Execute Python code in Jupyter runtime for compute-heavy tasks (ML, data processing, financial calculations)
invoke: /gpu-sandbox
version: 1.0.0
model: sonnet
audience: project
summary_line: "Execute Python code in Jupyter runtime for compute-heavy tasks (ML, data…"

platforms: ["claude-code"]
prerequisites: []
---

# GPU Sandbox — Jupyter Compute Runtime

## Purpose

Connect to a Jupyter runtime (local or remote) to execute Python code for compute-heavy tasks that benefit from a persistent kernel: ML inference, data processing, financial calculations, analytics.

## Prerequisites

The Jupyter MCP server must be configured. Check `.mcp.json` for the `jupyter` entry.

### Starting the Jupyter Runtime

Option 1 — Via docker-compose (self-hosted):
```bash
docker-compose -f docker-compose.cognitive-os.yml up -d jupyter
```

Option 2 — Local Jupyter:
```bash
pip install jupyter jupyterlab
jupyter notebook --port=8888 --NotebookApp.token='cognitive-os-dev' --no-browser
```

Option 3 — Google Colab:
Configure the MCP server with your Colab URL instead of localhost.

## Usage

Once the Jupyter MCP server is running, use the `jupyter` MCP tools:
- `jupyter_execute` — Run a code cell
- `jupyter_list_kernels` — List running kernels
- `jupyter_list_notebooks` — List available notebooks

## Use Cases

### Financial Calculations
```python
# Monte Carlo simulation for risk assessment
import numpy as np
simulations = np.random.normal(mean_return, std_dev, (10000, 252))
var_95 = np.percentile(portfolio_returns, 5)
```

### Data Processing
```python
# Process large transaction datasets
import pandas as pd
df = pd.read_csv('transactions.csv')
summary = df.groupby('type').agg({'amount': ['sum', 'mean', 'count']})
```

### ML Inference
```python
# Run model inference on user behavior data
from sklearn.ensemble import IsolationForest
model = IsolationForest(contamination=0.01)
anomalies = model.fit_predict(transaction_features)
```

### Analytics & Visualization
```python
# Generate analytics charts
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(daily_volumes, label='Transaction Volume')
plt.savefig('analytics.png')
```

## Notes

- The Jupyter kernel persists state between executions (variables, imports)
- For GPU tasks, ensure the Docker image or Colab runtime has GPU access
- Default token for local dev: `cognitive-os-dev`
- Port 8888 is reserved for Jupyter in the cognitive-os stack
