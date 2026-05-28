<!-- SCOPE: both -->
<!-- TIER: 2 -->
---
name: research-first-protocol
audience: os-dev, consumer-project
last-updated: 2026-04-24
---

# Research-First Protocol

## Purpose

High-risk changes (low-clarity acceptance criteria, high blast radius, low
reversibility, or many pending decisions) must go through a structured
research phase before any implementation agent is launched. This prevents
wasted implementation work, incorrect assumptions being baked into code, and
irreversible changes made without operator sign-off.

This rule is always active for `os-dev` scope work and available to consumer projects when `RULES-COMPACT.md` references `research-first-protocol` for high-risk agent work.

---

## When to Apply: 4-Dimensional Risk Classification

Score each dimension 0-2. Total score determines the workflow.

| Dimension | 0 (low) | 1 (medium) | 2 (high) |
|---|---|---|---|
| **Acceptance-criteria clarity** | All criteria are concrete and verifiable | Some criteria need clarification | No clear criteria; "done" is undefined |
| **Blast radius** | <3 files, 1 service | 3-20 files, 1-2 services | >20 files or multiple services |
| **Reversibility** | Easy rollback (config, feature flag) | Partial rollback possible | Hard to reverse (schema migration, breaking API) |
| **Decision count** | 0-1 decisions to make | 2-3 decisions | 4+ decisions, or decisions are mutually exclusive |

**Total score → Workflow:**

| Score | Workflow |
|---|---|
| 0-2 | Standard: launch a background implementation agent directly |
| 3-4 | Research-optional: run a quick scout (`/scout`) before implementing |
| 5-6 | Research-required: full 3-phase cycle (see below) |
| 7-8 | Research-required + operator review before any implementation agent |

When in doubt, score UP. A false positive (unnecessary research) wastes one
agent call. A false negative (skipped research on a risky change) can waste
hours of implementation work and produce irreversible damage.

---

## The 3-Phase Cycle

### Phase 0 — Research

Launch a read-only research agent. In the OS repo, use `templates/agent-research-only.md` as
the base prompt when available; in consumer projects, use the local research-only prompt template if installed, or instruct the agent explicitly to stay read-only. The agent:

1. Explores the codebase and relevant context
2. Produces a structured report at `docs/06-Daily/reports/<topic>-<YYYY-MM-DD>.md`
3. Saves key findings to Engram under `research/<topic>`
4. Does NOT implement, commit code, or modify anything outside the reports dir

The orchestrator commits only the report file once it lands.

### Phase 1 — Operator Triage

The human operator:

1. Reads the research report
2. Answers the numbered Open Questions (edit the report in-place, or reply to
   the orchestrator inline)
3. Selects the recommended path (or overrides it with reasoning)
4. Approves the proceed decision

The orchestrator persists the operator's decisions in one of two ways:
- **Engram observation**: `mem_save` with `topic_key: "research/<topic>"` (update
  the existing observation with `mem_update`) — preferred for tactical decisions
- **New ADR**: create `docs/02-Decisions/adrs/ADR-NNN-<topic>.md` — required when the decision
  sets a precedent affecting future work or other teams

### Phase 2 — Implementation

Launch the implementation agent with:
- A link to the research report (file path)
- The operator's answered Open Questions (inline in the prompt)
- The selected path from "Recommended Path"
- Standard closed-loop prompt structure (success criteria + verification)

The implementation agent reads the report but does NOT re-research. All
ambiguity was resolved in Phase 1.

---

## Report Location Convention

All Phase 0 research reports live under:

```
docs/06-Daily/reports/<topic>-<YYYY-MM-DD>.md
```

- `<topic>`: slug form, lowercase hyphens (e.g., `cos-init-migration`,
  `python-major-bumps`, `adr-067-phase-2`)
- `<YYYY-MM-DD>`: date the research agent ran (not the implementation date)
- One report per topic per run. If a topic is re-researched, create a new file
  with the new date — do not overwrite the old one (history matters).
- Reports MUST go in `docs/06-Daily/reports/` (git-tracked). Do NOT write to
  `.cognitive-os/reports/research/` — that path is gitignored and causes
  duplicate-counting in `/decision-triage`.

---

## Operator Decision Persistence

After Phase 1, decisions MUST be persisted before Phase 2 launches. Two paths:

### Tactical decision → Engram
Use when the decision only affects the current change and does not set a
project-wide precedent.

```python
mem_update(
  id: "<existing-research-observation-id>",
  content: "<original content> ... OPERATOR DECISIONS (2026-MM-DD): Q1: <answer>. Q2: <answer>. Selected path: <path>."
)
```

### Architectural precedent → ADR
Use when the decision will affect future agents, sets a new pattern, or is
referenced by multiple teams. Follow the ADR template at `docs/02-Decisions/adrs/`.

---

## Escape Hatches

The research-first protocol is NOT required when:

- The task is mechanical and fully specified (e.g., rename a symbol across N
  files — scope is known, no decisions, grep confirms count)
- Score 0-2 on the 4-dimensional classification
- A prior research report for this topic already exists AND the operator
  answered its open questions (check Engram `research/<topic>` first)
- The change is behind a feature flag with an instant rollback path
- The orchestrator is in `reconstruction` phase AND the task scope is a single
  service AND blast radius is confirmed < 10 files

Even with an escape hatch, a `/scout` recon pass is recommended for medium+
complexity tasks.

---

## Templates and References

- Research agent prompt: `templates/agent-research-only.md` when installed, otherwise an explicit read-only agent prompt
- Closed-loop prompt structure: `rules/closed-loop-prompts.md`
- Scout skill: `skills/scout/SKILL.md`
- ADR template: `docs/02-Decisions/adrs/` directory (follow existing ADR file naming convention)
- Engram topic convention: `research/<topic>`

---

## Integration with Existing Rules

| Rule | Integration |
|---|---|
| `closed-loop-prompts` | Phase 2 implementation prompts MUST follow closed-loop structure |
| `acceptance-criteria` | Research report's Decision Points define the acceptance criteria for Phase 2 |
| `phase-aware-agents` | Phase modifies enforcement: reconstruction=research optional at score 5; production=research mandatory at score 3+ |
| `blast-radius` | Blast radius hook feeds directly into the "blast radius" dimension |
| `adaptive-bypass` | Score 0-2 tasks bypass research entirely — consistent with trivial/small bypass |

---

## Contextual Trigger

This rule is loaded when: high-risk task classification, blast radius > 10 files,
ADR implementation, migration tasks, "research first", "Phase 0", or any task
that scores 5+ on the 4-dimensional classification above.
