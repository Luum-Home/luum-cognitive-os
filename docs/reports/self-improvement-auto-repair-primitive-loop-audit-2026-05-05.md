# Self-Improvement, Auto-Repair, and Primitive Evolution Audit — 2026-05-05

**Scope**: local documentation and implementation audit for whether the Obsidian/Engram graph work also supports Cognitive OS self-improvement, self-repair, and primitive evolution.

## Short answer

Yes, the same memory/graph direction supports self-improvement, but it is not the whole loop. The OS is designed as a governed MAPE-K system:

```text
Monitor -> Analyze -> Plan/Propose -> Execute with gates -> Persist Knowledge
```

Engram and the Obsidian export are primarily the **Knowledge** and human-audit layer. The actual self-improvement and repair loops are implemented through hooks, metrics JSONL, primitive ledgers, proposal scripts, skills, and tests. The safe product claim is:

> Cognitive OS is self-observing and self-proposing today, with bounded repair mechanisms and governed primitive evolution. It is not an unconstrained autonomous self-modifying system.

## Existing documentation found

| Document | What it says | Current reading |
|---|---|---|
| `docs/self-improvement-loop.md` | Defines the end-to-end loop: error capture, auto-refine, session learning, KPI monitoring, `/self-improve`, and governed updates to rules/skills/templates. | Architectural and partially implemented; some referenced atomic skills are not in the root `skills/` tree but the package skill exists. |
| `docs/self-repair-guide.md` | User-facing description of consequence engine, error learning, retry/circuit-breaker behavior, `/optimize-skill`, and `/self-improve`. | Useful operator guide, but some automatic hook-registration claims need to be read against current profiles/settings. |
| `docs/architecture.md` and `docs/overview.md` | Describe MAPE-K as the self-healing/self-improvement core and map monitor/analyze/plan/execute/knowledge to primitives. | Conceptual source of truth for the control-loop model. |
| `docs/adrs/ADR-083-governed-self-improvement-loop.md` | Decides self-improvement must be detect → propose → draft → verify → approve → promote; no silent mutation of live rules/root skills. | Important safety boundary; later ADRs absorb parts of it. |
| `docs/adrs/ADR-090-auto-skill-repair.md` | Detect skill degradation, emit repair queue, require gated action; no direct auto-regeneration. | Matches implementation in `lib/skill_failure_repair.py` and `hooks/skill-failure-monitor.sh`. |
| `docs/adrs/ADR-095-skill-synthesis-success-patterns.md` | Synthesizes skill drafts from recurring successful tool sequences. | Matches `lib/skill_synthesizer.py`; promotion remains operator-gated. |
| `docs/adrs/ADR-134-headless-self-improvement-proposer.md` | Converts audits into bounded self-improvement proposals; explicitly propose-only. | Matches `scripts/cos-self-improvement-loop` / `lib/self_improvement_loop.py`. |
| `docs/adrs/ADR-135-self-evolving-doctrine-proposals.md` | Lets COS propose doctrine amendments under `docs/proposals/` without editing live rules. | Matches `scripts/cos-doctrine-proposer` / `lib/doctrine_proposer.py`. |
| `docs/adrs/ADR-146-primitive-readiness-ledger.md` | Defines script primitive readiness ledger and role taxonomy. | Implemented; this is the machine-readable primitive-improvement substrate. |
| `docs/adrs/ADR-147-agent-capability-coverage-pipeline.md` | Defines ACC as cross-adapter mapping from real capabilities to agentic primitives. | Implemented as `scripts/acc_pipeline.py`; useful for primitive gap detection. |
| `docs/architecture/primitive-readiness-continuity-plan.md` | Living plan for evolving docs, scripts, hooks, rules, skills, memory, and harness adapters into governed primitives. | Best current continuity map for primitive evolution. |
| `docs/architecture/headless-self-improvement-proposer.md` | Explains propose-only self-improvement and the discipline gate. | Current boundary: self-improvement proposes, does not auto-merge. |
| `docs/self-usage-audit.md` | Older audit finding many loops were passive or incompletely registered. | Still useful as caution: design intent must be verified against active profiles, not docs alone. |
| `docs/research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md` | Places Obsidian as human-readable graph/audit layer over Engram, not memory authority. | Supports self-improvement by making memory/relations reviewable, but not by directly editing runtime. |

## Implementations found

### 1. Memory and knowledge layer

| Implementation | Role | Status |
|---|---|---|
| `lib/engram_lifecycle.py` | Confidence, decay, reinforcement metadata around Engram observations. | Implemented and tested. |
| `lib/engram_crystallizer.py` | Consolidates repeated observations into pattern digests. | Implemented with deterministic synthesis; not LLM synthesis. |
| `lib/engram_graph_walker.py` | Read-only traversal of typed Engram relations. | Implemented; depends on local SQLite relation table. |
| `hooks/engram-reinforce-on-access.sh` | Reinforces observations when accessed. | Implemented hook. |
| `hooks/engram-crystallize-on-session-end.sh` | Session-end crystallization. | Implemented hook. |
| `lib/engram_obsidian_exporter.py` and `hooks/engram-obsidian-export-on-stop.sh` | Human-facing graph export and optional Stop-hook export. | Implemented; opt-in via `COS_OBSIDIAN_VAULT`. |

**Interpretation**: this layer helps the SO remember failures, decisions, patterns, and relations. It is a support layer for self-improvement, not the executor of self-repair.

### 2. Error learning and auto-repair

| Implementation | Role | Status |
|---|---|---|
| `hooks/error-learning.sh` / `hooks/error-pipeline.sh` | Captures failures into JSONL. | Implemented. |
| `hooks/error-pattern-detector.sh` | Surfaces repeated error patterns before future work. | Implemented. |
| `hooks/auto-repair-dispatcher.sh` | Detects failing Agent/Bash output, suggests fixes, and after repeated errors attempts repair. | Implemented, advisory, exits 0. |
| `lib/auto_repair.py` | Worktree-isolated repair engine with safety blocklist, registry lookup, verification, and circuit breaker integration. | Implemented and unit-tested. |
| `lib/circuit_breaker.py` | Failure threshold / cooldown state. | Implemented and tested. |
| `scripts/cos-repair` / `scripts/cos_repair.py` | Repair CLI surface. | Present. |

**Safety boundary**: auto-repair blocks secrets, auth, payments, migrations, and infrastructure-sensitive paths; successful worktree repair returns a diff rather than silently merging into the main worktree.

### 3. Skill quality, repair, and optimization

| Implementation | Role | Status |
|---|---|---|
| `hooks/skill-feedback-tracker.sh` | Records per-skill success/failure and warns on repeated failures. | Implemented. |
| `hooks/skill-failure-monitor.sh` | Stop hook that emits repair signals to `skill-repair-queue.jsonl`. | Implemented. |
| `lib/skill_failure_repair.py` | Detects failing skills and proposes `regenerate`, `investigate`, or `deprecate`. | Implemented and tested. |
| `packages/skill-governance/skills/optimize-skill/SKILL.md` | Manual iterative skill optimization loop. | Implemented as a skill; modifies only target `SKILL.md` per iteration. |
| `packages/skill-governance/skills/self-improve/SKILL.md` | Meta wrapper around analysis/apply phases with human gate. | Implemented as a skill; human gate is explicit. |
| `lib/skill_synthesizer.py` | Drafts experimental skills from recurring successful tool sequences. | Implemented and tested; promotion is operator-gated. |
| `hooks/auto-skill-generator.sh` | Generates draft skills from complex successful Agent completions. | Implemented, but current activation depends on profile/settings. |

**Interpretation**: primitive improvement is deliberately detect/signal/draft first. Direct auto-regeneration is rejected to prevent runaway loops.

### 4. Consequence engine and learning pipeline

| Implementation | Role | Status |
|---|---|---|
| `lib/consequence_engine.py` | Promotes, maintains, warns, degrades, or disables skills/agents based on trust-score streaks. | Implemented and tested. |
| `hooks/consequence-evaluator.sh` | Hook bridge from tool output to consequence engine. | Implemented. |
| `hooks/dispatch-gate.sh` | Blocks disabled skills and applies model downgrades/circuit constraints before launch. | Implemented. |
| `hooks/completion-gate.sh` | Completion validation/retry/quality gate surface. | Implemented. |
| `lib/learning_pipeline.py` | Bridges prompt classifier, skill archive, consequence engine, error classifier, and trigger surfacing. | Implemented and tested. |
| `lib/skill_archive.py` | Stores skill execution snapshots and trend data. | Implemented. |
| `hooks/session-learning.sh` and `hooks/kpi-trigger.sh` | Session-level learning and self-improve recommendation flags. | Implemented. |

**Interpretation**: these pieces are the “nervous system” for adapting behavior: route cheaper models for degraded skills, block disabled skills, and recommend optimization.

### 5. Primitive evolution and coverage loop

| Implementation | Role | Status |
|---|---|---|
| `scripts/active_primitive_index.py` | Lists active/default/runtime primitive rows from lifecycle manifest. | Implemented. |
| `scripts/primitive_readiness_ledger.py` | Script role/readiness ledger. | Implemented. |
| `scripts/primitive_family_readiness_ledger.py` | Hook/skill/rule family ledgers. | Implemented. |
| `scripts/primitive_gap_snapshot.py` | Finds primitive gaps. | Implemented. |
| `scripts/primitive_coverage.py` | Coverage/claim proof support. | Implemented. |
| `scripts/acc_pipeline.py` | Agent Capability Coverage orchestrator over readiness/audit surfaces. | Implemented. |
| `scripts/cos_primitive_harvester.py` | Advises whether a conversation should become a primitive. | Implemented; no direct writes. |
| `scripts/cos_self_improvement_loop.py` | Propose-only improvement plan builder. | Implemented. |
| `scripts/cos_doctrine_proposer.py` | Proposed doctrine amendments under docs proposals. | Implemented. |
| `scripts/cos-self-improvement-discipline-gate` | Checks self-improvement proposals do not enable unsafe mutation. | Implemented. |

**Current sample output checked on 2026-05-05**:

- `scripts/cos_self_improvement_loop.py --profile core --json` emitted `mode: propose_only`, `policy.human_approval_required: true`, `policy.auto_merge: false`, and 3 proposals.
- `scripts/cos_doctrine_proposer.py --profile core --json` emitted 2 doctrine proposals and a policy stating proposals do not change runtime behavior.

## How Obsidian/Engram helps this loop

Obsidian is useful for self-improvement in three specific ways:

1. **Auditability**: exported Engram observations let humans inspect why a primitive was changed or why a repair path exists.
2. **Relation navigation**: wikilinks over typed Engram relations make it easier to navigate from failure pattern → ADR → primitive → test.
3. **Crystallization review**: repeated session learnings can be reviewed as semantic patterns before promotion to docs, skills, or scripts.

It should not become the executor. The executor remains the governed primitive loop: hooks, scripts, skills, tests, manifests, and human approval gates.


## Cross-project primitive improvement target

The desired end state is not only “agents are not amnesic.” It is a governed
learning system where evidence from the SO and from consumer projects can improve
both sides without leaking state or silently mutating runtime behavior.

### Two improvement loops, one safety contract

| Loop | Learns from | May improve | Promotion boundary |
|---|---|---|---|
| SO self-improvement | SO-maintainer sessions, SO tests, primitive ledgers, ACC, Engram observations. | Core SO hooks, scripts, skills, rules, docs, manifests. | ADR/proposal/test gate before live runtime changes. |
| Consumer-project primitive improvement | Downstream project failures, local skill feedback, harness projection evidence, consumer evidence bundles. | Project-local `.cognitive-os/` extensions first; upstream SO primitives only through exported evidence/proposals. | Consumer keeps local authority; upstream accepts only reviewed, provenance-carrying proposals. |

A project that implements the SO should be able to generate local improvement
signals such as:

- “this projected skill failed five times on this stack”;
- “this hook is too strict for this harness”;
- “this local workflow repeated often enough to become a project skill”;
- “this SO primitive needs a driver for this IDE/harness”;
- “this repair pattern worked in this project and should be proposed upstream.”

Those signals should become **proposals**, not direct upstream mutations.

### Transfer path for consumer learnings

The existing cross-instance runway already contains the right primitives:

1. Consumer project records local evidence in JSONL metrics, Engram observations,
   ACC outputs, and primitive readiness rows.
2. Consumer exports a bounded evidence package through the ADR-136 runway
   (`cos-export-consumer-evidence`, `cos-engram-bundle`, registry locks, or later
   Engram cloud sync).
3. Upstream imports evidence in propose-only mode (`cos-import-consumer-evidence`,
   `cos-engram-import-propose`) and preserves provenance/independence metadata.
4. The SO converts repeated evidence into one of:
   - a project-local extension recommendation;
   - a candidate SO primitive improvement;
   - a harness projection gap;
   - a docs/ADR update;
   - a rejected/non-transferable local pattern.
5. Promotion follows normal gates: tests, lifecycle metadata, ACC/consumer
   projection proof, and human review.

This keeps the “learning across projects” promise honest: consumer projects can
teach the SO, but only through reviewable evidence. A maintainer-owned drill does
not sign external adoption, and a consumer-local workaround does not become a
core primitive without proof.

### What should travel versus stay local

| Artifact | Travels upstream? | Notes |
|---|---:|---|
| Sanitized failure pattern | Yes | No secrets, no proprietary payloads, include stack/harness metadata. |
| Primitive readiness gap | Yes | Good input to ACC and lifecycle backlog. |
| Successful repeated workflow | Yes, as proposal | Draft skill/script only; no automatic promotion. |
| Consumer project credentials/config | No | Never copy `.env`, tokens, Keychain, provider auth, or local IDE state. |
| Project-specific business rules | Usually no | Keep as project-local primitives unless multiple independent projects confirm generality. |
| Engram observations | Yes, only via scoped bundle/propose import | Preserve `project`, `topic_key`, provenance, and conflict review. |
| Obsidian vault | No by default | It is an operator-local graph view; export/import should use Engram bundles or sanitized docs. |

### Required additional primitive

The explicit primitive is now implemented as **consumer improvement proposal export/import**.
It summarizes local consumer signals into a portable, sanitized proposal
bundle rather than dumping raw memory or full vault content.

Suggested shape:

```bash
scripts/cos-export-consumer-improvement-proposals \
  --project my-service \
  --since 30d \
  --profile core \
  --threshold 3 \
  --output /tmp/my-service-cos-improvement-proposals.json
```

The bundle should include:

- project/harness/profile metadata;
- primitive ids involved;
- failure/success counts;
- linked tests or manual proof;
- sanitized excerpts only;
- provenance and independence fields;
- recommended action: `project-local`, `upstream-candidate`, `harness-gap`,
  `docs-only`, or `reject`.

The matching upstream import should be propose-only:

```bash
scripts/cos-import-consumer-improvement-proposals \
  /tmp/my-service-cos-improvement-proposals.json
```

and write only under `.cognitive-os/improvements/proposals/` or
`docs/proposals/` until reviewed.

## Implementation reality matrix

| Capability | Designed? | Implemented? | Autonomous by default? | Notes |
|---|---:|---:|---:|---|
| Capture errors and sessions | Yes | Yes | Mostly yes when hooks are active | JSONL metrics plus Engram/session summaries. |
| Detect repeated error patterns | Yes | Yes | Advisory | Warns; does not silently change code. |
| Worktree-isolated known-fix repair | Yes | Yes | Limited/advisory | Safety blocklist; returns diff, no auto-merge. |
| Skill degradation detection | Yes | Yes | Signal-only | Emits queue; no auto-regeneration. |
| Skill optimization | Yes | Yes | Manual/gated | `/optimize-skill`. |
| Synthesize new skill drafts | Yes | Yes | Draft-only | Promotion requires operator action. |
| Consequence-based promote/degrade/disable | Yes | Yes | Partially automatic | Depends on hook/profile activation and trust-report extraction. |
| Propose self-improvement plans | Yes | Yes | Propose-only | No auto-merge or core/team auto-promotion. |
| Propose doctrine amendments | Yes | Yes | Propose-only | Writes only proposal docs when `--write`. |
| Promote primitives across lifecycle tiers | Yes | Partially | No | Requires evidence, lifecycle metadata, tests, and approval. |
| Use Obsidian as source of truth | Rejected | No | No | Obsidian remains derived graph/audit view. |

## Gaps and cautions

1. **Activation/profile drift matters**: docs describe loops, but current behavior depends on hook registration in active harness settings and profile projection.
2. **Some docs are older than current implementation**: `docs/self-usage-audit.md` records a weaker state and should be treated as historical caution, not the latest status.
3. **Self-improvement is governed, not free-running**: ADR-083/134/135 deliberately reject silent live-rule edits, auto-merge, and auto-promotion to core/team.
4. **Skill repair is signal-first**: the repair queue exists to prevent runaway regeneration.
5. **Primitive improvement is broader than skills**: current ledgers cover scripts, hooks, skills, and rules, but promotion still needs lifecycle metadata and proof.
6. **Engram/Obsidian are support layers**: they improve memory, audit, and relation traversal, but they do not replace tests or approval gates.

## Recommended next implementation slice

1. Add a single “self-evolution status” runbook or command output that summarizes:
   - active hooks related to self-improvement;
   - latest error-learning, skill-feedback, consequence, and repair-queue counts;
   - latest ACC/primitive readiness status;
   - whether `COS_OBSIDIAN_VAULT` export is active.
2. Add a manual test under `docs/manual-tests/` proving the self-improvement loop end-to-end without mutating live rules:
   - inject sample error/skill metrics into temp metrics dir;
   - run skill failure monitor or Python module;
   - run `scripts/cos-self-improvement-loop --profile core --json`;
   - verify `mode: propose_only` and `human_approval_required: true`.
3. Add a consumer improvement proposal exporter/importer pair so downstream projects can propose project-local or upstream primitive improvements without leaking raw memory or credentials.
4. Link Obsidian exported notes to primitive ids and ADRs, but keep `docs/` as the canonical curated surface.

## Verification commands used for this audit

```bash
engram search "auto mejora auto reparación self improve auto repair primitive improvement primitives" --limit 10

grep -RIn "auto[- ]\?improve\|self[- ]\?improve\|auto[- ]\?repair\|self[- ]\?repair\|primitive.*improv\|improv.*primitive\|optimize-skill\|repair\|reaper\|drift\|crystalliz\|reinforce\|skill.*feedback\|learning" docs rules hooks skills scripts lib tests manifests packages .cognitive-os

python3 scripts/cos_self_improvement_loop.py --profile core --json
python3 scripts/cos_doctrine_proposer.py --profile core --json
python3 scripts/active_primitive_index.py --project-dir . --json
```

## Key Learnings

1. Obsidian/Engram support self-improvement as memory and audit layers, but the actual repair/improvement executor is the governed MAPE-K primitive loop.
2. Cognitive OS intentionally favors propose-only and queue-based repair for high-risk self-modification surfaces.
3. Primitive evolution is now mediated by readiness ledgers, ACC, lifecycle metadata, and discipline gates rather than ad hoc docs claims.
4. Consumer projects should improve their own local primitives first and export sanitized, provenance-carrying proposals upstream only when evidence is transferable.
