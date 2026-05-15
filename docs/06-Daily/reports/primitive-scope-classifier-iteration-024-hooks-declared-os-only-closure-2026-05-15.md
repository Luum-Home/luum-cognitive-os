# Primitive SCOPE classifier — Iteration 024 declared os-only hook closure

Date: 2026-05-15

## Goal

Finish the declared `SCOPE: os-only` hook evidence batch after the distribution/SCOPE orthogonality fix.

## Manual classification decision

Keep these 35 hook primitives as `os-only` and add maintainer-only consumer availability proof:

- `hooks/kpi-trigger.sh`
- `hooks/legal-review-required-on-runtime-import.sh`
- `hooks/lethal-trifecta-gate.sh`
- `hooks/lib-symlink-divergence-detector.sh`
- `hooks/native-agent-heartbeat.sh`
- `hooks/post-agent-snapshot-restore.sh`
- `hooks/promotion-proposer-weekly.sh`
- `hooks/rate-limit-detector.sh`
- `hooks/reaper-daemon-launcher.sh`
- `hooks/research-to-runtime-firewall.sh`
- `hooks/review-spawner.sh`
- `hooks/rule-frontmatter-validator.sh`
- `hooks/rule-md-routing-validator.sh`
- `hooks/self-install.sh`
- `hooks/self-knowledge-refresh.sh`
- `hooks/session-changelog.sh`
- `hooks/session-end-reap.sh`
- `hooks/session-resume.sh`
- `hooks/session-start-stack-recommend.sh`
- `hooks/session-watchdog-launcher.sh`
- `hooks/skill-drift-detector.sh`
- `hooks/skill-failure-monitor.sh`
- `hooks/skill-feedback-tracker.sh`
- `hooks/skill-invocation-logger.sh`
- `hooks/skill-md-routing-validator.sh`
- `hooks/skill-synthesis-scanner.sh`
- `hooks/skill-tracker.sh`
- `hooks/skill-usage-tracker.sh`
- `hooks/spdx-header-required.sh`
- `hooks/stash-budget-warn.sh`
- `hooks/state-heartbeat.sh`
- `hooks/tool-sequence-capture.sh`
- `hooks/validation-lock-cleanup.sh`
- `hooks/validator-soak-weekly.sh`
- `hooks/work-queue-sync.sh`

## Evidence

Manual header/body review showed COS runtime-maintainer behavior, including:

- `.cognitive-os` metrics, runtime locks, session state, work queues, changelogs, task state, and skill telemetry.
- COS self-install/self-knowledge/watchdog/reaper daemons.
- COS governance gates for legal review, SPDX policy, clean-room research, symlink divergence, and rule/skill routing contracts.
- COS agent orchestration, review spawning, rate-limit fallback advice, KPI/self-improvement loops, and validator soak promotion.

These are hook event handlers for operating or maintaining COS. They may be installed in a consumer project as part of COS runtime projection, but they are not standalone project-agnostic authoring primitives.

## Metadata added

Added `primitive-consumer-availability.yaml` rows with `status: maintainer-only` and concrete rationale for all 35 paths.

## Before / after

Before this batch:

```json
{
  "total_unknown": 393,
  "by_prefix": {"hooks": 152, "rules": 83, "scripts": 158}
}
```

After this batch:

```json
{
  "total_unknown": 358,
  "by_prefix": {"hooks": 117, "rules": 83, "scripts": 158},
  "by_declared_scope": {"both": 354, "os-only": 4},
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 299,
    "os-only-semantic-candidate": 51,
    "project-only-semantic-candidate": 4
  }
}
```

## Acceptance criteria

- Classifier reports `unknown: 358`.
- Triage reports hook unknown reduced from 152 to 117.
- Only 4 declared `os-only` unknowns remain; next work should focus on `both` hook classification rather than blindly demoting.
- Registry lock regenerates and audits cleanly.
- Primitive parser/classifier/triage/portability tests pass.
- Primitive inventory remains structurally clean.
