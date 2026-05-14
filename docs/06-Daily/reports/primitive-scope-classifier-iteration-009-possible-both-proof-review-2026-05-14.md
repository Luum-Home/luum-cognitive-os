# Primitive Scope Classifier Iteration 9 — Possible `both` Proof Review

## Input

Iteration 7 identified nine rows as possible `both` rather than stale `both` markers:

- `rules/recommendation-grounding.md`
- `rules/trust-score.md`
- `hooks/agent-output-verifier.sh`
- `hooks/clarification-interceptor.sh`
- `hooks/epic-task-detector.sh`
- `hooks/resource-check.sh`
- `hooks/subagent-capability-preflight.sh`
- `scripts/cos-governed-agent.sh`
- `scripts/cos-governed-edit.sh`

## Manual decision

All nine remain `both`.

Reason: the current bodies are not merely Cognitive OS self-construction procedures. They encode repository-agnostic agent governance behavior that Cognitive OS uses on itself and can also project into downstream COS-managed projects:

| Path | Decision | Reason |
|---|---|---|
| `rules/recommendation-grounding.md` | keep `both` | Grounded ranking/recommendation discipline is repo-agnostic; COS paths are examples/evidence sources. |
| `rules/trust-score.md` | keep `both` | Evidence/uncertainty/verification reporting is a generic agent-completion protocol. |
| `hooks/agent-output-verifier.sh` | keep `both` | Verifying files agents claim to create is generic agent safety. |
| `hooks/clarification-interceptor.sh` | keep `both` | Agent clarification interception is generic orchestration quality behavior. |
| `hooks/epic-task-detector.sh` | keep `both` | Detecting large/bulk tasks before launch protects any repository. |
| `hooks/resource-check.sh` | keep `both` | Budget-aware agent launch governance applies to COS-managed downstream projects. |
| `hooks/subagent-capability-preflight.sh` | keep `both` | Subagent capability preflight is generic artifact-contract safety. |
| `scripts/cos-governed-agent.sh` | keep `both` | Explicit portable wrapper for harnesses without Agent hook parity. |
| `scripts/cos-governed-edit.sh` | keep `both` | Explicit portable wrapper for harnesses without Edit/Write hook parity. |

## Changes made

Added lifecycle metadata for all nine rows:

- `distribution: team`
- `owner_adr: ADR-314`
- paired proof command in `evidence_commands`
- `consumer_accessibility: lifecycle-declared-team`
- row-specific behavior evidence explaining the portable principle

No `SCOPE` markers were changed.

## Scoped classifier result

```bash
.venv/bin/python scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths rules/recommendation-grounding.md rules/trust-score.md \
          hooks/agent-output-verifier.sh hooks/clarification-interceptor.sh \
          hooks/epic-task-detector.sh hooks/resource-check.sh \
          hooks/subagent-capability-preflight.sh \
          scripts/cos-governed-agent.sh scripts/cos-governed-edit.sh \
  --fail-contradictions
```

Observed:

```json
{
  "total": 9,
  "by_suggested_scope": {"both": 9},
  "by_effective_scope": {"both": 9},
  "by_confidence": {"medium": 9},
  "contradictions": 0
}
```

Each row also has an existing paired portability/falsification test under `tests/red_team/portability/`.

## Full classifier delta

After this pass:

```json
{
  "total": 1199,
  "by_suggested_scope": {
    "both": 59,
    "os-only": 417,
    "project": 50,
    "unknown": 673
  },
  "by_effective_scope": {
    "both": 59,
    "os-only": 1090,
    "project": 50
  },
  "contradictions": 238
}
```

Unknown triage now reports `declared-both-os-internal-heavy: 81` instead of 90.

## Validation

```bash
.venv/bin/python -m pytest \
  tests/red_team/portability/test_agent-output-verifier.py \
  tests/red_team/portability/test_clarification-interceptor.py \
  tests/red_team/portability/test_epic-task-detector.py \
  tests/red_team/portability/test_resource-check.py \
  tests/red_team/portability/test_subagent-capability-preflight.py \
  tests/red_team/portability/test_recommendation-grounding.py \
  tests/red_team/portability/test_trust-score.py \
  tests/red_team/portability/test_cos-governed-agent.py \
  tests/red_team/portability/test_cos-governed-edit.py -q
```

Observed: `9 passed`.

## Decision

These nine are confirmed as `both` for now, but confidence remains medium because several proofs are safe-invocation or structural portability probes rather than full downstream behavior tests. Future hardening should make the proof tests more behavioral, not demote the primitives by default.
