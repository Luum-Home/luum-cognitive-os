# Declarative Patterns (Reference Only)

This directory holds **purely declarative** markdown that used to live under
`rules/` but is not enforceable — no hook fires, no auto-injection happens, and
sub-agents do not receive it at launch.

## Rationale (Sprint 2A, 2026-04-16)

The Capa-3 functional audit
(`../architecture/functional-audit/scorecard-rules.md`) classified every rule
file by its actual enforcement path. Rules whose classification was
**"declarative-only"** — policy described in markdown with no hook, no template
inclusion, and often used only as a conceptual/reference guide — were moved here
to separate **enforceable rules** from **documentation**.

## Separation of concerns

| Location | Purpose | Enforced by |
|----------|---------|-------------|
| `rules/*.md` | Behavioral rules the system enforces | Hooks (primary) + agent-mandatory-rules template (secondary) |
| `docs/04-Concepts/patterns/*.md` | Reference patterns humans read | None — documentation only |

If a pattern in this directory later grows enforcement machinery (hook or
template injection), it should be moved back into `rules/` and indexed in
`rules/RULES-COMPACT.md`.

## Files

| File | What it documents | Previous location |
|------|-------------------|--------------------|
| `plan-first.md` | Plan-first protocol for large changes | `rules/plan-first.md` |
| `dogfooding.md` | Self-hosting requirement: COS modifications should use COS workflows | `rules/dogfooding.md` |
| `os-vs-project.md` | Separation between COS (tool) and user project | `rules/os-vs-project.md` |
| `ecosystem-tools.md` | Reference for optional ecosystem integrations (Context7, Repomix, etc.) | `rules/ecosystem-tools.md` |
| `component-classification.md` | CORE vs PACKAGE component taxonomy | `rules/component-classification.md` |
| `cognitive-os-changes.md` | Plan-first protocol specifically for OS-level modifications | `rules/cognitive-os-changes.md` |
| `library-selection.md` | Checklist for evaluating new library dependencies | `rules/library-selection.md` |

## Cross-reference notes

- `rules/RULES-COMPACT.md` still indexes these patterns by key (e.g.
  `[plan-first]`, `[dogfooding]`). Consumers resolving those keys should look
  in `docs/04-Concepts/patterns/` first, then fall back to `rules/` for historical
  compatibility.
- `hooks/self-install.sh` still lists these names in `EXCLUDED_RULES` as
  "contextual" — the installer silently skips names it cannot find, so the
  stale entries cause no runtime error. Cleanup is deferred to the sprint that
  owns `self-install.sh`.
- `tests/audit/test_rules_enforcement.py` iterates `rules/*.md`; moving these
  files out of `rules/` removes them from parameterized tests, which is the
  intended outcome (they were declarative-only and should not be tested as
  behaviors).
