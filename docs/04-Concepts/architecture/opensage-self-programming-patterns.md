# OpenSage Self-Programming Patterns for Cognitive OS

**Date:** 2026-05-09
**Status:** Implemented as pattern contract + audit; no runtime adoption
**Sources:** `docs/reports/external-tools-radar-opensage-addendum-2026-05-09.md`, `docs/research/repo-scout/deep/opensage-agent__opensage-adk-2026-05-09.md`, `manifests/self-programming-agent-patterns.yaml`

## Why this exists

The `.ai` overlay in `<consumer-repo>/.ai` showed the missing COS root loop:

```text
canonical primitive
  -> IDE/harness adapter projection
  -> runtime evidence that the primitive was actually used
  -> codebase itinerary showing what the agent inspected
```

The OpenSage ADK adds another useful external reference: self-programming agents can create topology, tools, memory structures, and sandboxed execution paths dynamically. That strengthens ADR-256, but it also raises the governance bar. COS should not import OpenSage-style autonomy until the system can prove which primitive authorized each dynamic action and what evidence it produced.

## Decision

Adopt OpenSage as **pattern-only / adapter-lab input**, not as a default runtime dependency.

The implementation contract is `manifests/self-programming-agent-patterns.yaml`, audited by:

```bash
scripts/cos-self-programming-pattern-audit --json
```

The contract intentionally requires every OpenSage-inspired pattern to declare:

- external source URLs;
- existing COS surfaces;
- planned ADR-256 surfaces;
- required gates;
- observable evidence;
- adoption kind limited to `pattern-only` or `adapter-lab`.

## Pattern extraction matrix

| OpenSage pattern | COS interpretation | Existing COS surfaces | Required before runtime adoption |
|---|---|---|---|
| Dynamic agent topology | Compare AI-created vertical/horizontal subagents with COS launch preflight, squads, handoff receipts, and topology evidence. | `manifests/subagent-capabilities.yaml`, `manifests/agent-orchestration-adapters.yaml`, ADR-203, ADR-251, `lib/agent_lifecycle.py` | primitive contract, launch receipts, worktree isolation, intervention ledger |
| Dynamic tool/skill synthesis | Generated tools are allowed only as governed candidates, not immediately trusted runtime capabilities. | `lib/dynamic_tool_creator.py`, `skills/primitive-authoring/SKILL.md`, ADR-120, ADR-216, `lib/license_guard.py`, `lib/credential_safe_run.py` | primitive-authoring gate, reuse check, license gate, credential gate, sandbox policy |
| Sandboxed execution | Use OpenSage sandbox vocabulary as comparison data while preserving COS opt-in native sandbox defaults. | ADR-232, `manifests/sandbox-adapters.yaml`, `scripts/cos-sandbox-run`, `lib/sandbox_adapter.py`, ADR-211 | no implicit fallback, network off by default, service-readiness proof, rollback receipts |
| Graph/hierarchical memory | Compare graph memory with Engram recovery and ADR-256 codebase itinerary. | `docs/architecture/memory-lifecycle.md`, `lib/engram_lifecycle.py`, `lib/memory_retrieval_benchmark.py`, `docs/architecture/memory-layer-evolution-sdd.md` | retention policy, redaction policy, itinerary without contents, memory lifecycle doctor |
| Real benchmarks | Benchmark primitive use, not architecture claims. | `docs/architecture/runtime-benchmark-mvp.md`, `docs/architecture/primitive-fitness-evaluation-contract.md`, `scripts/runtime_benchmark_report.py`, `scripts/primitive_fitness_ledger.py` | primitive fitness rows, runtime benchmark, behavioral proof, trace join |

## Relationship to ADR-256

ADR-256 defines the durable COS answer:

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

OpenSage does not replace that. It supplies stress cases for it:

1. If agents can create agents, COS must know which launch primitive authorized each agent.
2. If agents can create tools, COS must know which authoring, license, credential, discovery, and sandbox gates approved each tool.
3. If tools run in sandboxes, COS must prove the actual sandbox plan and fallback behavior.
4. If memory becomes graph-shaped, COS must prove redaction, retention, and itinerary safety.
5. If benchmarks claim capability, COS must join benchmark outcomes to primitive interventions.

## Implementation status

Implemented now:

- `manifests/self-programming-agent-patterns.yaml` — machine-readable extraction contract.
- `scripts/self_programming_pattern_audit.py` — validates the contract.
- `scripts/cos-self-programming-pattern-audit` — CLI wrapper.
- `tests/unit/test_self_programming_pattern_audit.py` — regression coverage.

Not implemented yet:

- Runtime OpenSage adapter.
- Dynamic generated-tool execution beyond existing deferred COS dynamic-tool creator.
- ADR-256 `primitive-contracts.yaml` and intervention ledger runtime writers.
- Codebase itinerary capture.

## Adapter-lab entry criteria

An OpenSage-like adapter lab can start only when all of these are true:

1. `scripts/cos-self-programming-pattern-audit --json` passes.
2. ADR-256 phase 1 minimal primitive contracts exists.
3. ADR-256 phase 2 intervention ledger can record at least `observe`, `allow`, `warn`, and `block` rows.
4. Generated tools pass primitive-authoring, license, credential, and sandbox policy gates before invocation.
5. Sandbox fallback is explicit and recorded.
6. Memory writes have retention/redaction receipts.
7. Benchmarks report primitive use evidence, not just task success.

## Residual risk

The risk is not that OpenSage is irrelevant. The risk is adopting its autonomy before COS can observe and constrain it. Until ADR-256 runtime evidence exists, every OpenSage-inspired feature remains pattern-only.
