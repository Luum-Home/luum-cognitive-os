---

adr: 158
title: AI Agent Harness Landscape and Proof Backlog
status: accepted
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - manifests/ai-agent-harness-landscape.yaml
  - docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md
  - docs/04-Concepts/root/ide-compatibility.md
  - tests/contracts/test_ai_agent_harness_landscape.py
  - docs/09-Quality/manual-tests/ai-agent-harness-landscape-review.md
tier: maintainer
tags: [harness, portability, proof-level, acc, landscape]
---

# ADR-158: AI Agent Harness Landscape and Proof Backlog

## Status

**Accepted** — 2026-05-04

## Context

Cognitive OS previously kept broad compatibility claims in prose documents, especially `docs/04-Concepts/root/ide-compatibility.md`. Those lists were useful for ambition, but some labels such as `FULL` or `HIGH` implied runtime support based only on documentation reading.

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

## Operational Guide

### What changes for the operator

Before this ADR, compatibility claims lived in `docs/04-Concepts/root/ide-compatibility.md` as
prose labels (`FULL`, `HIGH`) with no machine-readable backing. Keeping the list
accurate required manual review of every vendor release and individual judgement
on what "FULL" meant.

After this ADR:

- `manifests/ai-agent-harness-landscape.yaml` is the single authoritative
  backlog. Every candidate surface carries a `proof_level` drawn from the
  four-value vocabulary: `native-lifecycle`, `runtime-smoke`, `structural`,
  `none`.
- `docs/04-Concepts/root/ide-compatibility.md` now points at proof-level metadata instead of
  free-form percentage claims. Do not update the prose table; update the manifest
  and regenerate.
- A candidate moves from landscape backlog to `manifests/harness-projection.yaml`
  only when a temp-project structural test or stronger proof exists. The manifest
  is the gate; the doc is the output.

### What this answers (and what it doesn't)

**Answers:**
- "Is harness X actually supported?" — Check `proof_level` in
  `manifests/ai-agent-harness-landscape.yaml`. `native-lifecycle` means the
  full COS hook surface is exercised. `none` means the candidate is backlog only.
- "What is the next harness to implement?" — Read the `next_action` field on each
  candidate entry in the landscape manifest; the report at
  `docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md` lists priority order.
- "Can I claim GitHub Copilot hosted agent support?" — Only after the proof_level
  is at least `structural`. Until then: "tracked in backlog, not yet implemented."

**Does not answer:**
- Whether a candidate whose `proof_level` is `structural` will behave correctly at
  runtime — that requires a `runtime-smoke` or `native-lifecycle` proof.
- Which harnesses competitors support. The manifest tracks what this project has
  probed, not the broader ecosystem state.

### Daily operational pattern

When a new harness or hosted agent surface is discovered:

1. Add a candidate entry to `manifests/ai-agent-harness-landscape.yaml` with
   `proof_level: none`, `availability_boundary`, `official_source`, and
   `next_action`.
2. Run contract tests to confirm the entry is structurally valid:
   ```bash
   python3 -m pytest tests/contracts/test_ai_agent_harness_landscape.py -q
   ```
3. When a structural test exists, update `proof_level` to `structural` and open a
   PR to `manifests/harness-projection.yaml` to register the projection surface.

Do not update `docs/04-Concepts/root/ide-compatibility.md` manually. That file is generated from
the manifest. Any hand-edit will be overwritten.

### Reading guide for cold readers

If you are reading this ADR without prior context:

1. Open `manifests/ai-agent-harness-landscape.yaml` — it lists every candidate
   surface and its current proof level.
2. Read `docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md` for the rationale
   behind the four proof levels and the priority ordering.
3. The key constraint: proof levels flow upward (`none` → `structural` →
   `runtime-smoke` → `native-lifecycle`) and never downward without a new entry.
   A regression in proof level means the old test broke; the manifest should
   reflect reality, not aspiration.

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
- `docs/06-Daily/reports/ai-agent-harness-landscape-2026-05-04.md` summarizes repo docs reviewed, official-doc-backed candidates, gaps, and priority order.
- `docs/04-Concepts/root/ide-compatibility.md` now points to proof-level metadata rather than percentage-like compatibility claims.
- Contract tests enforce required candidate fields and ensure implemented projection remains a subset of the landscape.
