---
adr: 158
title: AI Agent Harness Landscape and Proof Backlog
status: accepted
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - manifests/ai-agent-harness-landscape.yaml
  - docs/reports/ai-agent-harness-landscape-2026-05-04.md
  - docs/ide-compatibility.md
  - tests/contracts/test_ai_agent_harness_landscape.py
  - docs/manual-tests/ai-agent-harness-landscape-review.md
tier: maintainer
tags: [harness, portability, proof-level, acc, landscape]
---

# ADR-158: AI Agent Harness Landscape and Proof Backlog

## Status

**Accepted** — 2026-05-04

## Context

Cognitive OS previously kept broad compatibility claims in prose documents, especially `docs/ide-compatibility.md`. Those lists were useful for ambition, but some labels such as `FULL` or `HIGH` implied runtime support based only on documentation reading.

The agentic coding ecosystem has also changed quickly. Current official docs show additional or under-modeled surfaces such as Gemini CLI, Kiro, Cline, Goose, Amp, JetBrains Junie, Factory Droid, Qoder, Tabnine Agent, hosted GitHub Copilot coding agent, and hosted MCP-enabled builders.

The user explicitly clarified that we cannot test every paid/account-backed IDE and CLI. Therefore documentation review can justify backlog tracking, but it cannot justify runtime support claims.

## Decision

Create `manifests/ai-agent-harness-landscape.yaml` as the machine-readable candidate backlog for AI coding IDEs, CLIs, hosted agents, and provider/tool surfaces.

Update compatibility documentation to use proof levels only:

- `native-lifecycle`
- `runtime-smoke`
- `structural`
- `none`

The landscape manifest is not an implementation manifest. Implemented projection remains in `manifests/harness-projection.yaml`. A candidate can move from the landscape into implemented projection only when a temp-project structural test or stronger proof exists.

Hosted agents and provider integrations must stay distinct from local consumer-project projection.

## Consequences

### Positive

- The repo can track a broader ecosystem without overclaiming support.
- Future harness implementation slices have a single backlog source.
- Contract tests can enforce proof-level metadata and prevent stale compatibility labels from returning.

### Negative

- The landscape manifest will need periodic updates because vendor docs change frequently.
- Some candidates may remain in `none` for a long time even when they are strategically important.
- Hosted tools require a different adapter model than local project-file projection.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep the old `FULL`/`HIGH` compatibility table | It overstates runtime confidence and conflicts with the proof-level boundary. |
| Add every discovered tool directly to `harness-projection.yaml` | That manifest is for projection status, not broad market tracking. |
| Ignore hosted tools | They matter for ecosystem coverage, but must be separated from local projection. |
| Require account-backed smoke before tracking a candidate | Too strict for roadmap discovery; official-doc-backed candidates are useful as backlog entries. |

## Verification

```bash
python3 -m pytest tests/contracts/test_ai_agent_harness_landscape.py tests/contracts/test_harness_implementation_phases.py -q
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `manifests/ai-agent-harness-landscape.yaml` records candidate surfaces with proof levels, availability boundary, projection surface, official sources, and next action.
- `docs/reports/ai-agent-harness-landscape-2026-05-04.md` summarizes repo docs reviewed, official-doc-backed candidates, gaps, and priority order.
- `docs/ide-compatibility.md` now points to proof-level metadata rather than percentage-like compatibility claims.
- Contract tests enforce required candidate fields and ensure implemented projection remains a subset of the landscape.
