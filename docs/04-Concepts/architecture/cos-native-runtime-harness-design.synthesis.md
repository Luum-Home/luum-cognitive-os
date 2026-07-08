---
type: concept-synthesis
source: docs/04-Concepts/architecture/cos-native-runtime-harness-design.md
provenance: "Written 2026-05-14 to decide how COS should incorporate patterns from four external agent runtimes (Pi, Gollem/Fugue, Goose, Hermes Agent) without becoming a dependency pile or losing a single source of truth."
---

## What it is
Decision to build a COS-owned runtime/harness architecture ("COS Runtime Kernel") that borrows specific patterns from four external systems while keeping `manifests/primitive-contracts.yaml` as the sole source of truth for primitives.

## Key mechanics
- Pattern per source: Pi -> lifecycle model (beforeToolCall/afterToolCall, turn/session/compaction/resource events) but not its tool/resource definitions as primitive truth. Gollem/Fugue -> embedded backend (typed tools, approval callbacks, event bus, durable runs, traces) but not static composition that lets stale primitives linger. Goose -> safety/interoperability (inspectors, permissions, MCP/ACP, action-required UX) but not as a parallel governance platform. Hermes Agent -> product UX (memory, skills, self-improvement, cron, gateways) but not its memory model replacing Engram/governance.
- Flow: `manifests/primitive-contracts.yaml` -> Primitive Contract Loader -> Runtime Harness Contract -> COS Runtime Kernel -> {Lifecycle Engine, Execution Backend, Safety Inspector Mesh, Product Experience Layer} -> Normalized Evidence Writer -> `.cognitive-os/metrics/primitive-interventions.jsonl` + fidelity report.
- 6 core modules: (1) Primitive Contract Loader (`lib/runtime_harness/contracts.py`) loads/validates contracts, emits manifest hash; (2) Runtime Harness Contract (`runtime-harness-contract.v1` YAML) defines lifecycle events (before_tool_call, after_tool_call, model_request, model_response, session_start, session_end, compaction) each with a decision set (allow/block/ask/rewrite etc.) and permission outcomes (allow_once, allow_always, deny_once, deny_always, ask); (3) Lifecycle Engine (Pi-inspired); (4) Execution Backend (Gollem/Fugue-inspired: typed tools, approval callback, event bus, run/parent-run lineage, trace exporter, durable checkpoint store, coding tools read/write/edit/patch/grep/bash/git/test); (5) Safety Inspector Mesh (Goose-inspired: SecurityInspector, EgressInspector, PermissionInspector, RepetitionInspector, AdversaryInspector, PrimitiveContractInspector, SecretInspector, DestructiveGitInspector, ProtectedPathInspector); (6) Product Experience Layer (Hermes-inspired: skill browser, memory/session recall UX, cron, gateway delivery, run status, subagent delegation display - never owns primitive semantics).
- Normalized event envelope (`runtime-event.v1`) and normalized evidence row (`primitive-intervention.v1`) keep compatibility with `primitive_projection_fidelity.py`.
- Adapter/proof strategy: each of Pi/Gollem/Goose/Hermes gets an adapter that is a proof target, not canonical truth. First proofs: Pi adapter validates `destructive-git-blocker` via beforeToolCall; Gollem worker validates safe edit+test+destructive-block+stream; Goose adapter validates inspector/permission equivalence; Hermes benchmark validates skill/memory/cron flow.
- First implementation slice: `destructive-git-blocker` with 6 acceptance criteria (contract loads, before_tool_call exposed, `git reset --hard` blocked pre-execution, block writes `primitive-interventions.jsonl`, report marks proof enforced not structural-only, all four adapters can emit the same normalized row).
- Proposed new files: `manifests/runtime-harness-contract.yaml`, `lib/runtime_harness/{__init__,contracts,events,decisions,inspectors,evidence,kernel}.py`, `scripts/cos-runtime-harness-smoke.py`, smoke report JSON/MD, `tests/contracts/test_runtime_harness_contract.py`, `tests/behavior/test_runtime_harness_destructive_git.py`; optional Go path under `packages/runtime-worker-go/`.
- Decision rule: a candidate feature enters COS only if expressible as a lifecycle event, inspector decision, permission outcome, tool execution event, session/checkpoint event, product UX surface calling the kernel, or normalized evidence row - otherwise it stays a reference pattern.

## Relations & where used
References `manifests/primitive-contracts.yaml` as canonical primitive source; ties into `primitive_projection_fidelity.py` and the existing `destructive-git-blocker` hook.

## Status / caveats
Design document (dated 2026-05-14); proposed files and first implementation slice not confirmed as shipped within this doc.
