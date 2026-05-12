# UX2 — Hook Hygiene (Capa-3 follow-up)

Single coordinator pass that resolves the code-dead hook references, the
`confidentiality-enforcer.sh` profile regression, a missing session-start
sanity check, and the non-actionable `rate-limiter.sh` error output found in
`scorecard-hooks.md`.

Scope (files touched): hooks/*.sh (4 new, 1 modified),
`scripts/apply-efficiency-profile.sh` (profile registration), and
`.claude/settings.json` (regenerated via the script — not edited directly).

## D1 — Three code-dead hooks resolved

| Hook | Prior state | Resolution |
|---|---|---|
| `hooks/auto-verify.sh` | Referenced by 12+ rules/skills/docs, file absent | **Created** — PostToolUse Agent, non-blocking. Parses `ACCEPTANCE CRITERIA:` block from the agent prompt/response, runs verification commands (patterns: `` `cmd` = N ``, `` `cmd` >= N ``, `` `cmd` exits 0 ``, `` `cmd` returns empty ``), logs PASS/FAIL/NO_CRITERIA/NO_PARSEABLE to `.cognitive-os/metrics/auto-verify.jsonl`. |
| `hooks/auto-refine.sh` | Referenced by the `auto-refine` skill, `closed-loop-prompts.md`, `phase-aware-agents.md`, `piter-framework.md`, file absent | **Created** — PostToolUse Agent, non-blocking. Detects TEST_FAILURE / BUILD_ERROR / LINT_ERROR / AGENT_ERROR in the response, tracks retry count per task fingerprint (`.cognitive-os/metrics/auto-refine/{fingerprint}.count`, max 3), emits orchestrator retry instructions in `reconstruction`/`stabilization`, suggestion-only in `production`/`maintenance`. Escalation on 3rd failure. |
| `hooks/dod-gate.sh` | Docs-only reference (`agent-quality.md:90`), file absent | **Created** — PostToolUse Agent, minimal. Reads complexity from the agent response (`complexity: trivial/small/medium/large/critical` or heuristic keywords), checks the DoD criteria listed in `rules/definition-of-done.md`, logs to `dod-gate.jsonl`. Phase-aware label (`WARN` in reconstruction/stabilization, `BLOCK` note in production/maintenance) — advisory only, never exits non-zero. |

Each new hook uses `hooks/_lib/safe-jsonl.sh` (0-subprocess heartbeats) and
resolves session-scoped metrics via `.cognitive-os/sessions/<id>/metrics/`
with a fall-back to the global metrics directory.

**Design note**: `completion-gate.sh` remains the integrated 3-phase pipeline
(merged from auto-verify + dod-gate + auto-refine per its header). The new
standalone hooks are lighter siblings for users that want the signals in
isolation. All four are registered at the `standard` tier alongside
`completion-gate.sh`; double-firing is acceptable because each is advisory.

## D2 — `confidentiality-enforcer.sh` profile regression fixed

Before: registered in `lean` + `standard` tiers of
`scripts/apply-efficiency-profile.sh` but NOT in the active `.claude/settings.json`
(the `full` path was a no-op early-exit that preserved the prior file verbatim).
Result: anyone running the `full` profile had no confidentiality enforcement,
inverting the normal lean ⊂ standard ⊂ full coverage.

After:
- Removed the `full` tier early-exit.
- `full` now regenerates `settings.json` as a superset of `standard` plus the
  "only-in-full" hooks (`confidence-gate.sh`, `assumption-tracker.sh`,
  `consequence-evaluator.sh`, `auto-skill-generator.sh`,
  `auto-repair-dispatcher.sh`, `architecture-compliance.sh`, etc.).
- `confidentiality-enforcer.sh` is explicitly listed in the `full` tier's
  `post_edit` group.
- Total occurrences of `confidentiality-enforcer` in the profile script: 8
  (was 2).

## D3 — New `hooks/session-sanity.sh` (SessionStart)

Created to operationalize ADR-001's regression detector at session start.
Runs two checks, prints actionable guidance on failure, always exits 0:

1. **Skill catalog size**: counts entries (dirs + symlinks) under
   `.claude/skills/`. Below 20 → emits
   `"Only N skills exposed; expected 20+. Run: bash hooks/self-install.sh."`
2. **Settings ↔ disk consistency**: scans `.claude/settings.json` for
   referenced `.sh` basenames, verifies each exists in `hooks/` or
   `packages/*/hooks/`. Broken references → emits
   `"settings.json references hooks that do not exist on disk: <list>.
     Run: bash hooks/self-install.sh."`

Registered at the `standard` tier of `apply-efficiency-profile.sh` so the
default profile surfaces it, and at `full` as well.

## D4 — `hooks/rate-limiter.sh` actionable error output

Before (non-actionable):
```
RATE LIMIT: bash_command limit exceeded: 22/22 per minute (base 15 x 1.5 [reconstruction]). Wait 60s.
RATE_LIMIT_QUEUED: bash_command queued for retry in 60s.
Queue ID: 4cd39b98
Queue position: 4
```

After (machine-parseable header preserved, UX block added below):
```
RATE_LIMIT_QUEUED: bash_command queued for retry in 60s.
Queue ID: 4cd39b98
Queue position: 4
BLOCKED: bash_command limit exceeded: 22/22 per minute (base 15 x 1.5 [reconstruction]). Wait 60s.

WARNING  Rate limit reached for bash_command
    Current:     22/22 per minute (phase: reconstruction)
    Next slot:   in ~60s
    Queue:       4 commands pending (ID: 4cd39b98)
    Action:      your command will retry automatically, or cancel with Ctrl-C

    To avoid:    run "cos status" to see rate state anytime

Suggestion: ...
ORCHESTRATOR ACTION: Check queue with RateLimitQueue.dequeue_ready() after 60s
```

Contract preserved for scripts scanning for `RATE_LIMIT_QUEUED:`, `Queue ID:`,
`BLOCKED:`, `Suggestion:`, `ORCHESTRATOR ACTION:`. UX block inserted between
the machine header and the suggestions block using a `---UX---` separator
splitter inside the Python generator, stripped out before printing to stderr.

## D5 — `.claude/settings.json` regenerated

Ran `bash scripts/apply-efficiency-profile.sh standard` (current profile per
`cognitive-os.yaml → efficiency.profile`). Result:

| Metric | Before | After |
|---|---|---|
| Total hook commands | 56 | 54 |
| `confidentiality-enforcer` references | 0 | 1 |
| `session-sanity` references | 0 | 1 |
| `auto-verify` references | 0 | 1 |
| `auto-refine` references | 0 | 1 |
| `dod-gate` references | 0 | 1 |
| JSON validity | valid | valid |

The 56 → 54 delta is expected: the prior hand-rolled `settings.json` carried
"only-in-full" hooks (aguara-scan, architecture-compliance, kpi-trigger,
mcp-scan, observability-trace, parry-scan, scope-proportionality,
scope-creep-detector, semgrep-scan, subagent-context-injector, task-created,
task-completed, task-recorder, teammate-idle, user-prompt-capture, etc.)
that belong in the `full` tier per `scorecard-hooks.md`. Regenerating at
`standard` drops those (by design) and adds the 5 new/fixed hooks above.

To restore the "only-in-full" set, run:
```
bash scripts/apply-efficiency-profile.sh full
```

## Acceptance Criteria — all passing

```
D1: test -f hooks/auto-verify.sh  && bash -n hooks/auto-verify.sh   ✓
    test -f hooks/auto-refine.sh  && bash -n hooks/auto-refine.sh   ✓
    test -f hooks/dod-gate.sh     && bash -n hooks/dod-gate.sh      ✓
D2: grep -c "confidentiality-enforcer" scripts/...  = 8  (>=3)     ✓
D3: test -f hooks/session-sanity.sh && bash -n hooks/session-sanity.sh  ✓
    grep "session-sanity" scripts/...  = 3 matches                  ✓
D4: grep -c "Action:" hooks/rate-limiter.sh  = 1  (>=1)             ✓
D5: python3 -c "import json; json.load(open('.claude/settings.json'))"  ✓
    grep -c "\"command\":" .claude/settings.json  = 54              ✓
    All hooks parse clean                                            ✓
```

## Files Created
- `hooks/auto-verify.sh` (193 lines)
- `hooks/auto-refine.sh` (142 lines)
- `hooks/dod-gate.sh` (157 lines)
- `hooks/session-sanity.sh` (78 lines)
- `docs/04-Concepts/architecture/functional-audit/ux2-hook-hygiene.md` (this file)

## Files Modified
- `hooks/rate-limiter.sh` (error output made actionable; machine-parseable
  contract preserved)
- `scripts/apply-efficiency-profile.sh` (full tier now regenerates; standard
  + full register new hooks; confidentiality-enforcer regression fixed)
- `.claude/settings.json` (regenerated by the script — NOT edited directly)
