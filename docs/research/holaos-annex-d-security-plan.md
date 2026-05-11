---
title: "Annex D — Security, Runtime Plan, and Context Bootstrap"
date: 2026-05-10
author: research-agent (annex-d)
parent: holaos-comparison-2026-05-10.md
status: draft
source-repo: "/tmp/holaOS-investigation"
license-classification: "BSL-like — patterns only, clean-room"
scope: ["grant-signing", "workspace-runtime-plan", "proactive-context"]
---

# Annex D — Security, Runtime Plan, and Context Bootstrap

This annex performs a code-to-code comparison of three holaOS features against
the equivalent surface in `luum-agent-os`. The features were selected from the
top-10 prioritisation in the parent comparison because they target the highest
unaddressed risk and capability gaps:

1. **Grant signing (HMAC + nonce + TTL)** — replaces a simple bearer on `cosd`.
2. **Workspace runtime plan (compiled, checksummed)** — replaces ad-hoc YAML reads.
3. **Proactive context bootstrap** — strengthens SessionStart with a structured snapshot.

All citations are `path:line` against `/tmp/holaOS-investigation`. holaOS code is
**read for pattern extraction only**. Adoption plans are clean-room: rewrite in
Python/bash idioms, no strings copied, no derivative file structure.

---

## 1. Grant signing — HMAC vs bearer token

### 1.1 holaOS surface

`runtime/api-server/src/grant-signing.ts:1-48` is a 48-line module that issues
short-lived signed grants used to authorise broker calls. Highlights:

- **Material**: 32 random bytes generated lazily in-process, kept in a
  module-scoped `signingKey` (line 5-12). The key is **per-process**, not
  persisted — every server restart rotates it (intentional, since grants are
  short-lived).
- **Payload**: `grant:${workspaceId}:${appId}:${timestamp}:${nonce}` where
  `timestamp` is base-36 `Date.now()` and `nonce` is `randomUUID()` (line 14-19).
- **Signature**: `HMAC-SHA256` over the payload, base64url, appended (line 18).
- **Validation** (line 29-48):
  - Structural parse (must start with `grant:`, ≥6 colon-separated parts).
  - Recompute HMAC; reject on mismatch (`receivedSignature !== expectedSignature`).
  - Parse `timestamp`; reject if older than `GRANT_TTL_MS = 24h` (line 3, 45).
  - Returns `{ workspaceId, appId, timestamp, nonce }` on success, `null` on
    any failure.

The grant is **scope-bound** (workspaceId + appId baked into the signed payload)
so an attacker cannot move a leaked grant across workspaces or apps.

### 1.2 holaOS consumer

`runtime/api-server/src/integration-broker.ts:76-152` shows how grants gate
OAuth token resolution:

```
const validated = validateSignedGrant(params.grant);     // line 80
const parsed = validated
  ? { workspaceId: validated.workspaceId, appId: validated.appId, nonce: validated.nonce }
  : parseAppGrant(params.grant);                          // line 81-83 fallback (unsigned legacy)
if (!parsed) throw new BrokerError("grant_invalid", 401, "app grant is malformed");
```

The broker then looks up an `IntegrationBinding` keyed by `(workspaceId,
targetType="app", targetId=appId, integrationKey=provider)` (line 93-105),
falling back to the workspace-default binding. So the grant carries the
**authorisation subject**, but the actual capability is resolved against
server-side state — the grant only proves "this caller is allowed to ask".

`oauth-service.ts:1-129` is independent: it runs a PKCE flow against a real
OAuth provider, persists tokens via `RuntimeStateStore.upsertIntegrationConnection`,
and never touches the grant module. The grant guards subsequent **token
retrieval**, not the OAuth handshake itself.

### 1.3 luum surface

luum has `cosd` (the local control-plane daemon), authenticated by a bearer
token loaded from `COSD_API_TOKEN_FILE`:

- `scripts/cos_daemon.py:141-158` `load_api_token` reads the file once,
  `bearer_authorized` uses `hmac.compare_digest` for constant-time comparison.
- `scripts/cos_daemon.py:161-178` `remote_policy_guard` enforces "no remote
  bind without `--allow-remote` AND token".
- `scripts/cos_daemon.py:180-210` handler returns 401 on missing/invalid
  `Authorization: Bearer …`.
- `lib/cosd_auth_guard.py` is a pre-flight hook primitive that blocks Bash
  invocations binding `cosd` to non-local hosts without both `--allow-remote`
  and a token file, AND blocks edits to protected control-plane files
  (`scripts/cosd`, `scripts/cos_daemon.py`, `infra/cosd/**`, the two ADRs)
  unless `COS_ALLOW_COSD_AUTH_CONFIG_WRITE=1`.
- `rules/cosd-secure-api.md` and `docs/adrs/ADR-194-cosd-secure-remote-api.md`
  codify the policy.

**Critical delta**: luum has **one long-lived shared secret** (the token file).
There is no per-request signature, no nonce, no embedded TTL, no scope binding.
If the token file leaks, every endpoint is compromised until the operator
rotates and redeploys.

### 1.4 Delta table

| Property                | holaOS grant                       | luum cosd bearer                |
|-------------------------|------------------------------------|---------------------------------|
| Cryptography            | HMAC-SHA256, per-process key       | Constant-time string compare    |
| Lifetime                | 24h hard TTL in payload            | Until token file rotates        |
| Replay resistance       | `nonce` (uuid v4) — but **not stored**, so replay is technically possible within TTL until the consumer dedupes | None (any request with valid token replays trivially) |
| Scope binding           | `workspaceId` + `appId` in payload | None (token is omnipotent)      |
| Issuer revocation       | Process restart rotates key        | Manual file rotation            |
| Server-side state       | None (stateless validation)        | None                            |
| Audit                   | Caller-side (broker logs)          | `.cognitive-os/cosd/api-audit.jsonl` per write (ADR-194) |
| Attack surface          | Per-grant, time-bound              | Single token, infinite blast radius |

### 1.5 Threat model — HMAC grant vs bearer

What HMAC + nonce + TTL **mitigates** that the current bearer does not:

1. **Time-bound capability**: a leaked grant expires in 24h (or whatever TTL is
   configured) without operator action. luum's bearer is valid until file
   rotation, which in practice is "never" in dev environments.
2. **Scope confinement**: a grant for workspace A app X cannot be replayed
   against workspace B app Y. luum's bearer is omnipotent across endpoints
   and projects on the same daemon.
3. **Replay window narrowing**: combined with a nonce-dedup table on the
   server (holaOS does not currently dedupe nonces — gap), an intercepted
   grant can be made one-shot. A bearer is replayable for as long as it lives.
4. **Process-restart rotation**: holaOS's per-process key means that a memory
   disclosure attack on the API server (e.g. a heap dump) only leaks the
   signing key until next restart. luum's token file persists across restarts.
5. **Audit granularity**: each grant carries an identifying nonce → audit
   rows can correlate "this grant was used N times" rather than only "this
   token authorised N requests".

What HMAC does **not** address that bearer also does not:

- TLS / transport encryption (still requires reverse proxy per ADR-194 §7).
- Token/grant **distribution** (still leaks if the client stores it badly).
- Issuance authorisation (anyone who can call `createSignedGrant` can mint).

### 1.6 Clean-room adoption plan

**Priority: P0 — most urgent of the three features.** `cosd` is already
exposed under operator control (ADR-193/194). The remote-bind guardrails are
in place but the auth model is one shared static secret. Once any team
operates `cosd` across machines (the ADR-194 §7 reverse-proxy scenario), the
attack surface is exactly the same as a long-lived API key on a public host.

Files to create:

- `lib/cosd_grant.py` — `mint_grant(scope: dict, ttl_s: int) -> str` and
  `validate_grant(token: str, expected_scope: dict | None = None) -> Grant`.
  Stdlib only: `hmac`, `hashlib`, `secrets`, `time`. Payload format
  `v1:b64url(json(scope|iat|nonce)):b64url(sig)` (different from holaOS to
  avoid string-level derivation; also more extensible because scope is
  arbitrary JSON, not positional).
- `lib/cosd_grant_store.py` — optional nonce-dedup table (sqlite, TTL
  cleanup), addressing the replay gap that holaOS leaves open.
- `infra/cosd/grant-key.example` — keying material strategy doc (env file
  path, rotation policy, recovery procedure).

Files to modify:

- `scripts/cos_daemon.py` — add `--grant-key-file` next to `--token-file`,
  accept `Authorization: Grant <token>` in addition to bearer for a
  transition period, prefer grants when both are supplied.
- `rules/cosd-secure-api.md` — describe grant flow alongside bearer, mark
  bearer as deprecated for remote binds.
- `docs/adrs/` — new `ADR-XXX-cosd-grant-signing.md` capturing the rationale,
  the deprecation timeline, and the operator runbook.

**Effort**: ~2-3 days clean-room implementation + tests. Approx 250 LOC
production + 400 LOC tests. No external dependencies. Compatible with
existing `cosd_auth_guard` (the guard primitive's policy strings need a
small extension for the new flag).

---

## 2. Workspace runtime plan — compiled vs ad-hoc YAML

### 2.1 holaOS surface

`runtime/api-server/src/workspace-runtime-plan.ts` is 1,060 lines. It takes
`workspace.yaml` plus a map of referenced files and produces a
`CompiledWorkspaceRuntimePlan` (line 105-117):

```
{
  workspace_id, mode: "single",
  general_config, schema_aliases, resolved_prompts,
  resolved_mcp_servers, resolved_mcp_tool_refs, workspace_mcp_catalog,
  resolved_applications, mcp_tool_allowlist,
  config_checksum: sha256(workspace_yaml)   // line 984
}
```

Key properties:

- **Single-pass compilation**: `compileWorkspaceRuntimePlan` (line 970) is
  pure — no I/O. Inputs: yaml string + references map. Outputs: typed plan.
- **Deterministic checksum**: SHA-256 over the input yaml (line 984). Any
  byte change invalidates downstream caches.
- **Reference safety**: `runner-prep.ts:40-57` (`assertSafeRelativePath` +
  `readWorkspaceReference`) refuses paths that escape the workspace root
  via `..` or absolute roots. Defends against path-traversal during plan
  compilation.
- **MCP server identity rewriting**: `runner-prep.ts:82-107`
  (`workspaceMcpPhysicalServerId`, `mcpServerIdMap`) maps logical
  workspace-MCP server IDs to a sandbox-scoped physical ID derived from
  `sha256(sandboxId:workspaceId)`. Lets the runtime co-locate many
  workspaces on one host without server-ID collisions.
- **Catalog fingerprint**: `runner-prep.ts:138-152`
  (`workspaceMcpCatalogFingerprint`) hashes the tool catalog separately so
  sidecar restarts trigger only when the catalog changes, not when other
  parts of the plan churn.
- **Env-placeholder resolution**: `runner-prep.ts:113-136`
  (`resolveEnvPlaceholders`) expands only the strict pattern
  `{env:NAME}` — anything else passes through literally, malformed
  placeholders error out instead of silently leaving them as strings.

`apply-app-schema.ts:1-50` (header) describes a related primitive: declarative
SQL schemas with versioned, idempotent application, ADOPT/FRESH/UPGRADE state
machine, and a refusal to auto-apply destructive changes. Not strictly part
of the plan compiler but it's the same family of "declarative spec → typed
runtime artifact" approach.

### 2.2 luum surface

luum loads `cognitive-os.yaml` lazily on every callsite. The canonical
reader is `lib/config_loader.py` (204 lines):

- Variant 1: `read_top_level_int(key, default)` — regex line-scan, no PyYAML.
- Variant 2: `load_structured()` — full `yaml.safe_load`.
- Variant 3: `find_config_path()` — candidate-path locator.

The reader is robust and well-characterised (`test_cos_yaml_readers.py`),
but it is **a reader, not a compiler**. There is no:

- typed plan object,
- resolved MCP server / tool / application list,
- checksum that invalidates downstream caches,
- reference-resolution step that pulls in prompts, schemas, AGENTS.md, etc.,
- safe-relative-path enforcement on referenced files,
- env-placeholder pass.

Each callsite re-parses the YAML and re-resolves whatever fragments it
needs. Discovered callsites that read `cognitive-os.yaml`: `lib/dispatch.py`,
`lib/claude_executor.py`, `lib/release_analyzer.py`, `lib/singularity.py`,
`lib/context_diet.py`, `lib/queue_drainer.py`, `lib/rate_limiter.py`,
`lib/context_budget.py`, `lib/prompt_builder.py`, `lib/smart_infra.py`,
plus ~10 more. Each is an independent failure mode if the YAML schema drifts.

### 2.3 Delta

| Concern                       | holaOS                                     | luum                              |
|-------------------------------|--------------------------------------------|-----------------------------------|
| Single source of truth        | Compiled plan, frozen                      | YAML re-parsed at each callsite   |
| Schema validation             | Typed (TS) + explicit error codes          | Implicit (whatever each caller does) |
| Checksum / cache key          | sha256(yaml) on the plan                   | None                              |
| Reference resolution          | Single pass, path-safety enforced          | None (callsites read files ad-hoc) |
| Env-placeholder expansion     | Strict `{env:NAME}` parser, errors loudly  | Caller-by-caller string formatting |
| Catalog fingerprint           | Separate hash → narrow invalidation        | N/A                               |
| Tests                         | `workspace-runtime-plan.test.ts` + `runner-prep.test.ts` | Per-caller, no plan-level invariant |

### 2.4 Clean-room adoption plan

**Priority: P1.** Less urgent than grant signing because it is a
maintainability and consistency issue, not an exploitable hole. But the
cost of *not* doing it grows as new callsites accrete (~20 today).

Files to create:

- `lib/cos_plan.py` — `CompiledCosPlan` dataclass (workspace/project id,
  resolved skills, hooks, agents, MCP entries, env contract, checksum).
  `compile_plan(yaml_str: str, references: dict[str, str]) -> CompiledCosPlan`.
  `compile_plan_from_disk(project_dir: Path) -> CompiledCosPlan` (wraps the
  pure function with the I/O + safe-path guard).
- `lib/cos_plan_paths.py` — `assert_safe_relative(rel: str) -> Path` matching
  holaOS's safety check but in Python idiom.
- `tests/unit/test_cos_plan.py` — invariants: same yaml → same checksum,
  reference traversal blocked, env placeholder errors.

Files to modify (incremental migration, not in one PR):

- `lib/config_loader.py` — keep variants 1/2/3 for backwards compatibility,
  add `compile()` that returns the plan; mark variant 2 as "prefer
  `cos_plan.compile_plan_from_disk()` when callers need nested access".
- Top consumers (`dispatch.py`, `claude_executor.py`, `prompt_builder.py`)
  one at a time, behind a feature flag.
- `cognitive-os.yaml` schema document — add a `schema_version` key so the
  compiler can refuse unknown majors instead of silently mis-parsing.

**Effort**: ~5 days for the compiler + tests; migration is a longer tail
(~2 weeks of small PRs, one consumer at a time, gated by a "no new direct
yaml reads" lint).

---

## 3. Proactive context bootstrap — captureWorkspaceContext vs SessionStart hook

### 3.1 holaOS surface

`runtime/api-server/src/proactive-context.ts` (321 lines) exposes
`captureWorkspaceContext({store, memoryService, workspaceId})` that returns,
in one structured payload:

- `workspace` — db record + holaboss user ID.
- `snapshot` — applications, MCP tool IDs, cronjob delivery channels,
  executable_capabilities (formatted as `app::X`, `tool::Y`, `cron::Z`).
- `runtime_signals` — file_count, total_size, extension_counts, file
  previews of key files (workspace.yaml, README.md, AGENTS.md,
  package.json — first 1000 bytes each, line 45-52 of `workspace-snapshot.ts`),
  git branch + dirty bit.
- `warnings` — explicit `workspace_yaml_missing`,
  `workspace_runtime_plan_compile_failed:<err>` so callers can degrade
  gracefully (line 234-247).
- `workspace_yaml` — full content (caller can pass it to LLM).
- `filesystem_snapshot` — bounded recursive walk, max 5000 files,
  skip-dirs `.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build`
  (workspace-snapshot.ts:10-43).
- `memory` — captured memory views from the memory service.
- `cronjob_records`, `task_proposals` — live state.
- `tool_manifest` — derived from the compiled plan (graceful fallback when
  the compiler errors, line 307-318).
- `captured_at` — timestamp.

Two design points worth extracting:

1. **One synchronous call returns everything the agent needs to bootstrap.**
   No per-fact request fan-out. The agent gets a single context blob and
   can decide what to use.
2. **Graceful degradation on failure.** If the runtime plan won't compile,
   `proactive-context.ts:236-247` still returns a payload with `warnings`
   populated and uses `fallbackWorkspaceSignals` (line 105-131) — a
   reduced view computed by walking the raw yaml without the compiler.

### 3.2 luum surface

luum already has SessionStart hooks:

- `hooks/session-start-worktree-nudge.sh` — worktree-aware orientation.
- `hooks/session-start-stash-reapply.sh` — auto-reapply pre-session stashes.
- `hooks/session-startup-protocol.sh` (169 lines) — the closest match.
  Emits a compact 5-step summary covering Engram presence, plans/ADRs
  counts, work-queue state, runtime validator, "now execute" reminder.
  Budget: <500 ms, p95 <300 ms. Pure filesystem heuristics — no
  subprocess fan-out, no MCP calls.

The startup hook is **fast and orientational** but does not return a
structured artifact. It writes free-form text into the SessionStart
additionalContext stream; the model has to re-read directories itself to
get any actual content. There is no:

- bounded directory walk with size/extension stats,
- key-file preview block,
- git branch + dirty bit summary,
- compiled plan / tool manifest reflection,
- structured warnings the orchestrator can act on programmatically.

Engram covers cross-session memory, but the *project-state snapshot at
session start* is left to the model.

### 3.3 Compatibility with Claude Code SessionStart

holaOS's `captureWorkspaceContext` assumes a runtime that **owns** the
agent process and can inject a JSON blob synchronously. Claude Code's
SessionStart hook contract is different:

- The hook is a process invoked by the harness; its stdout is streamed
  into the model context as `additionalContext`.
- There is no return-channel for typed data — only text.
- Budget is tight (<1s in practice, hooks that exceed are killed and the
  session continues without their output).
- The hook cannot block the user.

To translate the holaOS pattern to a SessionStart hook, the design needs
to differ in three ways:

1. **Two-phase emission**: a thin hook (≤200 ms, current pattern) emits a
   compact YAML-fenced block with the core signals. The block points to
   an auxiliary file (`/tmp/.cos-snapshot.<session>.json`) the orchestrator
   can read on demand for full content.
2. **Selective payload**: the SessionStart additionalContext should
   *summarise* (counts, top 5 files, git state, last 3 ADRs) and let the
   model pull richer slices via tools. Embedding the full filesystem
   snapshot would blow the context budget.
3. **Failure as a first-class output**: like holaOS's `warnings` array,
   each subsystem (engram, ADR index, work queue, runtime plan) should
   emit a single-line status string so the model can see what is missing
   without having to probe.

### 3.4 Delta

| Concern                       | holaOS                                                | luum SessionStart today               |
|-------------------------------|-------------------------------------------------------|---------------------------------------|
| Output shape                  | Structured JSON                                       | Free-form text                        |
| Filesystem snapshot           | Bounded walk + extension stats + previews + git       | None (only md-file counts)            |
| Tool manifest                 | Derived from compiled plan                            | Not surfaced                          |
| Memory                        | Pulled from durable memory service synchronously      | Hint only ("run mem_search anyway")   |
| Warnings                      | Typed list                                            | Free text                             |
| Latency                       | API call (~hundreds of ms server-side)                | <300 ms p95                           |
| Failure mode                  | Graceful degradation, fallback signals                | Hook exits 0, summary is empty        |

### 3.5 Clean-room adoption plan

**Priority: P2.** This is a developer-experience win; not a correctness
or security fix. Worth doing once the grant signing (P0) and runtime plan
(P1) are in flight because both deliver inputs the snapshot wants
(checksum'd plan, scoped grants for any post-session tools the snapshot
mentions).

Files to create:

- `lib/cos_snapshot.py` — `capture_session_snapshot(project_dir: Path,
  *, max_files: int = 5000, preview_bytes: int = 1000) -> SnapshotPayload`.
  Pure function: walks the tree with skip-dirs from a config list, hashes
  key files, reads previews of `cognitive-os.yaml`, `README.md`,
  `AGENTS.md`, `CHANGELOG.md`, surfaces git branch + dirty bit (via
  `subprocess` with a 2-second timeout), counts ADRs, counts plans, calls
  `cos_plan.compile_plan_from_disk()` (P1 dependency) and captures
  warnings if it fails.
- `hooks/session-start-snapshot.sh` — thin wrapper around
  `lib/cos_snapshot.py`. Writes the full JSON to
  `.cognitive-os/sessions/<id>/snapshot.json` and emits a ≤40-line
  YAML-fenced summary to stdout for additionalContext.
- `tests/unit/test_cos_snapshot.py` — invariants: max-files respected,
  skip-dirs honoured, malformed yaml → warning not exception, missing
  cognitive-os.yaml → warning + degraded payload (not crash).

Files to modify:

- `hooks/session-startup-protocol.sh` — call into the new snapshot script
  (or merge), keep the 5-step protocol summary at the top.
- `.claude/settings.json` — register the new hook in SessionStart with a
  budget annotation.
- `rules/startup-protocol.md` — document the new snapshot file path so the
  agent knows it exists.

**Effort**: ~4 days for the snapshot library + hook + tests. Cheaper than
P1 because it leans on existing primitives (`config_loader`,
`adr_detector`, the file-walk helpers in `lib/paths.py`).

---

## 4. Recommendation summary by priority

| # | Feature                | luum priority | Why                                                                                 | Effort |
|---|------------------------|---------------|-------------------------------------------------------------------------------------|--------|
| 1 | Grant signing (HMAC + nonce + TTL + scope) | **P0**       | `cosd` is already exposed; current model is one omnipotent shared secret. Operational risk grows as more teams adopt the remote bind. | ~3 days |
| 2 | Compiled workspace runtime plan            | **P1**       | ~20 callsites read `cognitive-os.yaml` independently. Drift risk is real and compounds with every new consumer. | ~5 days + migration tail |
| 3 | Proactive session snapshot                 | **P2**       | DX/quality win; reduces wasted tool calls at session start. Depends on P1 for the plan checksum. | ~4 days |

### 4.1 Sequencing recommendation

Do them in order: P0 first because it is the only one that closes a
security gap, P1 next because P2 depends on it for the plan checksum,
P2 last as the capstone.

If sequencing is constrained, P0 must not slip — once a `cosd` instance
runs on a non-localhost interface in a real team, the static-token model
becomes a meaningful risk. The HMAC grant primitive can be added
backwards-compatibly alongside the current bearer (accept either, prefer
the grant when supplied), so the migration is non-breaking.

### 4.2 What we explicitly do NOT adopt from holaOS

- **OAuth service code** (`oauth-service.ts`) — we have no per-user OAuth
  flows in luum's threat model. The HMAC grant primitive is useful
  standalone; the broker+OAuth machinery around it is not.
- **`apply-app-schema.ts`** — luum has no `data.db` per workspace. The
  ADOPT/FRESH/UPGRADE pattern is interesting for future thinking but
  there is no current consumer.
- **Workspace MCP sidecar identity rewriting** — luum's MCP topology is
  flat per-project; there is no multi-workspace sidecar collision.
- Any literal string, file structure, or type name from holaOS. The
  adoption plans above intentionally rename and restructure to keep the
  result clean-room and defensible under the BSL-like license.

---

## 5. References

- holaOS source (read-only, `/tmp/holaOS-investigation/runtime/api-server/src/`):
  `grant-signing.ts`, `integration-broker.ts`, `oauth-service.ts`,
  `workspace-runtime-plan.ts`, `runner-prep.ts`, `apply-app-schema.ts`,
  `proactive-context.ts`, `workspace-snapshot.ts`.
- luum surface:
  `scripts/cos_daemon.py`, `lib/cosd_auth_guard.py`,
  `rules/cosd-secure-api.md`, `docs/adrs/ADR-194-cosd-secure-remote-api.md`,
  `lib/config_loader.py`,
  `hooks/session-startup-protocol.sh`,
  `hooks/session-start-worktree-nudge.sh`,
  `hooks/session-start-stash-reapply.sh`.
- Parent annex: `docs/research/holaos-comparison-2026-05-10.md`.
