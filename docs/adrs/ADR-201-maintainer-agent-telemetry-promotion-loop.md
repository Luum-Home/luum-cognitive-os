# ADR-201 — Maintainer Agent and Telemetry Promotion Loop

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A propose-only loop implemented  
**Date**: 2026-05-06  
**Related**: ADR-031, ADR-083, ADR-090, ADR-095, ADR-134, ADR-135, ADR-146, ADR-147, ADR-164, ADR-199, ADR-200  
**Report**: `docs/reports/self-improvement-maintainer-agent-gap-2026-05-06.md`

---

## Context

Cognitive OS already emits many operational signals: skill feedback, dispatch
metrics, action receipts, cost events, error learning, primitive readiness, and
state-retention audits. It also has propose-only self-improvement primitives.

The remaining failure mode is ownership. Most agents run because a human invoked
them for a project task. No always-on or scheduled agent has the explicit
contract to read Cognitive OS telemetry, detect degraded skills/providers/router
behavior, propose bounded changes, validate candidate impact, and request human
approval.

This means the system can be self-observing without being reliably
self-improving. The data exists in fragments, but disparity does not become
action unless a human or ad-hoc agent notices it.

The Hermes-style pattern of packaging skills solves provider/registry concerns:
capabilities can be distributed and consumed by a host. Cognitive OS also needs
a maintainer loop: consume skills, measure outcomes, produce/refine primitives,
and evaluate whether the change improved the system.

## Decision

Introduce a **Maintainer Agent** as a bounded, scheduled, propose-only runtime
role for Cognitive OS.

The maintainer agent owns this loop:

```text
observe telemetry -> detect drift -> propose change -> validate candidate -> request approval -> measure post-change impact
```

It may generate proposals, branches, candidate skill drafts, ADR amendments, and
verification plans. It may not auto-merge, auto-promote core/team primitives, or
silently mutate live runtime surfaces.

Add a first-class `PromoteFromTelemetry` primitive that converts repeated
runtime evidence into typed improvement proposals.

The primitive accepts evidence from at least:

- skill invocation and feedback streams;
- router/dispatch fallback streams;
- trust-report and verification outcomes;
- cost/rate-limit events;
- action receipts;
- primitive readiness and lifecycle ledgers;
- state-retention and reliability audits;
- rejected or ignored router suggestions, especially for safety/recovery primitives.

The first implementation must create a canonical **performance ledger** for
skills, providers, router choices, and selected agentic primitives. Each row must
be traceable to source metrics and include enough information to compare baseline
versus candidate behavior.

The performance ledger is a hard dependency. `PromoteFromTelemetry`, the
maintainer runner, post-change impact scoring, and proposal prioritization must
not ship as production behavior until slice 1 can compile a validated ledger from
fixture and live telemetry. Any implementation PR should mark the ledger slice as
the blocker in its title or commit/PR summary.

The ledger must validate signal quality before calculating rollups. It must flag
or quarantine malformed rows, impossible defaults, and identity corruption such
as a trust score defaulting to `75` without source evidence or skill-feedback
rows where `skill` contains a person/operator name instead of a skill id. Dirty
signals may be preserved for forensics, but they must not drive promotion,
demotion, confidence changes, or provider compatibility decisions.

The maintainer agent is cross-harness by contract. It may consume telemetry from
Claude Code, Codex, local CLI, service/headless workers, and future cloud hosts,
but proposals must be emitted in a harness-agnostic schema. Harness-specific
metadata is evidence context, not the proposal format.

## Signal quality gate

Before ledger rollups, the implementation must classify source rows as one of:

| Class | Meaning | May drive proposals? |
|---|---|---:|
| `valid` | Schema-valid, source-identifiable, semantically plausible. | Yes |
| `suspect` | Parseable but semantically odd, defaulted, or weakly sourced. | No, unless manually reviewed |
| `corrupt` | Malformed, wrong identity field, impossible value, or missing required source. | No |

The ledger output must report signal-quality counts per source stream. A high
suspect/corrupt ratio is itself a maintainer finding, but it must not be blended
into performance scoring.

## Cross-harness telemetry boundary

ADR-201 consumes telemetry from any supported harness, but it must not create a
separate maintainer agent per harness as the default product shape. The default
is one OS-level maintainer loop over normalized evidence:

```text
harness telemetry -> normalized ledger row -> harness-agnostic proposal
```

Harness-specific proposals are allowed only when the affected primitive or driver
is explicitly harness-scoped.

## Required proposal schema

Every generated proposal must include:

- proposal id;
- severity (`P0`, `P1`, `P2`, `P3`);
- self confidence (`0.0` to `1.0`);
- source metric streams;
- source event ids or line references when available;
- affected primitive/provider/skill/router rule;
- observed degradation or opportunity;
- candidate action;
- allowed write paths;
- blocked write paths;
- tests required before review;
- rollback plan;
- cooldown after apply;
- related proposals;
- experiment design, including canary scope or A/B plan when applicable;
- expected impact metric;
- human approval requirement;
- post-change measurement window.

Proposal ids must be deterministic for deduplication:

```text
proposal_id = hash(surface + degradation_pattern + day_window)
```

A second finding for the same surface/pattern/window must update or reference the
existing proposal rather than create a competing duplicate.

## Implementation contracts

### Proposal YAML shape

The initial implementation should write proposal records compatible with this
shape, whether stored as JSON or YAML:

```yaml
proposal_id: perf-ledger-router-auto-rollback-2026w19
schema_version: maintainer-proposal/v1
severity: P1
self_confidence: 0.78
surface: skill-router
harness_scope: harness-agnostic
source_metric_streams:
  - .cognitive-os/metrics/skill-suggestion.jsonl
  - .cognitive-os/metrics/skill-feedback.jsonl
source_event_refs: []
affected_primitive: lib/skill_router.py
degradation_pattern: recovery_skill_suggested_in_meta_discussion
candidate_action: add negative-context guard and tests
allowed_write_paths:
  - lib/skill_router.py
  - tests/unit/test_skill_router.py
blocked_write_paths:
  - .env
  - secrets/
tests_required:
  - python3 -m pytest tests/unit/test_skill_router.py -q
rollback_plan: revert candidate commit or disable new routing pattern
cooldown_after_apply: P7D
related_proposals: []
experiment_design:
  type: canary
  canary_scope: maintainer repo prompts + fixture corpus
  success_metric: false_positive_rate decreases without direct-intent recall loss
expected_impact_metric: fewer ignored/scary router suggestions
post_change_measurement_window: P7D
human_approval_required: true
outcome_on_regression: quarantine_proposal_and_open_manual_investigation
```

### Storage decision for the Performance Ledger

Slice 1 stores the canonical ledger in local SQLite, with JSONL export for audit
and portability:

- primary local store: `.cognitive-os/ledgers/performance-ledger.sqlite`;
- append/export stream: `.cognitive-os/metrics/performance-ledger.jsonl`;
- generated summaries: `.cognitive-os/reports/performance-ledger-latest.json`.

SQLite is the default because the maintainer loop needs joins, deduplication,
source-row references, and local service queries without requiring Postgres. A
future cloud control plane may replicate sanitized ledger rows into Postgres, but
that is not the local default.

### Service-mode security boundary

When the maintainer agent runs under `cosd`, a container, or any headless service
mode, every mutating action must pass through ADR-164 Host CLI Bridge Security
Boundary or its successor. Scheduled/headless invocation may observe and propose
without additional authorization, but execution of cleanup, file mutation, branch
creation, or proposal application requires the host-CLI security boundary,
operator policy, and audit receipt.

### Maintainer model policy

Default model policy:

| Phase | Default model | Escalation |
|---|---|---|
| ledger normalization | deterministic local code | none |
| proposal drafting | sonnet-class model | opus-class only for P0/P1 ambiguity or architecture decisions |
| candidate implementation | sonnet-class model | opus-class for complex debugging/architecture |
| final adversarial review | opus-class or external reviewer | required for P0/P1 |

The maintainer agent must not run an opus-class model continuously. Service-mode
scheduling should batch observations and use the cheapest model that satisfies
the proposal/review phase.

### Outcome-failure protocol

If post-change measurement shows regression or inconclusive impact:

1. mark the proposal outcome as `regressed` or `inconclusive`;
2. quarantine the proposal pattern from automatic re-application;
3. open a manual investigation item with source evidence;
4. apply the rollback plan only after human approval and normal destructive-git
   boundaries;
5. penalize maintainer self-confidence for similar future patterns until a
   reviewed correction lands;
6. feed the regression back into `PromoteFromTelemetry` as first-class evidence.

No maintainer-generated change may be considered successful only because tests
passed at apply time. Runtime impact measurement is part of the contract.

## Safety boundaries

The maintainer agent is not allowed to:

- merge to `main`;
- bypass ADR/proposal discipline gates;
- mutate `.env`, credentials, keys, provider auth, or user secrets;
- promote a primitive to `core` or `team` without human approval;
- delete or decommission primitives without a reversible archive/tombstone path;
- treat maintainer-owned drill evidence as external adoption evidence;
- lower safety gates just to improve apparent success rate;
- treat a quoted or critiqued skill command as positive invocation intent without negative-context checks.

## Relationship to ADR-134

ADR-134 created a headless self-improvement proposer. This ADR adds the missing
ownership and telemetry-performance layer.

ADR-134 answers:

> Can audits become bounded proposals?

ADR-201 answers:

> Who continuously reads runtime performance, decides which proposals to create,
> validates impact, and keeps the loop alive?

ADR-201 does not replace ADR-134. It schedules and feeds it with richer evidence.

## Consequences

### Positive

- Self-improvement stops depending on a human noticing scattered JSONL signals.
- Skill/router/provider degradation can produce a reviewed fix proposal before
  users experience repeated failures.
- Aspirational or dormant primitives can be decommissioned through evidence, not
  memory or taste.
- Product claims become more defensible: self-improvement is governed, measured,
  and owner-backed.

### Negative / trade-offs

- Adds a new background role that must itself be bounded and observable.
- Requires a canonical performance ledger over existing fragmented metrics.
- Proposal quality depends on source telemetry quality.
- A noisy maintainer agent could become operational debt unless cooldowns,
  budgets, deterministic proposal ids, and duplicate suppression are strict.
- SQLite introduces a local schema/migration surface for the performance ledger.

## Alternatives rejected

- **Skill registry only**: rejected because packaging capabilities does not own
  runtime outcomes.
- **Dashboard first**: rejected because visualization does not close the loop.
- **Auto-merge self-modification**: rejected because it violates governed
  self-improvement and creates high blast radius.
- **Human-only review of metrics**: rejected because it does not scale to
  service/headless/cloud operation.
- **Surface-by-surface one-off bots**: rejected because it repeats the
  self-bite pattern: local fixes without a universal ownership protocol.

## Implementation slices

1. **BLOCKER**: add `lib/performance_ledger.py` for skill/provider/router
   primitive rollups, including signal-quality validation before scoring.
2. Add `scripts/cos-performance-ledger` to produce JSON and human summaries with
   valid/suspect/corrupt counts per source stream.
3. Add `lib/promote_from_telemetry.py` and `scripts/cos-promote-from-telemetry`.
4. Add `scripts/cos-maintainer-agent` as a propose-only orchestrator over the
   validated ledger and ADR-134 proposal writer.
5. Add scheduled/headless invocation with lock, cooldown, budget limits, and
   ADR-164 host-CLI authorization for every mutation.
6. Add smoke tests proving a telemetry pattern creates one bounded proposal.
7. Add router negative-evidence capture for ignored/scary suggestions such as
   `/auto-rollback` in meta-discussions.
8. Add post-change impact measurement before any promotion can be marked
   successful.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_performance_ledger.py -q
python3 -m pytest tests/unit/test_performance_ledger_signal_quality.py -q
python3 -m pytest tests/unit/test_promote_from_telemetry.py -q
python3 -m pytest tests/behavior/test_maintainer_agent_loop.py -q
scripts/cos-performance-ledger --json
scripts/cos-promote-from-telemetry --dry-run --json
scripts/cos-maintainer-agent --once --dry-run --json
```

The ledger tests must prove that corrupt skill-feedback rows and unsourced
trust-score defaults are quarantined before rollups. The proposal tests must
prove deterministic proposal-id deduplication and required schema fields
including severity, self-confidence, cooldown, related proposals, and experiment
design. The behavior test must prove that repeated skill/router degradation
creates a single bounded harness-agnostic proposal with human approval required,
allowed write paths, tests, rollback plan, and outcome-failure protocol.

## Status

Accepted — Slice A implemented. The SQLite performance ledger, signal-quality quarantine, `PromoteFromTelemetry`, `cos-promote-from-telemetry`, and `cos-maintainer-agent --once --dry-run` are present and tested. Scheduled automation and mutation remain future/opt-in.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
