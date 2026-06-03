---
name: dod-check
description: Run a deterministic Definition of Done check for the current Cognitive OS worktree before claiming completion. Use when finishing implementation, review, prompt-modernization, hook, skill, rule, or release-prep work.
version: 1.0.0
audience: cognitive-os-maintainers
tags: [definition-of-done, verification, codex, quality]
---

# DoD Check

Use this skill before claiming work is complete in Codex.

## Workflow

1. Run the deterministic checker from the repository root:

```bash
python3 .codex/skills/dod-check/scripts/check_dod.py --format markdown
```

2. Treat `FAIL` items as blockers for completion claims.
3. Treat `WARN` items as explicit uncertainties in the Trust Report.
4. If the checker recommends a validation command, run the smallest command that covers the changed surface.
5. Report the checker verdict and any skipped checks in the final answer.

## Notes

- The script does not run expensive test lanes by default.
- Use `--run-recommended` only when the recommended command is safe for the current machine and task scope.
- Security, credential, release, and destructive-git boundaries remain governed by hooks/scripts rather than prose.
