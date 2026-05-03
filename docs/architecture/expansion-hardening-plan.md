# Expansion Hardening Plan

This plan operationalizes ADR-133. The goal is not to add more governance; it is
to prevent expansion from turning Cognitive OS into an always-on monster.

## Readiness target

- Today: **6/10** expandability.
- Target after three sprints: **8.5/10**.
- Definition of success: more machines, harnesses, sessions, and agents can run
  without increasing default-visible surface or silent failure risk.

## Workstreams

### A. Lab-first lifecycle enforcement

Done:

- `scripts/cos-lab-first-gate` blocks new/promoted `core`, `team`, `blocking`, or
  `default-on` primitives unless they carry `promotion_evidence` linked to
  `cos-boring-reliability`.
- Architecture readiness includes `lab-first-promotion-gate`.
- `bash scripts/cos-ci-local.sh quick` includes the lab-first gate in the local
  pre-push validation bundle.
- Contract tests cover new promoted primitives, evidence-backed exceptions, and
  grandfathered existing primitives.

Next:

- Add a monthly demotion report for default-visible primitives with zero runtime
  use in 90 days.

### B. Semantic governance matching

Known brittle patterns:

- Matching Git operations in commit bodies instead of parsed argv.
- Matching claim words in prose instead of structured claim payloads.
- Matching `bypass` anywhere in telemetry JSON instead of scoped fields.
- Treating `git push --delete` from `main` the same as direct push to `main`.

Done:

- `cos_false_positive_ledger.py` now uses scoped false-positive/bypass fields.

Next:

- Create a shared command classifier for Git operations.
- Move destructive Git, direct-main, and claim gates onto classifier results.
- Add false-positive regression tests for commit messages, filenames, docs text,
  remote branch deletion, and generated telemetry payloads.

### C. Harness portability tax

Done:

- `manifests/harness-driver-capabilities.yaml` declares Claude, Codex, and Bare
  CLI capabilities and honest limited/unsupported event surfaces.
- `scripts/harness_parity_audit.py` fails supported-event parity gaps without
  pretending limited/unsupported surfaces are complete.

Next:

- Add `harness_specific: true|false` or equivalent derived reporting for each
  runtime primitive.
- Track Claude-only runtime ratio as an expansion warning.
- Create driver acceptance templates for Cursor, Continue, and OpenCode before
  implementing those adapters.

### D. Federation foundation

Current risk:

- Engram, locks, markers, and skill registry are local-first. That is acceptable
  for one maintainer with one or two machines, but not for concurrent multi-PC or
  multi-maintainer operation.

Next:

- Define Engram sync conflict semantics.
- Add `skills/REGISTRY.lock` with deterministic skill versions.
- Add optional Redis/Valkey lease backend for branch/task/session locks.
- Add runtime marker schema with machine identity and reaper ownership.

### E. Autonomous-agent contract

Rule:

Unsupervised agents must not continue blindly through a degraded control plane.

Next:

- Add an action-count checkpoint: run `cos-boring-reliability` every N mutating
  actions or before publication.
- If status is not pass, escalate instead of bypassing.
- Persist the checkpoint in session metrics so the operator can audit compliance.

## Current acceptance commands

```bash
scripts/cos-lab-first-gate --json
python3 -m pytest tests/contracts/test_lab_first_promotion_gate.py -q
python3 scripts/cos_architecture_readiness.py --json
bash scripts/cos-ci-local.sh quick
```
