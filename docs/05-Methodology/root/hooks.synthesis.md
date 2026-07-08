---
type: methodology-synthesis
source: docs/05-Methodology/root/hooks.md
provenance: "Inventories every runtime hook by lifecycle event so operators know exactly which shell scripts intercept which Claude Code tool calls and why."
---

## What it is

The full inventory of Cognitive OS runtime hooks — shell scripts configured in `.claude/settings.json` that fire at specific points in the Claude Code session lifecycle, living in `hooks/`. Documents 46 registered hooks across 8 lifecycle events (out of 94 total scripts in `hooks/`; the remainder load on-demand or are utilities), plus deep-dives on 4 representative hooks and the inter-hook data-sharing library.

## Key mechanics

- **By lifecycle event**: SessionStart (3: self-install, session-init, crash-recovery), PreToolUse (9: rate-limiter, release-guard, large-file-advisor, concurrent-write-guard, clarification-gate, blast-radius, error-pattern-detector, parry-scan, aguara-scan), PostToolUse (24, including 8 hooks new in v0.4.0: auto-refine, auto-verify, dod-gate, auto-repair-dispatcher, error-learning, skill-feedback-tracker, parry-scan, reinvention-check), Stop (5: session-learning, session-cleanup, task-recorder, session-state-save, kpi-trigger), and 4 "Other" event hooks (TeammateIdle, TaskCreated, TaskCompleted, UserPromptSubmit x2).
- **Deep dives**: (1) `stack-detector.sh` detects Node/TS/NestJS/Express/React Native/Jest/Go/Java-Spring/Docker/DB/Clean-Architecture markers and writes `.claude/detected-stack.json`; (2) `block-prod-urls.sh` denies Bash commands matching production domain regexes (`example.com`, `prod.example.*`, etc.) with a `{"decision":"deny",...}` response; (3) `auto-test-on-edit.sh` maps edited file paths to per-service test commands (Java services get a reminder only — "too slow for auto-run" — JS/TS services get `npx jest --changedSince=HEAD`, Go gets `go test ./... -short`); (4) `skill-feedback-tracker.sh` detects Agent/Skill failures (non-zero exit or error keywords) and POSTs an Engram observation to `localhost:7437` under topic key `skill-feedback/{skill-name}`, feeding the `skill-adaptation` rule's 3-failure rewrite trigger.
- **Hook composition**: `hooks/_lib/hook-pipe.sh` lets hooks in the same event chain pass data downstream via `hook_emit`/`hook_read`/`hook_pipe_clear`, storing one value per file at `.cognitive-os/.hook-pipe/<event>-<key>.val`. One documented active flow: `clarification-gate.sh` emits `clarification_score` which `blast-radius.sh` reads to lower its HIGH-radius threshold from 40 to 20 when ambiguity ≥ 30. Pipe files persist for the session and are not auto-cleared.

## Relations & where used

- Hook names referenced here (`block-prod-urls.sh`, `auto-test-on-edit.sh`, `skill-feedback-tracker.sh`, `stack-detector.sh`) match usages in `automation.md`'s session-lifecycle diagram.
- `skill-feedback-tracker.sh` -> `skill-adaptation.md` rule integration is also described from the rule side in `rules.md` (Rule 4: Skill Adaptation) and the skill side in `skills.md` (Auto-Improvement Flow).
- `coverage-gate.sh` (described in `configurable-quality-gates.md` as Layer 1) is not listed in this hook inventory's tables, suggesting either it postdates this doc or lives under a project-specific `.claude/hooks/` path distinct from the core `hooks/` directory this doc catalogs.

## Status / caveats

- States 46 hooks registered / 94 total scripts as a **specific count as of the time this doc was written** — hook counts change as the OS evolves (compare to the walkthrough's captured `159 wired` for an installed project, a different number for a different install context).
- 8 hooks are explicitly marked "new in v0.4.0," anchoring parts of this doc to a specific release; hooks added after v0.4.0 would not appear here.
