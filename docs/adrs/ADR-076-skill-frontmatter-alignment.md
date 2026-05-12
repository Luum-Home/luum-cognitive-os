---
adr: 76
title: SKILL.md Frontmatter Alignment with Hermes Spec
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
---

# ADR-076: SKILL.md Frontmatter Alignment with Hermes Spec

**Status**: Accepted
**Date**: 2026-04-30
**Engram topic**: `cos/tier2-hermes-alignment`

---

## Status

Accepted.

## Context

COS skills live under `skills/*/SKILL.md` and are consumed by two separate
runtimes:

1. **Claude Code harness** — reads SKILL.md files directly during the session
   via the skill registry and `/` slash commands.
2. **Hermes agent runtime** — parses SKILL.md files using
   `.claude/plugins/hermes-agent/tools/skills_tool.py`, which implements the
   [agentskills.io](https://agentskills.io) standard.

The Hermes source (`tools/skills_tool.py` lines 28-46, MIT-licensed) defines
the canonical SKILL.md YAML frontmatter spec:

| Field | Required | Description |
|---|---|---|
| `name` | **Required** | Skill identifier, max 64 chars |
| `description` | **Required** | Brief description, max 1024 chars |
| `version` | Optional | Semver string (e.g., `1.0.0`) |
| `platforms` | Optional | List of OS/harness identifiers to restrict loading |
| `prerequisites` | Optional | Runtime requirements (env vars, commands) |
| `tags` | Optional | Categorization tags |
| `license` | Optional | SPDX license identifier |

At the time of this ADR, **all 142 COS skills** were missing `version`,
`platforms`, and `prerequisites` from their frontmatter. The `name` and
`description` fields were present in all files (required fields were already
satisfied).

Missing `version` prevents semantic versioning of skills across updates.
Missing `platforms` causes Hermes to load skills unconditionally on all
platforms, including environments where `claude-code`-specific skills are
irrelevant. Missing `prerequisites` leaves the field undefined when tooling
iterates skill metadata for dependency resolution.

Cross-runtime portability is a stated goal of Tier 2 Hermes alignment
(Engram topic `hermes-learning-loop-source-map`). Consistent frontmatter is
the minimum prerequisite for that portability.

## Decision

Add the three missing optional fields to every `skills/*/SKILL.md` with safe
defaults:

| Field | Default | Rationale |
|---|---|---|
| `version` | `"1.0.0"` | Semver starting point; skills pre-dating versioning receive 1.0.0 |
| `platforms` | `["claude-code"]` | COS is a Claude Code harness; restricts Hermes from loading on irrelevant runtimes |
| `prerequisites` | `[]` | Most skills have no runtime prerequisites; empty is correct default |

Rules for the defaults:
- **Idempotent**: if a field already exists with any value, it is not overwritten.
- **Additive only**: no existing frontmatter fields are modified or removed.
- **Fields appended inside the frontmatter block** (between `---` fences), after
  existing keys.

The alignment was executed by `scripts/align_skill_frontmatter.py`, a one-shot
Python script. The script uses regex-based frontmatter parsing (not YAML
round-trip) to avoid reordering or reformatting existing keys.

## Consequences

**Positive:**
- All 142 skills are now parseable by both COS tooling and the Hermes runtime
  with full metadata coverage.
- `platforms: ["claude-code"]` prevents skills from loading in unintended
  Hermes deployments (e.g., a Hermes instance running on a macOS desktop
  would not auto-load COS infrastructure skills).
- `version: "1.0.0"` establishes a versioning baseline; future skill bumps
  can increment via `/bump-version`.
- Catalog generator (`scripts/generate_compact_catalog.py`) continues to work
  without modification — new fields are ignored by the generator.

**Negative / trade-offs:**
- `platforms: ["claude-code"]` is a COS-specific value not in the Hermes
  platform registry (which lists `macos`, `linux`, `windows`). Hermes
  `skill_matches_platform()` falls back to "allow all" when the platform token
  is unrecognized, so this is safe but not restrictive in Hermes. A follow-up
  ADR should register `claude-code` as a valid Hermes platform token if
  deeper cross-runtime filtering is needed.
- `prerequisites: []` is intentionally minimal. Skills with actual runtime
  requirements (env vars, external commands) should be updated individually.

## Alternatives rejected

- **Leave existing skills unchanged**: Rejected because Hermes-compatible
  loaders need predictable metadata to reason about versioning, platform fit,
  and prerequisites.
- **YAML round-trip rewrite of every skill**: Rejected because it would reorder
  frontmatter and create noisy diffs across 142 files.
- **Use Hermes-only platform tokens**: Rejected because COS needs a harness
  identity that can distinguish Claude Code skills from generic OS/platform
  skills.

## Migration

The bulk pass was executed in the same commit as this ADR:
- **Script**: `scripts/align_skill_frontmatter.py`
- **Scope**: 142 SKILL.md files updated
- **Verification**: `for f in skills/*/SKILL.md; do for k in version platforms prerequisites; do grep -q "^$k:" "$f" || echo "MISSING $k in $f"; done; done` returns empty.

Future skills (created via `/add-skill` or `skills/skill-creator`) MUST include
all three fields from creation. The `add-skill` and `skill-creator` skills
should be updated to emit these fields in their templates (tracked separately).

## Verification

```bash
python3 scripts/align_skill_frontmatter.py --check
python3 -m pytest tests/audit/test_skill_frontmatter.py -q --tb=short
```

## References

- Hermes skills tool source: `.claude/plugins/hermes-agent/tools/skills_tool.py`
- Hermes plugin license: MIT
- agentskills.io frontmatter standard: lines 28-46 of skills_tool.py
- Engram topic: `cos/tier2-hermes-alignment`
- Executed by: `scripts/align_skill_frontmatter.py`
