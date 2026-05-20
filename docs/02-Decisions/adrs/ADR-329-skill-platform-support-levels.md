---
adr: 329
title: Skill Platform Support Levels
status: accepted
implementation_status: implemented
date: '2026-05-20'
supersedes: []
superseded_by: null
implementation_files:
- scripts/skill_platform_support_audit.py
- tests/audit/test_skill_platform_support_audit.py
- skills/session-wrapup/SKILL.md
- skills/os-session-wrapup/SKILL.md
- skills/session-backlog/SKILL.md
- skills/branch-worktree-closure/SKILL.md
- skills/worktree-triage/SKILL.md
- skills/primitive-harvester/SKILL.md
- skills/preserved-wip-cleanup/SKILL.md
tier: maintainer
classification_basis: Skill `platforms` must not imply equal runtime capability across IDEs or CLIs; each declared platform needs an explicit support level and evidence when the platform is generic or cross-harness.
tags:
- skills
- platform-support
- harness
- portability
- classification
---

# ADR-329 — Skill Platform Support Levels

## Status

Accepted and implemented for the existing `generic-cli` skill surface.

## Context

Primitive `SCOPE` answers where a primitive belongs: `os-only`, `project`, or
`both`. Skill `platforms` answers a different question: where the skill can be
loaded or used. Until this ADR, `platforms` was too declarative. A skill listing
`claude-code`, `codex`, and `generic-cli` could mean any of these without saying
which:

| Level | Meaning |
|---|---|
| `loadable` | The harness can read/load the skill metadata and body. |
| `documented-only` | The skill is safe as a manual instruction/fallback but not claimed as fully executable. |
| `advisory` | The skill provides operator guidance and may reference optional commands. |
| `executable` | The skill's declared workflow has concrete shell/CLI commands or scripts for that platform. |
| `lifecycle-enforced` | The harness can trigger/enforce the workflow through native or wrapped lifecycle events. |

Existing harness tooling is stronger for hooks and projection fidelity than for
skill step executability:

- `manifests/primitive-contracts.yaml` declares primitive projection fidelity by
  harness.
- `scripts/primitive_harness_coverage.py` measures observed harness coverage.
- `scripts/primitive_projection_fidelity.py` compares contracts to observed
  coverage.
- `scripts/cos-doctor-harness.sh` diagnoses the active harness.

For skills, the missing contract was: “This skill declares `generic-cli` because
it is documented/manual”, versus “This skill declares `codex` because Codex can
execute or trigger it with evidence”.

## Decision

Skill frontmatter may continue to expose the legacy list form:

```yaml
platforms:
- claude-code
- codex
- generic-cli
```

But any skill that declares `generic-cli` must also declare structured support
metadata:

```yaml
platform_support:
  generic-cli:
    support_level: documented-only
    evidence:
    - skills/example/SKILL.md
```

Allowed `support_level` values are:

- `loadable`
- `documented-only`
- `advisory`
- `executable`
- `lifecycle-enforced`

Rules:

1. `platforms` remains the compatibility/loading list consumed by existing skill
   loaders.
2. `platform_support.<platform>.support_level` carries the precise claim.
3. `generic-cli` must never imply automatic execution by default. Its safe
   baseline is `documented-only` unless there is executable CLI proof.
4. `support_level` values above `documented-only` need at least one evidence
   entry; lifecycle claims should point to hooks, settings, harness contracts, or
   tests.
5. The first ratchet is strict for `generic-cli` because it is the most likely
   overclaim. Other platform entries can be migrated incrementally.

## Implementation

Add `scripts/skill_platform_support_audit.py` as a deterministic audit. In
strict mode it fails when a skill declares `generic-cli` but lacks:

- `platform_support.generic-cli.support_level`; or
- at least one evidence entry; or
- a valid support level.

The existing `generic-cli` skills now declare support metadata. For example,
`/session-wrapup` is:

```yaml
platform_support:
  generic-cli:
    support_level: documented-only
    evidence:
    - skills/session-wrapup/SKILL.md
```

Codex and Claude Code support can be stronger when there is hook or settings
proof, but this ADR does not require every legacy platform to be fully migrated
in the first slice.

## Alternatives rejected

- **Keep `platforms` as a flat list only** — rejected because it overstates support: `generic-cli` can mean manual documentation while `claude-code` or `codex` may be lifecycle-triggered.
- **Require every platform to be executable immediately** — rejected because existing skills have valid documented/manual value and a hard migration would create noisy churn. The first strict ratchet targets `generic-cli`, the most ambiguous claim.
- **Move all platform semantics into `primitive-contracts.yaml` only** — rejected because skills need self-contained metadata for loaders and audits that read `SKILL.md` directly.

## Consequences

### Positive

- A skill can be portable without overstating runtime enforcement.
- `generic-cli` becomes honest: manual/documented unless proven executable.
- Future tools can join `platform_support` with primitive harness coverage and
  projection fidelity.
- New skills get a mechanical guardrail against vague platform claims.

### Negative / trade-offs

- Frontmatter grows slightly for cross-harness skills.
- Existing non-`generic-cli` platform entries remain partly declarative until a
  later ratchet.
- `documented-only` is intentionally weaker than executable proof; product
  claims must use the support level, not only the platform list.

## Verification

```bash
python3 scripts/skill_platform_support_audit.py --project-dir . --strict
python3 -m pytest tests/audit/test_skill_platform_support_audit.py tests/hooks/test_os_session_wrapup_addendum_trigger.py -q
```
