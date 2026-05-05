---
adr: 156
title: Qwen Code Structural Harness Projection
status: implemented
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
