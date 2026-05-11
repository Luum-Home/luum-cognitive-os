---
no-adr-required: true
rationale: benchmark specification — axes, workloads, metrics, and execution phases with no architectural decision content
---

<!--
RECONCILIATION STATUS: ARCHIVE (parking lot) — 2026-05-10 (post-v0.28.0)
Reconciled-by: P3 plan triage (see docs/reports/p3-plan-triage-2026-05-10.md)
Decision: ARCHIVE.
Rationale: Comparing COS against vanilla Claude/Codex/OpenCode and prior-art systems across workstation/VM/container/pod/cluster surfaces remains potentially valuable as marketing/positioning evidence and as a source of governance-overhead truth (the doctrine demands measurable hook overhead per ADR-237). However this plan competes with the explicit DEFER posture for cluster/Kubernetes runtimes in the External Tool Adoption Doctrine and in ADR-049 LLM dispatch posture; the only currently funded surfaces are workstation and (post-v0.26.0) Docker container worker. The Phase 1 local baseline can be revisited opportunistically without keeping this plan on the active P2 list. Park in .cognitive-os/plans/archive/ (recommendation only; do not move now); reactivate when (a) external buyers explicitly request comparative benchmarks, or (b) Shape-B federation/cluster trigger fires per ADR-132.
-->


# Runtime Comparison Benchmark Plan

This plan extends ADR-027 with a competitive benchmark matrix. The goal is not
to prove Cognitive OS is always faster than vanilla tools. The goal is to
measure where the operating layer adds enough governance, verification,
portability, memory, and repair quality to justify its overhead.

## Positioning

Cognitive OS should be compared against:

- vanilla Claude Code;
- vanilla Codex;
- Claude Code with Cognitive OS;
- Codex with Cognitive OS;
- OpenCode or other open harnesses where practical;
- prior-art systems documented in this repo, including Agent Zero, OpenClaw,
  Hermes Agent, Pi, and GGA, when a comparable workflow can be executed or
  approximated without license contamination.

The benchmark must cover multiple runtime surfaces:

- laptop / developer workstation;
- EC2 or VM;
- container;
- Kubernetes pod;
- clustered worker pool.

## Non-Goals

- Do not benchmark only cold-start speed and call it product value.
- Do not compare against competitors by documentation claims only.
- Do not adopt code from incompatible licenses.
- Do not claim Kubernetes or cluster superiority until a real worker runtime
  exists.
- Do not hide hook overhead; measure it explicitly.

## Benchmark Axes

### Environments

| Environment | Purpose | Current status |
|---|---|---|
| Developer workstation | Current local dogfood path | Ready |
| EC2 / VM | Headless single-node target | Planned |
| Container | Host-independent runtime target | Planned |
| Kubernetes pod | Cluster substrate | Planned |
| Clustered workers | Queue-backed repair/build runtime | Future |

### Tool Configurations

| Configuration | Why it matters |
|---|---|
| Claude Code vanilla | Baseline for current strongest local harness |
| Codex vanilla | Baseline for current Codex sessions |
| Claude Code + Cognitive OS | Measures governance overhead and memory benefits in Claude |
| Codex + Cognitive OS | Measures portability and self-hosting in Codex |
| OpenCode vanilla / OpenCode + COS | Measures open harness portability when available |
| Agent Zero | General autonomous-agent UX/runtime comparison |
| OpenClaw / Pi | Resilience/runtime-loop prior art comparison |
| Hermes Agent | Memory/self-reinforcement prior art comparison |
| GGA | Provider-agnostic review-hook comparison |

### Workloads

The workloads must be realistic and repeatable:

1. **Small bug repair** — failing unit test with a clear local fix.
2. **Cross-file bug repair** — failure spans multiple modules.
3. **Feature slice** — implement a small feature with docs and tests.
4. **Portability refactor** — remove vendor-specific assumptions.
5. **Security-sensitive edit** — detect secret/path/policy violation.
6. **Long session recovery** — resume after interruption or compaction.
7. **Provider churn simulation** — switch provider/model adapter without
   rewriting task logic.
8. **Cluster repair simulation** — enqueue multiple independent failures and
   verify worker isolation (future phases).

## Metrics

### Speed and Cost

- wall-clock time;
- model/tool tokens where available;
- API cost where available;
- local CPU/memory pressure;
- hook overhead;
- queue wait time;
- retry count.

### Quality

- tests passed after patch;
- number of regression failures;
- patch minimality;
- code review findings;
- correctness under hidden tests where available;
- rollback success.

### Operational Confidence

- reproducibility;
- audit trail completeness;
- memory saved/recovered;
- trace/metric completeness;
- safety gate triggers;
- developer intervention count;
- portability across harnesses.

### Durability

- whether the workflow survives provider change;
- whether state survives session restart;
- whether the same task can run in local/headless mode;
- whether artifacts avoid developer-specific absolute paths;
- whether a worker crash is recoverable.

## Comparison Matrix

| Runtime surface | Vanilla Claude | Claude + COS | Vanilla Codex | Codex + COS | Other tools | Required proof |
|---|---:|---:|---:|---:|---:|---|
| Workstation | Yes | Yes | Yes | Yes | OpenCode/GGA where available | local benchmark report |
| EC2 / VM | Planned | Planned | Planned | Planned | Agent Zero where available | headless single-node run |
| Container | Planned | Planned | Planned | Planned | Agent Zero/OpenCode where available | container artifact run |
| Kubernetes pod | Future | Future | Future | Future | OpenClaw/Pi concepts only unless runnable | pod smoke test |
| Clustered workers | Future | Future | Future | Future | OpenClaw/Pi concepts only unless runnable | queue-backed worker test |

## Harness Requirements

Every harness benchmark must record:

- command used;
- repository state;
- model/provider if known;
- enabled hooks/rules/skills;
- environment type;
- artifacts directory;
- summary JSON;
- failure classification.

Cognitive OS runs must additionally record:

- active harness driver;
- `.cognitive-os/install-meta.json` snapshot;
- doctor result;
- quality gate result;
- memory lifecycle result;
- path portability scan result.

## Execution Phases

### Phase 1 — Local Baselines

- [ ] Define benchmark fixture repositories.
- [ ] Run vanilla Claude Code and vanilla Codex manually or via scripts.
- [ ] Run Claude + COS and Codex + COS on the same workloads.
- [ ] Persist outputs under `.cognitive-os/reports/benchmarks/` or exported docs.
- [ ] Produce first comparison report.

### Phase 2 — Headless Single-Node Baselines

- [ ] Define `cos run-task` benchmark contract.
- [ ] Run on local headless mode.
- [ ] Run on EC2/VM.
- [ ] Compare against vanilla CLI runs where possible.

### Phase 3 — Container Baselines

- [ ] Build container image.
- [ ] Run the same fixtures with mounted workspaces.
- [ ] Verify path portability and artifact extraction.

### Phase 4 — Kubernetes / Pod Baselines

- [ ] Run one worker pod.
- [ ] Execute one fixture end-to-end.
- [ ] Capture logs, metrics, and artifacts.

### Phase 5 — Clustered Worker Baselines

- [ ] Run multiple workers.
- [ ] Enqueue multiple tasks.
- [ ] Prove no duplicate execution.
- [ ] Kill a worker and verify recovery.

## Reporting Format

Each benchmark run should emit a JSON document with at least:

```json
{
  "benchmark_id": "small-bug-repair-001",
  "environment": "workstation",
  "configuration": "codex-plus-cos",
  "workload": "small_bug_repair",
  "started_at": "2026-04-28T00:00:00Z",
  "duration_seconds": 0,
  "tests_passed": 0,
  "tests_failed": 0,
  "quality_gates_passed": false,
  "cost_usd": null,
  "hook_overhead_ms": null,
  "memory_recovered": false,
  "path_portability_passed": false,
  "result": "pass|fail|inconclusive",
  "notes": ""
}
```

## Initial Questions To Resolve

- Which benchmark fixtures are small enough to run often but realistic enough to
  matter?
- Which vanilla CLI commands can be automated without brittle UI assumptions?
- Which competitor tools are runnable under compatible licenses versus only
  referenceable as prior art?
- How much hook overhead is acceptable for each workload?
- Which quality metric best captures "easier to trust"?
