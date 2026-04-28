<!-- SCOPE: os-only -->
# Cross-Harness Authoring

## Rule

Before changing OS runtime paths, settings projection, hooks, skills, rules, or
bootstrap scripts, verify that the behavior is authored once and projected
through explicit harness drivers.

## Required Self-Check

1. If the behavior is canonical, keep it under `.cognitive-os/`, `hooks/`,
   `rules/`, `skills/`, `lib/`, or a manifest-backed contract.
2. If the behavior is harness-specific, place it behind the active driver
   surface such as `.claude/`, `.codex/`, or a settings adapter.
3. Do not make `.claude/settings.json` the implicit source of truth for Codex,
   Cursor, OpenCode, or future harnesses.
4. Tests must cover the canonical behavior and at least one projected harness
   path when claiming portability.
5. Documentation must label harness-only behavior honestly instead of calling it
   portable.

## Contextual Trigger

Load this rule when changing settings projection, harness detection, hook
registration, skills/rules installation, bootstrap scripts, or any code path
that mentions `.claude/`, `.codex/`, provider adapters, or cross-harness
portability.
