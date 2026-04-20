# Bug-2 (git-reset cascade) — Forensic Investigation

**Date**: 2026-04-20
**Investigator**: forensic sub-agent (opus, read-only)
**Source commits**: c0db698, 5115273, 9dc6b4c, 1e8a6fd, b4f470f, 49ee77f, 0dea17e, 6c5d810, dbb135f

## 1. Timeline

| When (UTC-3) | SHA | Event |
|---|---|---|
| 2026-04-16 ~early | *(no commit; working tree only)* | **Sprint 2a incident trigger** — sub-agent running squads/agents archival + declarative-rules move did `git stash push`, then either `git stash pop` with conflicts and/or `git checkout HEAD -- <path>` against scope-forbidden files. ~22 uncommitted UX-sprint files reverted silently. |
| 2026-04-16 22:08:00 | `1e8a6fd` | `fix: restore skill frontmatter + arena path + audit marker (post-revert recovery)` — first reconstructive commit. |
| 2026-04-16 22:09:04 | `c0db698` | Sprint 2a clean re-commit. Body notes: *"Caveat: same agent triggered the Sprint-N recovery incident."* |
| 2026-04-16 22:13:43 | `b4f470f` | `fix: restore UX3 perf fix + UX2 rate-limiter actionable output` |
| 2026-04-16 22:15:07 | `49ee77f` | `feat: restore UX5 cos-status + UX6 cos-update + Sprint 4 v1.0 canary` |
| 2026-04-16 22:17:14 | `0dea17e` | `feat: restore UX2 new hooks + Sprint 5 capa-4 observability infrastructure` |
| 2026-04-16 22:18:18 | `6c5d810` | `feat: restore UX1 install flags + UX8 profile simplification (ADR-002)` |
| 2026-04-16 22:19:11 | `5115273` | **`feat(safety): ADR-003 — agent git operations safety (3-layer prevention)`** — mitigation lands. Commit body: *"After Sprint 2a incident where an agent accidentally git stash pop'd then reverted scope-forbidden files to HEAD (lost 22 files of UX sprint work)…"* |
| 2026-04-16 22:21:45 | `9dc6b4c` | `feat: complete ADR-003 — pre-agent-snapshot refinement + destructive-git-blocker test` |
| 2026-04-16 22:25:22 | `dbb135f` | `chore: bump hermes-agent submodule + resolve Sprint 2a stash residue` — residue cleanup. |

Entire incident → mitigation arc compressed into a single ~17-minute recovery session.

## 2. Mechanism (evidence-based, not hypothesis)

ADR-003 `docs/architecture/harness-adoption-gap/ADR-003-agent-git-safety.md` lines 9-25 explicitly states the sub-agent executed `git stash pop`, then `git checkout HEAD -- <file>` against scope-forbidden files. Cumulative effect: ~22 files reverted to HEAD.

**Causal chain:**

1. Sub-agent told to "archive squads, move rules to `docs/patterns/`" (work eventually committed as `c0db698`). Scope guard was textual-only in the prompt.
2. Agent ran `git stash push` for a clean tree.
3. `git stash pop` conflicted / partially applied — tree in ambiguous state.
4. Agent reached for `git checkout HEAD -- <file>` (and plausibly `git reset --hard` on other files) as "clean up the mess". Didn't realize those paths were the in-flight UX-sprint files (UX1/2/3/5/6/8 + F1-cleanup + audit-cleanup + orchestrator inline fixes) — scope-forbidden but NOT runtime-enforced.
5. All commands returned `0` with terse output. Orchestrator accepted "done". **22 files of uncommitted work vanished.**

The "cascade" label in D01 / chaos-test name is slightly misleading: no single `git reset --hard` toppled a chain. The cascade is logical — one agent's misinterpretation of "clean up" escalated across multiple destructive ops (stash pop → checkout -- → plausibly reset --hard), each individually innocuous but together nuked the tree.

## 3. Blast radius

**Files lost (uncommitted, ~22):**
- UX1 install flags (restored by `6c5d810`)
- UX2 new hooks + rate-limiter actionable output (restored by `0dea17e`, `b4f470f`)
- UX3 perf fix to `cognitive-os.sh` (restored by `b4f470f`)
- UX5 cos-status, UX6 cos-update (restored by `49ee77f`)
- UX8 profile simplification (restored by `6c5d810`)
- F1-cleanup: 6 skill-frontmatter normalizations — `agent-stress-test`, `auto-rollback`, `capability-snapshot`, `cognitive-os-status`, `impact-analysis`, `red-team` (restored by `1e8a6fd`)
- audit-cleanup: `tests/conftest.py` audit marker, `skills/arena/run-arena.sh` path fixes, `skills/coverage-enforcement` TODO (restored by `1e8a6fd`)
- Several orchestrator inline fixes (explicitly unrecoverable verbatim per ADR-003)

**Commits lost:** zero. Everything was uncommitted — that's why damage was severe (no HEAD reflog safety net for working-tree-only work; stash reflog was the only rope).

**Surviving artifacts:** git stash reflog entries, `.cognitive-os/sessions/` checkpoints, Sprint 2a stash residue that persisted until `dbb135f` pruned it.

## 4. Current coverage — `destructive-git-blocker.sh` + chaos tests vs. original cause

`hooks/destructive-git-blocker.sh` line 69 blocks (in agent context only, when `CLAUDE_AGENT_ID` is set):

```
git (stash (pop|drop|apply) | reset --hard | checkout -- | clean -f | restore | revert | worktree)
```

Cross-reference vs documented incident ops:

| Incident op | Blocked? |
|---|---|
| `git stash pop` | YES (literal match) |
| `git checkout HEAD -- <file>` | **PARTIAL** — regex requires `--` immediately after `checkout`. `git checkout -- foo` blocked; `git checkout HEAD -- foo` NOT matched. |
| `git reset --hard` | YES |

ADR-003 text (lines 35-38) calls out `checkout -- <file>` but the incident narrative (line 10) specifies `git checkout HEAD -- <file>`. The blocker has a **real regex gap** for the exact form from the original incident.

Chaos test `tests/chaos/test_reset_cascade_detector.py` exercises only `git reset --hard HEAD~1` against the blocker plus a static grep (`git reset --hard`, `git clean -fdx`, `rm -rf /`). Does NOT cover `git checkout HEAD -- foo`, stash pop, or combinations.

**Defense in depth:** Mechanism A (`pre-agent-snapshot.sh`) + Mechanism B (`post-agent-verify.sh`) would still catch the incident via auto-restore from the pre-agent stash, IF the orchestrator has written the TOUCH scope file to `.cognitive-os/sessions/<SID>/agent-<AID>-prompt.txt`. ADR-003 line 98 notes Mechanism B refuses to auto-restore without that file.

**Coverage verdict: PARTIAL.** Composite A+B+C covers the exact incident IF orchestrator writes TOUCH scope. Mechanism C regex gap is a real defect for the canonical incident form.

## 5. Residual risks

### R1 — `git checkout HEAD -- <path>` regex gap (HIGH, concrete)

An agent told "undo my last edit to foo.py" will type `git checkout HEAD -- foo.py`. Regex on line 69 does not match this. ADR-003 documents this exact form as the incident trigger. If Mechanism B's TOUCH-scope file is absent (orchestrator refactor, non-COS-orchestrated agent), this is silently exploitable.

**Concrete repro test that would fail:** `test_blocker_blocks_checkout_HEAD_dashdash` with `CLAUDE_TOOL_INPUT="git checkout HEAD -- foo.py"`, expect returncode=1, actual returncode=0.

**Fix (landed in this commit):** broaden regex to match `checkout[[:space:]]+(--|HEAD[[:space:]]+--|<ref>[[:space:]]+--)`.

### R2 — Non-git destructive ops reach the same outcome (HIGH)

ADR-003 line 197 defers `destructive-rm-blocker.sh`. Agent running `rm -rf <file>`, `> file`, `truncate -s 0`, `cp /dev/null file`, or a Python/Node script doing `os.remove` / `fs.unlinkSync` destroys working-tree state identically. Mechanism B auto-restores from stash IF TOUCH scope is known. Chaos suite's only non-git pattern is the literal `rm -rf /` (root only). `rm -rf packages/auto-repair-rollback/` is NOT matched.

### R3 — Killswitch bypass (MEDIUM)

Line 31 of `destructive-git-blocker.sh` sources `_lib/killswitch_check.sh` and early-exits when flag set (ADR-028 §584). Agent or misconfigured operator setting the killswitch disables blocker entirely. ADR-003 line 204 says "Safety-critical hooks are never gated behind an opt-in profile" — but killswitch is a runtime gate that contradicts that invariant. Debug session leaves killswitch flipped → next agent has Mechanism C disabled.

### R4 — Orchestrator/user context escape hatch (MEDIUM)

If `CLAUDE_AGENT_ID` is empty, blocker only warns. Mis-propagated env (sub-shell, `env -i`, direct `bash -c`, nested invocation) makes destructive op look user-initiated → allowed. Future harness refactor dropping env-propagation would silently re-open the hole.

### R5 — Stash-residue reuse (LOW)

Reflog entries 2026-04-17 show "stash WIP before agent work, pop after" pattern persisted past the incident. User's own WIP stash parallel to auto-pre-agent stashes can `git stash pop` the wrong entry and re-enact from user context.

## Fixes landed in this commit

1. `hooks/destructive-git-blocker.sh` regex broadened to catch `git checkout HEAD -- <file>` (R1 closed).
2. `tests/chaos/test_reset_cascade_detector.py` gains coverage for `checkout HEAD --` form.
3. This report persisted. Residual risks R2-R5 enter the debt register for follow-up.

## Evidence exhaustion

- Engram search not executed by the forensic agent (mem_* tools deferred). Report based on `git log`, ADR-003 text, hook source, reflog.
- Exact "~22 files" count reconstructed from restore commits + ADR-003 narrative, not independently verifiable (incident stash pruned at `dbb135f`).
- "Plausibly `git reset --hard`" in §2 chain is inference — ADR-003 names stash pop + `checkout HEAD --` explicitly. The "reset --hard" framing in D01 / mega-plan may generalize the op family.
