# Primitive SCOPE classifier — Iteration 023 hooks declared os-only batch

Date: 2026-05-15

## Goal

Reduce post-orthogonality `unknown` debt without changing semantic SCOPE markers by adding missing evidence metadata for hooks already declared `SCOPE: os-only`.

## Manual classification decision

Keep these 20 hook primitives as `os-only` and add maintainer-only metadata:

- `hooks/aci-observation-capture.sh`
- `hooks/adoption-freeze-gate.sh`
- `hooks/adr-section-validator.sh`
- `hooks/aspirational-audit-weekly.sh`
- `hooks/attribution-completeness-validator.sh`
- `hooks/auto-skill-generator.sh`
- `hooks/codebase-itinerary-capture.sh`
- `hooks/completeness-check.sh`
- `hooks/cos-executor-daemon-launcher.sh`
- `hooks/cos-session-start-projector.sh`
- `hooks/decision-depth-gate.sh`
- `hooks/dependency-license-classifier.sh`
- `hooks/dequeue-notify.sh`
- `hooks/dispatch-gate.sh`
- `hooks/docker-drift-detector.sh`
- `hooks/external-cache-content-leak.sh`
- `hooks/external-pattern-cleanroom-gate.sh`
- `hooks/history-rewrite-documented.sh`
- `hooks/hook-header-validator.sh`
- `hooks/infra-health.sh`

## Evidence

The bodies and headers show COS-maintainer concerns rather than adopter-project-only or generic repo guidance:

- COS runtime/session state under `.cognitive-os/*`.
- COS governance documents and manifests (`docs/02-Decisions/adrs`, external adoption freeze, clean-room research annexes, license policy).
- COS orchestrator/concurrency/session-start behavior.
- COS infrastructure such as the executor daemon and cognitive-os Docker compose stack.

## Metadata added

For each missing row, added `primitive-consumer-availability.yaml` entries with `status: maintainer-only`. Existing lifecycle rows already supplied enough hook/runtime context for the classifier; the missing proof was consumer availability, not a SCOPE marker change.

## Before / after

Before this batch:

```json
{
  "total_unknown": 413,
  "by_prefix": {"hooks": 172, "rules": 83, "scripts": 158}
}
```

After this batch:

```json
{
  "total_unknown": 393,
  "by_prefix": {"hooks": 152, "rules": 83, "scripts": 158},
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 315,
    "os-only-semantic-candidate": 70,
    "project-only-semantic-candidate": 4
  }
}
```

## Acceptance criteria

- Classifier reports `unknown: 393`.
- Triage reports hooks unknown reduced from 172 to 152.
- Registry lock regenerates and audits cleanly.
- Primitive parser/classifier/triage/portability tests pass.
- Primitive inventory remains structurally clean.
