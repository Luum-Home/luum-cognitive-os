# ADR-256 — Primitive Contract Registry and Runtime Evidence Ledger

## Status
Accepted — implemented through Phases 1–6; OpenCode signed starter smoke implemented for four primitives

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

0. **Docs/contract freeze** — implemented through this ADR, `/primitive-authoring`, OpenSage pressure testing, and ADR-258 due diligence.
1. **Minimal registry** — implemented by ADR-257 through `manifests/primitive-contracts.yaml`.
2. **Intervention ledger** — implemented for destructive git/rm through `hooks/_lib/primitive-intervention.sh` and `.cognitive-os/metrics/primitive-interventions.jsonl`.
3. **Codebase itinerary** — implemented by `hooks/codebase-itinerary-capture.sh` with content-free Read/Grep/Glob/LS metadata.
4. **Projection and impact report** — implemented by `scripts/primitive_projection_fidelity.py` and `scripts/portable_ai_consumer_impact.py`.
5. **Trace joiner + observable self-use** — implemented by `lib/trace_joiner.py` and `scripts/cos-observe-primitives`.
6. **Consumer UX** — implemented by `scripts/cos-adapters`, `cos adapters ...`, and `cos observe primitives`.


## Implementation evidence

| Phase | Evidence |
|---|---|
| Registry | `manifests/primitive-contracts.yaml`, `tests/contracts/test_primitive_contract_registry.py` |
| Intervention ledger | `hooks/_lib/primitive-intervention.sh`, `tests/contracts/test_primitive_intervention_ledger.py` |
| Codebase itinerary | `hooks/codebase-itinerary-capture.sh`, `tests/contracts/test_codebase_itinerary.py` |
| Projection fidelity | `scripts/primitive_projection_fidelity.py`, `tests/contracts/test_primitive_projection_fidelity.py` |
| Observable self-use | `lib/trace_joiner.py`, `scripts/cos-observe-primitives`, `tests/contracts/test_observable_primitive_self_use.py` |
| Consumer UX | `scripts/cos-adapters`, `tests/contracts/test_consumer_adapter_ux.py` |

OpenCode is now split: the signed starter slice (`destructive-git-blocker`, `destructive-rm-blocker`, `large-file-advisor`, `skill-router`) is `governed-wrapper-enforced` through `packages/opencode-adapter/plugins/cos-primitive-guard.js` and `docs/reports/opencode-primitive-adapter-smoke-latest.md`; all other OpenCode primitive contracts remain `host-plugin-lifecycle-capable`.

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

The current COS proof is no longer structural for the signed starter slice: `cos_init.py --harness opencode` now projects `opencode.json` plus `.opencode/plugins/cos-primitive-guard.js`. Runtime enforcement may be claimed only for primitives listed in `docs/reports/opencode-primitive-adapter-smoke-latest.json`; all other primitives remain plugin-capable backlog.

## Consequences

- Primitive portability becomes contract-driven instead of inferred from scattered
  hook, skill, rule, script, lifecycle, and projection metadata.
- Cross-IDE claims can distinguish enforced, wrapper-enforced, plugin-capable,
  structural-advisory, CI-enforced, documented-only, and unsupported projections.
- Runtime evidence can be compared across harnesses once intervention and
  itinerary ledgers exist.
- The first implementation slices intentionally duplicate some lifecycle/readiness
  data while the registry proves its join value.
- Projection and trace tooling must eventually consume the registry; otherwise it
  becomes another passive manifest.

## Alternatives rejected

| Alternative | Rejection rationale |
|---|---|
| Keep lifecycle/readiness/projection manifests separate with no root contract | Rejected because agents still cannot answer which primitive has which capability requirement, fidelity, and runtime evidence in one row. |
| Start by adding more IDE adapters | Rejected because it expands projection surface without closing the source-of-truth gap. |
| Treat structural adapters as runtime enforcement | Rejected because Cursor/Copilot-style instruction surfaces cannot honestly claim blocking behavior without a native, wrapper, plugin, or CI enforcement path. |
| Copy the `.ai/` overlay wholesale into COS | Rejected because `.ai/` is a useful product mirror, while COS needs richer contracts and evidence ledgers internally. |

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
