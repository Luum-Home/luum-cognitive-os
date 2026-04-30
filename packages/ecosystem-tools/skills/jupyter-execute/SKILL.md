<!-- SCOPE: both -->
---
name: jupyter-execute
description: Execute code in a Jupyter kernel sandbox for data analysis, Python snippets, and benchmarks
invoke: /jupyter-exec
version: 1.0.0
model: sonnet
audience: project
paths: ["*.py", "*.ipynb", "pyproject.toml"]
summary_line: "Execute code in a Jupyter kernel sandbox for data analysis, Python snippets…"

platforms: ["claude-code"]
prerequisites: []
---

# Jupyter Execute — Sandboxed Code Execution

## Purpose

Execute Python code in an isolated Jupyter kernel. The agent writes code, Jupyter executes it in a sandbox separate from the local shell. Use this for data analysis, testing Python snippets, running benchmarks, or any compute task that benefits from isolation.

## Prerequisites

The Jupyter container must be running in the cognitive-os Docker stack:

```bash
docker-compose -f docker-compose.cognitive-os.yml up -d jupyter
```

Or start a local Jupyter server:
```bash
jupyter notebook --port=8888 --NotebookApp.token='test-token' --no-browser
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JUPYTER_TOKEN` | `test-token` | Authentication token for the Jupyter server |
| `JUPYTER_BASE_URL` | `http://localhost:8888` | Jupyter server URL |
| `JUPYTER_SANDBOX` | `false` | When `true`, route Python execution to Jupyter instead of local shell |

## Invocation

```
/jupyter-exec <code>
```

Or programmatically via `lib/jupyter_client.py`:

```python
from jupyter_client import execute_code, is_jupyter_available

if is_jupyter_available():
    result = execute_code("print('hello from sandbox')")
    if result["success"]:
        print(result["stdout"])  # "hello from sandbox"
    else:
        print(result["error"])
```

## Use Cases

### Run Data Analysis
```python
import pandas as pd
data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
print(data.describe())
```

### Test Python Snippets in Isolation
```python
# Test a function without affecting local environment
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

print(fibonacci(10))  # 55
```

### Execute Benchmarks
```python
import time
start = time.perf_counter()
result = sum(range(10_000_000))
elapsed = time.perf_counter() - start
print(f"Sum: {result}, Time: {elapsed:.3f}s")
```

### Validate Generated Code
Before integrating generated code into the codebase, execute it in the sandbox to verify correctness:
```python
# Agent-generated code runs here first
# If it passes, integrate into the project
```

## Sandbox Mode

When `JUPYTER_SANDBOX=true`, the `jupyter-sandbox.sh` hook intercepts Python execution via Bash and routes it to the Jupyter kernel instead. This provides automatic sandboxing without changing agent behavior.

The hook is OFF by default. Enable it for untrusted code execution scenarios.

## API Reference

| Function | Description |
|----------|-------------|
| `is_jupyter_available()` | Check if Jupyter server is reachable |
| `execute_code(code, kernel, timeout, kernel_id)` | Execute code, return stdout/stderr/result/success |
| `list_kernels()` | List all running kernels |
| `create_kernel(name)` | Create a new kernel, return kernel_id |
| `delete_kernel(kernel_id)` | Shut down a kernel |
| `is_sandbox_mode()` | Check if JUPYTER_SANDBOX is enabled |

## Notes

- Kernels persist state between executions (variables, imports remain available)
- Default execution timeout is 60 seconds
- The client degrades gracefully when Jupyter is unavailable (returns error dict)
- Port 8888 is reserved for Jupyter in the cognitive-os Docker stack
