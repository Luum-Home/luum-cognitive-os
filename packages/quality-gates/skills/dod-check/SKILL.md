---
name: dod-check
command: /dod-check
description: Run a deterministic Definition of Done check before claiming implementation, review, prompt-modernization, hook, skill, rule, or release-prep work is complete.
trigger: Manual invocation or before claiming task completion
inputs:
- task_description (optional): What was done
- complexity (optional): trivial | small | medium | large | critical. Auto-classified when omitted.
outputs:
- verdict: PASS | PARTIAL | FAIL
- complexity: classified complexity level
- checks: deterministic hygiene and validation recommendations
audience: project
version: 1.1.0
platforms:
- claude-code
- codex
prerequisites: []
routing_intents:
- check definition of done for a completed task
- verify task completion criteria before declaring work finished
- run a done check before claiming completion
- assess whether implementation work is finished
- report missing items against the definition of done
triggers:
- dod-check
- /dod-check
- $dod-check
- Definition of Done Check
---
<!-- SCOPE: both -->
# Definition of Done Check

Use this skill before claiming work is complete.

## Workflow

1. Run the deterministic checker from the repository root. In this SO repo, use:

```bash
python3 scripts/dod_check.py --format markdown
```

In an installed consumer project, use the projected skill-local checker:

```bash
python3 .cognitive-os/skills/cos/dod-check/scripts/check_dod.py --format markdown
```

2. Treat `FAIL` items as blockers for completion claims.
3. Treat `PARTIAL` as unfinished work unless the skipped lane is explicitly out of scope.
4. Treat `WARN` items as explicit uncertainties in the Trust Report.
5. If the checker recommends a validation command, run the smallest command that covers the changed surface.
6. Report the checker verdict and any skipped checks in the final answer.

## Output format

The checker reports one of three verdicts: `PASS`, `PARTIAL`, or `FAIL`. `PASS` means deterministic checks found no blockers. `PARTIAL` means required evidence is incomplete or a validation lane was intentionally skipped. `FAIL` means at least one deterministic blocker is present.

## Phase enforcement

In `reconstruction` and `stabilization`, missing DoD evidence is usually a `WARN` unless the task is security-, release-, or credential-sensitive. In `production` and `maintenance`, missing required evidence is a `BLOCK` for completion claims.

## Notes

- The checker does not run expensive test lanes by default.
- Use `--run-recommended` only when the recommended command is safe for the current machine and task scope.
- Security, credential, release, and destructive-git boundaries remain governed by deterministic hook and script checks rather than prose.
- Claude Code invokes this as `/dod-check`; Codex invokes the projected skill as `$dod-check`. Both use the same deterministic checker logic.

## Contextual Trigger

Keywords: done, completion, Definition of Done, DoD, verify finished work, Trust Report, before final answer.
