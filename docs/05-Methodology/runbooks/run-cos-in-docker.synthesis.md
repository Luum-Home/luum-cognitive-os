---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/run-cos-in-docker.md
provenance: "Operator entry point for the ADR-140 cloud-worker container surface, letting anyone evaluate Cognitive OS, run it headless/CI, or produce a compliance-evaluable audit trail without installing anything onto a shell profile."
---

## What it is

Runbook for the containerized "cloud worker" surface of Cognitive OS — an alternative to laptop shell-profile installation, aimed at evaluation, headless/CI use, cross-OS portability, and compliance-evaluable audit surfaces (BYOK credentials, `audit_class`/`tenant_id` tagging per ADR-142). Explicitly not the path for daily Claude Code/Codex governance on a personal laptop (that's `getting-started.md`).

## Key mechanics

- Prerequisites: Docker ≥ 24, Docker Compose v2, a repo clone/worktree. Windows-native Docker without WSL2 is unsupported per ADR-140.
- Quick start: `bash scripts/cos-cloud-worker-bootstrap.sh self-test` builds the `luum-cognitive-os-worker:local` image, runs `--self-test`, exercises `hooks/git-commit-scope-guard.sh` inside the container, and writes audit-trail entries.
- Bootstrap subcommands: `config` (validate compose without starting), `self-test`, `up` (worker only), `up-full` (adds the `engram-cloud` Compose profile: postgres+pgvector plus the engram-cloud server), `down`, `path`.
- Credentials are caller-supplied per ADR-139 — the worker never reads the host shell environment implicitly; env vars documented include `COS_WORKSPACE`, `COGNITIVE_OS_SESSION_ID`, `LLM_PRIMARY_API_KEY`/`LLM_FALLBACK_API_KEY`, `ENGRAM_CLOUD_*` (port/db/user/password/insecure-no-auth/allowed-projects), `TENANT_ID`, `AUDIT_CLASS`, `CREDENTIAL_SOURCE`, `BILLING_IDENTITY`.
- Consumer mode: point `COS_WORKSPACE` at any external project directory so the worker runs configured hooks against it, bind-mounted at `/workspace`, without touching the host.
- `up-full` brings up engram-cloud (ADR-141) as a replication-only complement to the existing git-jsonl path — local SQLite remains authoritative, not replaced.
- ADR-142 compliance: every worker boot writes structured JSONL audit entries with five fields (`tenant_id`, `audit_class`, `credential_source`, `billing_identity`, `engram_project_scope`) written by construction, not by explicit application logging; seven `audit_class` values map to SOC 2/ISO 27001/GDPR controls.
- Container architecture: `docker/cos-worker/` holds a `python:3.11-slim`-based Dockerfile, a compose file with `cos-worker` (always) plus `cos-engram-proxy`/`cos-engram-cloud-db`/`cos-engram-cloud` (engram-cloud profile only), and a thin `entrypoint.sh`. ADR-140 deliberately chose Compose over shell-profile bootstrap magic for observability/reproducibility.
- Explicit non-goals: no Windows-native-without-WSL2 support, no auto credential pickup from the host shell profile, and this is not meant for daily IDE governance use.
- Troubleshooting covers missing `docker` binary, daemon connectivity, engram-cloud's lack of a `/healthz` endpoint (404 is itself evidence the server is up), and empty audit-trail files traced to a `COS_WORKSPACE` mismatch.

## Relations & where used

Ties together ADR-140 (containerized deployment), ADR-141 (engram-cloud replication), ADR-142 (compliance audit surface), ADR-139 (BYOK multi-provider runtime), ADR-137 (why the surface exists), `bootstrap-portability.md`, `cloud-worker-runtime-tooling-research-2026-05.md`, and two manual test docs (`headless-docker-service-runtime.md`, `engram-cloud-docker-sync.md`).

## Status / caveats

None found — this is a stable, versioned operator runbook rather than a point-in-time snapshot, though the example audit-trail JSON timestamp (`2026-05-05`) is illustrative sample data, not a live claim.
