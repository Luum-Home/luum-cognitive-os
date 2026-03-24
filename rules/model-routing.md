# Model Routing — Auto-Updated by /model-optimizer

## Routing Table

| Skill | Recommended Model | Confidence | Avg Cost | Notes |
|---|---|---|---|---|
| sdd-init | sonnet | default | — | Reads structure only |
| sdd-explore | sonnet | default | — | Code exploration |
| sdd-propose | opus | default | — | Deep reasoning needed |
| sdd-spec | sonnet | default | — | Structured writing |
| sdd-design | opus | default | — | Architecture decisions |
| sdd-tasks | sonnet | default | — | Mechanical decomposition |
| sdd-apply | sonnet | default | — | Implementation |
| sdd-verify | sonnet | default | — | Verification checks |
| sdd-archive | haiku | default | — | Simple documentation |
| systematic-debugging | opus | default | — | Root cause analysis |
| test-driven-development | sonnet | default | — | Fast red-green cycles |
| verification-before-completion | sonnet | default | — | Evidence checking |

## How This Works

The orchestrator checks this table before delegating to sub-agents.
- **high** confidence: Always use recommended model
- **medium** confidence: Use recommended, continue collecting data
- **default** confidence: Initial guess, needs real data from /model-optimizer

## Model Cost Reference

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Best For |
|---|---|---|---|
| opus | $15 | $75 | Deep reasoning, architecture, debugging |
| sonnet | $3 | $15 | General tasks, implementation, specs |
| haiku | $0.25 | $1.25 | Simple documentation, archiving |

## Usage

Run `/model-optimizer` to analyze collected metrics and update this table.

This table is auto-updated by running `/model-optimizer`.
Last updated: 2026-03-21 (initial defaults)
