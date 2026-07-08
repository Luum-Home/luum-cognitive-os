---
type: quality-synthesis
source: docs/09-Quality/manual-tests/headless-docker-service-runtime.md
provenance: "Manual proof drill establishing what is and is not proven about running Cognitive OS headless in Docker, including host vs container provider-auth boundaries, so headless claims stay evidence-backed."
---

## What it is
A manual test proving Cognitive OS can run in a service/headless lane (no IDE required), validating the Docker worker, local queue, lease, artifact, and communication boundary — while explicitly recording what remains unproven for host Codex/Claude account-backed execution inside containers. Complements, does not replace, IDE harness proof paths.

## Key mechanics
- Architecture under test: bug/ticket -> Cognitive OS Runtime -> Planner/Router -> Worker pod/EC2/Docker worker -> sandboxed checkout -> patch+tests -> quality gates -> PR/patch proposal, with a parallel memory/traces/metrics path.
- Preconditions: Docker daemon + `docker compose` running; no provider API key required for the default drill; uses a disposable `git archive HEAD` workspace under `/tmp` so dirty worktree changes aren't mounted.
- Default drill: `scripts/cos-headless-service-drill --json --keep-workspace` — expects worker `--self-test` pass, host auth probes without credential-store reads, container probes returning `unsupported`/`auth_required`/`ready`, and a completed local-command task with queue-drain confirmation.
- Optional pytest wrapper (`tests/integration/test_headless_service_drill.py`) skips by default; requires `COS_RUN_HEADLESS_SERVICE_DOCKER=1` to run the Docker lane.
- Optional cost-bearing provider smoke: `COS_RUN_PROVIDER_SMOKE=1` invokes the host Codex CLI through the service-control-plane adapter (only when `cos-auth-probe` reports `ready`); model must be pinned (e.g. `COS_CODEX_EXEC_MODEL=gpt-5.4`) if the CLI rejects the default model version.
- 2026-05-05 evidence: host auth probes for Codex/Claude return `ready` without reading credential stores; container probes return `unsupported` because the worker image intentionally does not mount host CLI binaries or token stores — this is correct behavior under the no-credential-scraping policy, not a bug.
- Completed local-command task writes artifacts (`task.json`, `lease.json`, `executor.json`, `result.json`, `redaction-report.json`, stdout/stderr logs) under `.cognitive-os/service/artifacts/task-headless-service-drill/<lease-id>/`.
- Host Codex provider smoke failed on the default model (`gpt-5.5` rejected by installed CLI) but passed with an explicit `gpt-5.4` override — demonstrates the model-pinning requirement is load-bearing, not cosmetic.
- Host Claude provider smoke is separate, cost-bearing, and requires manual opt-in via `scripts/cos-task-submit` + `scripts/cos-worker-run-once --allow-provider-call`; results are recorded via `scripts/proof-drill-evidence-record` as `claude-provider-host-smoke`, mapped by ACC to `proof_claim:host-claude-provider-adapter`.

## Relations & where used
Complements ADR-091/137/140 headless runtime work and the sibling `headless-runtime-proof-drills.md` P-series drills. Depends on `scripts/cos-auth-probe`, `scripts/cos-headless-service-drill`, `scripts/cos-task-submit`, `scripts/cos-worker-run-once`, `scripts/proof-drill-evidence-record`, and the ACC pipeline's `proof_claim` mapping. Uses `docker/cos-worker/docker-compose.yml`.

## Status / caveats
Point-in-time evidence snapshot dated 2026-05-05; results may drift as the worker image or CLI versions change. Explicitly lists "not proven": Codex/Claude provider execution inside the container, remote ingress, VM, Kubernetes, or a protected host-CLI bridge. The doc is self-disciplined about separating proven vs. proven-negative vs. not-proven claims — no inconsistency found.
