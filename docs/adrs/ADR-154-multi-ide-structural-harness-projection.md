---

adr: 154
title: Multi-IDE Structural Harness Projection
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos_init.py
  - manifests/harness-projection.yaml
  - tests/behavior/test_consumer_project_projection.py
  - tests/contracts/test_acc_pipeline_contract.py
  - docs/architecture/multi-ide-harness-implementation-plan.md
  - docs/manual-tests/multi-ide-structural-projection.md
tier: maintainer
tags: [harness, portability, acc, projection, ide]
---

# ADR-154: Multi-IDE Structural Harness Projection

## Status

**Implemented for structural projection scope** — 2026-05-04. OpenCode, VS Code Copilot, and Cursor project-local projections are generated and tested; this does not claim native lifecycle-hook parity.

## Context

ACC now has a strict fail-new ratchet and a registry that distinguishes implemented harnesses from planned harnesses. The next risk is overclaiming support for every IDE while the repo only proves Claude/Codex lifecycle projection.

Several IDEs expose project-level prompt/config surfaces that can be tested without account access:

- OpenCode supports `opencode.json` with `instructions`, `mcp`, permissions, and plugins.
- VS Code Copilot automatically consumes `.github/copilot-instructions.md` and supports workspace/user MCP configuration.
- Cursor supports project rules under `.cursor/rules` and MCP configuration.

These are not equivalent to Claude/Codex native lifecycle hooks, but they are real project-local projection surfaces.

## Decision

Promote OpenCode, VS Code Copilot, and Cursor from roadmap-only to `implemented` structural projection harnesses.

`cos_init.py` now supports:

- `--harness opencode`, generating `opencode.json` with COS instruction references, MCP placeholder, and conservative permission settings;
- `--harness vscode-copilot`, generating `.github/copilot-instructions.md` and `.vscode/mcp.json`;
- `--harness cursor`, generating `.cursor/rules/cognitive-os.mdc` and `.cursor/mcp.json`.

These harnesses install the same `.cognitive-os/` rules, skills, hooks, templates, and metadata as other consumer projects, but their driver files are instruction/config projections rather than native lifecycle hook settings.

## Consequences

### Positive

- ACC can prove multi-IDE structural projection without requiring accounts or GUI automation.
- The implemented/planned boundary becomes more useful: implemented means temp-project structural proof exists, not universal runtime parity.
- Cursor, OpenCode, and VS Code Copilot users receive project-local instructions that point to COS rules and skills.

### Negative

- Structural projection can still pass even if an IDE extension is not installed or authenticated.
- These drivers do not enforce lifecycle hooks natively. Runtime enforcement still requires Claude/Codex hooks or governed wrapper paths.
- Generated MCP files are placeholders until specific MCP servers are configured by users or future profiles.

## Operational Guide

### What changes for the operator

Before this ADR: OpenCode, VS Code Copilot, and Cursor were planned harnesses — visible in the roadmap but not executable by `cos_init.py` or counted in ACC.

After this ADR, these three IDEs can receive a COS projection without accounts:

| Harness | Entry point | Generated files |
|---|---|---|
| `opencode` | `cos_init.py --harness opencode` | `opencode.json` |
| `vscode-copilot` | `cos_init.py --harness vscode-copilot` | `.github/copilot-instructions.md`, `.vscode/mcp.json` |
| `cursor` | `cos_init.py --harness cursor` | `.cursor/rules/cognitive-os.mdc`, `.cursor/mcp.json` |

ACC records `opencode/default`, `opencode/full`, `vscode-copilot/default`, `vscode-copilot/full`, `cursor/default`, `cursor/full` projection counts. To verify:
```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

### What this answers (and what it doesn't)

**Answers:**
- "Can I use COS with Cursor / OpenCode / VS Code Copilot today?" — Yes for project-local instruction and MCP placeholder projection. The generated files point the IDE to COS rules and skills.
- "Are the lifecycle hooks (like `SessionStart`) available in these IDEs?" — No. Native lifecycle hooks are only enforced in Claude Code and Codex. These harnesses project instructions/config only.
- "Is ACC proof of real runtime behavior in these IDEs?" — No. ACC proves structural projection (temp-project files are generated and syntactically correct), not IDE runtime behavior.

**Does not answer:**
- "Will MCP servers work out of the box?" — Generated MCP files contain empty `mcpServers` placeholders. Concrete server configuration is left to the operator or a future profile.
- "Is OpenCode / Cursor / VS Code Copilot installed and authenticated?" — Structural projection is account-free; runtime use requires installation and credentials.

### Reading guide for cold readers

1. Run `python3 scripts/cos_init.py --harness cursor --project-dir /tmp/test-consumer` (or `opencode`, `vscode-copilot`) to see what a structural projection produces.
2. Read `manifests/harness-projection.yaml` to understand the `implemented` vs `planned` boundary and the structural-proof limitations noted for these three harnesses.
3. Read `tests/behavior/test_consumer_project_projection.py` to see exactly which files are asserted in each harness's temp-project proof.
4. For Claude/Codex lifecycle hooks, see those harness ADRs — these three harnesses intentionally do not claim hook parity.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep all non-Claude/Codex harnesses planned | Too conservative; primary docs support project-local instruction/config surfaces for several IDEs. |
| Mark structural projection as full runtime support | Overclaims; config files are not the same as native hook execution. |
| Require account-backed GUI tests for promotion | Blocks useful structural proof on licenses/accounts and makes local CI brittle. |

## Verification

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py tests/contracts/test_acc_pipeline_contract.py -q
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
```

## Implementation Evidence

- `scripts/cos_init.py` supports `opencode`, `vscode-copilot`, and `cursor` harness values.
- `manifests/harness-projection.yaml` marks those three as `implemented` with structural-proof limitations.
- `tests/behavior/test_consumer_project_projection.py` validates generated files in temp consumer projects.
- ACC records default/full projection counts for Claude, Codex, Cursor, OpenCode, and VS Code Copilot.
