# ADR-048 — Docker Container Image Freshness

## Status

**Accepted** — 2026-04-21. Follow-up to a live incident the same day.

## Relationship to ADR-018 and local-daemon ADRs

ADR-048 does not make Docker mandatory again. It governs the freshness and recreation contract for any Docker containers that remain as optional, fallback, CI, or reference surfaces after ADR-018 and the local-daemon decisions in ADR-042, ADR-043 (deprecated 2026-05-05 — see ADR-171), and ADR-045. If a service has a healthy local-daemon path, that path is preferred for developer-default usage; if Docker is used, ADR-048 prevents stale pinned-image drift.

## Context

### The incident

On 2026-04-21 the `cognitive-os-langfuse-worker` container was in a crash
loop, restarting every 16 seconds with:

```
[dumb-init] ./worker/entrypoint.sh: No such file or directory
```

Inspection revealed:

- `docker-compose.cognitive-os.yml` pinned the worker to
  `langfuse/langfuse-worker:3@sha256:0e7a6d86…` (new, correct)
- The running container was created from an older image sha
  (`sha256:50674bb0…`) whose entrypoint (`./worker/entrypoint.sh`) had
  been removed upstream. The new image uses `node worker/dist/index.js`
  directly, no shell entrypoint.

Root cause: **updating the `@sha256:` pin in compose does NOT recreate
running containers**. Docker's `restart: unless-stopped` policy spawns new
containers using the same (old) image — it does not pull the new pinned
digest. Only `docker compose up -d --force-recreate` (optionally preceded
by `pull`) actually rolls the containers forward.

### The meta-incident

While building the validator to detect this drift, the first implementation
compared `{{.Image}}` (container's **image config ID**) against the pin's
`@sha256:…` (**manifest digest**). These are **two different hash schemes**
of the same image:

- Manifest digest — hash of the image manifest JSON (what the registry
  stores and what `@sha256:` references)
- Image config ID — hash of the image config blob (what `docker inspect`
  returns for `.Image`)

Every running container was flagged as stale until the bug was caught. This
is exactly the class of error that `rules/decision-depth-gate.md` (written
the same session) was designed to prevent: "before declaring two values
inconsistent, verify they're not the same thing in different encodings."
I violated my own rule.

## Decision

Introduce a **3-layer defense + automated prevention** pattern for Docker
image freshness, mirroring the pattern already used for
`meta.settings_freshness` (apply-efficiency-profile.sh SHA tracking).

### Layer 1 — Validator contract

`scripts/cos-config-audit.sh` gains a new meta-contract
`meta.docker_container_freshness`. It:

- Parses `@sha256:` digests from `docker-compose.cognitive-os.yml`
- For each running `cognitive-os-*` container, inspects `Config.Image`
  (which preserves the creation-time pin including digest)
- Compares the pinned digest string against `Config.Image`
- Reports IMPL when all match, ASPIR with fix hint otherwise

**Critical implementation detail**: the comparison uses `Config.Image`, NOT
`.Image`. The former contains the literal pin reference; the latter
contains the image config ID and would always mismatch.

### Layer 2 — SessionStart advisory hook

`hooks/docker-drift-detector.sh` runs on SessionStart:

- Fast (<200 ms typical), graceful-degrade
- Silent exit 0 when compose/docker/daemon absent
- Emits one-line WARNING to stderr on drift so the agent sees it in
  startup context
- Never auto-recreates (recreation has blast radius — can sever in-flight
  connections)
- Logs structured JSONL to `.cognitive-os/metrics/docker-drift.jsonl`

### Layer 3 — Gotcha documentation

`templates/project-gotchas.md` gains an explicit entry on docker-compose
pin updates. Sub-agents editing the compose file receive this context via
the existing injector.

### Layer 4 — Auto-prevention in cos-update.sh

`recreate_docker_if_compose_changed()` is added to `scripts/cos-update.sh`,
mirroring the existing `regenerate_settings_if_profile_changed()` pattern:

- Tracks SHA-256 of `docker-compose.cognitive-os.yml` at
  `.cognitive-os/state/docker-compose.sha`
- On update: if the compose changed (or `--force`), runs
  `docker compose pull` then `docker compose up -d --force-recreate --no-build`
- Failure of either step is non-fatal (WARN + continue); the SHA cache is
  NOT updated so the next run retries
- Dry-run mode short-circuits with a note

This closes the drift for downstream projects: whenever `cos-update` runs
and compose has moved forward (pin bump, service addition), containers
are rolled automatically. No more silent drift accumulation.

### `--no-build` rationale

The compose file includes some services built from local Dockerfiles
(e.g. `nemo-guardrails`). A transient build failure in one service
(e.g. pip install error) would otherwise abort the entire recreate. Using
`--no-build` ensures pulled image updates land even when local builds are
broken — a deliberate availability trade-off. Users who need a rebuild
run `docker compose build` manually.

## Consequences

### Positive

- **Drift detected automatically**: CI cron semanal + SessionStart +
  on-demand `cos-config-audit` all catch container staleness.
- **Drift fixed automatically downstream**: cos-update auto-recreates
  when compose moves forward. No manual intervention required.
- **Pattern generalized**: same `track SHA + detect change + auto-apply`
  shape now used in 3 places (settings.json, docker containers, Python
  deps via uv sync). New meta-contracts can follow the template.
- **Invariant test locked in**: regression test in
  `tests/unit/test_docker_drift_detector.py::test_validator_distinguishes_manifest_digest_from_image_id`
  will catch the exact bug again.

### Negative

- **`--force-recreate` blast radius**: rolling a container severs open
  connections (HTTP streams, websocket subscriptions). Acceptable for
  dev environments; production deployments using cos-update should be
  paused during the update window.
- **Build failures still abort partial stacks**: if a local build breaks
  (like the nemo-guardrails pip failure observed on 2026-04-21), the
  `--no-build` flag prevents abort but users may not realize their
  broken service is being skipped.
- **Manifest digest vs image ID is a subtle trap**: any future validator
  comparing docker hashes must read this ADR first. The distinction is
  not obvious from Docker's CLI output alone.

### Neutral

- SHA files (`.cognitive-os/state/*.sha`) are gitignored — per-install
  state. Fresh clones start at PARTIAL until first `cos-update` runs.

## Rollout

1. ✅ Layer 1 validator contract — commit `d44a904`
2. ✅ Layer 2 SessionStart hook — commit `d44a904`
3. ✅ Layer 3 gotcha doc — commit `d44a904`
4. ✅ Validator bug fix (manifest digest vs image ID) — this ADR's session
5. ✅ Layer 4 cos-update auto-recreate — this ADR's session
6. ✅ Invariant test — this ADR's session

## Related

- `rules/decision-depth-gate.md` — meta-rule that should have prevented
  the validator bug (I wrote it in the same session and violated it).
- `scripts/cos-update.sh::regenerate_settings_if_profile_changed` — the
  pattern this decision generalizes.
- ADR-042 — Valkey local daemon (separate docker-exit story).
- `meta.settings_freshness` contract — sibling meta-contract.

## Verification

```bash
# Detect drift now
python3 scripts/cos-config-audit.sh | grep docker_container_freshness

# Simulate the auto-fix path
bash scripts/cos-update.sh --dry-run | grep docker-compose

# Tests
python3 -m pytest tests/unit/test_docker_drift_detector.py -v
```

## Appendix — What I would have caught with decision-depth-gate

Per `rules/decision-depth-gate.md`, resolving an inconsistency between two
values requires Q1-Q4 analysis. Retrospective:

- **Q1 — Relationship**: `{{.Image}}` vs `{{.Config.Image}}` vs the pin
  `@sha256:…` — are they the same thing? ANSWER (correctly applied would
  have been): no, they're two hash schemes; relationship = "encoding of
  the same object." I did not ask this question before writing the first
  validator.
- **Q2 — Coherence**: pick an actual image, show its manifest digest vs
  config ID. ANSWER: they differ by construction. Comparing them directly
  always mismatches.
- **Q3 — Resolution menu**: use the field that preserves the pin verbatim
  (`Config.Image`). Done.
- **Q4 — Forbidden shortcut**: don't "clarify with a note" — fix the
  comparison. Done.

Added as an example in the gate doc's "cases caught" section.
