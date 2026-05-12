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

## Operational Guide

### What changes for the operator

Before this ADR: Kimi Code was treated primarily as a VS Code extension or provider candidate, with no first-class CLI projection path. The `kimi-code` harness was listed as planned.

After this ADR:

- `cos_init.py --harness kimi-code` is a valid installation command:
  ```bash
  python3 scripts/cos_init.py --default --harness kimi-code --project-dir /path/to/consumer
  ```
  This writes `AGENTS.md` (with a bounded Cognitive OS Kimi block, preserving existing content), `.kimi/mcp.json` (empty `mcpServers` placeholder), and `.kimi/README.md` (CLI invocation boundary documentation).
- ACC records `kimi-code/default` and `kimi-code/full` projection counts.
- `manifests/harness-implementation-phases.yaml` records Kimi alongside Qwen in Phase 3.

The intended CLI invocation documented in `.kimi/README.md`:
```bash
kimi --work-dir . --mcp-config-file .kimi/mcp.json
```

### What this answers (and what it doesn't)

**Answers:**
- "How does Kimi Code CLI discover COS context?" — Via `AGENTS.md`, which the Kimi Help Center documents as the project-level context file for the CLI.
- "Where should MCP server configuration go for Kimi?" — In `.kimi/mcp.json`. The generated file is an empty placeholder; add concrete `mcpServers` entries for the consumer's tools.
- "Is existing `AGENTS.md` content preserved?" — Yes. The installer appends or replaces only the marked Cognitive OS Kimi block, leaving other content intact.

**Does not answer:**
- "Is Kimi Code CLI installed and authenticated on the consumer machine?" — Structural projection is account-free; actual CLI use requires Kimi installation and authentication.
- "Does Kimi Code receive the same lifecycle hook enforcement as Claude Code?" — No. No native COS lifecycle hook parity is claimed for this structural projection.
- "What Kimi CLI version is required?" — The surfaces used (`--work-dir`, `--mcp-config-file`, `AGENTS.md`) are from official Kimi documentation; verify against the installed CLI version if behavior differs.

### Reading guide for cold readers

1. Run `python3 scripts/cos_init.py --default --harness kimi-code --project-dir /tmp/test-kimi` and inspect `AGENTS.md`, `.kimi/mcp.json`, and `.kimi/README.md`.
2. Read `manifests/harness-projection.yaml` entry for `kimi-code` — note the `structural-cli-proof` limitation annotation alongside Qwen.
3. Read `docs/manual-tests/kimi-code-cli-structural-projection.md` for expected file assertions and their rationale.
4. Compare with ADR-156 (Qwen Code): both are Phase 3 structural harnesses; Kimi targets the CLI surface while Qwen targets project settings + context files.

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
