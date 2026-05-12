---

adr: 157
title: Kimi Code CLI Structural Harness Projection
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos_init.py
  - manifests/harness-projection.yaml
  - manifests/harness-implementation-phases.yaml
  - tests/behavior/test_consumer_project_projection.py
  - tests/contracts/test_acc_pipeline_contract.py
  - docs/manual-tests/kimi-code-cli-structural-projection.md
tier: maintainer
tags: [harness, kimi, cli, projection, acc, portability]
---

# ADR-157: Kimi Code CLI Structural Harness Projection

## Status

**Implemented for structural CLI projection scope** — 2026-05-04. Kimi Code project-local CLI context/config projection is generated and tested; authenticated CLI execution remains outside this ADR.

## Context

The previous roadmap treated Kimi mostly as a VS Code/provider candidate. That was incomplete: Kimi Code has an official CLI. The official CLI documentation signs:

- `kimi` as the main command;
- `--work-dir` for selecting the workspace root;
- `--config-file` and `--mcp-config-file` for explicit configuration files;
- `kimi mcp` / MCP configuration;
- project-level `AGENTS.md` context in Kimi Help Center guidance.

This is enough for account-free structural projection, while runtime execution still depends on Kimi CLI installation and authentication.

## Decision

Promote `kimi-code` to an implemented structural CLI harness.

`cos_init.py --default|--full --harness kimi-code` now writes:

- `AGENTS.md` with a bounded Cognitive OS block for Kimi Code CLI;
- `.kimi/mcp.json` with an empty `mcpServers` placeholder;
- `.kimi/README.md` documenting the intended CLI invocation boundary.

The installer preserves existing `AGENTS.md` content by appending or replacing only the marked Cognitive OS Kimi block.

## Consequences

### Positive

- Kimi Code is no longer treated only as a provider/IDE extension candidate.
- COS can project Kimi CLI context without requiring credentials.
- The generated files give operators a clear `kimi --work-dir . --mcp-config-file .kimi/mcp.json` path.

### Negative

- Automated tests do not prove account-backed Kimi CLI runtime behavior.
- `.kimi/mcp.json` is intentionally empty until a profile or operator configures concrete MCP servers.
- No native COS lifecycle hook parity is claimed.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep Kimi planned until account-backed CLI smoke exists | Too conservative; the CLI and project context surfaces are documented and structurally testable. |
| Configure global `~/.kimi/config.toml` | Violates project-local projection and risks touching user credentials/config. |
| Generate real MCP servers by default | Unsafe and environment-dependent. |

## Verification

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py -q
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `scripts/cos_init.py` accepts `--harness kimi-code` and writes `AGENTS.md`, `.kimi/mcp.json`, and `.kimi/README.md`.
- `manifests/harness-projection.yaml` marks `kimi-code` as implemented structural CLI projection.
- `manifests/harness-implementation-phases.yaml` records Kimi alongside Qwen in Phase 3.
- Automated tests assert generated Kimi files and ACC projection counts.
