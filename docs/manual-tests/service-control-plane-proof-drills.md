# COS Service Control Plane Proof Drills

These are opt-in proof drills for the future `cosd` service control plane. They
must not run in normal unit/audit/contract lanes.

## Drill P0 — Contract inventory

Purpose: prove the repo declares the service boundary before implementing it.

```bash
test -f docs/architecture/service-control-plane-research-2026-05-04.md
test -f docs/architecture/service-control-plane-implementation-plan.md
test -f docs/manual-tests/service-control-plane-proof-drills.md
```

Expected result: all files exist and describe current-vs-future claims without
claiming a production daemon.

## Drill P1 — Local no-model queue

Purpose: prove `cosd` can admit and complete one task without provider
credentials.

Command shape:

```bash
scripts/cos-task-submit --kind local-command --command 'printf ok > result.txt'
scripts/cos-worker-run-once --executor local-command --json
scripts/cos-queue-drain --json
```

Expected evidence:

- one task admitted;
- one active lease;
- one completed result;
- artifact bundle with task, lease, result, and logs;
- no provider credentials required.

Current status: implemented as a local proof with JSONL queue, one-shot worker,
and filesystem artifact bundle.

## Drill P2 — Account-backed Codex CLI probe

Purpose: prove an official Codex CLI session can be used as an executor without
COS reading `~/.codex/auth.json`.

Preconditions:

- run only on a trusted host;
- operator has already authenticated `codex` or intentionally configured
  `CODEX_API_KEY`;
- no public/untrusted repository.

Future command shape:

```bash
scripts/cos-auth-probe --provider codex --mode account-session --json
scripts/cos-task-submit --kind provider --executor codex-cli --prompt 'summarize this temp repo'
scripts/cos-worker-run-once --executor codex-cli --json
```

Expected evidence:

- `auth_probe.status == "ready"` or `"auth_required"`;
- no token-like strings in logs;
- no direct read of `~/.codex/auth.json`;
- `cost_mode` is reported as `subscription_account`, `api_metered`, or
  `unknown` instead of being inferred silently;
- worker output is a proposal/artifact, not a merge.

## Drill P3 — Account-backed Claude Code probe

Purpose: prove an official Claude Code session can be used as an executor
without COS reading Claude credential stores.

Preconditions:

- run only on a trusted host;
- operator has authenticated `claude`, configured documented OAuth token, API
  key, or provider-cloud auth;
- no public/untrusted repository.

Future command shape:

```bash
scripts/cos-auth-probe --provider claude --mode account-session --json
scripts/cos-task-submit --kind provider --executor claude-cli --prompt 'summarize this temp repo'
scripts/cos-worker-run-once --executor claude-cli --json
```

Expected evidence:

- `auth_probe.status == "ready"` or `"auth_required"`;
- `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and OAuth tokens are not printed;
- no direct read of `~/.claude` or macOS Keychain;
- `cost_mode` is reported as `subscription_account`, `api_metered`,
  `provider_cloud_metered`, or `unknown` instead of being inferred silently;
- output remains propose-only.

## Drill P4 — Docker sidecar CLI proof

Purpose: prove a containerized official CLI path only when auth is explicit and
provider-supported.

Preconditions:

- run only on a trusted machine;
- use a temporary repository;
- authenticate inside the container or mount only provider-documented
  credential material;
- never copy opaque laptop credential folders into the image.

Future command shape:

```bash
docker compose -f docker/cos-worker/docker-compose.yml run --rm cos-worker \
  scripts/cos-auth-probe --provider codex --mode device-login --json
```

Expected evidence:

- status is `ready`, `auth_required`, or `unsupported`;
- the proof names the exact credential mode used;
- token-like strings are redacted from container logs;
- the artifact states whether the adapter is `host`, `container`, or `cloud`
  eligible.

## Drill P5 — Container auth-negative proof

Purpose: prove a container without explicit credentials fails safely.

Command shape:

```bash
docker compose -f docker/cos-worker/docker-compose.yml run --rm cos-worker \
  scripts/cos-auth-probe --provider codex --mode account-session --json
```

Expected evidence:

- status is `auth_required` or `unsupported`;
- no stack trace;
- no repeated retry storm;
- no host credential probing.

## Drill P6 — Crash/resume

Purpose: prove worker leases are safe.

Future command shape:

```bash
scripts/cos-task-submit --kind local-command --command 'sleep 60; printf ok > result.txt'
scripts/cos-worker-run-once --executor local-command --json &
kill -9 "$!"
scripts/cos-queue-drain --json
scripts/cos-worker-run-once --executor local-command --json
```

Expected evidence:

- first lease becomes stale;
- task is requeued or marked `needs_human`;
- second worker cannot publish under the expired lease;
- artifact bundle explains the transition.

## Drill P7 — Provider lab promotion

Purpose: promote Kimi, MiniMax, DeepSeek, or another provider from lab only
after a documented auth/output contract.

Required evidence:

- provider docs or official CLI/API contract linked;
- `cos-auth-probe` status mapping implemented;
- no credential scraping;
- missing auth returns `auth_required`;
- one no-op/summarization task produces redacted artifacts;
- provider remains in lab until the drill passes.
