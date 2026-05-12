# Radar 2026-05-08 — Implementation Tracker

**Scope**: items derived from [`external-tools-radar-2026-05-08.md`](external-tools-radar-2026-05-08.md) §2 (Adoption Plan). The radar itself is an immutable snapshot of the 2026-05-08 decision; this tracker records execution progress against it without mutating the snapshot.

Mirrors the pattern of [`docs/03-PoCs/research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md`](../research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md).

## Status legend

- ✅ implemented and committed
- 🟡 partially implemented / next slice needed
- 🔲 not started
- ⏸ intentionally deferred

## Wave 1 — Housekeeping (1 day)

| # | Topic | Status | Commit / evidence | Source |
|---|---|---:|---|---|
| H1 | ADR-253 tombstone for squads | ✅ | `e7ed3c6b` — [`docs/02-Decisions/adrs/ADR-253-tombstone-squads.md`](../adrs/ADR-253-tombstone-squads.md), `Superseded-by: ADR-251` | C §🔍3 |
| H2 | README hook count: "11+3" → "12+2" | ✅ | `b5062d0f` — [README.md:26](../../README.md) | E auditoría |
| H3 | Trust Report claim → match hook reality (advisory + log) | ✅ | `b5062d0f` — [README.md:36-38](../../README.md). `trust-score-validator.sh` validates + logs to `.cognitive-os/metrics/trust-scores.jsonl`; does not block task closure | E DEBT-1 |
| H4 | Bubblewrap policy hardening | ✅ partial | `b5062d0f` — [`packages/agent-lifecycle/lib/sandbox_adapter.py`](../../packages/agent-lifecycle/lib/sandbox_adapter.py). Added `--die-with-parent`, `--unshare-pid/uts/ipc`, `--unshare-cgroup-try`, `--new-session`. **Seccomp BPF profile pending** (>>1-2h budget; tracked as T-H4-seccomp). `--ro-bind /` retained intentionally (no equivalent without breaking process startup). | B §🔍4 |
| H5 | "85% token reduction" claim → qualify as upstream-Anthropic figure, unmeasured locally | ✅ | `b5062d0f` — 4 occurrences in 2 docs (SYNTHESIS + tool-discovery-dynamic-registration). Local instrumentation tracked as T-H5-local-metrics | B §🔍7 |
| H6 | Skill schema convention: adopt `description: "Use when…"` across `skills/*/SKILL.md` | ✅ implemented | `scripts/migrate_skill_descriptions_use_when.py` rewrites/checks the convention; `tests/audit/test_skill_descriptions_nonempty.py` enforces it; `skills/CATALOG-COMPACT.md` regenerated. | D §🔍13 |

**Wave 1 progress: 5/6 implemented or documented, 1 implementation pending.** Closed work landed on `main` through `e7ed3c6b`, `b5062d0f`, `b55f2fb8`, and `c0e899c2`.

### H4 follow-ups (tracked, out of Wave 1 scope)
- **T-H4-seccomp**: BPF syscall filter profile for bwrap. Threat model drafted in [`docs/09-Quality/security/bwrap-seccomp-threat-model.md`](../security/bwrap-seccomp-threat-model.md); BPF implementation remains opt-in/pending workload smokes.

### H5 follow-ups (tracked, out of Wave 1 scope)
- **T-H5-local-metrics**: ✅ implemented local ToolSearch token-delta estimates in `lib/deferred_tool_loading.py`, dispatch metrics at `.cognitive-os/metrics/toolsearch-token-delta.jsonl`, CLI `scripts/cos-deferred-tool-plan --token-delta`, and unit/behavior/integration tests.

### H6 closure
- Batch migration is now script-backed and idempotent: `python3 scripts/migrate_skill_descriptions_use_when.py --check --json`.
- Acceptance: nonconforming count is 0 and audit tests enforce the routing description convention for future skills.
- Note: this improves skill discoverability and routing metadata. The existing dogfood `skill_coverage` dimension is behavior-test coverage, so it should not be interpreted as a direct H6 score unless the scorer is changed separately.

## Wave 1.5 — Drift fix retro and post-reassessment cleanup

| # | Topic | Status | Commit / evidence | Source |
|---|---|---:|---|---|
| R1 | Control-plane audit registry drift fix | ✅ | `b55f2fb8` — closed control-plane-audit registry drift before the radar reassessment wave continued. | post-review drift fix |
| R2 | External Tool Intelligence Plane / project overlay substrate | ✅ | `84570d5a` design doc + `abe9e3cf` ADR-254/manifest/scripts/tests. | full reassessment follow-up |
| C1 | LiteLLM direct dependency contradicts ADR-049 direct-provider routing | ✅ | Removed pre-`v0.28.0`; `scripts/cos-tool-adoption-audit --json` reports `status: pass, findings: 0`. | full reassessment P0 |
| C2 | Langfuse direct dependency contradicts Phoenix/OTel posture | ✅ | Removed pre-`v0.28.0` (only mlflow comment retains historical mention). | full reassessment P0 |
| C3 | `memu` package likely wrong / requires package verification | ✅ | Removed pre-`v0.28.0`. | full reassessment P0 |
| C4 | `pytest-smell` declared but no visible consumer/gate | ✅ | Removed pre-`v0.28.0` from `pyproject.toml`. | full reassessment P0 |

## Post-`v0.28.0` follow-ups (carry into 0.28.1 / 0.29.0)

| # | Topic | Status | Source / evidence |
|---|---|---:|---|
| F1 | `make test-laptop-integration` exhausted local 900s laptop timeout at 56%; classify as sizing issue and run via stable shards. | ✅ implemented | `scripts/cos-integration-shard-plan`, `make test-laptop-integration-plan`, `make test-laptop-integration-shard SHARD_INDEX=N`; ADR-072 lane taxonomy + ADR-100 resource-governed test execution. |
| F2 | OpenCode primitive adapter smoke requires `node` in PATH; passed during release-confidence bundle via `fnm`. Document as runbook prerequisite. | ✅ documented | `docs/05-Methodology/runbooks/public-launch-day.md` Prerequisites; CHANGELOG `[0.28.0]` Release notes. |
| F3 | Portability tests for 7 new SCOPE: both libs/scripts (lib/{repo_map,dspy_pilot,integration_shard_plan}.py, packages/.../agentapi_msgfmt.py, scripts/cos-{repo-map,dspy-pilot,integration-shard-plan}). | ✅ implemented | `tests/red_team/portability/test_*.py` (7 files, 22 probes total — bilateral + falsification each); gate `hooks/scope-marker-portability-gate.sh` exits 0. |
| T-H4 BPF compilation | Strict seccomp BPF profile generation/compilation for bwrap. Manifest + opt-in command construction shipped in v0.28.0. | ⏸ parked | Requires workload smokes + threat-model validation per `docs/09-Quality/security/bwrap-seccomp-threat-model.md`; activate after benchmark evidence; not a release blocker. |
| T-public-launch | T-0 GitHub visibility flip per `docs/05-Methodology/runbooks/public-launch-day.md`. | ⏸ operator decision | Manual single-person action; runbook stable; no auto-execution path. |
| T-W3-bench | Wave 3 hardening — repo-map benchmarking against pure `lib/context_diet.py`. | 🔲 follow-up | Compare graph-rank token efficiency on real codebases before promoting `lib/repo_map.py` past optional pilot. |
| T-W3-dspy-real | Wave 3 hardening — DSPy real dependency pilot when installed (sdd-verify integration). | 🔲 follow-up | Today the seam is opt-in; turn on real DSPy structured-skill compile path once a benchmark proves quality delta. |
| T-W3-parsers | Wave 3 hardening — parser ports over vendored agentapi fixtures (golden test → real adapter parsing for each harness). | 🔲 follow-up | `lib/harness_adapter/testdata/agentapi/` is vendored; per-harness parser conformance still pending. |

**Gate note:** the reassessment and doctrine are intentionally documentation-before-implementation. Runtime adoption work should not start from prose alone; it must pass ADR-254's manifest, audit, and research-check path.

**Post-0.28 status:** C1-C4 are closed by the adoption audit. Remaining Wave 1 carry-overs are H6 plus the tracked H4/H5 follow-ups below; none block `v0.28.0`.

## Wave 2 — Memory bundle (10–14 days, single SDD change)

Candidate change name: `memory-layer-evolution`. Bundled because the four items share a single schema migration; splitting would force two parallel schema bumps.

**SDD status**: Slice 0 benchmark implemented 2026-05-08. Executable plan: [`.cognitive-os/plans/architecture/memory-layer-evolution-wave2.md`](../../.cognitive-os/plans/architecture/memory-layer-evolution-wave2.md). No Engram schema/retrieval default changes landed in Slice 0; Slice 1 must preserve `strategy=current` compatibility and pass `scripts/cos-memory-benchmark`.

| # | Topic | Status | Source | License |
|---|---|---:|---|---|
| M1 | graphiti bi-temporal schema (`valid_from`/`valid_to`) for Engram observations | ✅ additive migration landed; default retrieval remains `strategy=current` | `lib/engram_wave2_schema.py`, `scripts/cos-engram-wave2-schema-migrate`, `tests/unit/test_engram_wave2_schema.py`; A §🔍2c | Apache-2.0 (schema only) |
| M2 | LightRAG dual-level (entity + topic) retrieval scoring → `engram_lifecycle.py` | ✅ opt-in runtime mode landed | `retrieval_strategy="dual-level"` / `"wave2-m2"`; A §🔍2a | MIT (algorithm port) |
| M3 | HippoRAG personalized PageRank as alternative mode in `engram_graph_walker.py` | ✅ opt-in PPR runtime mode landed | `EngramGraphWalker.personalized_pagerank()` + `retrieval_strategy="ppr"` / `"hybrid"`; A §🔍2b | MIT (algorithm port) |
| M4 | `memory_class` enum overlay (`semantic`/`episodic`/`procedural`/`working`); couple `memory_decay` to `working` | ✅ opt-in runtime overlay landed | `retrieval_strategy="memory-class"` / `"hybrid"`; A §🔍12 | MIT (MIRIX overlay) |

**Required ordering**: M1 (schema) before M2/M3/M4 (consumers). M2 and M3 can run in parallel once M1 lands. M4 is overlay, lands last.

### Slice 0 baseline — current local retrieval

Baseline report: [`docs/06-Daily/reports/memory-retrieval-baseline-current-local-2026-05-08.json`](memory-retrieval-baseline-current-local-2026-05-08.json).

Result: `status=block`, `passed=0/3`, `block=3`, `temporal_correct=1/3`, `source_supported=2/3`. The current lexical/Jaccard-style baseline fails both temporal freshness and explicit multi-hop support-chain requirements.

Implication for ordering: M1 has the highest immediate delta because temporal validity/supersession fixes two of three blocking fixtures. M3 is second because explicit path/support-chain retrieval fixes the multi-hop fixture. M2 should wait until M1/M3 provide the schema/graph signals it can rank. M4 remains last as taxonomy/backfill overlay.


### Benchmark-local Wave 2 modes

The first implementation pass landed non-default benchmark-local modes instead
of production Engram changes. This preserves `strategy=current` while proving
the expected deltas:

| Mode | Status | Reported effect |
|---|---:|---|
| `temporal-local` | 🟡 benchmark-local | fixes stale temporal blockers; leaves multi-hop blocker |
| `graph-path-local` | 🟡 benchmark-local | passes all Slice 0 fixtures by adding relation support chains |
| `dual-level-local` | 🟡 benchmark-local | preserves pass with entity/topic scoring shape |
| `memory-class-local` | 🟡 benchmark-local | preserves pass with memory class overlay |

Production Engram defaults remain unchanged until an explicit follow-up ports
M1/M3 behind a non-default runtime flag and passes the same benchmark.

### Wave 2 comparison decision

Report: [`docs/06-Daily/reports/memory-retrieval-wave2/comparison-2026-05-08.json`](memory-retrieval-wave2/comparison-2026-05-08.json).

`graph-path-local` is selected as the next port target because it is the
smallest mode that passes all Slice 0 fixtures. It fixes the same 3 fixtures as
`dual-level-local` and `memory-class-local`, but avoids porting M2/M4 before the
required temporal and support-chain substrate exists.

Next implementation target: **M1+M3 real Engram port behind a non-default flag**.

### Runtime M1+M3 port

`lib/engram_lifecycle.py` now supports explicit
`retrieval_strategy="wave2-m1-m3"` (or environment variable
`COS_ENGRAM_RETRIEVAL_STRATEGY=wave2-m1-m3`). The default `current` strategy is
unchanged: existing callers receive the same lifecycle-ranked payload unless
they opt in.

The opt-in path adds:

- temporal validity / supersession-aware reranking using open/closed
  `valid_to` metadata and accepted `supersedes` edges in `memory_relations`;
- bounded relation support-chain annotations through
  `lib/engram_graph_walker.py`;
- `retrieval_strategy`, `temporal_status`, `support_chain`, and `wave2_score`
  fields only in the opt-in response.

M1 schema migration/backfill is now implemented by `scripts/cos-engram-wave2-schema-migrate`. Remaining M3 work: a true PPR mode. The current runtime port remains opt-in behavior over existing fields/relations, not a default switch.

### M1 default decision

Decision record:
[`docs/06-Daily/reports/memory-retrieval-wave2/m1-default-decision-2026-05-08.json`](memory-retrieval-wave2/m1-default-decision-2026-05-08.json).

`temporal-local` justifies the M1 runtime port but **does not justify flipping
the default**:

- `current-local`: `passed=0/3`, `block=3`, `temporal_correct=1/3`,
  `source_supported=2/3`;
- `temporal-local`: `passed=2/3`, `block=1`, `temporal_correct=3/3`,
  `source_supported=2/3`;
- remaining blocker: `multi-hop-adr-implementation-test`.

Default remains `strategy=current`. M1 stays opt-in until M3/source-support
closes the remaining blocker or a release owner records an explicit waiver.

**Acceptance criteria** (proposed, to confirm at `/sdd-new memory-layer-evolution`):
- Schema migration is idempotent and reversible.
- Existing Engram queries return identical results pre/post-migration when bi-temporal fields default to `created_at`/`superseded_at`.
- Dual-level retrieval beats current FTS5+graph-walk on a benchmark suite (to be defined).
- PPR mode is a flag, not a default — current BFS depth-2 stays default until benchmark confirms PPR is superior.
- `memory_class` is an additive column with backfill (`bugfix → procedural`, `decision → semantic`, `discovery → episodic`).

## Wave 3 — Codegen + selective integrations (3 weeks, parallelizable)

| # | Topic | Status | Source | License |
|---|---|---:|---|---|
| W3-1 | `lib/repo_map.py`: graph-rank + token budget context selector with COS governance overlay | ✅ initial runtime landed | `lib/repo_map.py`, `scripts/cos-repo-map`; D §🔍9 | Apache-2.0 pattern-port |
| W3-2 | DSPy pilot: optional structured-I/O seam for one skill (`sdd-verify`); do **not** touch `lib/skill_router.py`. | ✅ optional pilot seam landed | `lib/dspy_pilot.py`, `scripts/cos-dspy-pilot`; dependency remains optional | MIT |
| W3-3 | Vendor `lib/msgfmt/testdata/` from agentapi golden fixtures → `lib/harness_adapter/testdata/`. No Go sidecar. | ✅ testdata vendor landed | `lib/harness_adapter/testdata/agentapi/`, source commit `00ff7ffdc4badcf68b3903dd799cf6e2d4370d86`; C §🔍10 | MIT (testdata only) |

**Independence**: W3-1, W3-2, W3-3 share no files — they can run in parallel once Wave 2 lands. W3-1 and W3-3 now have design docs; W3-2 remains not started.

## Tier-4 confirmed non-pursuits (carried from radar §3)

Listed here for completeness so this tracker is the single source of truth on "what we are NOT doing":

- 🔲 NATS JetStream as default cross-session bus — **rejected**, file-IPC + ADR-233 covers MVP
- 🔲 Firecracker / hypervisor sandboxes as primary — **rejected**, Bubblewrap (H4 done) covers 80%; E2B remains opt-in tier-3
- 🔲 OPA / Rego policy engine — **rejected**, single-operator OS doesn't need ABAC
- 🔲 Temporal / Cadence durable workflows — **rejected**, `@event_wrap` + ADR-226 covers MVP
- 🔲 Multi-machine cloud orchestration — **rejected**, local-first is positioning

## Post-0.28 prioritization

Recommended next order after `v0.28.0`:

1. **M2/M4 consumers after M1** — schema substrate is available; keep defaults unchanged until benchmark evidence justifies a switch.
2. **T-H4 seccomp BPF implementation** — opt-in command construction and policy manifest exist; compiled BPF/profile generation still requires workload smokes before any default switch.
3. **Post-W3 hardening** — repo-map benchmarking, DSPy real dependency pilot when installed, and parser ports over the vendored agentapi fixtures.
5. **Public launch runbook execution** — operational visibility flip; separate from code release tagging.

## Maintenance contract

- This tracker is **mutable** (status updates, commit references). The radar 2026-05-08 itself is **immutable**.
- When a Wave-2 or Wave-3 item starts, update its row to 🟡 with the SDD change ID or commit prefix.
- When all items in a wave reach ✅ or ⏸, append a closure note ("Wave N closed YYYY-MM-DD in commit X").
- New radar editions (2026-05-XX+) get their own tracker file. Do not mix waves across editions in one tracker.

**Last updated**: 2026-05-10 by Codex remaining-technical-backlog session; F1 shards, Wave2 M2/M3/M4 opt-in runtime, T-H4 opt-in seccomp command path, and Wave3 initial slices are implemented.
