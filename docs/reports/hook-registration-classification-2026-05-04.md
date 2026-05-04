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
| `candidate_promote` | 4 | Worth evaluating for default projection or consolidation. |
| `git_or_manual` | 2 | Git hook or manual flow, not a Claude hook. |
| `demoted` | 2 | Explicitly kept out of default projection by lifecycle metadata. |
| `internal_helper` | 2 | Called/sourced by other hooks; standalone projection would duplicate work. |
| `projected_elsewhere` | 1 | Not in Claude because another harness projects it. |
| **Total** | **64** | Current `.claude/settings.json` unregistered top-level hooks. |

## Promotion candidates

These are the only hooks in the current set that should get near-term design
attention before further registration work:

| Hook | Why not registered now | Next decision |
|---|---|---|
| `hooks/agent-output-verifier.sh` | Overlaps `completion-gate.sh` and `post-agent-verify.sh`; needs false-positive proof. | Evaluate whether to merge into existing post-agent verification. |
| `hooks/release-guard.sh` | Valuable release safety, but absent from canonical projection. | Decide: PreToolUse Bash registration vs. move fully into `cos release`/git policy. |
| `hooks/resource-check.sh` | Budget guard overlaps `token-budget-monitor.sh` and `rate-limiter.sh`. | Decide whether to merge with the existing token/rate guards. |
| `hooks/tool-loop-detector.sh` | Needs integration with `tool-sequence-capture.sh` / ACI capture rather than another parallel hot-path hook. | Evaluate merged loop detection in the existing trajectory capture path. |

## Decisions

1. Do **not** register all 64 hooks. The classification shows most are future,
   conditional, manual, deprecated, or helpers.
2. Treat `manifests/hook-registration-classification.yaml` as the ratchet for
   remaining hook debt. Adding/removing projection must update the manifest.
3. Prioritize consolidation over new hot-path hooks for the four promotion
   candidates.
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
