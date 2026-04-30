# Conversation Reality Audit — 2026-04-30

> Investigation plan for validating whether Cognitive OS is real daily leverage or an overgrown aspirational system.

## Purpose

The conversation raises the right product risk: Cognitive OS may contain a real core, but its surface area can make it hard to know which pieces actually fire, which pieces merely exist, and which pieces improve developer work enough to justify their cognitive cost.

This audit turns that concern into measurable evidence. It does not treat documentation, file existence, or claimed architecture as proof. A primitive is counted as real only when it has runtime wiring, behavioral evidence, and a user-visible outcome.

## Questions Under Review

1. Which capabilities are real behavior versus aspirational or dormant assets?
2. How efficient is the system for normal day-to-day development?
3. How friendly is the developer experience for both maintainers and new adopters?
4. Which developer pains does the system remove, and which pains does it create?
5. How automatic is the system in practice, without hidden manual rituals?
6. Where is Cognitive OS materially better or worse than prior alternatives such as Hermes, OpenClaw, and vanilla harness workflows?

## Acceptance Criteria

1. Each major product claim is classified as `proven`, `partial`, `aspirational`, or `harmful-overhead` with concrete evidence.
2. Every `proven` claim has at least one runtime path and one behavioral test or captured metric.
3. Every `aspirational` claim names the file, hook, skill, rule, or doc that makes the unsupported claim.
4. Daily-development cost is measured with wall-clock latency, tool-call count, hook count, and token/context payload estimates.
5. DX findings include at least one maintainer workflow and one fresh-adopter workflow.
6. Competitive comparison is based on actual installed behavior or documented prior-art findings, not product-language preference.
7. The final report recommends deletion, demotion, packaging, or hardening for each high-cost surface.

## Initial Evidence Snapshot

These measurements were taken from the working tree on 2026-04-30.

| Signal | Result | Interpretation |
|---|---:|---|
| `dogfood_score.py --json` overall | 65.22 / 100 | The system is substantive but not mature enough for broad top-level claims. |
| Hook wiring | 76 / 165 registered and tested | Less than half of hook files have both runtime registration and test references. |
| Skill coverage | 35 / 143 by dogfood heuristic | Skill catalog is much larger than its direct behavioral proof surface. |
| Harness portability | 268 / 495 clean files | `.claude` / `CLAUDE_PROJECT_DIR` gravity is still significant. |
| Metrics JSONL files | 72 non-empty / 94 total | Many subsystems emit evidence, but 22 metric streams are empty. |
| Hook timing events | p50 324 ms, p95 1622 ms, max 13332 ms | Latency is now measurable; p95 hook cost is meaningful for turn feel. |
| `skill-feedback-tracker.sh` | registered in `.claude/settings.json` now | The earlier detached-hook claim appears historically true but needs current-status phrasing. |

## Audit Model

### Classification Labels

- `proven`: registered or invoked, exercised by behavioral tests, and producing durable runtime evidence.
- `partial`: implemented and partly wired, but missing either consumption, tests, metrics, or user-visible closure.
- `aspirational`: documented or present on disk, but no live invocation path or behavioral proof.
- `harmful-overhead`: real behavior whose runtime, cognitive, or maintenance cost exceeds observed value.

### Evidence Hierarchy

1. Runtime invocation observed in settings, hook timing, JSONL metrics, or command output.
2. Behavioral test that executes the path and checks side effects.
3. Integration with a consumer that uses the emitted signal.
4. Documentation or ADR only.
5. File existence only.

Documentation and file existence are supporting context, not proof.

## Workstream A — Hype Versus Behavior

### Method

1. Inventory hooks, skills, rules, scripts, libs, templates, dashboards, and squads.
2. For each item, compute:
   - declared purpose
   - invocation path
   - consumer path
   - metric output
   - behavioral tests
   - last meaningful activity
3. Build a `reality matrix` with the classification labels above.
4. Flag contradiction patterns:
   - documented in README but not registered
   - registered but never emits metrics
   - emits metrics but nobody consumes them
   - tests only check existence or metadata
   - ADR says accepted but implementation is absent or stale

### Commands

```bash
uv run python3 scripts/dogfood_score.py --json
python3 scripts/cos_test_quality_audit.py --json
python3 -m pytest tests/audit/ -q
python3 -m pytest tests/contracts/ -q
```

### Outputs

- `docs/reports/reality-matrix-2026-04.md`
- deletion/demotion candidates grouped by primitive type
- list of product claims that need wording changes

## Workstream B — Daily Efficiency Baseline

### Method

Measure a realistic loop, not isolated scripts:

1. start session
2. inspect context
3. edit one small file
4. run focused validation
5. run broad-enough validation
6. produce summary or commit-ready state

Capture:

- wall-clock time
- hook invocations
- p50/p95 hook latency
- total tool calls
- context payload estimate
- number of user-visible interruptions
- number of manual recovery steps

### Scenarios

| Scenario | Purpose |
|---|---|
| vanilla Codex or Claude Code, no COS | control baseline |
| COS default profile | expected daily path |
| COS full profile | upper-bound governance cost |
| self-hosting repo | worst-case internal dogfood |
| fresh client repo | adoption reality |

### Outputs

- `docs/reports/dx-efficiency-baseline-2026-04.md`
- recommended default profile limits
- hooks to disable, merge, or make async

## Workstream C — Developer Experience

### Maintainer DX Checks

- Can a maintainer find the right skill without grep?
- Can a hook be added without hand-editing multiple projection files?
- Can parallel ADR work avoid number collisions?
- Can symlinked libs and generated projections be understood by subagents without repeated prompting?
- Can failures explain what blocked and how to fix it?

### Fresh-Adopter DX Checks

- Can a new project install core safely?
- Can the user see which hooks are active versus available?
- Can the user understand optional packages without reading the whole repo?
- Can the user remove or downgrade noisy rules?
- Can the user run one command that proves the system works?

### Outputs

- DX friction table with severity and fix owner
- onboarding proof checklist update
- candidate CLI UX improvements

## Workstream D — Pain Removed Versus Pain Added

### Pain Removed Ledger

For each claimed benefit, require a before-and-after story:

| Pain | COS mechanism | Evidence required |
|---|---|---|
| lost context across sessions | Engram / memory lifecycle | recovered decision in a new session |
| agents say done too early | acceptance criteria / completion gates | blocked or corrected premature completion |
| unsafe edits | pre-tool hooks / policy gates | prevented destructive or secret-touching action |
| model churn | provider normalization / harness drivers | same contract across two harnesses or providers |
| test sprawl | `cos-test` lanes | focused validation selects useful subset |

### Pain Added Ledger

Track costs the system itself introduces:

- hook-chain latency
- catalog lookup friction
- ADR coordination collisions
- noisy governance prompts
- generated-file confusion
- optional service setup complexity
- false-positive blocks

### Output

A net-value table: `removed`, `added`, `net`, `recommended action`.

## Workstream E — Automagic Reality

### Automation Maturity Scale

1. `manual`: user must know and run the command.
2. `assisted`: system suggests the command but does not execute safely.
3. `wired`: hook or workflow fires automatically.
4. `closed-loop`: emitted signal is consumed by another primitive.
5. `self-correcting`: system verifies outcome and repairs or escalates.

Each automagic claim must be placed on this scale.

### Focus Areas

- memory persistence and retrieval
- rule tier expansion
- hook profile projection
- feedback loop closure
- auto-rollback and auto-refine
- skill discovery and routing
- ADR numbering and governance

## Workstream F — Alternatives and Prior-Art Comparison

### Comparison Axes

- governance strength
- progressive disclosure
- skill discoverability
- memory model
- cross-harness portability
- setup complexity
- daily latency
- proof quality
- deletion discipline

### Required Comparisons

- vanilla Claude Code / Codex
- Hermes Agent
- OpenClaw
- relevant prior tools already captured in research logs

### Output

A scored comparison matrix with explicit `COS wins`, `COS loses`, and `uncertain` cells.

## Decision Rules

| Finding | Action |
|---|---|
| proven and high-value | keep core and improve docs/demo |
| proven but noisy | make configurable, async, or profile-gated |
| partial with clear value | harden with consumer, metric, and behavioral test |
| partial with low value | demote to optional package or archive |
| aspirational and user-facing | remove from product story until proven |
| aspirational and internal-only | archive or mark experimental |
| harmful-overhead | delete, merge, or disable by default |

## Final Report Shape

The final report should answer in this order:

1. One-page verdict: real core, inflated surface, top risks.
2. Scorecard across the six user questions.
3. Evidence table for the most important claims.
4. Delete/demote/harden recommendations.
5. Default-profile changes that reduce daily friction.
6. Claims that marketing/docs must stop making.
7. Next measurement cadence.

## Current Working Verdict

Cognitive OS appears real but overgrown. The strongest evidence supports governance, verification, memory continuity, and portability work. The weakest evidence is around broad automagic claims, large skill/rule catalogs, and advanced remediation loops. The next best move is not another feature sprint; it is a reality-reduction sprint that measures, deletes, demotes, or hardens every high-cost surface.

## Living Investigation Checklist

Use this checklist as the working board for the primitive-by-primitive reality audit. Mark each item only when backed by evidence in repo, metrics, tests, or command output.

### 0. Baseline Inventory

- [x] Capture current dogfood score and dimension breakdown.
- [x] Count primitive families: hooks, rules, skills, agents, memory, MCP/tools, config/projection, metrics, tests, docs/ADRs.
- [x] Record initial hook wiring, skill coverage, metrics emptiness, and hook latency snapshot.
- [x] Create `docs/reports/primitive-gap-matrix-2026-04.md` with row-level findings.
- [x] Define final severity taxonomy for gaps: blocker, high, medium, low.

### 1. Hooks

- [ ] Inventory all hook files and map each to lifecycle event: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, or unsupported.
- [ ] Mark each hook as registered, unregistered, generated-only, deprecated, or optional-package.
- [ ] Identify hooks with non-empty metrics output.
- [ ] Identify hooks with empty metrics output despite being registered.
- [ ] Identify hooks with behavioral tests versus existence/config-only tests.
- [ ] Identify hooks that emit signals nobody consumes.
- [ ] Identify hooks whose latency contributes materially to p95 turn delay.
- [ ] Identify overlapping hooks that should be merged.
- [ ] Classify each hook as proven, partial, aspirational, or harmful-overhead.
- [ ] Recommend keep / async / profile-gate / merge / demote / delete for each high-cost hook.

### 2. Skills

- [ ] Inventory all skills and frontmatter quality.
- [ ] Map each skill to actual invocation path: manual-only, contextual trigger, hook/router selected, or undocumented.
- [ ] Identify skills with behavioral tests.
- [ ] Identify skills with only catalog/frontmatter tests.
- [ ] Identify skills never referenced outside their own `SKILL.md`.
- [ ] Identify overlapping or duplicate skills.
- [ ] Identify skills that require hidden maintainer knowledge.
- [ ] Classify each skill as proven, partial, aspirational, or harmful-overhead.
- [ ] Recommend core / optional package / archive / merge / rewrite for each skill cluster.

### 3. Rules

- [ ] Inventory all rules and compact-index references.
- [ ] Verify tier metadata using the actual loader contract (`<!-- TIER: N -->`).
- [ ] Identify rules loaded by default versus contextual only.
- [ ] Identify rules referenced in docs but not loaded by runtime.
- [ ] Identify rules with enforcement hooks or tests.
- [ ] Identify rules that are purely advisory prose.
- [ ] Identify rules that duplicate other rules.
- [ ] Classify each rule as proven, partial, aspirational, or noisy-overhead.
- [ ] Recommend keep Tier-0/1, demote Tier-2, merge, or delete.

### 4. Agents and Subagents

- [ ] Inventory agent definitions and runtime spawning paths.
- [ ] Identify which agent behaviors are harness-native versus COS-defined.
- [ ] Verify whether agent prelaunch/context-injection hooks fire.
- [ ] Measure context payload added per delegated agent.
- [ ] Identify coordination gaps such as ADR number collisions.
- [ ] Classify agent primitives as proven, partial, aspirational, or DX-risk.
- [ ] Recommend boundaries for what COS should and should not own.

### 5. Memory

- [ ] Inventory memory hooks, libraries, skills, and Engram integration points.
- [ ] Map save, search, recall, prefetch, and compaction flows.
- [ ] Verify which memory writes happen automatically versus manually.
- [ ] Verify which memory reads influence later behavior.
- [ ] Identify emitted memory signals without consumers.
- [ ] Test a cross-session recall path with concrete evidence.
- [ ] Classify memory features as proven, partial, aspirational, or privacy/DX-risk.
- [ ] Recommend minimal default memory loop and optional advanced memory package.

### 6. MCP and Tool Integrations

- [ ] Inventory MCP/tool references in settings, docs, hooks, rules, skills, scripts, and tests.
- [ ] Separate installed/required/optional/reference-only tools.
- [ ] Identify tools described as available but not configured.
- [ ] Identify integrations that require credentials or services not checked by doctors.
- [ ] Identify integrations with graceful degradation.
- [ ] Identify integrations with product-facing claims but no live proof.
- [ ] Classify each integration as proven, partial, aspirational, or setup-risk.
- [ ] Recommend core dependency, optional adapter, documentation-only, or removal.

### 7. Config, Profiles, and Projection

- [ ] Inventory canonical config keys in `cognitive-os.yaml`.
- [ ] Map config keys to readers and runtime effects.
- [ ] Identify dead config keys with no readers.
- [ ] Identify hardcoded behavior that should read config.
- [ ] Verify projection into Claude, Codex, Cursor, Windsurf, or other drivers.
- [ ] Identify profile drift between default, standard, full, and self-hosting.
- [ ] Classify projection paths as proven, partial, aspirational, or portability-risk.
- [ ] Recommend config deletion, migration, or projection hardening.

### 8. Metrics and Observability

- [ ] Inventory JSONL metric streams and owning primitive.
- [ ] Identify streams that are non-empty, empty, stale, or ownerless.
- [ ] Identify metrics consumed by dashboards, scorecards, gates, or docs.
- [ ] Identify metrics that only accumulate noise.
- [ ] Verify append safety and rotation behavior for high-volume streams.
- [ ] Classify metrics as decision-grade, diagnostic-only, dead, or harmful-noise.
- [ ] Recommend retention, aggregation, deletion, or owner assignment.

### 9. Tests and Quality Gates

- [ ] Inventory tests by lane: unit, behavior, contract, integration, audit.
- [ ] Run `scripts/cos_test_quality_audit.py` and classify test quality.
- [ ] Identify tests that only check existence, frontmatter, or filenames.
- [ ] Identify critical primitives lacking behavioral tests.
- [ ] Identify quality gates that block real failures versus advisory-only gates.
- [ ] Identify flaky, skipped, xfailed, or resource-heavy tests.
- [ ] Classify gates as proven, partial, aspirational, or harmful-overhead.
- [ ] Recommend focused test additions and theater-test removals.

### 10. Docs, ADRs, and Product Claims

- [ ] Inventory product-facing claims in README, docs overview, business docs, and ADRs.
- [ ] Map each claim to code, tests, metrics, or manual proof path.
- [ ] Identify obsolete ADRs or accepted ADRs without implementation evidence.
- [ ] Identify roadmap/future docs presented as current behavior.
- [ ] Identify terminology drift from `agentic primitive`.
- [ ] Classify claims as proven, partial, aspirational, or misleading.
- [ ] Recommend wording changes, demotions, or archive moves.

### 11. Alternatives and Prior Art

- [ ] Compile prior research findings for Hermes, OpenClaw, vanilla Claude/Codex, and other investigated tools.
- [ ] Define comparison axes: governance, memory, skill discovery, setup, latency, portability, proof quality, deletion discipline.
- [ ] Score COS against alternatives using current evidence only.
- [ ] Identify copied/adopted patterns that are genuinely better.
- [ ] Identify alternative patterns COS should still adopt.
- [ ] Identify areas where COS loses and should stop pretending otherwise.

### 12. Final Reduction Sprint Backlog

- [ ] Produce keep/harden/demote/delete backlog ordered by DX and runtime impact.
- [ ] Pick default-profile changes that reduce daily friction immediately.
- [ ] Pick one hook merge candidate.
- [ ] Pick one skill-catalog simplification candidate.
- [ ] Pick one docs claim correction batch.
- [ ] Define monthly measurement cadence.

### 13. Periodic Automation

- [x] Add a repository script that generates a primitive gap snapshot from current repo evidence.
- [x] Append periodic snapshots to `.cognitive-os/metrics/primitive-gap-snapshot.jsonl`.
- [x] Generate a latest Markdown report at `docs/reports/primitive-gap-latest.md`.
- [x] Add a scheduled GitHub Actions workflow for weekly primitive gap snapshots.
- [ ] Add threshold-based escalation once baseline noise is reduced.
- [ ] Add issue/PR creation for new blocker/high regressions.
- [ ] Add row-level hook audit automation beyond family-level snapshot.
