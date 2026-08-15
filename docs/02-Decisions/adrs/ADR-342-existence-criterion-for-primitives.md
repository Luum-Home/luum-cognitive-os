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
| Runs at an event where it can no longer prevent | the moment | `subagent-budget-enforcer` is registered only on `PostToolUse` (`.claude/settings.json`), 129 block rows in `.cognitive-os/metrics/subagent-budget-enforcer.jsonl` — the only per-hook ledger in the system carrying any — all after the fact, and its counter increments before the decision, so each blocked retry still spends budget |
| Reads a field the payload never carries | the input | 6 phantom-field reads, identical over the 52-payload in-repo corpus and over 2810 live payloads (`scripts/audit_payload_field_contracts.py --canary [--live]`) |
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
| 1 | **Is the name it is invoked by actually published by the host?** Every tool name, event name and matcher the primitive declares appears in the contract of the harness that will run it. | *harness half: no census — see Consequences.* Documentation half only: does a named path exist at all | `python3 scripts/audit_adr_path_reality.py` |
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

- **Question 1 has no census for the half that matters.** This is the largest
  gap this ADR opens: there is no script today that compares declared tool
  names, event names and matchers against each harness's published contract.
  Until there is, that half of question 1 is answered by hand from the
  forensics reports, which is exactly the condition that produced the defect.
  Building it is the first follow-up. What *did* land the same day is the
  cheaper documentation half — `scripts/audit_adr_path_reality.py` answers
  "does the file this document names exist", over 3105 path claims in 503 ADRs,
  and finds 129 phantom paths (16 relocated). Useful, and not a substitute:
  a path that exists says nothing about whether the harness publishes the name
  the primitive is invoked by.
- Applying the decision rules honestly will reduce the reported coverage
  number before it improves it.
- The rules constrain repairs, which makes some red gates take longer to turn
  green. That is the intent.

**Not decided here**

- Nothing is deleted or deregistered by this ADR. Pruning the surface is an
  operator decision; this ADR only says what may be counted as coverage.

## Alternatives rejected

The first two are not hypotheticals. They are the two earlier framings of this
same session's finding, each written down and each superseded by the next, in
order of discovery — `docs/06-Daily/reports/depuracion-sintesis-2026-08-15.md`
§"Lo que no se conectó, y conecta": *"Las tres tesis del día no son tres. Son
una tesis y dos versiones peores de ella."*

- **"Controls that ask for self-assessment age badly" as the criterion.**
  Rejected as *too narrow*, not as wrong. Self-assessment does fail question 4
  structurally — the judge is the interested party — but it explains only a
  minority of the population, and adopting it as the criterion would have left
  the phantom-field, wrong-event and wrong-tool-name shapes unmeasured. Kept as
  a decision rule ("asks the model about its own work → demote to instrument"),
  not as the criterion.
- **"They were not broken gates, they were honest instruments with a gate's
  name" as the criterion.** Rejected for the same reason, and it is also the
  reason the first framing over-counted: the census had classified by the token
  in the filename. Adopting it would have made the fix a renaming exercise.
  Reclassifying by behaviour (`scripts/hook_behavior.py`) abolished the
  `ambiguo` class, dropped theatre from 22 to 12, and showed 189 of 256
  canonical hooks carrying a name that implies a class they do not have — which
  is a symptom of the wider absence, not the absence itself. Kept as the
  decision rule "class is derived from behaviour, never from the filename".
- **Classifying primitives by filename token.** Rejected because the measuring
  instrument was itself an instance of the defect it was measuring: it read a
  declared name instead of an observed behaviour. This is why the criterion
  requires every answer to come from outside the primitive.
- **Pruning the surface in this ADR — deleting or deregistering what fails.**
  Rejected because it fuses two decisions with different owners and different
  blast radius. Several refutations during the session prevented deleting
  something that was live. This ADR only fixes what may be *counted*; what gets
  removed stays an operator decision (see Consequences, "Not decided here").
- **Treating "cheap green" as part of the same convergence.** Rejected as
  narrative. The four shapes describe the *control*; the repair rule describes
  *whoever fixes it*. They are different families and the only contact point is
  that both are measured by the same censuses. It is in the Decision because it
  is needed, not because it completes a pattern — stated as such in the
  synthesis report, §"Donde estoy forzando la narrativa, y lo digo".

## Verification

The criterion says no primitive answers a question about itself. An ADR whose
verification is `grep -rn "ADR-342"` would be the same defect in documentary
form, so the evidence below is the four censuses **run**, with their real
output and exit codes. Exit convention: `0` no findings, `1` findings, `2`
error — so `1` here is the honest state of the system, not a broken command.

```bash
# Q2 — does it run where it can still prevent?
python3 scripts/audit_gate_registration.py                        # exit 1
# Q3 — does the field it reads arrive?
python3 scripts/audit_payload_field_contracts.py --canary         # exit 1
python3 scripts/audit_payload_field_contracts.py --canary --live  # exit 1
# Q4 — has it been seen deciding?
python3 scripts/audit_gate_liveness.py                            # exit 1
# Q1, documentation half only
python3 scripts/audit_adr_path_reality.py                         # exit 0 (under ratchet)
# inverse direction: implemented decisions with no ADR behind them
python3 scripts/audit_decision_backing.py                         # exit 0 (under ratchet)
# this ADR's own section/evidence contract
.venv/bin/python -m pytest tests/audit/test_adr_contracts.py -q
```

Run 2026-08-15, output as printed:

```text
$ python3 scripts/audit_gate_registration.py
canonical hooks (symlink-resolved): 256   (aliases collapsed: 42)
class derived from BEHAVIOUR (scripts/hook_behavior.py), not filename
  gate          76   wired   72   unwired    4
  inert         20   wired   12   unwired    8
  instrument   160   wired  143   unwired   17
hooks whose FILENAME implies a different class : 189
gates absent from .claude/settings.json : 31
gates with NO executor at all          : 4
allowlist entries                      : 185
allowlist entries that ARE wired (cushion): 153

$ python3 scripts/audit_gate_liveness.py
phase=reconstruction  gates(wired)=72
  live             6
  advisory-only    16
  untested         19
  unmeasured       18
  theatre          12
  telemetry-lying  1

$ python3 scripts/audit_payload_field_contracts.py --canary
payload reads scanned: 213   BLIND 0   GUARDED 66   INERT 147
canary [corpus]: 52 payloads scanned
FIELDS HOOKS DEPEND ON THAT NO PAYLOAD EVER CARRIED:  (6)
  hooks/auto-refine.sh:84                            .tool_response.error
  hooks/post-git-orphan-notifier.sh:102              .tool_response.exit_code
  hooks/skill-usage-tracker.sh:64                    .tool_response.duration_ms
  hooks/tool-sequence-capture.sh:62                  .tool_response.exit_code
  packages/quality-gates/hooks/completion-gate.sh:442 .tool_response.error
  packages/skill-governance/hooks/skill-tracker.sh:135 .tool_response.model

$ python3 scripts/audit_adr_path_reality.py
ADRs scanned................ 503
path claims (adr,path)...... 3105
PHANTOM PATHS............... 129   (of which relocated 16)

$ python3 scripts/audit_decision_backing.py
ADR corpus: 503 files, 343 distinct numbers
  blocking-gate    population= 76 unbacked= 10 ratchet=10
  package          population= 32 unbacked= 18 ratchet=18
  policy-manifest  population= 66 unbacked= 12 ratchet=12
DANGLING ADR CITATIONS (1) -- reads as backed, is not:
  adr-section-validator: cites ADR-000 (no such ADR file)
```

What the run establishes, per question:

- **Q2** reproduces exactly: 189 of 256, and 185 allowlist entries of which 153
  are wired — the 32 slots of slack quoted in the Decision are still there.
- **Q3** reproduces the *shape* and refutes the *number*: see "Recount" below.
- **Q4** shows the four-way split the criterion depends on staying separate:
  `unmeasured` (18) and `untested` (19) are neither `live` (6) nor `theatre`
  (12). Rolling them up would report 59 wired gates as covered when 6 have been
  observed deciding.
- **Cross-check**: `audit_decision_backing.py` runs the criterion backwards —
  40 implemented decision surfaces with no ADR behind them, and one hook citing
  `ADR-000`, which does not exist. A citation that reads as backing and is not
  is the same defect as a control that reads as a gate and is not.

**Recount — a figure in this ADR was wrong by the end of the day.** The
phantom-field count was published as 9 reads over 2686 payloads. Recounted with
the command as written, it is **6**, identically over the 52-payload in-repo
corpus and over 2810 live payloads. The table in Context has been corrected.
The ADR predicted this fall and the criterion does not depend on the count —
question 3 stands at 9, 6 or 0, and a 0 would be the criterion working, not the
criterion refuted. Two figures moved for a different reason and are recorded so
nobody re-derives them as constants: `subagent-budget-enforcer` block rows went
from 66 to 129 in its own ledger, and `hook-timing.jsonl` gained 1473 rows
between two runs of the liveness census within this session. The censuses
measure a live system; absolute invocation counts belong to the window in which
the command ran.

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
