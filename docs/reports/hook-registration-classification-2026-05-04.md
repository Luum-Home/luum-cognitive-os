# Hook Registration Classification — 2026-05-04

## Scope

This report classifies every top-level `hooks/*.sh` file that is absent from the
live Claude projection in `.claude/settings.json` after ADR-144. It does **not**
claim these hooks are broken. It separates deliberate non-projection from hooks
that deserve promotion work.

Machine-readable source of truth: `manifests/hook-registration-classification.yaml`.
Audit contract: `tests/audit/test_hook_registration_classification.py`.

## Current counts

| Status | Count | Meaning |
|---|---:|---|
| `future` | 23 | Real idea, not ready for default projection. |
| `conditional_opt_in` | 13 | Requires env/service/profile/tool availability. |
| `manual_trigger` | 10 | Should be run by command, cron, CI, or operator. |
| `deprecated` | 7 | Compatibility or superseded implementation; archive candidate. |
| `candidate_promote` | 0 | All near-term candidates have been promoted, demoted, or folded into existing streams. |
| `git_or_manual` | 2 | Git hook or manual flow, not a Claude hook. |
| `demoted` | 5 | Explicitly kept out of default projection by lifecycle metadata or candidate-resolution decisions. |
| `internal_helper` | 2 | Called/sourced by other hooks; standalone projection would duplicate work. |
| `projected_elsewhere` | 1 | Not in Claude because another harness projects it. |
| **Total** | **63** | Current `.claude/settings.json` unregistered top-level hooks. |

## Candidate resolution

All remaining promotion candidates were resolved on 2026-05-04:

| Hook | Decision | Rationale |
|---|---|---|
| `hooks/agent-output-verifier.sh` | Demote/manual diagnostic. | Regex-only prose file-claim parsing overlaps `completion-gate.sh`/`post-agent-verify.sh` and is too false-positive-prone for a default hot-path hook until Agent returns are structured. |
| `hooks/resource-check.sh` | Demote; do not project. | Budget/rate pressure is already covered by `token-budget-monitor.sh` and `rate-limiter.sh`; a second Agent preflight would duplicate policy and startup/hot-path cost. |
| `hooks/tool-loop-detector.sh` | Fold into `tool-sequence-capture.sh`. | Loop detection now uses the existing PostToolUse sequence stream for repeated signatures and ping-pong patterns, avoiding another parallel hook. |

## Decisions

1. Do **not** register all 64 hooks. The classification shows most are future,
   conditional, manual, deprecated, or helpers.
2. Treat `manifests/hook-registration-classification.yaml` as the ratchet for
   remaining hook debt. Adding/removing projection must update the manifest.
3. `hooks/release-guard.sh` was promoted because it is deterministic and
   release-safety critical; all other candidates were demoted or folded into
   existing hooks to avoid parallel hot-path work.
4. Keep `concurrent-write-guard-codex-proxy.sh` out of Claude projection; it is
   a Codex-only proxy and is validated as `projected_elsewhere`.

## Verification

Executed:

```bash
python3 -m pytest tests/audit/test_hook_registration_classification.py -q
python3 scripts/check_hook_registration.py
```

Expected results:

- `test_hook_registration_classification.py`: 3 passed.
- `check_hook_registration.py`: exits 0; the remaining profile-registration debt
  is allowlisted or classified.
