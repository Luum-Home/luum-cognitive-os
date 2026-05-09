# VS Code Copilot portable `.ai` adapter

Schema: `portable-ai-adapter.v1`

This adapter is generated from Cognitive OS canonical primitive manifests.
It must not invent primitive behavior or overclaim runtime enforcement.

## Current projection

- harness id: `vscode-copilot`
- status: `implemented`
- proof level: `structural`
- projection mode: `copilot-instructions-and-workspace-mcp`

## Settings paths

- `.github/copilot-instructions.md`
- `.vscode/mcp.json`

## Rule

Read `.ai/profiles/vscode-copilot.json` for declared fidelity before projecting primitives into this host.
Structural advisory surfaces are not runtime enforcement.
