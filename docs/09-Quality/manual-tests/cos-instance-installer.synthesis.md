---
type: quality-synthesis
source: docs/09-Quality/manual-tests/cos-instance-installer.md
provenance: "Manual test validating the dedicated operational SO-instance installer (scripts/cos-instance-init), distinct from the consumer-project projector scripts/cos_init.py."
---

## What it is
A manual test procedure for `scripts/cos-instance-init`, the installer that provisions operational Cognitive OS **instances** (e.g. `local`, `docker-headless`, `host-cli-bridge` profiles) — a different concern from `scripts/cos_init.py`, which projects Cognitive OS *into consumer projects*.

## Key mechanics
- Contract tests: `python3 -m pytest tests/contracts/test_cos_instance_profiles.py -q`.
- Dry-run proofs per profile: `scripts/cos-instance-init --profile local --dry-run --json` (no provider credentials written) and `--profile docker-headless --dry-run --json` (references `docker/cos-worker/docker-compose.yml` and `scripts/cos-headless-service-drill`).
- Write proof: run against a disposable workspace (`git archive HEAD | tar -x`) with `--write --json` for both `local` and `docker-headless` profiles; expects files at `.cognitive-os/instances/{profile}/commands.md` and `.cognitive-os/instances/{profile}/instance.json`.
- Guard rail: `--profile host-cli-bridge --write --json` must report `status: write-blocked` — planned-but-not-implemented profiles are write-blocked by design, not silently accepted.
- Optional Docker smoke: `scripts/cos-headless-service-drill --json` expects `ok=true` when Docker and the worker image are available.

## Relations & where used
Distinguishes SO-instance provisioning (this test) from consumer-project projection (`consumer-project-primitive-accessibility.md`, `first-run-onboarding.md`, `five-minute-demo.md`). The `docker-headless` profile connects to `docker/cos-worker/docker-compose.yml`, also exercised by `engram-cloud-docker-sync.md`.

## Status / caveats
No provider API key or Docker required for the dry-run/write proof (Docker only needed for the separate smoke step). Procedural spec with no embedded dated execution evidence — treat expected outputs as the contract, not a captured run.
