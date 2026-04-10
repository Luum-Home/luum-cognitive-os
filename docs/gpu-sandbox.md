# GPU Sandbox (Jupyter MCP)

> This functionality is implemented as the `/gpu-sandbox` skill. Run `/gpu-sandbox` to use it.
>
> For the full procedure, see `packages/infra-lifecycle/skills/gpu-sandbox/SKILL.md`.

## Overview

The GPU Sandbox provides a Jupyter compute runtime accessible via MCP for executing Python code in compute-heavy tasks: ML inference, data processing, financial calculations, and analytics. It spins up (or connects to) a Jupyter server, executes code in an isolated kernel, and returns results — all without leaving the agent session.
