# ADR-256 — Primitive Contract Registry and Runtime Evidence Ledger

## Status
Proposed — plan-first, no runtime implementation yet

**Date:** 2026-05-09  
**Owner:** platform-safety  
**Tier:** core  
**Related:** ADR-057, ADR-064, ADR-154, ADR-189, ADR-190, ADR-205, ADR-211, ADR-249, ADR-252

## Context

Cognitive OS has primitives, harness projection manifests, dogfood scoring,
primitive coverage, hook timing, action receipts, consumer-fleet audit, service
readiness gates, and run traces. The missing root contract is a single record
that joins:

```text
primitive definition
  -> required capabilities
  -> harness/runtime projection fidelity
  -> installed consumer impact
  -> service/headless impact
  -> runtime intervention evidence
  -> codebase itinerary
  -> trace join
```

Without this, COS can keep adding correct pieces that remain fragmented. It can
say hooks exist, projections exist, or metrics exist, but cannot always answer:

> This primitive exists, reaches these projects/runtimes, claims this fidelity,
> and produced this intervention in this run.

## External pressure test: OpenSage

OpenSage ADK is a useful stress case for this ADR because it combines dynamic agent topology, dynamic tool/skill synthesis, sandboxed execution, graph/hierarchical memory, and real benchmark loops. COS may extract those patterns only through `manifests/self-programming-agent-patterns.yaml`; it must not adopt a self-programming runtime until this ADR can prove primitive authorization and runtime evidence for each dynamic action.

## Decision

Introduce a **Primitive Contract Registry** and **Runtime Evidence Ledger**.

A primitive is not fully governed until it has:

1. canonical contract row;
2. required capability declaration;
3. projection fidelity by harness and runtime shape;
4. consumer-fleet impact classification when install/update/projection may affect downstream projects;
5. service/headless impact classification when it can run outside IDE lifecycle;
6. runtime evidence mapping when it observes, advises, warns, blocks, allows, or suggests;
7. trace compatibility through `session_id` and, where available, `tool_use_id`.

## New surfaces

### `manifests/primitive-contracts.yaml`

Initial sketch:

```yaml
schema_version: primitive-contracts.v1
contracts:
  - id: destructive-git-blocker
    family: hook
    source: hooks/destructive-git-blocker.sh
    intent: Block destructive git operations before execution.
    trigger:
      kind: before_tool_call
      tool_intent: shell_command
    requires: [inspect_shell_command, block_tool_call, emit_metric, emit_intervention]
    actions:
      preferred: block
      fallback: warn
      reason_codes: [destructive_git_op]
    evidence:
      metrics: [.cognitive-os/metrics/git-op-blocks.jsonl]
      interventions: [.cognitive-os/metrics/primitive-interventions.jsonl]
      proof_tests: [tests/behavior/test_destructive_git_blocker.py]
    projection:
      claude: {fidelity: native-lifecycle-enforced}
      codex: {fidelity: governed-wrapper-enforced}
      opencode: {fidelity: host-plugin-lifecycle-capable, notes: Use permissions and tool.execute.before/after plugin hooks after adapter smoke.}
      cursor: {fidelity: structural-advisory}
      shell-ci: {fidelity: ci-enforced}
      cosd-service: {fidelity: documented-only, notes: Not exposed through remote cosd endpoints.}
    impact:
      consumer_fleet: none|install-update-risk|unknown
      service_mode: harness-embedded-only|shell-ci-safe|headless-worker-safe|cosd-service-safe|unsupported
```

### `.cognitive-os/metrics/primitive-interventions.jsonl`

Canonical action stream:

```json
{
  "schema_version": "primitive-intervention.v1",
  "timestamp": "2026-05-09T00:00:00Z",
  "session_id": "session-or-run-id",
  "tool_use_id": "optional-tool-use-id",
  "primitive_id": "destructive-git-blocker",
  "primitive_family": "hook",
  "primitive_source": "hooks/destructive-git-blocker.sh",
  "harness": "codex",
  "tool": "Bash",
  "action_kind": "block",
  "reason_code": "destructive_git_op",
  "target_ref": "redacted-or-hashed-target",
  "source_metric": ".cognitive-os/metrics/git-op-blocks.jsonl"
}
```

Allowed actions: `block`, `warn`, `advise`, `suggest`, `observe`, `allow`.

### `.cognitive-os/metrics/codebase-itinerary.jsonl`

Safe, content-free record of what the agent inspected. It must not store file
contents or raw secret/private values.

## Phases

0. **Docs/contract freeze** — ADR, plan, `/primitive-authoring` gate, `.ai` overlay lesson, and OpenSage pressure-test contract.
1. **Minimal registry** — five contracts: destructive git, destructive rm, reinvention check, large-file advisor, skill router.
2. **Intervention ledger** — bridge two hooks first, then script/advisory primitives.
3. **Codebase itinerary** — safe Read/Grep/Glob/LS metadata without contents.
4. **Projection and impact report** — join harness fidelity, consumer-fleet audit, and service-readiness gate.
5. **Trace joiner + observable self-use** — join itinerary + interventions + existing run trace.
6. **Consumer UX** — small commands around adapters/observe surfaces.

## OpenCode adapter note

OpenCode is not merely an instruction-file harness. Its official runtime surface
includes configurable permissions and plugins with `tool.execute.before` and
`tool.execute.after` events. ADR-256 should therefore project eligible COS
primitives to OpenCode through an adapter stack:

```text
opencode.json / AGENTS.md advisory context
  -> OpenCode permissions for coarse allow/ask/deny
  -> OpenCode plugin hook for pre/post tool enforcement
  -> primitive-interventions.jsonl row for comparable COS evidence
```

The current COS proof remains structural because `cos_init.py --harness opencode`
only signs `opencode.json`. Runtime enforcement may be claimed only after a COS
OpenCode plugin adapter and smoke test exist.

## Non-goals

- Do not copy a `.ai` overlay wholesale into COS.
- Do not migrate every primitive in phase 1.
- Do not claim runtime enforcement from structural advisory projection.
- Do not store contents/secrets in itinerary.
- Do not expose service/cosd operations that violate ADR-211 service readiness or cosd remote boundaries.

## Verification plan

Future lanes:

```bash
python3 -m pytest tests/contracts/test_primitive_contract_registry.py -q
python3 -m pytest tests/contracts/test_primitive_intervention_ledger.py -q
python3 -m pytest tests/contracts/test_codebase_itinerary.py -q
python3 -m pytest tests/contracts/test_primitive_projection_fidelity.py -q
python3 -m pytest tests/contracts/test_observable_primitive_self_use.py -q
```
