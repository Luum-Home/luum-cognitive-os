---
adr: 69
title: Research-First Protocol for High-Risk Changes
status: proposed
implementation_status: planned
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit proposed status without accepted status
---

# ADR-069: Research-First Protocol for High-Risk Changes

## Status

**Proposed** — 2026-04-24. Adopted alongside three concrete research tasks (H/I/J)
spawned in this same session. Implementation phases tracked in §8.

## Context

Today's session (2026-04-24) shipped 15+ background agents successfully — parser
fixes, ADR drafts, refactors, CI tweaks, gofmt sweeps. The fire-and-forget model
worked: each agent had a narrow scope, a verifiable acceptance criterion, and a
reversible diff. Operator approved batches and moved on.

But during planning, three items were carved out of the batch and explicitly
marked "needs a dedicated session, not fire-and-forget":

- **Item H** — migrate `scripts/cos-init.sh` (~300 lines of awk/sed) to Python
- **Item I** — extend ADR-067's template+hook+audit pattern to `rules/`, `hooks/`, ADRs
- **Item J** — bump Python deps across major versions (wrapt 1→2, rich 14→15, cryptography 46→47)

The operator pushed back ("no entiendo esto"), and the orchestrator answered:
these have judgment calls mid-flight that a fire-and-forget agent cannot make
alone. The operator agreed and added: "dale si, aunque expone esto en una
documentación, ADR" — codify it before the next session re-invents the
distinction.

Why background agents work for some things but not for these:

| Works for                                  | Fails for                                                 |
|--------------------------------------------|-----------------------------------------------------------|
| `gofmt ./...`                              | "rewrite this 300-line shell script in Python"            |
| `grep -c 'old-name' = 0`                   | "does the new auth flow still work the same way?"         |
| `pip install --upgrade requests`           | `cryptography` 46→47 breaks `pyOpenSSL`, `urllib3` deps   |
| Add ADR file, commit, done                 | "extend pattern to 4 directories with non-uniform shapes" |
| Fix typo in a single file                  | Migration where each file is a different judgment call    |

The cost of botched fire-and-forget on a critical path is asymmetric. Example:
`scripts/cos-init.sh` is the FIRST experience every consumer of the OS has. A
silently broken Python rewrite that "passes the smoke test" but mangles the
generated `cognitive-os.yaml` ships an unusable OS to every new project. Reverting
costs a release cycle. Compare that to a botched gofmt: `git revert <sha>`,
done.

This ADR formalizes the routing: when do we ship a research report and operator
decision FIRST, then implementation; vs. when do we just ship.

## Decision — Risk classification

A task gets routed by four dimensions. If **any** dimension is "High", route to
research-first. Otherwise standard background-agent treatment applies.

| Dimension                       | Low                                              | High                                                           | Routing                |
|--------------------------------|--------------------------------------------------|----------------------------------------------------------------|-----------------------|
| **Acceptance criteria clarity** | Verifiable bash command (e.g. `grep -c "X" = 0`) | Subjective ("does this still work?", "is this idiomatic?")     | High → research-first |
| **Blast radius**                | <5 files, isolated module                        | >50 files OR infra OR critical-path (init, auth, CI)           | High → research-first |
| **Reversibility**               | `git revert <sha>` is clean                      | Hard (breaking schema, transitive dep upgrade, lockfile churn) | High → research-first |
| **Decision count**              | 0–2 yes/no choices                               | 3+ judgment calls (architecture, naming, tradeoffs)            | High → research-first |

### Worked examples — why H, I, J each trip the gate

| Task                                       | AC clarity                              | Blast radius                                     | Reversibility                                  | Decision count                                                  | Verdict          |
|--------------------------------------------|-----------------------------------------|--------------------------------------------------|------------------------------------------------|-----------------------------------------------------------------|------------------|
| **H** `cos-init.sh` → Python               | High (no single bash check works)       | High (every new project hits this script first)  | Medium (revert works, but consumer pain real)  | High (CLI lib? config schema? error-handling style? testing?)   | Research-first   |
| **I** ADR-067 Phase 2 (rules/hooks/ADRs)   | Medium (per-dir, "matches the pattern")  | High (template+hook applied 4 places)            | Medium (per-file revert OK, hook revert risky) | High (per-dir schema, opt-in vs opt-out, hook ordering)         | Research-first   |
| **J** Python major bumps                   | High (`pytest` exit code is the AC)     | Medium (lockfile + transitive deps)              | Low (lock churn, transitive breaks ripple)     | High (which to defer? how to triage breakage? CI matrix policy?) | Research-first   |
| (counter) gofmt the repo                   | High (`gofmt -l` empty)                 | Low (formatting only)                            | High (revert clean)                            | Low (none)                                                       | Standard agent   |
| (counter) bump `requests` 2.31 → 2.32      | High (`pytest` passes)                  | Low (one transitive)                             | High (lockfile only)                           | Low (none)                                                       | Standard agent   |

The counter-examples are why the gate exists: most tasks are still
fire-and-forget. The gate fires only when judgment is the bottleneck.

## Decision — Research-first protocol (3 phases)

For any task flagged "research-first", the orchestrator runs three phases
sequentially. Phase 0 is automatic. Phase 1 is human. Phase 2 is automatic again
once Phase 1 lands.

### Phase 0 — Research agent (READ-ONLY)

Spawned automatically with research-only constraints:

- No commits
- No file modifications outside `docs/reports/` (git-tracked; NOT `.cognitive-os/reports/research/` which is gitignored)
- No invocation of side-effecting scripts
- Output is a single Markdown file under that directory

Required structure of the report (skeleton):

```markdown
# Research: <topic> — <YYYY-MM-DD>

## 1. Inventory
What exists today. Counts, file lists, current behavior. No interpretation.

## 2. Decision points
Each numbered. For each: options + tradeoffs + risk per option.

## 3. Risk assessment
Per option from §2, what breaks, who notices, how loud the failure is.

## 4. Open questions for operator
Bullet list. Each must be answerable yes/no or pick-one.

## 5. Recommended path
The agent's recommendation, with reasoning. Operator can override.

## 6. Acceptance criteria draft
What Phase 2 will need to verify. May be incomplete until Phase 1 lands.
```

### Phase 1 — Operator decision

The operator reads the report, answers the open questions, and picks an option
per decision point. The operator's decisions are persisted somewhere queryable —
either as an Engram observation under `research/<topic>/decision`, or as a
follow-up ADR if the decision is itself ADR-worthy.

This phase has no SLA. The operator owns the timing. The point is that the
implementation does NOT start until decisions are made.

### Phase 2 — Implementation agent

Spawned with the operator's decisions baked into the prompt. Because decisions
are made, the prompt now has narrow, verifiable acceptance criteria — which puts
the task back into "standard background-agent" territory. The 3-phase cycle
collapses to the regular fire-and-forget protocol from this point.

Phase 2 is allowed to surface "decision X turned out to be unworkable, recommend
re-running Phase 1". This is rare but the escape hatch must exist.

## Decision — Where reports live

- Path: `docs/reports/<topic>-<YYYY-MM-DD>.md` (git-tracked, NOT gitignored)
- Engram topic key: `research/<topic>` (one report per topic; updates upsert)
- Cross-link: the spawning ADR (or task) MUST add the report path under its
  "Related" section so future readers can trace the decision trail
- Reports are durable artifacts, not throwaway. They're the rationale record
  the team will read 6 months from now to remember "why did we choose Click
  over argparse for cos-init.py?"

### §5b — Auto-create `decision/<topic>` engram observations

When an operator accepts a recommendation (Phase 1), the orchestrator MUST call
`lib/decision_tracker.record_decision(topic_key, decision_text, recommendation)` to
persist an engram observation under `decision/<topic_key>`. This allows
`/decision-triage` to cross-reference answered decisions and mark them ANSWERED
instead of surfacing them as PENDING indefinitely.

## Decision — When NOT to use research-first

The protocol adds latency. Don't apply it where it doesn't earn its keep:

- Mechanical changes (rename a symbol, gofmt, formatter sweep)
- Acceptance criteria is one bash command (`grep -c X = 0`, `pytest passes`)
- Reversibility is `git revert <sha>` with no transitive impact
- Operator already knows what they want; the agent is just typing
- Bug fixes with a clear repro and a clear root cause

These get standard background-agent treatment. The risk classification table
above is the discriminator — if all four dimensions are "Low", skip research.

## What we replicate / what we don't

- **Replicate** for every "I think we need a dedicated session" instinct: the
  3-phase cycle is the formalization of that instinct. If an item triggers it,
  route through research-first instead of waiting for a manual session.
- **Do NOT replicate** SDD's full pipeline for everything. SDD has 8 phases
  (explore → propose → spec → design → tasks → apply → verify → archive).
  Research-first has 3. Most tasks don't need SDD's depth — they need a
  judgment-call gate, not a full process.
- **Complement, don't replace** `/sdd-explore`. SDD-explore is for greenfield
  ("what should we build?"). Research-first is for brownfield/migration
  ("what's there now and which option do we pick?"). Both can coexist.

## Implementation phases

1. **Phase 1 — codify (this ADR).** Land the protocol so the next session can
   reference it.
2. **Phase 2 — pilot with H/I/J.** Each spawns a research agent today. Reports
   land in `docs/reports/` (git-tracked; see §5 fix 2026-04-27).
3. **Phase 3 — operator triage.** Per-report decisions captured (Engram
   observation OR follow-up ADR per item).
4. **Phase 4 — implementation.** Only starts after Phase 3. Standard
   background-agent protocol applies once decisions are baked in.
5. **Phase 5 (later)** — add `templates/agent-research-only.md` so the
   orchestrator has a base prompt for research-only spawns. Tracked as an open
   question (§13) for now.

## Consequences

### Positive

- High-risk tasks get human judgment AT the critical points, not after.
- Reports are reusable artifacts. Six months from now, "why did we choose
  Click?" has an answer.
- Less "the agent invented X mid-flight; now we live with X forever".
- The protocol scales to teams: any contributor can read the report, agree or
  disagree, before code lands.
- The risk classification table makes routing explicit and auditable.

### Negative

- 2–3× wall-clock for high-risk tasks (research → decision → impl, vs.
  research+impl in one shot). For H/I/J this is acceptable given blast radius;
  for everything else the gate filters them out.
- Adds an artifact (the report) that must be maintained. Reports go stale.
  Mitigation: cross-link from the spawning ADR so stale reports surface during
  ADR review.
- Not all teams will accept the extra round-trip. Solo developers especially
  may feel "I am the operator AND the implementer, why am I writing a report
  to myself?" The honest answer: future-you isn't current-you, and the report
  is what future-you will thank current-you for.

### Neutral

- Low-risk task throughput unchanged. The 4-dimension gate keeps fire-and-forget
  fast.
- No change to existing SDD or background-agent infrastructure. This ADR is
  meta-process, not new code (until Phase 5).

## Alternatives rejected

1. **Always use SDD for non-trivial changes.** SDD has 8 phases.
   Research-first has 3. SDD is overkill for most brownfield migrations where
   "what's there?" is the dominant question, not "what should we build?".
   SDD also encourages a propose → spec → design cascade that is slow when the
   real bottleneck is operator judgment, not agent reasoning.

2. **Always use background agents; operator triages later.** This is what bit
   us today with the cos-init.sh discussion. By the time the operator triaged,
   the agent had invented X, X had a blast radius, and the triage became a
   damage-control conversation instead of a design conversation. Triage-first
   only works when blast radius is small enough that "undo" is cheap.

3. **Manual scripting / no agents.** Defeats the purpose of an agent system.
   Also doesn't scale: the operator becomes the bottleneck for every
   non-trivial change, and research-first only fires on a minority of tasks.

4. **Have the agent ask questions mid-flight.** Possible in interactive
   sessions but breaks the fire-and-forget assumption that this OS is built
   on. Queued/spawned agents have no human to ask. Research-first front-loads
   the questions so all subsequent work is asynchronous.

5. **Use SDD's `/sdd-explore` phase as the research step.** Considered.
   `/sdd-explore` is greenfield-oriented ("what should we build?") and pulls
   in the SDD pipeline expectations (it expects a propose to follow).
   Research-first is brownfield-oriented and terminates cleanly without
   committing the operator to the rest of SDD. Different shape, different fit.

## Verification

Acceptance criteria for this ADR landing:

- [x] `docs/adrs/ADR-069-research-first-protocol.md` exists at the documented
  path
- [ ] Each of H, I, J produces a `docs/reports/<topic>-<date>.md` report
  in this same session (NOT `.cognitive-os/reports/research/` — that path is gitignored)
- [ ] Reports contain the §0-skeleton structure: Inventory + Decision points +
  Open questions + Recommended path
- [ ] After this session, operator decisions land in a queryable place
  (Engram observation under `decision/<topic>` via `lib/decision_tracker.record_decision()`)
- [ ] Future research-first invocations cite this ADR by number

Verification commands:

```bash
test -f docs/adrs/ADR-069-research-first-protocol.md
ls docs/reports/*.md | wc -l                       # >=3 after H/I/J land
grep -l "ADR-069" docs/adrs/*.md                   # future ADRs cite this one
python3 scripts/decision_triage.py --critical-only 2>&1 | grep "Total unanswered"
```

## Related

- **ADR-066** (polyglot language boundaries) — informs Item H (Python rewrite)
- **ADR-067** (frontmatter defense-in-depth) — directly relates to Item I
  (extend the same pattern to rules/hooks/ADRs)
- **ADR-068** (adaptive test runner capacity) — sibling: also a "policy ADR
  with deferred implementation" pattern
- `rules/agent-quality.md` — this ADR is a meta-rule on top of agent-quality
  (defines WHEN to apply quality vs. WHEN agents may fly solo)
- `rules/closed-loop-prompts.md` — research-first is closed-loop at a higher
  altitude (operator IS the loop)
- `templates/agent-preamble.md` — `templates/agent-research-only.md` will be
  added as part of Phase 5 (see §13)
- `/decision-triage` skill — surfaces all unanswered operator decisions produced by research-first reports (and ADR open questions) in a unified ranked view

## Open questions

1. **Should we add a `templates/agent-research-only.md` base prompt?** Likely
   yes for Phase 5. The prompt would enforce the read-only constraint and the
   §0 skeleton structure. Open: should it be a separate template, or a flag on
   the existing agent preamble?

2. **How to handle research that surfaces "this should be three separate
   ADRs"?** Options: (a) cascade — spawn three more research agents, one per
   sub-topic; (b) compress — write one report covering all three with clear
   sub-sections. Default to (b) until we hit a case where (a) is obviously
   right.

3. **Does this replace `/sdd-explore` or complement it?** Provisional answer:
   complement. `/sdd-explore` for greenfield (no existing system to inventory),
   research-first for brownfield/migration (existing system dominates the
   problem). If a session blends both, run research-first on the brownfield
   parts and `/sdd-explore` on the greenfield parts.

4. **What's the SLA for Phase 1 (operator decision)?** No SLA today —
   operator owns timing. If reports start piling up un-triaged, revisit. Track
   un-triaged report count as a leading indicator.

5. **Should low-confidence "is this really high-risk?" tasks default to
   research-first or to standard agents?** Default to research-first when in
   doubt. The cost of an unnecessary report is one extra Markdown file. The
   cost of an unnecessary fire-and-forget on a critical path is a release
   cycle.
