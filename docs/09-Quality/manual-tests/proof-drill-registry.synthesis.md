---
type: quality-synthesis
source: docs/09-Quality/manual-tests/proof-drill-registry.md
provenance: "Manual test proving agents can choose between normal tests, smoke opt-ins, and proof drills without adding provider/Docker/account-backed checks to default lanes."
---

## What it is
A manual test procedure (dated 2026-05-05) that validates the proof-drill registry contract: the mechanism that lets Cognitive OS classify checks as normal tests, smoke opt-ins, or proof drills, and keeps provider-credential and Docker-backed checks out of default CI/test lanes.

## Key mechanics
- **Registry contract test**: `python3 -m pytest tests/contracts/test_proof_drill_registry.py -q` must pass.
- **Skill contract test**: `python3 -m pytest tests/audit/test_skills_contracts.py -q` validates the `proof-drill` skill's frontmatter, references, catalog presence, and absence of stub markers.
- **Opt-in row inspection**: a Python snippet loads `manifests/proof-drill-registry.yaml` and prints every entry whose `class` is `smoke-opt-in`, `proof-drill`, or `manual-proof`; every printed row must have `default_lane: False`.
- **Consumer-project boundary check**: the `consumer-project-run-tests` registry row must point to `skills/run-tests/SKILL.md`, not an SO-only proof script, keeping consumer-project validation project-owned by default.
- **Optional provider smoke**: `bash scripts/smoke-qwen-fallback.sh`, run only with explicit operator opt-in and `ALIBABA_QWEN_API_KEY` present; missing credentials are treated as skipped evidence, not proof of breakage.
- **Optional Docker/headless proof**: `scripts/cos-headless-service-drill --json`, run only with explicit Docker/headless opt-in.
- Evidence to record for every drill: command, working directory, exit code, artifact paths, credential posture, cost posture, bounded proof claim, and remaining gaps.

## Relations & where used
Anchors the proof-drill classification system referenced by other manual tests in this directory (e.g. `service-control-plane-proof-drills.md`), the `manifests/proof-drill-registry.yaml` manifest, and the `proof-drill` skill. Establishes the default-lane / opt-in boundary that other Quality docs assume.

## Status / caveats
Dated point-in-time manual test spec (2026-05-05); it documents expected commands and outcomes rather than an embedded historical run log. Treat as a repeatable procedure, not a one-time proof.
