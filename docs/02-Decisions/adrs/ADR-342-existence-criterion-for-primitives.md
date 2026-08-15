---
adr: 342
title: Existence Criterion for Primitives
status: accepted
implementation_status: partial
date: 2026-08-15
---
# ADR-342: Existence Criterion for Primitives

- Implementation status: partial (three of the four censuses exist; the first has no census yet)
- Date: 2026-08-15
- Owner: Cognitive OS maintainers

## Status

Accepted. A primitive counts as existing coverage only when four questions
about it are answered from outside itself, each by a reproducible command.
A primitive that fails any of the first three is not weak coverage — it is
zero coverage, and must not be counted in any coverage figure.

## Context

The whole 2026-08-15 depuration session was, in the end, one finding: **a
control can be written, registered, projected into every harness, and still
not exist.** Four distinct shapes were measured, each with its own census,
and none of them is an implementation bug. Every one of them is the same
absence: **nothing compares what a control declares against what its host
actually publishes.**

| Shape | What is missing | Measured today |
|---|---|---|
| Names a tool the host does not have | the invocation surface | 3 dispatch sites in `.opencode/plugins/cos-primitive-guard.js` branch on `toolName === "agent"`; OpenCode's subagent tool is `task` |
| Runs at an event where it can no longer prevent | the moment | `subagent-budget-enforcer` is registered only on `PostToolUse` (`.claude/settings.json`), 66 block rows, the highest in the system, all after the fact — and its counter increments before the decision, so each blocked retry still spends budget |
| Reads a field the payload never carries | the input | 9 phantom-field reads across 2686 real payloads (`scripts/audit_payload_field_contracts.py --canary`) |
| Uses a matcher the host parser silently drops | the binding | historically `"prompt"` / `"shutdown"` in the Codex driver, on events that accept no matcher |

Two prior framings of the same session were narrower and are superseded by
this one, not contradicted:

1. **"Controls that ask for self-assessment age badly"** — true, and a special
   case: self-assessment fails the fourth question below structurally, because
   the judge is the interested party. But it explains only a minority of the
   population.
2. **"Many of those were not broken gates — they were honest instruments with a
   gate's name"** — true, and the reason the first framing over-counted. The
   census classified by the token in the filename. Reclassified by behaviour
   (`scripts/hook_behavior.py`), the `ambiguo` class was abolished, theatre fell
   from 22 to 12, `secret-detector` entered the gate population for the first
   time, and **189 of 256 canonical hooks carry a name implying a class they do
   not have** (`python3 scripts/audit_gate_registration.py`). The measuring
   instrument was itself an instance of the defect: it read a declared name
   instead of an observed behaviour.

A second, independent failure mode was demonstrated repeatedly *by this
session against itself*: when a control is found not to exist, the cheapest
available fix changes the measurement rather than the control. Concrete
instances from today, all caught before landing: a patch that moved a read
from one nonexistent field to another nonexistent field; twelve
characterization tests pinning the defect against a field that does not
exist; a contract test asserting an auditor's bug verbatim, which is why the
bug survived; an opencode test checking that a design document repeated
identifiers the driver had invented; a ratchet pinning the literal `119`,
proposed to be moved to `159`. This ADR therefore also fixes what counts as a
repair.

## Decision

### The criterion

> **A primitive exists when its decision can be shown to have occurred over a
> real input, and none of the four answers comes from the primitive itself.**

Operationally, four questions. Each has an owner census and a command. A
primitive may not answer any of them about itself.

| # | Question | Answered by | Command |
|---|---|---|---|
| 1 | **Is the name it is invoked by actually published by the host?** Every tool name, event name and matcher the primitive declares appears in the contract of the harness that will run it. | *no census yet — see Consequences* | — |
| 2 | **Does it run where it can still prevent?** If its behaviour is a gate, its event precedes the effect. Post-effect execution makes it an instrument, whatever its name. Side effects (counters, budgets) may not precede the decision. | registration + behaviour census | `python3 scripts/audit_gate_registration.py` |
| 3 | **Does the field it reads arrive?** Every payload field read appears in at least one real payload, and its absence is observable — a `// default` that is itself a legal reading makes absence invisible. | payload contract canary | `python3 scripts/audit_payload_field_contracts.py --canary` |
| 4 | **Has it been seen deciding?** At least one recorded decision over a real input, not a fixture. Zero decisions over N runs is a finding, not a healthy state. | liveness census | `python3 scripts/audit_gate_liveness.py` |

### Decision rules

- **Fails 1, 2 or 3 → the control does not exist.** Repair it or deregister
  it. It may not be counted as coverage, may not appear in a readiness ledger
  as satisfied, and may not be cited as the reason a risk is handled.
- **Passes 1–3, fails 4 → unmeasured, not healthy.** Prove it with a canary
  over a real input before counting it. `unmeasured` and `untested` are
  distinct from `live` in the liveness census for this reason and must stay
  distinct in any rollup.
- **Asks the model about its own work → cannot pass 4 with authority.**
  Demote to instrument. It may inform, it may not gate. A better model
  self-assesses more convincingly, not more accurately, so this class degrades
  as the models improve.
- **Class is derived from behaviour, never from the filename.** A name is a
  hypothesis about a class; `scripts/hook_behavior.py` is the verdict.

### What counts as a repair

A repair must **move the answer to one of the four questions**. The following
are explicitly not repairs, and a change consisting only of these is rejected:

- moving a ratchet to a new literal so the current reality fits under it;
- adding a characterization test that pins the defective behaviour, including
  pinning a read of a field that does not exist;
- asserting a known bug verbatim in a contract test;
- testing that a document repeats an identifier some code invented, in place
  of testing the code against the host's published contract;
- editing the artifact a guard flagged instead of fixing the guard, when the
  guard's finding is wrong;
- regenerating a snapshot, loosening an assert, or adding a suppression, where
  the underlying question's answer is unchanged.

A baseline above reality is a bug, not a cushion: the registration census
reports 185 allowlist entries of which 153 are already wired, i.e. 32 slots of
slack under a number that reads as "accounted for".

### Method

Two mechanisms produced more real defects in one day than the hook layer
produced in twenty-six, and both are hereby part of how these questions get
answered:

- **The refutable brief.** Every sub-agent gets explicit standing permission to
  refute the premise of whoever assigned it, and briefs carry the command, not
  the conclusion (skill `encargo-refutable`). Every refutation today prevented
  a wrong action; several prevented deleting something live.
- **Cross-verification.** Independent agents with disjoint context measuring
  the same thing. Of 19 published figures recounted at the end of the session,
  4 reproduced exactly; the rest were superseded, refuted, made stale by a
  same-day fix, or not measurable in this checkout. The full reconciliation is
  in `docs/06-Daily/reports/depuracion-sintesis-2026-08-15.md`.

## Consequences

**Positive**

- Coverage claims become falsifiable with four commands instead of a reading
  of the hook directory.
- The four shapes stop being four separate incidents and become one gap with
  one owner.
- The demotion rule gives self-assessment controls a landing place — instrument
  — instead of a binary keep/delete argument.

**Negative / cost**

- **Question 1 has no census.** This is the largest gap this ADR opens: there
  is no script today that compares declared tool names, event names and
  matchers against each harness's published contract. Until there is, question
  1 is answered by hand from the forensics reports, which is exactly the
  condition that produced the defect. Building it is the first follow-up.
- Applying the decision rules honestly will reduce the reported coverage
  number before it improves it.
- The rules constrain repairs, which makes some red gates take longer to turn
  green. That is the intent.

**Not decided here**

- Nothing is deleted or deregistered by this ADR. Pruning the surface is an
  operator decision; this ADR only says what may be counted as coverage.

## Provisional figures

Two agents were still in flight when this was written: one building the real
`error-pipeline` / `error-learning` fix (detection by type change rather than
by a nonexistent `exit_code`), one turning the phantom-field canary into a gate
with an anonymized corpus. **The count of 9 phantom-field reads over 2686
payloads is provisional and expected to fall.** The criterion does not depend
on the count — question 3 stands whether the answer is 9, 3, or 0, and a count
of 0 would be the criterion working, not the criterion refuted.

## References

- `docs/06-Daily/reports/depuracion-sintesis-2026-08-15.md` — synthesis and
  figure reconciliation
- `docs/06-Daily/reports/depuracion-quirurgica-2026-08-15.md` — the morning
  framing, superseded in scope by this ADR
- `docs/06-Daily/reports/arq-contrato-gate-instrumento-2026-08-15.md` — gate vs
  instrument contract design, and the cost of enforcing class at the wrapper
- `docs/06-Daily/reports/payload-contract-architecture-2026-08-15.md` — question 3
- `docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md` — question 2
- `docs/06-Daily/reports/codex-contract-forensics-2026-08-15.md`,
  `docs/06-Daily/reports/opencode-contract-forensics-2026-08-15.md` — question 1
- `rules/gates-sin-trampa` (skill `gates-sin-trampa`) — the cheap-green family
  this ADR's repair rule extends to primitives
