---
tool_id: fastmcp
status: integrate
source_manifest: manifests/external-tools-adoption.yaml
---

# External Tool Deep Dive — FastMCP

## Scope

FastMCP is the selected MCP server implementation boundary for COS MCP surface
work. COS should not reimplement MCP transport semantics when a mature external
implementation can sit behind the package boundary.

## Source links

- Radar: `docs/06-Daily/reports/external-tools-radar-full-reassessment-2026-05-08.md`
- Package surface: `packages/mcp-server/`

## License and provenance

Declared license: Apache-2.0 in `manifests/external-tools-adoption.yaml`.
Targeted source verification is still required before vendoring code or making a
public claim beyond the local package integration.

## Footprint

| Surface | Impact |
|---|---|
| OS repo | Optional MCP package dependency. |
| Consumer projects | Optional; only projects enabling MCP server surface need it. |
| Service mode | Optional. |
| Docker runtime | Optional; no default daemon requirement. |

## Adapter boundary

COS owns policy, tool definitions, receipts, and claim boundaries. FastMCP owns
MCP server mechanics behind `packages/mcp-server/cos_mcp.py`.

## Evidence

- Consumer: `packages/mcp-server/cos_mcp.py`
- Test: `tests/unit/test_cos_mcp_server.py`

## Test plan

Run the MCP server unit tests and any future cross-harness registration smoke
before promoting public claims.

## Rollback path

Keep COS tool definitions separate from the FastMCP binding so a different MCP
server runtime can replace the adapter without rewriting governance semantics.

## Public-claim boundary

Public claims may say COS exposes an MCP server package when tests pass. They
must not claim universal MCP compatibility until external client registration
smoke exists.
