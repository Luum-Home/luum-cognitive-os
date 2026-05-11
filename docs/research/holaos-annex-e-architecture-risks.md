---
title: "holaOS Annex E — Architecture Patterns & Risk Analysis"
parent: holaos-comparison-2026-05-10.md
annex: E
status: research-only
research_only: true
date: 2026-05-10
source_repo: /tmp/holaOS-investigation (commit 6aeaf99)
license_constraint: "Modified Apache 2.0 — pattern-only, clean-room"
scope: project
type: discovery
---

# Annex E — Architecture Patterns & Risk Analysis

> Companion to `holaos-comparison-2026-05-10.md`. Annex A covered surface inventory; this
> annex zooms into **six architectural patterns worth studying** and a hard look at
> **adoption risk** (license, stack, dependencies, inversion, maturity). Every claim
> is anchored in a holaOS source path; every recommendation lands on a concrete luum
> file. No code is copied — only patterns are evaluated, per BSL-like license terms.

---

## 0. TL;DR

- **Adopt now (3):** capability-projection HTTP boundary (pattern 2), grant-signing HMAC envelope (pattern 3, slice), and post-run jobs queue with claim/lease/heartbeat semantics (pattern 6).
- **Park (3):** environment-engineering thesis (pattern 1) as long-range north star, embedding recall manifest (pattern 5) only if/when luum grows embeddings, hidden subagent fan-out (pattern 4) once main-conversation continuity becomes a top-3 complaint.
- **Discard (3):** Composio proxy/SaaS coupling, Electron desktop shell, BSL "frontend" lock-in. Not aligned with luum's open-source CLI distribution.
- **License verdict:** internal use OK; OSS distribution requires clean-room **patterns only** (we already operate this way); SaaS multi-tenant requires a commercial license from Holaboss — full BLOCK on copying source.
- **Maturity caveat:** the investigation snapshot has **1 commit** in `git log` (squashed/exported tree) but **80 `*.test.ts` files** spread across runtime/desktop/sdk. Treat it as a mature codebase whose history is not visible to us.

---

## 1. Pattern Catalog

Each pattern: holaOS evidence (paths + quoted lines), luum equivalent that already exists or is missing, a concrete design proposal (target paths under `lib/`, `scripts/`, `packages/`), and a Value/Effort/Risk verdict.

### Pattern 1 — Environment Engineering (the thesis)

**holaOS evidence.**
- `/tmp/holaOS-investigation/README.md` line ~36: *"holaOS is an open agent computer for any digital work. It reimagines the computer as a shared environment where humans and AI agents operate side by side… everything lives in one place where memory, execution, and goals remain coherent, so work doesn't reset or lose state."*
- `/tmp/holaOS-investigation/AGENTS.md`: project-level conventions are baked into `AGENTS.md` rather than scattered docs. Commit format, validation cadence (`make check`, `npm run runtime:test`), and "always use Context7 MCP for library/API docs" are encoded as durable repo law.
- `/tmp/holaOS-investigation/docs/plans/` contains 20+ dated plan documents (`2026-03-30-integrations-engineering-design.md`, `2026-04-30-workspace-data-layer-tier2.md`, etc.) — every architectural shift is a plan-first PR.

**Reading.** The thesis is *the environment is the agent*. Persistent workspace data (SQLite per workspace), apps with their own schemas, durable cronjobs, evolving memory, and a shared filesystem are first-class. Agents are episodic visitors to a stateful place — opposite of stateless LLM calls with retrieval bolted on.

**luum today.**
- `rules/RULES-COMPACT.md §1 Adaptive Workflow` already mandates plan-first for OS changes (`[plan-first]`, `[cognitive-os-changes]`, `[dogfooding]`).
- Engram + sessions form a memory environment, but the "environment" is the *operator's repo* + Engram, not a managed workspace owned by the OS.
- No equivalent of holaOS's `workspaceDirForId` / `ensureWorkspaceDataDb` pattern.

**Proposed luum equivalent.** Do **not** copy. The right import is the *plan-first cadence* (already adopted) and the *workspace-as-environment* mindset for future multi-tenant scenarios (e.g., when luum scales to managed teams). File a parking-lot ADR `docs/adr/ADR-XXX-environment-engineering-thesis.md` that catalogs the idea and says "revisit when SaaS path is on the roadmap."

**Verdict.** Value=H (long-range), Effort=H (months), Risk=H (full architectural inversion). **Park.**

---

### Pattern 2 — Capability Projection over HTTP

**holaOS evidence.**
- `/tmp/holaOS-investigation/runtime/harnesses/src/capability-http.ts` (243 lines). Exposes `requestCapabilityJson`, `formatCapabilityToolResultForModel`, and `nodeRequestJson`. Crucial primitive at lines 197–243:

  ```ts
  // formatCapabilityToolResultForModel(payload, options)
  // → if serialized > 32 KB threshold, return a compact_envelope:
  //   { tool_result_format: "compact_envelope", status: "truncated",
  //     serialized_bytes, summary: topLevelPayloadSummary(payload),
  //     preview, raw_result: { available: true, stored_in: "tool_result.details.raw" } }
  ```

  Default thresholds: `DEFAULT_COMPACT_TOOL_RESULT_THRESHOLD_BYTES = 32 * 1024`, preview `8 * 1024`. The compaction is **automatic and transparent** to the agent.

- `/tmp/holaOS-investigation/runtime/harnesses/src/runtime-capability-tools.ts` (1005 lines) wires those primitives into per-capability tool definitions (`cronjobs`, `scratchpad`, `subagent`, `todo`). All capabilities cross a single HTTP boundary (`runtimeApiBaseUrl`).

**Why interesting.** A clean **harness-side / runtime-side split**: the LLM agent sees JSON tools, the runtime owns state, and traffic between them is one HTTP wire. Result-size compaction is a *single chokepoint* — every capability inherits it for free. This solves the result-truncation problem holaOS-wide.

**luum today.**
- `rules/RULES-COMPACT.md §9 [result-management]` mandates truncation but enforcement is per-hook (`hooks/result-cap.sh` and similar). We have a "result truncation hook-enforced" rule but each tool/skill handles compaction differently.
- `lib/agent_output_extractor.py` post-processes JSONL, but the LLM still sees raw tool output before that.
- No single function `format_tool_result_for_model(payload)` that every tool routes through.

**Proposed luum equivalent.** Create `lib/tool_result_envelope.py` with:
- `def format_tool_result_for_model(payload, threshold=32_768, preview=8_192) -> dict`
- Returns either the raw payload (small) or a `{format: "compact_envelope", status: "truncated", serialized_bytes, summary, preview, raw_pointer}` dict matching holaOS shape.
- Wire it into `lib/agent_runner.py` and `lib/dispatch_helper.py` so every dispatched-tool result is filtered before reaching the model.

Pattern is **trivially clean-room** — the idea (size threshold + summary + preview + pointer) is generic and well-documented in API engineering. We re-implement in Python.

**Verdict.** Value=H, Effort=L (1–2 days), Risk=L. **Adopt now.**

---

### Pattern 3 — Apps with Data Schemas + Signed Grants

**holaOS evidence.**
- `/tmp/holaOS-investigation/runtime/api-server/src/data-schema.ts` (292 lines). Each app ships an `app.runtime.yaml` with a `data_schema:` block. Parser is pure (no I/O), DDL builder is pure, schema hash is recorded:

  ```ts
  export interface DataSchema {
    version: number;
    tables: TableDef[];
    sha: string;   // stable hash of manifest contents
  }
  ```

  Lines 100–104 enforce **namespace hygiene**: table names must start with `${appId}_`, making cross-app collisions structurally impossible.

- `/tmp/holaOS-investigation/runtime/api-server/src/apply-app-schema.ts` (281 lines). Idempotent apply with four outcomes: `noop` / `adopted` (pre-existing tables) / `fresh` (new install) / `upgraded` (additive auto-diff). Destructive changes (drop/rename/type) are **rejected** at apply time — apps must ship explicit migrations. Tracked in `_app_schema_versions(app_id PRIMARY KEY, version, manifest_sha, applied_at)`.

- `/tmp/holaOS-investigation/runtime/api-server/src/grant-signing.ts` (48 lines, **read in full**):

  ```ts
  const GRANT_TTL_MS = 24 * 60 * 60 * 1000;
  let signingKey: Buffer | null = null;   // per-process random 32-byte key

  export function createSignedGrant(workspaceId: string, appId: string): string {
    const timestamp = Date.now().toString(36);
    const nonce = randomUUID();
    const payload = `grant:${workspaceId}:${appId}:${timestamp}:${nonce}`;
    const signature = createHmac("sha256", getSigningKey())
      .update(payload).digest("base64url");
    return `${payload}:${signature}`;
  }
  ```

  HMAC-SHA256, 24h TTL, nonce-bound, base64url-encoded. Validation re-derives the signature and checks TTL.

**Why interesting.** Two distinct primitives bundled:
1. **Schema-as-manifest:** every app declares its DB tables in YAML; runtime applies them additively; SHA detects drift.
2. **Capability grants:** a signed token says "this workspace authorizes this app for the next 24 h" without DB lookups or central session state.

**luum today.**
- We **already do** YAML manifests for skills, hooks, ADRs — but **not** for per-component data schemas.
- No HMAC grant primitive. `packages/aguara-security` covers credentials, not short-lived grants.
- `lib/skill_router.py` + `lib/skill_manifest.py` map skill manifest → behavior but skip the "schema versioning + additive diff" idea.

**Proposed luum equivalent (split the bundle).**

A) **Skill/Plugin manifest schema versioning** — extend `lib/skill_manifest.py` to declare a `state_schema:` block with `version` + `sha` + idempotent apply for any plugin that owns durable state (Engram observation shapes, JSONL ledgers). Apply at install time. New file: `lib/manifest_state_apply.py`. Pure functions; tests under `tests/unit/test_manifest_state_apply.py`.

B) **HMAC grants for cosd remote API** — `rules/RULES-COMPACT.md §10 [cosd-secure-api]` already mandates bearer auth for `cosd` remote. Add a short-lived grant token next to it: `lib/grant_signing.py` with `create_signed_grant(workspace_id, capability, ttl_minutes=1440)` and `validate_signed_grant(token)`. Clean-room — the construction (HMAC over `prefix:scope:ts:nonce`) is textbook.

**Verdict.**
- Sub-pattern A (schema versioning): Value=M, Effort=M (1 week), Risk=L. **Park** — wait until we have plugin state to manage.
- Sub-pattern B (HMAC grants): Value=H, Effort=L (1 day), Risk=L. **Adopt now**, slot into `cosd` per ADR queue.

---

### Pattern 4 — Hidden Subagents in the Main Session

**holaOS evidence.**
- `/tmp/holaOS-investigation/runtime/api-server/src/subagent-model.ts` (115 lines, read in full). Resolves a `ResolvedSubagentExecutionProfile = { model, thinkingValue }` from a precedence chain: configured subagent model > selected model > runtime default. `defaultThinkingValueForModel` maps families to thinking budgets: `gpt-5.*` → `"medium"`, `claude-haiku-4-5` → `"8192"`, `claude-sonnet-*` / `claude-opus-*` → `"medium"`, etc.

- `/tmp/holaOS-investigation/runtime/api-server/src/main-session-event-worker.ts` (314 lines). The most interesting half is lines 74–110, `buildMainSessionEventBatchInstruction`:

  > "You are the workspace's main session. Write exactly one assistant message in your normal conversational voice based on the queued background task events below. Do not mention internal event ids, queueing, hidden workers, or implementation details."

  Followed by a long prompt instructing the main session to *naturally weave background results back into the conversation*. Background events are batched, deduped by `eventId@updatedAt`, and the **main session itself** is asked to surface them — there is no separate "system: here's an update" channel.

**Why interesting.** A subagent runs out-of-band, completes work, and the system **re-enters the main conversation** to deliver results in the main agent's voice. The user perceives one continuous assistant, not a swarm. Compare with our `delegate` async (orchestrator launches sub-agent, sub-agent finishes, orchestrator decides how to summarize) — equivalent in mechanism, but holaOS's "main session voice" prompt is a UX *commitment* we don't make explicit.

**luum today.**
- `lib/agent_runner.py` + `lib/agent_lifecycle.py` provide async sub-agent launch.
- `lib/anchored_summarizer.py` could be the seam for "weave results back in the main voice."
- The Global CLAUDE.md `Agent Teams Orchestrator` section instructs the orchestrator to "synthesize results" but does not formalize the *re-enter main voice* contract.

**Proposed luum equivalent.** Two slices:
1. **Codify the contract** — append to `rules/RULES-COMPACT.md §8 Prompt Engineering` a `[main-voice-continuity]` rule: when a delegated agent returns, the orchestrator must phrase the result as a natural continuation, not an "AGENT: ..." dump.
2. **Subagent execution profile** — port the precedence chain to `lib/model_routing.py` (already exists per `RULES-COMPACT.md §4 [model-routing]`). Add `resolve_subagent_profile(selected_model, override=None) -> dict(model, thinking_budget)` that follows: configured override → user-selected → default. Use it before every `Agent` launch so the orchestrator stops passing raw model strings.

**Verdict.** Value=M, Effort=L (rule + 50 LOC), Risk=L. **Park** — important once main-conversation continuity becomes a top complaint; current orchestrator already handles delegation cleanly.

---

### Pattern 5 — Embedding Recall with a Cacheable Manifest

**holaOS evidence.**
- `/tmp/holaOS-investigation/runtime/api-server/src/memory-recall-manifest.ts` (1176 lines). Top-of-file constants reveal the **shape of the recall budget**:

  ```ts
  const MAX_FRONTMATTER_LINES = 40;
  const MAX_MEMORY_SNIPPET_CHARS = 360;
  const MAX_SCOPE_SAMPLE_TITLES = 6;
  const MAX_INDEX_ENTRIES = 200;
  const MAX_PRIMARY_PATHS = 8;
  const MAX_RESERVE_PATHS = 4;
  const VECTOR_WORKSPACE_LIMIT = 12;
  const VECTOR_USER_LIMIT = 8;
  const VECTOR_PRIMARY_PATHS = 8;
  const VECTOR_RESERVE_PATHS = 4;
  const PLAN_AND_CANDIDATE_TIMEOUT_MS = 7000;
  const FINALIZE_TIMEOUT_MS = 7000;
  ```

  Recall is a three-stage pipeline: **plan → candidate selection → finalize**, each timed out at 7 s. Scopes are `workspace | preference | identity`. A `RecallStatus` of `sufficient | expand_once | none` controls whether to widen.

- Memory entries carry `verificationPolicy` + `assessMemoryFreshness` — recall is biased toward fresh, verified memories.

- `/tmp/holaOS-investigation/runtime/api-server/src/recall-embedding-backfill-worker.ts` (486 lines) backfills embeddings for unindexed entries on a 60 s poll, with a 30 s initial delay and `ENTRY_PAGE_SIZE = 200`. Honors `active_session_run` to back off when the workspace is busy.

**Why interesting.** A *manifest* (the index file + frontmatter) acts as a fast, cacheable pre-filter before any vector search. Vector search is bounded (12 + 8 paths) and time-boxed. Backfill is decoupled and respects load.

**luum today.**
- Engram is the moral equivalent (topic keys, observations, search). `lib/engram_client.py` + the `engram:memory` MCP do recall.
- No explicit *manifest cache* layer in front of Engram search.
- No backfill worker concept for embeddings — Engram handles it server-side.

**Proposed luum equivalent.** Engram already abstracts the embedding/storage tier; the missing piece is the **plan→candidate→finalize budgeting**. Slot a thin recall planner into `lib/recall_planner.py`:
- Input: query + scope hint
- Stage 1: `mem_context` (fast, no embeddings)
- Stage 2: `mem_search` with `VECTOR_WORKSPACE_LIMIT=12` style caps + 7 s timeout
- Stage 3: `mem_get_observation` for top-K full content
- Status: `sufficient | expand_once | none`

This stops the current pattern of agents calling `mem_search` with default limits and either over-fetching or missing context.

**Verdict.** Value=M, Effort=M (1 week), Risk=L. **Park** — Engram handles 80% already; revisit when context-budget becomes the bottleneck.

---

### Pattern 6 — Post-Run Jobs Queue

**holaOS evidence.** Five cooperating workers under `runtime/api-server/src/`:

| Worker | Lines | Role |
|---|---|---|
| `queue-worker.ts` | 650 | Claims session inputs, leases (300 s default), heartbeat (`HB_QUEUE_CLAIM_STALE_HEARTBEAT_MS=20000`), abort + concurrency (`HB_QUEUE_WORKER_CONCURRENCY=2`) |
| `bridge-worker.ts` | 758 | Polls a remote *proactive bridge* for cross-process jobs; env-gated by `HOLABOSS_RUNTIME_USE_TS_BRIDGE_WORKER` |
| `runner-worker.ts` | 789 | Spawns child processes for the actual run; emits `RunnerEvent` stream with heartbeat (`5000 ms`), run timeout (`1800 s`), idle timeout (`900 s`) |
| `app-lifecycle-worker.ts` | 1335 | Starts/stops apps; applies data schemas via `applyAppSchema()` before spawning |
| `recall-embedding-backfill-worker.ts` | 486 | See Pattern 5 |

Key primitives:
- **Lease + claim** (`leaseSeconds`, `claimedBy = "sandbox-agent-ts-worker:${pid}:${uuid}"`).
- **Stale heartbeat reclaim** (`claimStaleHeartbeatMs`).
- **Terminal-event guard** (`TERMINAL_EVENT_TYPES = {"run_completed", "run_failed"}`).
- **Pausable session runs** (`pauseSessionRun({workspaceId, sessionId})`).
- **AbortController per run** (cancellation is first-class).

**Why interesting.** This is a textbook **work-stealing, leased, heartbeat-protected** queue with per-job AbortController and observable terminal events — built on plain `RuntimeStateStore` (SQLite) without Redis/Valkey. Workers compose: app-lifecycle calls into schema-apply, queue-worker delegates to runner-worker, bridge-worker fans in remote jobs. All TypeScript, all auditable.

**luum today.**
- `lib/work_queue.py`, `lib/queue_advisor.py`, `lib/queue_drainer.py`, `lib/dead_letter_queue.py`, `lib/file_mutation_queue.py`, `lib/merge_queue.py`, `lib/rate_limit_queue_migration.py`, `lib/request_queue.py` — eight separate queues with overlapping concepts.
- No unified **lease + heartbeat + claim + stale-reclaim** model. We use file locks + timestamps.
- `[non-blocking-retry]` rule mentions CronCreate but the retry mechanism is per-script.

**Proposed luum equivalent.** Consolidate luum's queue zoo behind a single primitive in `lib/leased_work_queue.py`:
- `claim(worker_id, ttl_seconds) -> Job | None`
- `heartbeat(job_id, worker_id)` (extends lease)
- `complete(job_id, result)` / `fail(job_id, error)`
- Stale-reclaim sweep when `now - last_heartbeat > stale_threshold`
- Terminal-event set for completion detection
- AbortController equivalent via `multiprocessing.Event` or POSIX signals

Migrate `work_queue.py` first, then `request_queue.py`. Other queues (`dead_letter_queue`, `merge_queue`) become **views** on the leased queue with different consumers. This collapses 8 queue modules into 1 + 7 thin views.

**Verdict.** Value=H, Effort=H (2–3 weeks, touches many call-sites), Risk=M (regression surface). **Adopt now** as a multi-sprint ADR. This is the single biggest engineering win in the annex.

---

## 2. Risk Matrix

### 2.1 License — Modified Apache 2.0 (BSL-like)

**Full LICENSE text** (`/tmp/holaOS-investigation/LICENSE`, 45 lines, verbatim quotes below):

> Copyright (c) 2026 Holaboss

> "holaOS may be utilized commercially, including as a backend service for other applications or as an agent-computing platform for enterprises. Should the conditions below be met, a commercial license must be obtained from the producer:
>
> a. Hosted or embedded service: Unless explicitly authorized by Holaboss in writing, you may not use the holaOS source code to provide a hosted service to third parties, or embed holaOS as a component of a product or service that is sold, licensed, or otherwise commercially distributed to third parties.
>
> - This restriction applies to offering holaOS (in whole or substantial part) as a SaaS platform, a managed service, or as an integrated component within another commercial offering.
> - Internal use within a single organization (including multiple workspaces) does not require a commercial license."

> "b. LOGO and copyright information: In the process of using holaOS's frontend, you may not remove or modify the LOGO or copyright information in the holaOS console or applications. … 'frontend' … includes all components located in the `desktop/` directory…"

> "As a contributor, you should agree that: a. The producer can adjust the open-source agreement to be more strict or relaxed as deemed necessary. b. Your contributed code may be used for commercial purposes…"

> "Apart from the specific conditions mentioned above, all other rights and restrictions follow the Apache License 2.0."

**Restrictive clauses identified.**
1. **§1.a** No hosted/embedded service to third parties without a commercial license. SaaS = blocked.
2. **§1.a** "in whole or substantial part" — ambiguous threshold; safer to read as "any meaningful chunk of holaOS source."
3. **§1.b** Frontend (the `desktop/` directory) carries logo/copyright preservation requirements.
4. **§2.a** Unilateral license-change reservation by the producer — future versions may be more restrictive.
5. **§2.b** Contributor grants commercial-use rights to the producer.

**Mapping to luum `RULES-COMPACT.md §10 [license-policy]`.** Our policy: **BLOCK AGPL/SSPL/BSL; ALLOW MIT/BSD/Apache.** holaOS's modified Apache 2.0 sits in the BSL family for our purposes — the hosted-service restriction is exactly the BSL hallmark. **Verdict: BLOCK for source copying; ALLOW for clean-room pattern adoption** (since the underlying patterns — HMAC, work-leasing, result envelopes — are public engineering knowledge).

**Use-case × license matrix.**

| Use case | Verdict | Reasoning |
|---|---|---|
| Read holaOS source for ideas | OK | Public repo; no clause prevents study |
| Internal-only use inside luum org | OK | §1.a explicitly allows single-org internal use |
| Copy source fragments into luum (open-source `pip install`) | **BLOCK** | luum is distributed; embedding holaOS code falls under "embed holaOS as a component of a product … commercially distributed to third parties" the moment any luum user is commercial |
| Adopt patterns clean-room (re-implement in Python) | OK | Patterns are not copyrightable; LICENSE governs source, not ideas |
| luum becomes SaaS multi-tenant with any holaOS code | **BLOCK** | §1.a hosted-service prohibition is unambiguous |
| luum becomes SaaS multi-tenant with only clean-room patterns | OK | But document the clean-room boundary in each ADR |
| Mirror desktop/ UI for inspiration | Mixed | §1.b protects logos; we'd strip them anyway |
| Vendor `runtime/` as a dependency | **BLOCK** | Substantial-part rule + future license change reservation |

**Operating posture for luum.** Treat holaOS as a *patterns library*. Every adoption must:
1. Cite the holaOS path in the ADR.
2. Confirm the implementation is from-scratch Python (no copy/transliteration).
3. Note that the pattern itself is generic (HMAC, work-leasing, etc.) — not a holaOS invention.

---

### 2.2 Stack Mismatch (TS/Electron/SQLite vs bash/Python/YAML)

**What translates well.**
- **State machines & policy code.** `subagent-model.ts`, `data-schema.ts` parsers, `grant-signing.ts` — pure functions with clear inputs/outputs. Direct Python ports.
- **Constants & budgets.** Pattern 5's 12 named constants map to a Python `dataclass` or YAML config.
- **Verdict-shaped return types** (`ApplySchemaResult` discriminated union → Python `TypedDict` + `Literal["noop"|"adopted"|"fresh"|"upgraded"|"rejected"]`).

**What does NOT translate.**
- **`better-sqlite3` patterns.** holaOS leans hard on synchronous SQLite + WAL mode (`db.pragma("journal_mode = WAL")`). Python has `sqlite3` stdlib but luum currently uses JSONL + file locks. Migrating storage layer is a *separate* project from adopting any single pattern.
- **Electron IPC / desktop renderer.** The `desktop/` tree is fundamentally a UI shell — no luum analog needed.
- **`@holaboss/runtime-state-store` package.** A 200+ method SQLite façade. Re-implementing wholesale is not justified. Adopt only the *concepts* (lease, claim, terminal events) into our existing storage.
- **Node child process / `spawn`.** `runner-worker.ts` spawns CLI tools as children with stream parsing. luum uses `subprocess.run` + JSONL parsers; conceptually equivalent, no rewrite needed.
- **AbortController.** TS native; Python equivalent is `threading.Event` or `asyncio.CancelledError`. Different ergonomics, same intent.

**Risk score.** Stack mismatch is *low-medium* for patterns 2, 3, 4, 6 (logic-shaped), *high* for any attempt to import storage layout (pattern 1's workspace-as-SQLite). Don't try to port pattern 1 — port its philosophy only.

---

### 2.3 Composio Dependency (commercial lock-in)

**Evidence.** `/tmp/holaOS-investigation/runtime/api-server/src/composio-service.ts` (70 lines, read in full):

> "ComposioService — runtime-side client that proxies Composio operations through the Hono backend server, authenticated via the user's session cookie.
> The runtime never calls Composio directly and never holds COMPOSIO_API_KEY."

Architecture: holaOS runtime → Hono backend → Composio SaaS. The Composio API key lives only server-side. holaOS is **structurally coupled** to a third-party SaaS for integrations.

**Risk to luum.**
- **Vendor lock-in.** Composio is a commercial SaaS; adopting its proxy model means we'd be paying for it or running our own equivalent.
- **Indirection layer (Hono backend).** Even if we wanted Composio, the proxy assumes a hosted backend with session cookies — incompatible with luum's CLI distribution.
- **Better alternative exists.** MCP servers (`packages/mcp-server/`) already solve the "third-party integration" problem in a vendor-neutral, locally-runnable way.

**Verdict. DISCARD.** Do not adopt the Composio pattern. MCP is luum's answer and is strictly more open.

---

### 2.4 Architectural Inversion (holaOS replaces the harness; luum sits on top of one)

This is the deepest adoption barrier. **luum is a harness orchestrator that runs *inside* Claude Code; holaOS is a harness *replacement*** — it owns the entire conversation loop, model selection, tool dispatch, and UI.

**Concrete points where this limits direct adoption:**

1. **Main-session prompt control.** holaOS literally writes prompts back into the main conversation (Pattern 4's `buildMainSessionEventBatchInstruction`). luum cannot inject into the main Claude Code conversation — only into sub-agents. Any "re-enter main voice" pattern degrades into "orchestrator summarizes after."

2. **Model routing.** holaOS picks the model per call (`subagent-model.ts`). luum requests a model via Claude Code's Agent API; the harness ultimately decides. Our `[model-directive]` rule reflects this constraint.

3. **Tool surface.** holaOS designs its own tool catalog (`runtime-capability-tools.ts` with 1005 lines of definitions). luum tools are whatever Claude Code + MCP expose. We cannot add a new top-level tool to the main conversation; we can only ship MCP servers or skills.

4. **Persistence.** holaOS owns `workspace/data.db` per workspace, applies schemas to it, spawns apps against it. luum's persistence is Engram (external service) + JSONL ledgers (file-based). We don't own a per-workspace DB and we don't want to — Engram is the canonical store.

5. **Lifecycle.** holaOS workers run continuously (`while !stopped` poll loops). luum hooks run **per event** (PostToolUse, PreToolUse, etc.). A "post-run jobs queue" in luum means JSONL append + a hook-triggered drainer, **not** a daemon.

**Implication.** Every pattern adoption must pass a translation step: "how does this work when the harness, not us, owns the conversation?" The patterns that translate well (2, 3-b, 6) all live below the conversation layer — they're storage, security, or infrastructure. The patterns that translate poorly (1, 4) live at the conversation layer.

---

### 2.5 Maturity Assessment

**Test coverage.** `find /tmp/holaOS-investigation -name "*.test.ts" -o -name "*.spec.ts" | wc -l` → **80 test files**, distributed across `runtime/api-server/`, `runtime/harnesses/`, `runtime/harness-host/`, `desktop/electron/`, `sdk/app-sdk/`. Includes `apply-app-schema.test.ts`, `grant-signing.test.ts`, `queue-worker.test.ts`, `composio-service.test.ts`, `data-schema.test.ts`. The patterns we care about are all backed by tests.

**Commit cadence.** `git log --oneline | wc -l` → **1 commit** (`6aeaf99 fix: anchor main-session followup snapshots to session bindings (#332)`). This is a snapshot export, not the real history. The PR number `#332` is a signal of a real upstream project. Treat as: history not visible, but file maturity (file sizes 200–1335 lines, fixture dirs, plan docs from March–April 2026) indicates a real engineering team behind it.

**Documentation.** 20+ dated plan documents in `docs/plans/`. Convention: dated plan → implementation → tests. `AGENTS.md` codifies commit format and validation. README has badges (CI, Node 24.14.1, Electron, TypeScript, Modified Apache 2.0).

**Verdict.** Mature codebase. The risk is **not** that the patterns are half-baked — it's that they're entangled with the holaOS architectural inversion (2.4) and the BSL license (2.1).

---

## 3. Anti-Patterns — Things to NOT Adopt

1. **Workspace marketplace** — `docs/plans/2026-03-31-marketplace-design.md`, `docs/plans/2026-04-02-desktop-billing-credits-implementation-plan.md`. luum is OSS, not a billable platform.
2. **Electron desktop shell** (`desktop/`). luum is CLI-first; we don't ship a UI.
3. **Composio dependency** (see §2.3). MCP is the right answer for integrations.
4. **`AGENTS.md` as the only convention doc.** luum already has `rules/RULES-COMPACT.md` + `.claude/rules/cos/` + ADRs. Adding a parallel `AGENTS.md` would fragment conventions. We can borrow holaOS's commit-format strictness, but slot it into existing docs.
5. **`desktop/` LOGO/copyright lock-in** (§1.b). Even if we adopted any UI, we wouldn't inherit branding constraints.
6. **Per-process random signing key** (`grant-signing.ts:9: let signingKey: Buffer | null = null`). Random-per-process means a restart invalidates outstanding grants. Fine for ephemeral runtimes; **not** fine for luum where grants might need to survive a reboot. **Modify the pattern:** persist the key in `.cognitive-os/secrets/grant-key` (mode 0600) and rotate on schedule.
7. **`HB_QUEUE_WORKER_CONCURRENCY=2` as a default.** Too conservative for luum's local-dev profile. Pick our own default based on CPU count.
8. **Embedding everything by default.** Pattern 5's backfill worker indexes every memory entry. luum should keep Engram opt-in per topic; not all memories need vectors.
9. **Long prompts as runtime constants.** `main-session-event-worker.ts` lines 78–105 hard-code a 28-line system prompt. luum prefers prompts in `templates/` or skills, not in code.
10. **Unilateral license-change clause** (§2.a). We can't replicate this in luum — luum is Apache-2.0 strict, and the producer-reservation clause is the BSL signal we deliberately reject.

---

## 4. Consolidated Verdict

### 4.1 Top 3 patterns to adopt NOW

| # | Pattern | Target file | Effort | ADR slot |
|---|---|---|---|---|
| 1 | Capability HTTP result envelope (compact_envelope) | `lib/tool_result_envelope.py` (new) + wire into `lib/agent_runner.py`, `lib/dispatch_helper.py` | 1–2 days | ADR — "Universal tool result compaction" |
| 2 | HMAC signed grants for cosd remote API | `lib/grant_signing.py` (new) + cosd integration per `[cosd-secure-api]` | 1 day | ADR — "Short-lived capability grants" (slice of Pattern 3) |
| 3 | Unified leased work queue | `lib/leased_work_queue.py` (new) consolidating 8 existing queue modules | 2–3 weeks | ADR — "Queue consolidation under lease/heartbeat" |

### 4.2 Top 3 to PARK (revisit later)

| # | Pattern | Trigger to revisit |
|---|---|---|
| 1 | Environment-engineering thesis (whole-stack inversion) | If/when luum considers managed multi-tenant SaaS |
| 2 | Recall planner with plan/candidate/finalize stages | When Engram context budget becomes the operator's top complaint |
| 3 | Hidden subagent main-voice continuity | When users report "the agent feels fragmented across delegations" |

### 4.3 Top 3 to DISCARD

| # | Anti-pattern | Reason |
|---|---|---|
| 1 | Composio SaaS proxy | Vendor lock-in; MCP already solves this open-source |
| 2 | Electron desktop shell + frontend logo lock-in | luum is CLI; §1.b of LICENSE adds constraints we don't need |
| 3 | Marketplace + billing module | Outside luum's scope; non-aligned with OSS distribution |

### 4.4 Cross-cutting recommendation

File a **single umbrella ADR** — *"holaOS pattern absorption posture"* — that:
- Confirms BSL/modified-Apache 2.0 is treated as **patterns-only** under `[license-policy]`.
- Mandates that every adoption ADR cite the holaOS source path and certify clean-room implementation.
- Lists the 3 NOW + 3 PARK + 3 DISCARD verdicts above as the canonical reference.
- References this annex (E) and the parent comparison doc.

Engram topic key: `research/holaos/annex-e` (scope=project, type=discovery).

---

## 5. Source-Path Index (for ADR cross-references)

| Pattern | holaOS file(s) | Lines |
|---|---|---|
| 1 — Environment engineering | `README.md`, `AGENTS.md`, `docs/plans/*` | n/a |
| 2 — Capability HTTP | `runtime/harnesses/src/capability-http.ts`, `runtime-capability-tools.ts` | 243, 1005 |
| 3 — Data schemas + grants | `runtime/api-server/src/data-schema.ts`, `apply-app-schema.ts`, `grant-signing.ts` | 292, 281, 48 |
| 4 — Hidden subagents | `runtime/api-server/src/subagent-model.ts`, `main-session-event-worker.ts` | 115, 314 |
| 5 — Embedding recall manifest | `runtime/api-server/src/memory-recall-manifest.ts`, `recall-embedding-backfill-worker.ts` | 1176, 486 |
| 6 — Post-run jobs queue | `queue-worker.ts`, `bridge-worker.ts`, `runner-worker.ts`, `app-lifecycle-worker.ts`, `recall-embedding-backfill-worker.ts` | 650, 758, 789, 1335, 486 |
| Composio coupling | `runtime/api-server/src/composio-service.ts` | 70 |
| LICENSE | `LICENSE` | 45 |

---

*End of Annex E.*
