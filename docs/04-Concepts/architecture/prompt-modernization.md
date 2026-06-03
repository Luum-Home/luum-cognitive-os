# Prompt Modernization Doctrine

## Purpose

Cognitive OS prompts should match modern Claude-family behavior: explicit scope, clear action, concise context, and deterministic enforcement outside prose where possible. This doctrine is grounded in Anthropic guidance for recent Claude models, especially Opus 4.8 literal instruction following, effort calibration, tool triggering, and overtrigger risks from aggressive prompting.

## Principles

1. Use direct, normal language for workflow guidance. Reserve emergency wording for security, data loss, destructive operations, credentials, legal exposure, and release integrity.
2. Prefer positive action guidance over negative phrasing. Say what the agent should do, when it applies, and how success is checked.
3. State scope explicitly. If a rule applies to every section, every file, or every sub-agent, name that scope instead of relying on implication.
4. Keep role prompts short. A one-sentence role can be useful, but durable behavior should live in skills, rules, hooks, or scripts.
5. Move deterministic enforcement to scripts and hooks. Prompts describe intent; executable gates verify commands, files, metrics, and release boundaries.
6. Use examples when they encode format or edge cases. Keep examples aligned with desired behavior because newer models attend closely to example details.
7. Tune tool use with precise triggers. If a model overuses a tool, narrow when the tool helps. If it underuses a tool, explain why and when to use it.
8. Separate finding from filtering in review prompts. Ask review agents to surface candidate issues broadly, then let a later verification/ranking step filter severity and confidence.

## Rewrite patterns

| Older pattern | Modernized pattern |
|---|---|
| `CRITICAL: You MUST use this tool when...` | `Use this tool when it improves correctness or materially reduces uncertainty.` |
| `NEVER skip tests.` | `Before closing implementation work, run the smallest validation lane that exercises the changed behavior, or explain the specific blocker.` |
| `DO NOT use markdown.` | `Write prose in flowing paragraphs; use markdown only for headings, code, and compact tables.` |
| `Always spawn agents for research.` | `Spawn sub-agents when the work benefits from parallel file discovery or independent review; handle narrow visible edits directly.` |
| `Only report high-severity issues.` | `Report every plausible issue with severity and confidence; a later step can filter or deduplicate.` |

## Scope for this repository

Apply this doctrine to user-facing and model-facing text in:

- `AGENTS.md`
- `rules/`
- `skills/`
- `.codex/skills/`
- `.claude/commands/`
- hooks that emit `additionalContext`, `updatedInput`, or human-readable model guidance

Do not mechanically rewrite shell error labels, metric status names, enum values, test fixtures, security scan severity labels, or quoted external text. Those are protocol/data surfaces, not prompt style.

## Review checklist

- Does the instruction say the action and scope directly?
- Is the language proportionate to the risk?
- Could a hook or script verify this instead of relying on prose?
- Does the prompt distinguish research, planning, editing, verification, and review?
- Are examples minimal and aligned with the desired behavior?
- Did the change preserve existing safety gates for secrets, destructive git, credentials, legal/license boundaries, and releases?


## Audit ratchet

Use `scripts/prompt_aggressive_language_audit.py` to separate prompt-style debt from allowed security, protocol, severity, and skill-frontmatter language. For a bounded wave, pass the exact files and `--fail-debt`:

```bash
python3 scripts/prompt_aggressive_language_audit.py path/to/file.md --fail-debt
```

For repo-wide planning, run without `--fail-debt` to get the current debt inventory before choosing the next wave. Treat repo-wide output as planning data until the backlog is ratcheted down; use `--fail-debt` only for bounded file sets in the active wave.

## Validation

Use a two-level validation approach:

1. Structural check: count aggressive terms in changed model-facing files and confirm reductions are intentional.
2. Behavioral check: run the narrow tests for changed rules, skills, hooks, or docs. For prompt-only docs, validate links and grep for accidental scope drift.
