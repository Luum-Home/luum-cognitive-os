---
adr: 172
title: Multi-Surface UI Architecture - CLI + Phoenix + Engram Cloud + Obsidian
status: accepted
date: 2026-05-05
supersedes: [ADR-170]
superseded_by: null
implementation_files:
  - scripts/cos-boring-reliability
  - scripts/cos-doctrine-proposer
  - scripts/cos-self-improvement-loop
  - docs/architecture/boring-reliability-control-plane.md
  - docs/architecture/cognitive-prosthesis.md
  - pyproject.toml
tier: maintainer
tags: [ui, cli, phoenix, engram-cloud, obsidian, multi-surface, governance]
---
# ADR-172: Multi-Surface UI Architecture

## Status

Accepted. Supersedes [ADR-170](ADR-170-operator-cli-as-primary-ui-surface.md).

## Context

Three prior ADRs framed the UI question through a single-surface lens:

- [ADR-169](ADR-169-dashboard-formal-demotion.md) (2026-05-05) demoted the in-tree
- [ADR-170](ADR-170-operator-cli-as-primary-ui-surface.md) (2026-05-05) demoted
  finding, declaring the Operator-CLI plus markdown reports as the primary surface.

Each of those ADRs implicitly assumed one UI surface should be canonical at any
already produces multiple distinct kinds of artefact, each of which has a
different ideal viewing surface:

| Artefact kind | Examples | Best surface |
|---|---|---|
| Live operator state | cos-boring-reliability JSON, hook reality, profile drift | Terminal CLI (fast, scriptable, pipe to jq) |
| LLM traces | OpenTelemetry spans, latency, cost, eval scores | Phoenix web UI (port 6006, see ADR-058) |
| Memory across sessions | Engram observations, decisions, conflict graphs | Engram Cloud (web, cross-instance, federated per ADR-136) |
| Long-form decisions / research notes | ADRs, doctrine documents, audit reports | Obsidian (or any markdown reader) |

Forcing all four into a single web dashboard would be a multi-sprint product
effort, would duplicate what Phoenix and Obsidian already do well, and would
re-create the same aspirational-not-real pattern that ADR-171 closed for
output is excellent for live state and pipe-friendly inspection, but is the
wrong shape for trace flame graphs, cross-session memory navigation, and
markdown rendering with embedded diagrams.

The honest design is to embrace multi-surface: each kind of artefact lives on
the surface that fits it best, and COS does not invent or maintain UIs where
existing tools already cover the need.

## Decision

The UI is **four cooperating surfaces**, not one. Each surface has a specific
artefact-kind contract and a defined activation path. None of them is mandatory
for COS to operate; each is opt-in.

### Surface 1 - Operator CLI (always-on, mandatory)

**Artefact kind**: live operator state.
**Activation**: built into the repo, no install needed.
**Entry points**: scripts/cos-boring-reliability, scripts/cos-doctrine-proposer,
scripts/cos-self-improvement-loop, scripts/cos-runtime-hook-reality,
scripts/cos-silent-failure-audit, scripts/cos-tier-claim-audit,
scripts/cos-cross-instance-drill, scripts/cos-recovery-drill,
scripts/cos-pr-review.sh, scripts/cos-cloud-worker-bootstrap.sh.
**Output**: structured JSON or human-readable text. Pipes cleanly to jq, yq,
shell scripts, and CI gates.
**Why this surface**: live state is high-frequency, scriptable, and benefits
from being the same shape as audit logs. Web rendering would slow it down
without adding value.

### Surface 2 - Phoenix (opt-in, LLM traces)

**Artefact kind**: OpenTelemetry traces - span attributes, latency, token cost,
eval scores.
**Activation**: `bash scripts/dependency-lane.sh install observability && uv run phoenix serve` on
local port 6006.
**Source of truth**: ADR-058 already governs Phoenix as the trace surface.
**Why this surface**: trace flame graphs and cost/latency dashboards are
genuinely web-shaped. The maintained, OTEL-aligned tool already exists. Building
or buying anything else for this would be reinvention.
**Boundary**: Phoenix renders **traces**. It does not render lifecycle states,
doctrine proposals, demotions, audit_class, federation triggers, or any other
COS governance concept. Surface 1 covers those.

### Surface 3 - Engram Cloud (opt-in, cross-session memory)

**Artefact kind**: persistent memory - observations, decisions, conflict graphs,
session summaries, federated cross-instance learnings (per ADR-136).
**Activation**: Engram MCP tools work locally by default. Engram Cloud is the
hosted federated layer; activation requires a cloud endpoint and BYOK setup
per ADR-139.
**Why this surface**: memory is persistent, queryable, and benefits from a web
UI for graph traversal, conflict resolution, and cross-instance comparison.
The CLI surface (mem_search, mem_context) is sufficient for in-session use;
the cloud surface is the durable navigation layer.
**Boundary**: Engram Cloud is for memory. It does not replace the CLI for live
state, Phoenix for traces, or markdown reports for long-form decisions.

### Surface 4 - Obsidian / markdown reader (opt-in, long-form artefacts)

**Artefact kind**: ADRs (docs/adrs/), doctrine documents (docs/architecture/,
docs/runbooks/), audit reports and case studies (docs/reports/).
**Activation**: clone the repo, point any markdown editor at the directory.
Obsidian is recommended because of its native graph view, backlinks, and
embedded diagram support; any markdown viewer works (VS Code, GitHub web,
mdBook, etc.).
**Why this surface**: long-form decision text is best read in a markdown
renderer, not in a terminal scrolling through cat. Git history is the audit
trail. Backlinks across ADRs are useful navigation. Obsidian's daily-notes and
graph view also fit the "doctrine evolves over time" pattern naturally.
**Boundary**: this surface is read-only in operational terms. ADRs are
created via the standard /sdd-* workflow or hand-edited under git; reports
are emitted by the operator CLIs into docs/reports/. Obsidian is the reader,
not the editor of source-of-truth.

### Cross-surface contract

- **No surface is required.** A solo maintainer running only Surface 1 has a
  fully functional COS. Adding Phoenix/Engram-Cloud/Obsidian is a per-need
  decision, not a default install.
- **No surface is canonical for everything.** Asking "what's the COS UI?" is
  the wrong shape; the right answer is "which artefact?" - then the surface
  follows.
- **Surfaces do not duplicate each other.** If two surfaces seem to render the
  same artefact, one of them is doing the wrong job. Check the table at the top
  of the Context section.
- **No new web-dashboard code lands** for governance / lifecycle / doctrine /
  demotion / audit_class / federation. Those are CLI plus markdown territory.
  Phoenix covers traces. Engram Cloud covers memory. Anything else is a new
  ADR with a real driver, real schema, and real consumer.

## Acceptance Criteria

1. ADR-172 is accepted and cross-references ADR-058, ADR-136, ADR-139, ADR-169,
   ADR-170, ADR-171.
2. ADR-170 frontmatter is updated to superseded_by: ADR-172. The CLI-as-primary
   clause survives, generalised into Surface 1; the implication that only the
   CLI matters is replaced by the multi-surface contract.
3. ADR-169 is unaffected - the dashboard demotion holds.
4. CHANGELOG [Unreleased] references ADR-171 and ADR-172 together as the
   v0.26.1 / v0.27.0 UI-doctrine pair.
5. docs/INDEX.md (or equivalent) lists the four surfaces with their
   activation commands, so a new operator can find them in one place.
6. No new in-tree web-dashboard code lands until a future ADR explicitly
   revokes ADR-172.

## Border Cases

- **External buyer asks for "the dashboard".** The answer is: which artefact?
  Live state -> terminal screenshare of cos-boring-reliability --json | jq.
  Traces -> Phoenix on port 6006. Memory -> Engram Cloud (when activated) or
  mem_context CLI. Decisions -> markdown reports plus ADR tree in Obsidian.
- **Buyer requires a single web pane.** That is a Shape B trigger per ADR-132
  and warrants a separate ADR - not an emergency single-pane build under
  Shape A.
- **Phoenix and Engram Cloud both have web UIs. Do they conflict?** No. Phoenix
  shows trace timelines for an LLM call; Engram Cloud shows the persistent
  memory graph. They are orthogonal surfaces over orthogonal data. Tabs in the
  same browser, not the same page.
- **Obsidian is upstream-maintained and might break.** Obsidian is the reader;
  the source of truth is plain markdown files in git. If Obsidian disappears,
  swap it for VS Code, mdBook, or cat. The contract is markdown-on-disk, not
  Obsidian-specific.
  tRPC API, and an external consumer to justify the maintenance load. The
  multi-surface architecture does not block it; it just declines to make it the
  default.

## Consequences

**Positive.**

- Each artefact lives on the surface where it is genuinely best read. Trying
  to force trace flame graphs into a CLI, or governance state into a
  trace-shaped tool, or memory graphs into static markdown, would all be the
  wrong shape.
- Zero new web-dashboard code to maintain. Maintenance load is bounded to
  the CLI surface (already maintained), Phoenix (upstream-maintained), Engram
  Cloud (separate maintenance lane per ADR-136/139), and markdown files (no
  rendering code).
- The doctrine compounds: every audit emits markdown to docs/reports/,
  every Engram observation is queryable, every LLM call is traced, every
  operator action has a CLI entry point. None of those depend on each other
  to function.
- External buyers see four named, activatable surfaces - each with a one-line
  activation command. That is more honest and more flexible than a single
  "the UI" claim.

**Negative / trade-offs.**

- **Cognitive load.** A new operator has to learn that there are four surfaces,
  not one. Mitigation: docs/INDEX.md and docs/runbooks/run-cos-in-docker.md
  document the activation sequence; Surface 1 alone is sufficient for getting
  started.
- **Discoverability.** Phoenix on port 6006 and Engram Cloud's URL are not visible
  from the CLI by default. Mitigation: cos-boring-reliability will surface a
  "surfaces available" footer in a follow-up enhancement (out of scope here);
  for now the runbook is the discovery path.
- **Cross-surface state inconsistency.** Phoenix sees a trace; Engram has a
  memory; the CLI shows a state - three views of the same operator action.
  They will not always be perfectly synchronised in time. Mitigation: each
  surface has its own freshness contract; no surface claims to be the
  single source of truth for cross-surface joins.

## Alternatives rejected

- **Single canonical UI surface.** Rejected for the reasons above: each artefact
  kind has a different ideal shape, and forcing one surface produces either a
  multi-sprint custom build (per ADR-171's lessons) or impoverished rendering
  (per ADR-170's CLI-only frame).
- **Build a custom multi-pane web dashboard that embeds Phoenix plus Engram Cloud
  plus governance state.** Rejected because (a) it is the same multi-sprint
  pattern that ADR-169 demoted dashboard/ for, (b) the integration burden
  multiplies as each upstream surface evolves, (c) no consumer requires it.
- **Ship without Phoenix / Engram Cloud, declare CLI plus markdown sufficient.**
  This was ADR-170. It was correct that CLI plus markdown are sufficient for
  governance. It was wrong to imply that traces and persistent memory should
  also be CLI-only - those needs already have the right surfaces, and pretending
  otherwise pushes operators to build their own.

## Falsifiable Claim

The multi-surface architecture holds while **all** of the following remain true.
If any breaks for the indicated duration, ADR-172 must be revisited:

1. **No surface drifts into another's territory.** Phoenix does not start
   rendering doctrine; the CLI does not start rendering trace flame graphs;
   Engram Cloud does not start being the source-of-truth for ADRs; Obsidian
   does not become an editor for live state. If any drift is observed in a
   90-day audit, the boundary is revisited.
2. **Each surface remains activatable in one command** (or zero, for Surface 1).
   If the activation grows to multi-step config or runtime dependencies that
   are not BYOK-style, the opt-in claim breaks.
3. **No external buyer requires a unified web pane within 6 months.** If three
   independent external evaluators cite "I need one screen with everything" as
   a blocker, that is a Shape B trigger per ADR-132 and a unified surface ADR
   is warranted.
4. **The four surfaces collectively cover the operator and trace and memory and
   long-form-decision needs.** If a new artefact kind emerges that fits none of
   the four surfaces (e.g., real-time agent collaboration, multi-tenant access
   control), a fifth surface is added under a new ADR - not by stretching
   one of the existing four.

If conditions 1-4 hold for one calendar year, the multi-surface architecture
is judged correct and stabilises as the COS UI doctrine.

## Cross-references

- [ADR-058](ADR-058-observability-migration-langfuse-to-phoenix.md) - Phoenix
  as LLM trace surface; this ADR adopts that decision as Surface 2.
- [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) - Shape A/B fork
  criteria; "buyer requires unified UI" is a Shape B trigger.
- [ADR-136](ADR-136-cross-instance-learning-runway.md) - federation runway for
  Engram, the substrate of Surface 3.
- [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) - BYOK pattern for Engram Cloud and
  any other hosted surface activation.
- [ADR-169](ADR-169-dashboard-formal-demotion.md) - dashboard demotion;
  unaffected.
- [ADR-170](ADR-170-operator-cli-as-primary-ui-surface.md) - superseded by this
  ADR; its CLI-as-primary clause survives, generalised into Surface 1.
  this ADR is the companion that explains what covers the UI role instead.
- docs/architecture/boring-reliability-control-plane.md - the operating doctrine
  the CLI surface enacts.
- docs/architecture/cognitive-prosthesis.md - "Subtraction plus maturity-driven"
  - multi-surface respects that by not building any new surface.

---

## Implementation evidence (2026-05-05 snapshot)

This section records the concrete artefacts that back each surface at the
time of acceptance. It is not a contract — implementation will drift over
time — but it documents what existed in tree on the day this ADR was
accepted, so the falsifiable claim has a baseline.

### Surface 1 — Operator CLI

Entry points present in `scripts/` at acceptance:

- `cos-boring-reliability` — the operator dashboard
- `cos-doctrine-proposer` — propose-only doctrine evolution (ADR-135)
- `cos-self-improvement-loop` — closed-loop improvements (ADR-134)
- `cos-runtime-hook-reality` — wired-vs-firing hook audit
- `cos-silent-failure-audit` — surfaces silently-failing hooks
- `cos-tier-claim-audit` — verifies tier claims against evidence
- `cos-cross-instance-drill` — federation runway smoke test (ADR-136)
- `cos-recovery-drill` — recovery and rollback exercise
- `cos-pr-review.sh` — manual PR review workflow
- `cos-cloud-worker-bootstrap.sh` — cross-OS Docker bootstrap (ADR-140)

All emit structured JSON or human text. None require a web UI.

### Surface 2 — Phoenix

Activation present in the explicit heavy dependency lane at acceptance:

```text
# requirements/dependency-lanes/observability.txt
arize-phoenix>=4.0
arize-phoenix-otel>=0.6
```

Activation command: `bash scripts/dependency-lane.sh install observability && uv run phoenix serve`.

Phoenix port at acceptance: 6006 (default). Trace data flows via OpenTelemetry
spans emitted by `lib/dispatch.py` (ADR-049) and the LLM provider adapters.

### Surface 3 — Engram Cloud

Substrate present in tree at acceptance:

- Engram MCP tools (`mem_save`, `mem_search`, `mem_context`, etc.) work
  locally via the engram plugin.
- Federation runway is documented in ADR-136 but the cloud endpoint is not
  yet activated by default. Activation requires the BYOK pattern from
  ADR-139.

Surface 3 is opt-in **and** not yet activated by default — that is honest
and matches the ADR-172 contract that "no surface is required".

### Surface 4 — Obsidian / markdown reader

Substrate is `docs/`:

- `docs/adrs/` — currently 172 ADRs at acceptance (this one is the most recent)
- `docs/architecture/` — boring-reliability-control-plane.md,
  cognitive-prosthesis.md, federation-runway.md, etc.
- `docs/runbooks/` — run-cos-in-docker.md and operator runbooks
- `docs/reports/` — dated audit reports, baseline snapshots, case studies

All git-tracked, all readable in any markdown viewer. Obsidian is a
recommended reader because of native graph-view + backlinks, but is not
required.

### What is intentionally absent

- No in-tree web dashboard code (`dashboard/` was demoted in ADR-169 and
  remains under `dashboard/ARCHIVED.md`).
- No custom multi-pane UI (rejected as multi-sprint reinvention; revisitable
  via future ADR-173 if a real driver appears).

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

