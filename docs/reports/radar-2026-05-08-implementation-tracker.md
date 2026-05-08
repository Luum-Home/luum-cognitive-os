# Radar 2026-05-08 — Implementation Tracker

**Scope**: items derived from [`external-tools-radar-2026-05-08.md`](external-tools-radar-2026-05-08.md) §2 (Adoption Plan). The radar itself is an immutable snapshot of the 2026-05-08 decision; this tracker records execution progress against it without mutating the snapshot.

Mirrors the pattern of [`docs/research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md`](../research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md).

## Status legend

- ✅ implemented and committed
- 🟡 partially implemented / next slice needed
- 🔲 not started
- ⏸ intentionally deferred

## Wave 1 — Housekeeping (1 day)

| # | Topic | Status | Commit / evidence | Source |
|---|---|---:|---|---|
| H1 | ADR-253 tombstone for squads | ✅ | `e7ed3c6b` — [`docs/adrs/ADR-253-tombstone-squads.md`](../adrs/ADR-253-tombstone-squads.md), `Superseded-by: ADR-251` | C §🔍3 |
| H2 | README hook count: "11+3" → "12+2" | ✅ | `b5062d0f` — [README.md:26](../../README.md) | E auditoría |
| H3 | Trust Report claim → match hook reality (advisory + log) | ✅ | `b5062d0f` — [README.md:36-38](../../README.md). `trust-score-validator.sh` validates + logs to `.cognitive-os/metrics/trust-scores.jsonl`; does not block task closure | E DEBT-1 |
| H4 | Bubblewrap policy hardening | ✅ partial | `b5062d0f` — [`packages/agent-lifecycle/lib/sandbox_adapter.py`](../../packages/agent-lifecycle/lib/sandbox_adapter.py). Added `--die-with-parent`, `--unshare-pid/uts/ipc`, `--unshare-cgroup-try`, `--new-session`. **Seccomp BPF profile pending** (>>1-2h budget; tracked as T-H4-seccomp). `--ro-bind /` retained intentionally (no equivalent without breaking process startup). | B §🔍4 |
| H5 | "85% token reduction" claim → qualify as upstream-Anthropic figure, unmeasured locally | ✅ | `b5062d0f` — 4 occurrences in 2 docs (SYNTHESIS + tool-discovery-dynamic-registration). Local instrumentation tracked as T-H5-local-metrics | B §🔍7 |
| H6 | Skill schema convention: adopt `description: "Use when…"` across `skills/*/SKILL.md` | 🟡 design ready | `c0e899c2` — [`docs/skills/skill-description-use-when-migration.md`](../skills/skill-description-use-when-migration.md) defines migration plan; batch rewrite still pending. | D §🔍13 |

**Wave 1 progress: 5/6 implemented or documented, 1 implementation pending.** Closed work landed on `main` through `e7ed3c6b`, `b5062d0f`, `b55f2fb8`, and `c0e899c2`.

### H4 follow-ups (tracked, out of Wave 1 scope)
- **T-H4-seccomp**: BPF syscall filter profile for bwrap. Effort: 1-2 days. Needs threat model first (which syscalls are dangerous in our context).

### H5 follow-ups (tracked, out of Wave 1 scope)
- **T-H5-local-metrics**: instrument `.cognitive-os/metrics/` to record actual token-cost delta when ToolSearch is active vs not. Effort: 1-2 days. Closes the "claimed vs measured" gap permanently.

### H6 plan
- Single sub-agent (Sonnet) pass over `skills/**/SKILL.md`. For each: read existing description, propose `Use when …` formulation, write back. Idempotent: skip files that already start with `Use when`. Output: count of skills migrated + diff summary.
- Acceptance: `grep -L "^description:.*Use when" skills/**/SKILL.md` returns 0 (every SKILL.md follows the convention) **or** the exceptions are explicit (e.g. ADR-X declares foo-skill as legacy).

## Wave 1.5 — Drift fix retro and post-reassessment cleanup

| # | Topic | Status | Commit / evidence | Source |
|---|---|---:|---|---|
| R1 | Control-plane audit registry drift fix | ✅ | `b55f2fb8` — closed control-plane-audit registry drift before the radar reassessment wave continued. | post-review drift fix |
| R2 | External Tool Intelligence Plane / project overlay substrate | ✅ | `84570d5a` design doc + `abe9e3cf` ADR-254/manifest/scripts/tests. | full reassessment follow-up |
| C1 | LiteLLM direct dependency contradicts ADR-049 direct-provider routing | 🔲 cleanup pending | Detected by `scripts/cos-tool-adoption-audit --json` via `manifests/external-tools-adoption.yaml`; remains in `requirements.txt`. | full reassessment P0 |
| C2 | Langfuse direct dependency contradicts Phoenix/OTel posture | 🔲 cleanup pending | Detected by `scripts/cos-tool-adoption-audit --json`; remains in `requirements.txt`. | full reassessment P0 |
| C3 | `memu` package likely wrong / requires package verification | 🔲 cleanup pending | Detected by `scripts/cos-tool-adoption-audit --json`; remains in `requirements.txt`. | full reassessment P0 |
| C4 | `pytest-smell` declared but no visible consumer/gate | 🔲 cleanup pending | Detected by `scripts/cos-tool-adoption-audit --json`; remains in `pyproject.toml`. | full reassessment P0 |

**Gate note:** the reassessment and doctrine are intentionally documentation-before-implementation. Runtime adoption work should not start from prose alone; it must pass ADR-254's manifest, audit, and research-check path.

## Wave 2 — Memory bundle (10–14 days, single SDD change)

Candidate change name: `memory-layer-evolution`. Bundled because the four items share a single schema migration; splitting would force two parallel schema bumps.

| # | Topic | Status | Source | License |
|---|---|---:|---|---|
| M1 | graphiti bi-temporal schema (`valid_from`/`valid_to`) in `memory_relations` | 🟡 design ready | A §🔍2c; [`docs/architecture/memory-layer-evolution-sdd.md`](../architecture/memory-layer-evolution-sdd.md) | Apache-2.0 (schema only) |
| M2 | LightRAG dual-level (entity + topic) retrieval scoring → `engram_lifecycle.py` | 🟡 design ready | A §🔍2a; [`docs/architecture/memory-layer-evolution-sdd.md`](../architecture/memory-layer-evolution-sdd.md) | MIT (algorithm port) |
| M3 | HippoRAG personalized PageRank as alternative mode in `engram_graph_walker.py` | 🟡 design ready | A §🔍2b; [`docs/architecture/memory-layer-evolution-sdd.md`](../architecture/memory-layer-evolution-sdd.md) | MIT (algorithm port) |
| M4 | `memory_class` enum overlay (`semantic`/`episodic`/`procedural`/`working`); couple `memory_decay` to `working` | 🟡 design ready | A §🔍12; [`docs/architecture/memory-layer-evolution-sdd.md`](../architecture/memory-layer-evolution-sdd.md) | MIT (MIRIX overlay) |

**Required ordering**: M1 (schema) before M2/M3/M4 (consumers). M2 and M3 can run in parallel once M1 lands. M4 is overlay, lands last.

**Acceptance criteria** (proposed, to confirm at `/sdd-new memory-layer-evolution`):
- Schema migration is idempotent and reversible.
- Existing Engram queries return identical results pre/post-migration when bi-temporal fields default to `created_at`/`superseded_at`.
- Dual-level retrieval beats current FTS5+graph-walk on a benchmark suite (to be defined).
- PPR mode is a flag, not a default — current BFS depth-2 stays default until benchmark confirms PPR is superior.
- `memory_class` is an additive column with backfill (`bugfix → procedural`, `decision → semantic`, `discovery → episodic`).

## Wave 3 — Codegen + selective integrations (3 weeks, parallelizable)

| # | Topic | Status | Source | License |
|---|---|---:|---|---|
| W3-1 | `lib/repo_map.py`: graph-rank + tree-sitter + token budget. Replaces static allowlist in `lib/context_diet.py` for codegen-context selection | 🟡 design ready | D §🔍9; [`docs/architecture/repo-map-context-selector.md`](../architecture/repo-map-context-selector.md) | Apache-2.0 (Aider port) |
| W3-2 | DSPy pilot: integrate as dependency for one structured-I/O skill (start with `sdd-verify`). Do **not** touch `lib/skill_router.py`. | 🔲 not started | A §🔍1 | MIT |
| W3-3 | Vendor `lib/msgfmt/testdata/` from agentapi (11-harness golden fixtures) → `lib/harness_adapter/testdata/`. No Go sidecar. | 🟡 design ready | C §🔍10; [`docs/architecture/harness-golden-fixtures.md`](../architecture/harness-golden-fixtures.md) | MIT (testdata only) |

**Independence**: W3-1, W3-2, W3-3 share no files — they can run in parallel once Wave 2 lands. W3-1 and W3-3 now have design docs; W3-2 remains not started.

## Tier-4 confirmed non-pursuits (carried from radar §3)

Listed here for completeness so this tracker is the single source of truth on "what we are NOT doing":

- 🔲 NATS JetStream as default cross-session bus — **rejected**, file-IPC + ADR-233 covers MVP
- 🔲 Firecracker / hypervisor sandboxes as primary — **rejected**, Bubblewrap (H4 done) covers 80%; E2B remains opt-in tier-3
- 🔲 OPA / Rego policy engine — **rejected**, single-operator OS doesn't need ABAC
- 🔲 Temporal / Cadence durable workflows — **rejected**, `@event_wrap` + ADR-226 covers MVP
- 🔲 Multi-machine cloud orchestration — **rejected**, local-first is positioning

## Maintenance contract

- This tracker is **mutable** (status updates, commit references). The radar 2026-05-08 itself is **immutable**.
- When a Wave-2 or Wave-3 item starts, update its row to 🟡 with the SDD change ID or commit prefix.
- When all items in a wave reach ✅ or ⏸, append a closure note ("Wave N closed YYYY-MM-DD in commit X").
- New radar editions (2026-05-XX+) get their own tracker file. Do not mix waves across editions in one tracker.

**Last updated**: 2026-05-08 by Codex session after ADR-254 / full reassessment cleanup sync.
