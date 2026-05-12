# Surface 5 TUI and Secure cosd Roadmap

## Purpose

Define the next implementation shape for two optional-but-natural standalone
extensions:

1. a real Bubble Tea Surface 5 operator TUI; and
2. secure remote-capable `cosd` access beyond the local file queue / local-only
   API slice.

This roadmap answers the open questions from existing Cognitive OS features
rather than inventing a new product surface. It should be read with:

- [ADR-161: Remote Control Plane and Provider Adapter Boundary](../adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md)
- [ADR-189: Surface Implementation Coverage for Agentic Primitives](../adrs/ADR-189-harness-implementation-coverage.md)
- [ADR-190: Harness Action Receipts and VCS Event Telemetry](../adrs/ADR-190-harness-action-receipts.md)
- [ADR-192: Surface 5 Bubble Tea Adoption](../adrs/ADR-192-surface-5-adopt-bubbletea.md)
- [ADR-193: cosd Local Network API](../adrs/ADR-193-cosd-local-network-api.md)
- [ADR-194: cosd Secure Remote API Guardrails](../adrs/ADR-194-cosd-secure-remote-api.md)
- [ADR-195: Surface 5 Operable TUI Contract](../adrs/ADR-195-surface-5-operable-tui-contract.md)
- [COS Service Runtime Boundary](cos-service-runtime-boundary.md)
- [COS Service Control Plane Implementation Plan](service-control-plane-implementation-plan.md)
- [Agent Message Bus](agent-message-bus.md)
- [Boring Reliability Control Plane](boring-reliability-control-plane.md)
- [Standalone Ship Readiness — 2026-05-06](standalone-ship-readiness-2026-05-06.md)

## Self-answer from repository features

The TUI and secure `cosd` should not start as a generic dashboard. Cognitive OS
already has enough concrete feature surfaces to define the first useful product.

| Existing COS feature | Current command/artifact | TUI value | Secure `cosd` value |
|---|---|---|---|
| Standalone ship readiness | `docs/04-Concepts/architecture/standalone-ship-readiness-2026-05-06.md`, `.goreleaser.yaml`, `scripts/install-goreleaser.sh` | Show release readiness and exact missing external steps. | None initially; release remains operator/local. |
| Runtime/status health | `scripts/cos-status.sh --json` | Overview tab: profile, harness, hooks, skills, rules, health. | Read-only `/status` can expose daemon-side health. |
| ACC / primitive coverage | `scripts/cos-coverage --json --refresh`, `docs/06-Daily/reports/primitive-harness-coverage-latest.json` | Coverage tab: gaps, partials, surface counts, stale cache. | Optional read endpoint later; not a write path. |
| Boring reliability | `scripts/cos-boring-reliability --json` | Reliability tab: false positives, WIP safety, runtime reality, preamble budget. | Optional read endpoint later. |
| Harness action receipts | `scripts/cos-action-receipt stats/report`, `.cognitive-os/metrics/vcs-actions.jsonl` | Receipts tab with trust labels: advisory/observed/verified/authoritative. | Write/audit semantics should reuse receipt trust vocabulary. |
| `cosd` ADR arbiter | `scripts/cosd status`, `serve`, `serve-unix`, `.cognitive-os/cosd/*` | Daemon tab: queue depth, last arbitrations, submit/process actions. | Core API: health/status/submit/process plus auth/audit for remote writes. |
| Service control plane | `scripts/cos-task-submit`, `scripts/cos-worker-run-once` | Tasks tab: local-command/provider task queue, leases, results. | Future API expansion after auth: task submit/claim/result. |
| Headless safe mode | `scripts/cos-headless-safe-mode status --json` | Admission tab: safe-mode state and explicit enable/disable action. | Remote write requires auth and audit. |
| Headless pipeline | `scripts/cos-headless-pipeline --json` | Proof tab: run/observe local standalone proof ladder. | Local only at first; remote trigger requires token and audit. |
| Agent message bus | `scripts/cos_agent_message.py inbox/check/ack --json` | Inbox tab: blocking findings, questions, ack/reject action. | Future endpoint for directed messages; auth required for ack/write. |
| Validation capsule | `scripts/cos-validation-status.sh --json` | Locks tab: active validation lock health, stale diagnosis. | Read-only first; break actions stay local/operator-only initially. |
| Worktree/WIP safety | `scripts/cos-worktree-triage.sh --json`, `scripts/cos-wip-safety-score` | WIP tab: dirty state, risky worktrees, cleanup checklist. | Do not expose destructive cleanup remotely in v1. |

This mapping implies the first TUI should be an **operator console for existing
local evidence**. It should not introduce a parallel database, scheduler, or
permission model.

## Surface 5 functional TUI scope

### Product target

The first real TUI should answer one operator question:

> Can I see, from one terminal surface, whether Cognitive OS is ready, healthy,
> blocked, or waiting for my action?

### Initial tabs

| Tab | Data source | First-state semantics | Allowed actions in v1 |
|---|---|---|---|
| Overview | `cos-status --json`, standalone readiness doc metadata | Read-only summary. | Refresh. |
| Release | `.goreleaser.yaml`, GoReleaser smoke metadata if present, readiness doc | Read-only release readiness. | Run `scripts/install-goreleaser.sh --check` only. |
| cosd | `scripts/cosd status --json` or local Unix socket `/status` | Show daemon running/stopped, queue depth, last arbitrations. | `process-once`; submit ADR intent only behind explicit form/confirm. |
| Coverage | `scripts/cos-coverage --json`, primitive coverage reports | Show gaps/partials/stale cache. | Refresh coverage. |
| Reliability | `scripts/cos-boring-reliability --json` | Show fail/warn/pass cells. | Refresh only. |
| Receipts | `scripts/cos-action-receipt stats` | Show action counts by trust/action/source. | Generate report. |
| Headless | `scripts/cos-headless-safe-mode status --json`, `scripts/cos-headless-pipeline --json` | Show admission and proof pipeline readiness. | Run pipeline only with confirmation. |
| Inbox | `scripts/cos_agent_message.py inbox/check --json` | Show blocking/unacked messages. | Acknowledge selected message with confirmation. |

### Non-goals for first TUI

- Do not replace existing CLI commands.
- Do not mutate git state.
- Do not run provider/model calls.
- Do not expose secret values or credential store paths.
- Do not claim hook execution parity; Surface 5 is a UI surface under ADR-189.

### Accepted command contract

```bash
cos tui                         # Bubble Tea interactive TUI
cos tui --snapshot              # deterministic non-interactive summary
cos tui --project-dir /path/to/project
```

The accepted ADR-195 MVP is read-only. Future forms such as `cos tui --operate
refresh-all --confirm` or `cos tui --cosd unix:///tmp/cosd.sock` require the
confirmation and receipt gate from ADR-195 before they become supported
contracts.

Compatibility rule: `scripts/cos-tui` remains as a shim until the Go TUI reaches
feature parity for snapshot and whitelisted operations.

### Implementation slices

1. **Read model layer** — implemented for the ADR-195 MVP.
   - `cmd/cos/internal/tui/app.go` reads release evidence, `cosd` queue state,
     primitive coverage summaries, and TUI receipt counts from existing files.
   - Readers use existing JSON artifacts/runtime paths; no new database.

2. **Bubble Tea shell** — implemented for the ADR-195 MVP.
   - `cos tui` renders Overview, cosd, Coverage, Release, and Receipts tabs.
   - `cos tui --snapshot` provides deterministic smoke-test output.
   - Mutating actions stay disabled until a whitelist entry exists.

3. **Action receipts**
   - Every TUI action emits `surface_kind=ui`, `surface_id=tui`, `mode=operable`
     receipts or reuses existing `tui-actions.jsonl` semantics.

4. **Operable actions**
   - Port current `scripts/cos-tui` operations first: refresh coverage,
     refresh partials, refresh all.
   - Add `cosd process-once` and inbox ack only after confirmation UX exists.

### Acceptance criteria

```text
ACCEPTANCE CRITERIA:
1. `cos tui --snapshot` works outside a Git checkout using `scripts/cos-root` precedence.
2. The Go TUI has at least Overview, cosd, Coverage, Release, and Receipts tabs.
3. All mutating actions require explicit confirmation and emit an action receipt.
4. Tests cover model updates, render snapshots, failed data-source handling, and no mutation without confirmation.
5. `scripts/cos-tui` remains compatible or delegates to the Go implementation.
```

## Secure cosd remote scope

### Current baseline

ADR-193 implemented local API transports:

```bash
bash scripts/cosd --project-dir /path/to/project serve --host 127.0.0.1 --port 8765
bash scripts/cosd --project-dir /path/to/project serve-unix --socket /tmp/cosd.sock
```

Both expose:

- `GET /healthz`
- `GET /status`
- `POST /submit-intent`
- `POST /process-once`

This is a local control-plane adapter over the file queue. It is not yet a safe
remote service.

### Threat model from existing COS doctrine

The remote boundary should follow ADR-161 and the service-control-plane plan:

- remote/chat/web ingress is untrusted;
- no remote input may directly run scripts/hooks;
- all work must pass queue, lease, allowlist, redaction, and audit gates;
- account-backed CLIs are black boxes and credentials must not be scraped;
- direct writes require proof/audit and operator intent.

### Secure API policy

| Policy | Decision |
|---|---|
| Default bind | `127.0.0.1` only. |
| Unix socket | Allowed for local operation; filesystem permissions still matter. |
| Non-local bind | Refuse unless `--allow-remote` and auth are configured. |
| Auth | Bearer token via `--token-file` or `COSD_API_TOKEN_FILE`; token never printed. |
| Token generation | `scripts/cosd token-create` or separate helper can write `0600` token files. |
| Read scope | `/healthz` can stay unauthenticated on localhost; `/status` requires auth when remote. |
| Write scope | `/submit-intent`, `/process-once`, future task actions always require auth when auth is enabled or bind is remote. |
| TLS | Do not implement custom TLS first; document reverse-proxy/TLS termination for remote. |
| Audit | Every write request appends `.cognitive-os/cosd/api-audit.jsonl`. |
| Redaction | Authorization header, token file path contents, provider prompts, and stderr tails are redacted. |

### Proposed flags

```bash
scripts/cosd serve \
  --host 127.0.0.1 \
  --port 8765 \
  --token-file .cognitive-os/runtime/cosd.token

scripts/cosd serve \
  --host 0.0.0.0 \
  --port 8765 \
  --allow-remote \
  --token-file .cognitive-os/runtime/cosd.token
```

### Proposed endpoint authorization

| Method | Path | Local no-auth | Remote/auth mode |
|---|---|---:|---:|
| `GET` | `/healthz` | allowed | allowed |
| `GET` | `/status` | allowed | bearer required |
| `POST` | `/submit-intent` | allowed for localhost v1, bearer preferred | bearer required |
| `POST` | `/process-once` | allowed for localhost v1, bearer preferred | bearer required |
| `POST` | future `/tasks/submit` | bearer required | bearer required |
| `POST` | future `/messages/ack` | bearer required | bearer required |

### Future API expansion order

Do not add every CLI command to `cosd`. Expand by safety tier:

1. **Read-only**: status, queue depth, last arbitrations, safe-mode state,
   coverage summary pointers.
2. **Bounded writes**: submit ADR intent, process-once, message ack.
3. **Task queue**: submit local-command task, claim/run once, result read.
4. **Provider tasks**: only after provider adapter auth probes and redaction are
   integrated.
5. **Never v1**: direct protected-branch push, destructive cleanup, raw shell
   execution from remote input.

### Acceptance criteria

```text
ACCEPTANCE CRITERIA:
1. `scripts/cosd serve --host 0.0.0.0` refuses to start unless `--allow-remote` and token auth are configured.
2. Wrong/missing bearer token returns 401 for protected endpoints.
3. Correct bearer token allows protected write endpoints.
4. Tokens are never printed in logs, responses, audit rows, or test failures.
5. Write requests append `.cognitive-os/cosd/api-audit.jsonl` with actor, endpoint, transport, status, and redacted metadata.
6. Tests cover localhost, Unix socket, remote bind refusal, wrong token, correct token, and audit emission.
```

## Recommended implementation order

1. **Secure `cosd` auth/remote guard**
   - It is the narrower safety-critical slice.
   - It gives the future TUI a safe local/remote contract to consume.

2. **TUI read-only MVP** — accepted and implemented by ADR-195.
   - Built against existing JSON artifacts and runtime files.
   - No new mutation paths.

3. **TUI operable actions**
   - Add actions only after confirmation + receipts are proven.

4. **Task-control-plane API expansion**
   - Add task endpoints after secure auth and audit are stable.

## Proposed ADR sequence

- `ADR-194-cosd-secure-remote-api.md` — accepted and implemented for bearer-token auth, remote-bind refusal, and API audit rows.
- `ADR-195-surface-5-operable-tui-contract.md` — accepted and implemented for the read-only Surface 5 MVP.

This order put the security boundary ahead of the UI that may consume it. The
remaining Surface 5 work is operable actions with confirmation and receipts.
