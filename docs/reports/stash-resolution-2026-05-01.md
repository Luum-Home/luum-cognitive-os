# Stash Resolution Report — 2026-05-01
> Local stash stack audit before clearing accumulated WIP stashes. Each stash was archived under `refs/archive/stashes/2026-05-01/<n>` before any cleanup.
## Retrieval
To inspect an archived stash after the normal stash stack is cleared:
```bash
git show refs/archive/stashes/2026-05-01/0
git stash branch recover-stash-0 refs/archive/stashes/2026-05-01/0
```
A local bundle was also created at `.git/stash-archive-2026-05-01.bundle`, and a redundant external backup was copied to `$HOME/.codex/backups/luum-agent-os/stash-archive-2026-05-01.bundle`. Per-stash patch/stat/file-list backups were exported to `$HOME/.codex/backups/luum-agent-os/stashes-2026-05-01/`.
## Classification
| Stash | Archive ref | State vs current main | Subject | Files touched |
| ---: | --- | --- | --- | ---: |
| 0 | `refs/archive/stashes/2026-05-01/0` | already applied | `On main: park-main-before-headless-run-task-merge-2026-05-01` | 2 |
| 1 | `refs/archive/stashes/2026-05-01/1` | conflicts or stale | `On main: codex-post-anthropic-validation-side-effects-20260501` | 4 |
| 2 | `refs/archive/stashes/2026-05-01/2` | applies cleanly but unreviewed | `On main: park-main-primitive-coverage-report-side-effect-2026-05-01` | 1 |
| 3 | `refs/archive/stashes/2026-05-01/3` | conflicts or stale | `On (no branch): park-86ef-post-cherrypick-side-effects-2026-05-01` | 7 |
| 4 | `refs/archive/stashes/2026-05-01/4` | already applied | `On main: park-main-primitive-surface-reduce-side-effect-2026-05-01` | 2 |
| 5 | `refs/archive/stashes/2026-05-01/5` | applies cleanly but unreviewed | `On (no branch): park-86ef-test-side-effect-wip-after-final-validation-2026-05-01` | 2 |
| 6 | `refs/archive/stashes/2026-05-01/6` | already applied | `On codex/resolve-pending-items-20260501-lock-proof: park-current-lazy-catalog-autorevert-wip-after-validation-2026-05-01` | 2 |
| 7 | `refs/archive/stashes/2026-05-01/7` | already applied | `On main: park-main-leftover-untracked-wip-before-resolving-pending-items-2026-05-01` | 1 |
| 8 | `refs/archive/stashes/2026-05-01/8` | conflicts or stale | `On (no branch): park-dd97-dirty-wip-before-resolving-pending-items-2026-05-01` | 9 |
| 9 | `refs/archive/stashes/2026-05-01/9` | conflicts or stale | `On (no branch): park-86ef-dirty-wip-before-resolving-pending-items-2026-05-01` | 14 |
| 10 | `refs/archive/stashes/2026-05-01/10` | conflicts or stale | `On codex/direct-anthropic-api-policy: park-70d0-dirty-wip-before-resolving-pending-items-2026-05-01` | 166 |
| 11 | `refs/archive/stashes/2026-05-01/11` | conflicts or stale | `On (no branch): park-40b8-dirty-wip-before-resolving-pending-items-2026-05-01` | 5 |
| 12 | `refs/archive/stashes/2026-05-01/12` | conflicts or stale | `WIP on main: 727e2053 docs(audit): benchmark primitive coverage backends` | 28 |
| 13 | `refs/archive/stashes/2026-05-01/13` | conflicts or stale | `On main: pre-origin-main-sync 2026-05-01T12:00:30-03:00` | 17 |
| 14 | `refs/archive/stashes/2026-05-01/14` | conflicts or stale | `WIP on main: 83cba771 feat(adr-068): phase 2 — capacity decision logging to .cognitive-os/metrics/test-runs/` | 24 |
| 15 | `refs/archive/stashes/2026-05-01/15` | conflicts or stale | `On main: cos-20260430-170836` | 31 |
| 16 | `refs/archive/stashes/2026-05-01/16` | conflicts or stale | `On main: cos-20260430-165827` | 25 |
| 17 | `refs/archive/stashes/2026-05-01/17` | conflicts or stale | `WIP on main: 5418448d fix(pre-commit): scope Gate 3f to staged files only — no working-tree scan` | 24 |
| 18 | `refs/archive/stashes/2026-05-01/18` | conflicts or stale | `On main: cos-20260430-134321` | 123 |
| 19 | `refs/archive/stashes/2026-05-01/19` | conflicts or stale | `On main: cos-20260430-124451` | 8 |
| 20 | `refs/archive/stashes/2026-05-01/20` | conflicts or stale | `On main: cos-20260429-235238` | 4 |
| 21 | `refs/archive/stashes/2026-05-01/21` | empty patch | `On main: wip:absolute-path-scanner-before-release` | 0 |
| 22 | `refs/archive/stashes/2026-05-01/22` | conflicts or stale | `On main: cos-20260427-201643` | 7 |
| 23 | `refs/archive/stashes/2026-05-01/23` | conflicts or stale | `On main: cos-20260421-173206` | 3 |
| 24 | `refs/archive/stashes/2026-05-01/24` | conflicts or stale | `On main: cos-20260417-150236` | 27 |
| 25 | `refs/archive/stashes/2026-05-01/25` | conflicts or stale | `On main: cos-20260411-180245` | 2 |
| 26 | `refs/archive/stashes/2026-05-01/26` | conflicts or stale | `On main: cos-20260411-175207` | 6 |
| 27 | `refs/archive/stashes/2026-05-01/27` | conflicts or stale | `On main: cos-20260411-154637` | 13 |
| 28 | `refs/archive/stashes/2026-05-01/28` | conflicts or stale | `On main: cos-20260411-150357` | 7 |
| 29 | `refs/archive/stashes/2026-05-01/29` | conflicts or stale | `On main: cos-20260411-144138` | 59 |
| 30 | `refs/archive/stashes/2026-05-01/30` | conflicts or stale | `On main: cos-20260411-125310` | 1 |
| 31 | `refs/archive/stashes/2026-05-01/31` | conflicts or stale | `On main: cos-20260411-124725` | 1 |
| 32 | `refs/archive/stashes/2026-05-01/32` | conflicts or stale | `On main: cos-20260411-124633` | 94 |
| 33 | `refs/archive/stashes/2026-05-01/33` | conflicts or stale | `On main: cos-20260410-114653` | 20 |
| 34 | `refs/archive/stashes/2026-05-01/34` | conflicts or stale | `On main: cos-20260328-120558` | 4 |

## Resolution Policy

- `already applied`: safe to clear from stash stack; current history already contains equivalent changes.
- `empty patch`: safe to clear from stash stack; no working-tree patch remains.
- `applies cleanly but unreviewed`: archived instead of auto-applying because these are unrelated generated/WIP changes.
- `conflicts or stale`: archived instead of auto-applying because the patch conflicts with current main or depends on old tree shape.

No stash is destroyed without an archive ref and local bundle.


## Final Resolution — Minutious Pass

The normal stash stack was intentionally emptied only after three recovery paths existed:

1. local git refs: `refs/archive/stashes/2026-05-01/<n>` for all 35 former stashes;
2. verified bundle: `.git/stash-archive-2026-05-01.bundle`;
3. external backup copy and per-stash patches under `$HOME/.codex/backups/luum-agent-os/`.

Resolution categories:

- Stashes `0`, `4`, `6`, and `7` were already represented by current history and do not need re-application.
- Stash `21` had an empty patch.
- Stashes `2` and `5` apply cleanly but are unreviewed generated/WIP changes, so they remain archived instead of being auto-committed.
- All remaining stashes conflict with current `main` or depend on stale tree shape. They remain recoverable through archive refs/patches but were not auto-applied because doing so would reintroduce old broad WIP into a clean, tested `main`.

No stash content was discarded without a local ref, bundle entry, and patch backup.
