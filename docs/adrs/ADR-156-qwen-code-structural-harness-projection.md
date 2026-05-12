---

adr: 156
title: Qwen Code Structural Harness Projection
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
  - docs/manual-tests/qwen-code-structural-projection.md
tier: maintainer
tags: [harness, qwen, projection, acc, portability]
---

# ADR-156: Qwen Code Structural Harness Projection

## Status

**Implemented for structural projection scope** — 2026-05-04. Qwen Code project-local settings/context projection is generated and tested; account-backed Qwen runtime behavior remains outside this ADR.

## Context

The multi-IDE rollout plan identified Qwen Code as the next viable structural harness after OpenCode, VS Code Copilot, Cursor, and Shell/CI. Qwen Code official documentation signs two project-local surfaces that are enough for account-free structural projection:

- project settings at `.qwen/settings.json`;
- `mcpServers` in settings for MCP tool declarations;
- hierarchical context files such as `QWEN.md`, configurable through `context.fileName`, with include directories.

This is enough to project COS context/instructions and MCP placeholders into a consumer project without claiming native lifecycle hooks or account-backed Qwen runtime behavior.

## Decision

Promote `qwen-code` to an implemented structural harness.

`cos_init.py --default|--full --harness qwen-code` now writes:

- `.qwen/settings.json` with:
  - `context.fileName` pointing to `QWEN.md`, `AGENTS.md`, and `.cognitive-os/rules/cos/RULES-COMPACT.md`;
  - `context.includeDirectories` pointing to `.cognitive-os/rules/cos` and `.cognitive-os/skills/cos`;
  - empty `mcpServers` as an explicit placeholder;
  - conservative `tools.approvalMode = default`;
- `QWEN.md` with the COS instruction boundary.

## Consequences

### Positive

- Qwen Code receives a project-local COS context/config projection backed by official settings and context-file semantics.
- Automated tests can prove projection without Qwen credentials or a GUI/CLI runtime.
- ACC now records `qwen-code/default` and `qwen-code/full` projection proof.

### Negative

- This does not prove account-backed Qwen Code CLI or IDE runtime behavior.
- MCP servers are intentionally empty until a consumer profile or operator configures concrete tools.
- Qwen does not gain native COS lifecycle hook parity from this structural projection.

## Operational Guide

### What changes for the operator

Before this ADR: `qwen-code` was a planned entry in `manifests/harness-projection.yaml`. No projection driver existed and ACC could not count Qwen-specific files in consumer temp projects.

After this ADR:

- `cos_init.py --harness qwen-code` is a valid installation command:
  ```bash
  python3 scripts/cos_init.py --default --harness qwen-code --project-dir /path/to/consumer
  ```
  This writes `.qwen/settings.json` (with `context.fileName`, `context.includeDirectories`, empty `mcpServers`, and `tools.approvalMode`) and `QWEN.md`.
- ACC records `qwen-code/default` and `qwen-code/full` projection counts.
- `manifests/harness-implementation-phases.yaml` records Qwen as the first implemented Phase 3 harness.

### What this answers (and what it doesn't)

**Answers:**
- "How does Qwen Code find COS rules and skills?" — Via `.qwen/settings.json`'s `context.includeDirectories` pointing to `.cognitive-os/rules/cos` and `.cognitive-os/skills/cos`, and `context.fileName` listing `QWEN.md`, `AGENTS.md`, and `RULES-COMPACT.md`.
- "What MCP servers are configured?" — None by default. `mcpServers` is an empty object placeholder. Concrete MCP server entries must be added by the operator or a future consumer profile.
- "Is Qwen Code's native runtime tested?" — No. Tests prove structural projection (files exist, schema is correct). Account-backed Qwen CLI or IDE runtime behavior is outside this ADR.

**Does not answer:**
- "Does Qwen Code receive the same lifecycle hook enforcement as Claude Code?" — No. Qwen Code does not have native COS lifecycle hook parity from this structural projection.
- "Which Qwen Code version or edition is required?" — Documentation-matched surfaces (`context.fileName`, `context.includeDirectories`, `mcpServers`) are assumed stable; check official Qwen Code docs if settings schema changes.

### Reading guide for cold readers

1. Run `python3 scripts/cos_init.py --default --harness qwen-code --project-dir /tmp/test-qwen` and inspect `.qwen/settings.json` and `QWEN.md`.
2. Read `manifests/harness-projection.yaml` entry for `qwen-code` — note the `structural-proof` limitation annotation.
3. Read `docs/manual-tests/qwen-code-structural-projection.md` for the expected file assertions and their rationale.
4. Consult `manifests/harness-implementation-phases.yaml` to understand where Qwen sits relative to other Phase 3 harnesses (Kimi Code is the sibling).

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Wait for account-backed Qwen runtime proof | Blocks useful project-local structural support on credentials. |
| Put all instructions only in `QWEN.md` | Misses the signed project settings and include-directory contract. |
| Configure real MCP servers by default | Unsafe and account/environment-dependent; placeholders are the correct baseline. |

## Verification

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py -q
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `scripts/cos_init.py` accepts `--harness qwen-code` and writes `.qwen/settings.json` plus `QWEN.md`.
- `manifests/harness-projection.yaml` marks `qwen-code` as implemented structural projection with limitations.
- `manifests/harness-implementation-phases.yaml` records Qwen as the first implemented Phase 3 harness.
- Automated tests assert generated Qwen settings, context files, MCP placeholder, and ACC projection counts.
