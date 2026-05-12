# Case Study — Absorbing an External Senior Review Without Collapse

**Date:** 2026-05-02 → 2026-05-03
**Audience:** External adopters and future contributors evaluating whether the boring-reliability doctrine actually behaves as advertised.
**Companion docs:** [`boring-reliability-control-plane.md`](../architecture/boring-reliability-control-plane.md), [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md), [ADR-126](../adrs/ADR-126-agentic-primitive-lifecycle-governor.md), [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md), [ADR-133](../adrs/ADR-133-expansion-without-monsterization.md).

## Why this exists

The boring-reliability doctrine claims that Cognitive OS can absorb external critique by converting it into ADRs, manifest changes, and CI-enforced gates rather than into defensiveness or feature sprawl. That claim is hard to evaluate from the doctrine alone. This document captures one concrete cycle so readers can decide for themselves whether the doctrine behaves as written.

The cycle is preserved as a worked example, not as a marketing artefact. The interesting property is **traceability**: every step links to an artefact in the repository.

## The cycle

### Step 1 — External SR review (input)

A senior/Solutions-Architect read of the repository was solicited explicitly. The review asserted, in summary:

- Surface area (162 skills, 188 hooks, 112 rules, 1.6K-line `cognitive-os.yaml`) presents as framework, not guardrail.
- Token tax of the default profile was non-trivial; full profile was near context-window saturation.
- ADR programme had volume but no demonstrated retirement discipline; lifecycle states were paper.
- Recommendation: a `--minimal` tier and a hard threshold on default-visible primitives, or the surface would re-inflate within sprints.

Captured at: [`docs/08-References/business/cos-vs-vanilla-dx-review.md`](../business/cos-vs-vanilla-dx-review.md), [`docs/06-Daily/reports/dx-assessment-2026-05-02.md`](../reports/dx-assessment-2026-05-02.md).

### Step 2 — Strategic reframing (decision capture)

Instead of treating the review as a request for cosmetic surface reduction, the response framed it as a distribution problem and a lifecycle problem:

- [ADR-124](../adrs/ADR-124-cos-distribution-boundaries.md) — distribution tiers (`core` / `team` / `maintainer` / `lab`) so the small surface and the full surface can coexist.
- [ADR-125](../adrs/ADR-125-governance-tools-value-boundary.md) — explicit value boundary: governance must earn its runtime cost; low-ROI primitives are demoted, not preserved by inertia.
- [ADR-126](../adrs/ADR-126-agentic-primitive-lifecycle-governor.md) — eight lifecycle states (`candidate` → `sandbox` → `advisory` → `blocking` → `default-on` → `demoted` → `archived` → `deleted`) with required metadata.

The review was not absorbed as an opinion. It was absorbed as an obligation to make existing doctrine machine-checkable.

### Step 3 — Structural enforcement (the part that matters)

Three primitives were added to make the framing self-policing rather than aspirational:

- [`scripts/active_primitive_index.py`](../../scripts/active_primitive_index.py) — hard thresholds on the default-visible surface (`VISIBLE_WARN_THRESHOLD = 12`, `VISIBLE_FAIL_THRESHOLD = 25`), wired into CI through [`scripts/cos-ci-local.sh`](../../scripts/cos-ci-local.sh).
- [`scripts/lab_first_promotion_gate.py`](../../scripts/lab_first_promotion_gate.py) — every new primitive starts in `lab`/`sandbox`; promotion to `core` / `team` / `default-on` requires a machine-readable evidence block. See [ADR-133](../adrs/ADR-133-expansion-without-monsterization.md).
- [`scripts/session_start_budget.py`](../../scripts/session_start_budget.py) — measures and budgets what gets injected into the session preamble, attacking the runtime token cost the review named.

These exist so the next person who proposes adding a primitive must first explain why it does not start in `lab`. The default direction of travel was inverted.

### Step 4 — Demote with evidence (the first real test)

The review observed that `lifecycle_state: demoted` did not appear anywhere in the manifest, leaving ADR-126 as paper. A demotion was performed against `hooks/task-completed.sh` — not by deletion, but by lifecycle state transition with an explicit evidence block:

```yaml
lifecycle_state: demoted
demotion_evidence:
  demoted_on: '2026-05-03'
  reason: COS extension hook is not required for default team/core adoption;
    demotion proves ADR-126 inactive lifecycle semantics without deleting the primitive.
sunset_criteria: archive after 90 days with no opt-in use
```

Proof artefact: [`docs/06-Daily/reports/lifecycle-demotion-task-completed-2026-05-03.md`](../reports/lifecycle-demotion-task-completed-2026-05-03.md). Implementation commit: `97307e34 feat: prove lifecycle demotion semantics`.

The demotion is intentionally small. It exercises the semantics without asking for organisational courage. The next demotions are expected to be larger and ROI-driven.

### Step 5 — Doctrine update (closing the loop)

The rationale layer was extended so future readers do not have to re-derive the framing:

- [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md) — companion doc to the control plane: why the system has the shape it has, including the explicit naming of the velocity-vs-durability tradeoff that ADR-132's trigger conditions sit on top of.
- [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — strategic decision left open: at what point the present single-maintainer calibration should be re-shaped for wider adoption.

The cycle ended with an open question documented as such, not with a claim of completion.

## What made the cycle possible

The cycle is not a heroics story. It is the predictable output of having the following properties already in place:

1. **A persistent decision substrate.** ADRs and Engram make it cheap to capture a decision now that future-self can read later. Without that, critique evaporates within a session.
2. **Bilateral verification primitives.** ADR-105 (claim verification) and `aspirational_audit.py` mean a claim like "we archived these hooks" can be falsified mechanically. That eliminates the most expensive failure mode — wishful self-reporting.
3. **A doctrine that named retirement as a first-class action.** ADR-125 and ADR-126 existed *before* the review; the review's pressure was to operationalise them, not to invent them.
4. **CI as the durable surface.** Wiring the new thresholds into `cos-ci-local.sh` (commit `d368a324`) means the discipline survives the moment of attention that produced it.

If any of those four are missing, the same external review absorbs as defensiveness or feature-add, not as doctrine clarification.

## Bilateral pressure: why the cycle closed in hours instead of weeks

A fifth property is worth naming separately because it is easy to miss and easy to lose: external review is **bilaterally obligating**. Both sides have to escalate or the cycle does not close.

**On the reviewer's side**, the obligation is to produce findings concrete enough to act on — not *"this looks complex"* but *"primitive X with property Y violates contract Z, here is the artefact that proves it"*. A review that lands as opinion lands as defensiveness on the receiving end. A review that lands as falsifiable claim lands as obligation.

**On the maintainer's side**, the obligation is symmetric: translate the falsifiable claim into committed code, not leave it as a sketch in the conversation buffer. A review that the maintainer absorbs as draft but does not execute degrades into the same artefact graveyard the doctrine was built to prevent. The reviewer is obliged to not be lazy; the maintainer is obliged to not stop at the sketch.

In this cycle, the wall-clock from review delivery to enforcement merged on `main` was approximately 8 hours overnight, covering five production-grade ADRs, three gate refactors with unit tests, a control-plane audit, and this case study itself. That speed is **not** evidence of skill or virtue. It is evidence of the single-maintainer property that [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md) catalogues:

- One brain holding the full model means decisions do not need to be socialised before execution.
- One repository without code-owners means a refactor of `destructive-git-blocker.sh` does not need approval.
- One context with full read/write access to artefacts means tests can land in the same commit as the code they cover.

This is **the positive side of the trade-off** that ADR-132's `single-maintainer calibration` section names. The same property that ADR-132 marks as a SPOF risk *for durability* is the property that enabled the cycle to close *for velocity*. The two readings — risk and lever — describe the same fact.

Two consequences follow:

1. **Multi-maintainer absorption of the same review would be slower by 5–10×.** Not because individual contributors would be slower at writing each artefact, but because each artefact would pass through coordination costs (review, approval, naming consensus, branch protection). The cycle would still close, but in days instead of hours, and with broader buy-in. That is the durability side of the trade-off doing its work.

2. **Single-maintainer velocity is consumable.** It is bounded by the maintainer's continuous attention, which is finite. A second cycle of comparable depth in the same week would degrade in quality because the prosthesis (Engram, ADRs, dashboard) buys persistence, not unbounded throughput. Replication of this cycle as a routine practice should expect a cadence floor of weeks, not days.

The bilateral pressure point is what makes external review a useful primitive at all. Without it, review is just an audit. With it, review is the trigger that converts standing doctrine into runtime artefacts. The four properties listed in *"What made the cycle possible"* are the prerequisites; the bilateral obligation is the spark.

## Protected landing as the trade-off made visible

One sub-cycle exposed the velocity-vs-durability trade-off in miniature. A
documentation insight briefly landed on `main` directly during concurrent
orchestration. The local direct-main guard then blocked the push, forcing the
operator to restore the intended shape: create a session branch, re-apply the
scoped edit, commit it there, open a PR, and merge through the protected path.

The repair cost was small — roughly five minutes — but it is the point of the
governance. Pure velocity would have been a direct push. Durability required a
traceable branch, PR, merge, and reviewable landing path. The lesson is not
"never bypass"; emergency bypasses remain available. The lesson is that bypass
must be explicit, scoped, and audited. `hooks/direct-main-guard.sh` now requires
`COS_DIRECT_MAIN_BYPASS_REASON` or `COS_BYPASS_REASON` for direct-main bypasses
and appends the event to `.cognitive-os/metrics/direct-main-bypass.jsonl`.

This makes the bilateral obligation operational: if the maintainer chooses speed
over the governed path, the choice becomes evidence, not folklore.

## Self-triggered absorption: the doctrine working at micro-scale

The "Protected landing" sub-cycle above documents *what happened*. Worth naming separately is *the structural property it demonstrates*: the system absorbed friction it produced **about itself, during its own documentation pass**, and converted that friction into a doctrine artefact within the same wall-clock.

Concretely: the friction with `direct-main-guard.sh` happened during the documentation pass for this case study. Approximately 40 minutes after the recovery, commit `95239a50 fix: audit direct main bypasses` landed on `main` — hardening the guard by ~80 lines, adding unit tests for the bypass paths, and creating [`docs/04-Concepts/architecture/direct-main-policy.md`](../architecture/direct-main-policy.md). The fix targets the exact failure mode the documentation pass surfaced.

The structural difference from the main external-review cycle: the main cycle absorbed an **external** input (a senior review). This sub-cycle absorbed an **internal** input (the cycle's own friction) and produced the same class of artefact — gate hardening, tests, policy doc — without an external trigger. **The cycle ate its own friction.**

The implication for durability: a system that codifies its own internal friction has a feedback loop the external-review cycle does not have to keep providing. The first external cycle is a trigger; subsequent improvements can be self-triggered by the cost of running the system itself. The next operator hitting the same friction inherits the hardened gate, not the recovery procedure.

For external adopters evaluating the doctrine, this turns into a **falsifiable claim**: if the doctrine is real, the system should consume its own friction over time, which means low long-term operational overhead from recurring failure modes. If after several months of use the same friction recurs *without* producing a hardening commit and a corresponding policy doc, the claim is wrong and the doctrine is not behaving as written. The micro-cycle documented above is the first data point; subsequent ones can be tracked by correlating dates of `docs/04-Concepts/architecture/*-policy.md` additions against `git log --grep='^fix: audit'` entries on `main`.

The naming matters because this property is what allows the system to scale without continuous external pressure. External review is what produced this case study. Internal friction-absorption is what will produce the next twenty improvements without a second external review being required.

## Cadence asymmetry between reviewer and maintainer

A property that generalises the bilateral pressure point above and explains why review documents are *structurally stale by the time they finish writing*: the reviewer and the maintainer operate at different cadences by design.

The reviewer's work is durability work — slow prose, structured tables, falsifiable claims. Wall-clock cost is dominated by the writing of the prose around the analysis, not by the analysis itself. The maintainer's work in single-maintainer mode is velocity work — small commits, scoped fixes, no coordination tax. Wall-clock cost is dominated by typing.

In this cycle's documentation pass, two distinct snapshots taken by the reviewer were rendered partially obsolete by maintainer commits **before the prose around them finished writing**. Once for an early "no movement" status table on six axes — five of the six were resolved by boring-reliability commits landing while the table was being typed. Again for a later "four warn sections plus readiness fail" punch list — resolved by `33d8891a fix: clarify boring reliability warn exit` and `beb7d30c fix: clarify session start diet metrics`, which arrived between the reviewer's audit pass and the prose containing the punch list.

This is not failure of the audit. It is the two cadences operating correctly, in opposite directions, on the same target. The friction between them is what produces the artefacts both sides care about — without the lag, the maintainer would have nothing to absorb; without the velocity, the reviewer would have nothing to audit.

For external adopters: expect any audit of this system to be partially obsolete by the time you read it. The artefact value of an audit is **not its present-tense snapshot** — that drifts within hours under active maintenance — **but its structural frame**: what categories of risk, what kinds of evidence, what falsifiable claims. The snapshot expires; the frame composts into the next audit.

A useful heuristic: read review documents as time-windowed dated photographs. Treat them as accurate at their timestamp and structural beyond it. The case study above has the date in its filename (`-2026-05-02.md`) precisely so future readers can apply that calibration without thinking about it. The companion documents — [`boring-reliability-control-plane.md`](../architecture/boring-reliability-control-plane.md), [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md), the relevant ADRs — are the structural frame; this case study is the photograph.

## Self-evolving doctrine: when the audit subsystem proposes rules about itself

After the cycle had absorbed external review (main cycle) and absorbed its own internal friction (self-triggered absorption above), it took one more recursive step worth naming: **the system began proposing amendments to its own doctrine, derived from its own audit data, without any external prompt for that specific amendment**.

The mechanism landed as two ADRs in sequence within minutes of each other:

- [ADR-134](../adrs/ADR-134-headless-self-improvement-proposer.md) — `cos-self-improvement-loop` reads control-plane evidence and emits bounded **operational** proposals (gate refactors, configuration changes, scoped fixes). Propose-only mode, human approval required, sandboxed write paths, blocked actions list.
- [ADR-135](../adrs/ADR-135-self-evolving-doctrine-proposals.md) — `cos-doctrine-proposer` reads the same evidence and emits proposed **doctrine amendments** as markdown under `docs/03-PoCs/proposals/`. Status `proposed`, `runtime_effect: none`. The system proposes new rules; it does not apply them.

On first execution against the live audit data, the doctrine proposer generated **five concrete amendments**, each grounded in observation rather than speculation:

| Amendment | Trigger evidence | Source audit |
|---|---|---|
| Review direct-main bypasses as emergency debt | 10 bypass events recorded | `direct-main-bypass.jsonl` |
| Prefer semantic matching over substring matching in gates | 24 false-positive events on `git-op-blocks` | `cos-false-positive-ledger` |
| Warnings need expiry, owner, or explicit deferral | 2 demotions, 0 ROI-signed | `cos-demotion-loop-audit` |
| Maintainer-cache allowlists are not transferable doctrine | 1,580 occurrences across 201 files, 65 in `legacy_audited` | `cos-silent-failure-audit` |
| Self-improvement remains propose-only until promotion evidence exists | 7 active proposals, `auto_merge: false` policy | `cos-self-improvement-loop` |

The second amendment — *"Prefer semantic matching over substring matching in gates"* — is structurally identical to a finding in the original external review (Risk B: substring-match governance). The proposer did not have access to the review document. It re-derived the finding by reading its own `cos-false-positive-ledger` and counting the events. **The system internalised the review's framework deeply enough to reproduce one of its findings on its own observability data.**

Each proposal is structured the same way other primitives in the system are structured:

- `evidence` — concrete data from a named audit
- `proposed_rule` — the specific rule or refinement
- `non_goals` — anti-patterns to avoid (e.g. *"ban emergency bypasses"*, *"remove conservative safety gates"*, *"silence historical false positives without classification"*)
- `required_follow_up` — operational steps the rule implies

The presence of `non_goals` in every proposal is the signal that the proposer is not naive: it knows what kind of over-correction the doctrine is meant to prevent and refuses to propose it. That property is what allows the system to propose changes to itself without becoming unsafe.

The ceiling, named explicitly in ADR-135: *"This must not become autonomous policy mutation. Doctrine is governance surface."* All amendments land as markdown under `docs/03-PoCs/proposals/` with `runtime_effect: none`. The next operator decides whether each one becomes part of the doctrine; the system does not promote its own proposals.

For external adopters, this turns into another **falsifiable claim**: if the doctrine proposer is real, subsequent runs against new audit data should produce new proposals when the data shifts (and stop producing existing proposals when their evidence is resolved). If after several months of evolving audit data the proposal set is static, the loop is broken. The first generation is the baseline; subsequent ones can be tracked by `git log docs/03-PoCs/proposals/` and correlating timestamps with audit-event volume.

The recursion now reaches four levels: external review → ADRs and enforcement → audit subsystem observing the system → audit subsystem proposing amendments to the rules that govern it. The fifth level — auto-application of approved amendments — is **deliberately not built**. That is the boundary between "self-improving under governed human review" and "autonomous self-modifying software". The product claim sits on the right side of that boundary by design.

## Convergence: when internal proposals reproduce external review findings

Worth naming as a distinct observation from the capability above (the system *can* propose doctrine amendments) is the specific outcome on first execution: **one of the five amendments the system generated internally is structurally identical to a finding from the external review that triggered this cycle, derived entirely from internal observability data, with no access to the review document.**

The escalating recursion in this cycle, ordered by depth rather than wall-clock:

- **Stage 1 — observation only.** The system ran audits passively: warnings logged, no action taken. State at the start of the cycle.
- **Stage 2 — friction absorption.** The system absorbed friction it produced about itself during its own documentation pass and converted it into a hardening commit (`95239a50`), without external prompt for that specific fix. Documented above as *"Self-triggered absorption"*.
- **Stage 3 — operational proposals.** The system proposed bounded operational fixes for itself (commit `5ee415ba`, ADR-134, 7 active proposals) — all in `propose-only` mode with sandboxed write paths and human approval required.
- **Stage 4 — doctrine proposals.** The system proposed amendments to its own doctrine based on its own audit data (commit `4b20619c`, ADR-135, 5 active proposals).

The second of those 5 doctrine proposals — *"Prefer semantic matching over substring matching in gates"*, triggered by 24 false-positive events on `git-op-blocks` — is structurally equivalent to **Risk B** in the original external SR review (substring-match governance, with concrete examples of gates firing on commit-message content rather than parsed command shape). The internal proposer did not have access to the review document. It re-derived the finding by counting events in `cos-false-positive-ledger` and applying the same admission contract every other proposal uses.

This is qualitatively different from *"the system absorbs external critique"*. It is **the system internally producing the same observations a competent external reviewer would produce**, by reading the same control-plane evidence the reviewer would read.

The natural follow-up question is whether this convergence means the external reviewer is now redundant. ADR-135 answers that explicitly: it is not, and must not become so. The product claim — *"self-improving under governed human review"* — preserves the human reviewer as a structural invariant, not as a dependency to be removed once the internal loop matures.

Two reasons for that ceiling, named for adopters:

1. **Internal observation reads its own data.** External review reads observability *plus* intent, context, prior art, and adjacent systems the internal data alone does not capture. The two are different inputs even when their outputs sometimes converge. Convergence on one item does not mean parity on all items.
2. **Promotion of a doctrine amendment is governance, not maintenance.** Governance changes that bypass external human review collapse the property the doctrine was built to preserve. The convergence above is a useful signal of internal coherence; it is not a license to remove the reviewer.

For external adopters, the falsifiable claim becomes: if the doctrine proposer produces **zero** amendments that converge with an independent external review, the loop is too narrow (it is only catching internal patterns the reviewer also misses). If it produces **only** amendments the external reviewer would not reach, the loop is hallucinating. The healthy zone is **partial convergence**, with the external reviewer continuing to surface findings the internal loop does not.

This case study itself is a single data point. Replication would require running the cycle a second time, against an independent external reviewer, and observing whether the internal proposer's generated set partially overlaps the new findings. The artefact is the loop; the evidence is in subsequent runs.

## Runway-not-rocket: building Shape B's infrastructure without operating Shape B

A property that closes the recursion documented above is the **runway-not-rocket discipline**: the system invests in the infrastructure required for the next operating shape without actually operating it.

[ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md) named the future Shape B (multi-maintainer, federated, distributed) and recommended *"do not implement Shape B until trigger fires"*. That recommendation is correct but easy to fail at: the natural temptations are either to implement none of Shape B (leaving the gap) or to implement all of it (premature complexity). Neither is right.

[ADR-136](../adrs/ADR-136-cross-instance-learning-runway.md) built the third option: a runway that

1. **costs less than full Shape B operation** — four non-speculative primitives: consumer evidence exchange, deterministic registry locks (`agentic-primitive-registry.lock.yaml` SHA-pinning every primitive, `skills/REGISTRY.lock` for the skill set), portable Engram bundle (export plus import-propose-only), and federation trigger audit;
2. **reduces the activation cost when triggers fire** — a future maintainer joining does not require the system to be redesigned from scratch; the primitives are present, dormant;
3. **does not commit the system to Shape B operation** — all imports are propose-only; locks are observed not enforced cross-machine; bundles are produced on demand, not synced automatically.

The structural elegance is in `manifests/federation-triggers.yaml`. ADR-132 named six trigger conditions for Shape B in prose. The runway converts each into an observable counter:

```yaml
observed:
  active_maintainers: 1
  active_machines: 2
  concurrent_remote_writers: 0
  external_consumer_reports_30d: 0
  repeated_cross_machine_lock_conflicts: 0
  unsupervised_remote_agents: 0
shape_b_triggers:
  active_maintainers: 2
  active_machines: 3
  concurrent_remote_writers: 1
  external_consumer_reports_30d: 1
  repeated_cross_machine_lock_conflicts: 2
  unsupervised_remote_agents: 1
```

When any observed value crosses its trigger threshold, the audit fires and the system *proposes* the Shape A → Shape B transition through the same propose-only mechanism documented in earlier sections. The transition stops being a discretionary human decision; it becomes an audit signal with a structural follow-up.

Combined with ADR-134 (`auto_merge: false`) and ADR-135 (`runtime_effect: none`), the runway forms the third ceiling stacked on the previous two. A fourth ceiling — anti-self-validation through required provenance — landed shortly after when the runway's first end-to-end drill made the gap visible. Four deliberate architectural refusals, each blocking a distinct runaway class:

| ADR / commit | Refusal | What it prevents |
|---|---|---|
| ADR-134 | `auto_merge: false` | Self-applying operational fixes without review |
| ADR-135 | `runtime_effect: none` | Self-modifying doctrine without review |
| ADR-136 | "runway, not federation" | Self-federating without trigger evidence |
| `d4535df0` | `independence + provenance required` | Self-validating with maintainer-owned evidence |

The fourth refusal closes the most subtle attack vector — one that became visible only after the runway's first drill ran end-to-end. Without it, a maintainer could:

- run a drill against a consumer project they themselves own;
- generate consumer evidence;
- import it via `cos-import-consumer-evidence`;
- produce an audit reporting external help;
- promote primitives based on that audit;
- close a self-flattering loop indistinguishable from real adoption.

The fix is structural. `manifests/external-adoption-evidence.yaml` codifies the schema of an admissible external-help claim: `independence.maintainer_owned: false`, `independence.same_machine: false`, `independence.same_repo: false`, `independence.self_reported: false`, plus a `provenance.producer` block carrying type, identity, optional signature, and timestamp. Evidence with any `independence` flag set to `true` is rejected as drill output, not as adoption signal. The system **refuses to validate itself with its own data**.

The first drill report — [`docs/06-Daily/reports/cross-instance-consumer-e2e-2026-05-03.md`](../reports/cross-instance-consumer-e2e-2026-05-03.md) — applies that schema to its own output and explicitly disqualifies itself: *"This is a drill report, not external adoption evidence. The generated consumer evidence is maintainer-owned, same-machine, same-repo, and self-reported; it must not sign the helps-projects product claim."* The doctrine is applied to the doctrine's own first verification artefact.

For external adopters, this is the falsifiable claim: a system that builds Shape B's runway should not also operate Shape B, and a system that runs drills should not also count drill output as adoption signal. If `cos-federation-trigger-audit` reports zero observed triggers and federation primitives are nonetheless executing in production, the discipline is broken. If the runway primitives never activate after triggers fire, the runway is decorative. If `manifests/external-adoption-evidence.yaml` accumulates entries with `maintainer_owned: true` *and* those entries are used to sign claims, the anti-self-validation is broken. The healthy state is **dormant runway with continuous trigger observability and zero self-signed adoption evidence**.

The runway-not-rocket pattern, plus the anti-self-validation refusal, is what makes the system **defendable as a product** rather than as a research project. A user adopting Cognitive OS today gets Shape A, knows the trigger conditions for Shape B, inherits a path to Shape B that does not require redesigning the system, *and* receives a guarantee that the product claims are not self-flattered through closed evidence loops. None of those properties require Shape B to be operating now.

## What the cycle does not prove

Stated honestly so the artefact is useful:

- **One demotion is not a discipline.** The discipline is the second, third, and tenth demotion, especially when one of them must be defended against the cost of building it. Re-read this document after the lifecycle manifest holds three or more `lifecycle_state: demoted` entries before drawing conclusions about durability.
- **The ROI dashboard has not yet signed a decision.** The first demotion was justified by portability, not by `cos_governance_roi.py` output. The dashboard is instrument, not cutting tool, until a demotion's stated reason is "ROI dashboard reported sustained net-negative".
- **Single-maintainer absorption is not multi-maintainer absorption.** The cycle completed inside one operator's continuous attention. The same shape under two contributors with disagreement would expose coordination costs this cycle did not pay. ADR-132 names that gap.

## Replication template

If another project wants to run a comparable cycle, the minimum scaffolding is:

1. A persistent decision log with stable identifiers (ADRs, Engram, equivalent).
2. At least one mechanical falsifier of self-reports (claim verification, aspirational audit, or equivalent).
3. A lifecycle vocabulary that includes a demotion state distinct from delete.
4. A CI gate that fails the build when the default surface grows past a declared threshold.
5. An explicit doctrine that declares retirement (not addition) as the dominant operation in the current phase.

Items 1–3 are paper without item 4. Item 4 is performative without item 5. Item 5 is a slogan without items 1–3. The combination is what makes the cycle reproducible rather than dependent on any one operator's diligence.

## Maturity position at end of cycle (snapshot, 2026-05-03)

The reviewer was asked, after the cycle closed, for a single-line characterisation of the system's maturity. The answer is preserved here verbatim because *"is it mature?"* is the question the doctrine demands an honest, falsifiable answer to — and because future reviewers should have a baseline to compare against rather than re-derive the question.

> **Post-adolescent operational.** The system has the internal discipline, the self-awareness, the instruments, and the doctrine. What it lacks is *tenure* (real production time under pressure it does not control) and *bilateral external validation* (use by third parties with measurable feedback). Those two do not accelerate with commits — only with calendar and exposure.

The phrasing is deliberate. *"Mature"* without qualification would be the lazy-reviewer answer the bilateral-pressure section warns against. *"Immature"* would ignore the evidence of self-correction this cycle produced. *"Post-adolescent"* names the specific shape: the system has stopped being undirected (childhood), has acquired internal regulation (adolescence), but has not yet earned the operational tenure that converts internal regulation into externally trustable robustness (adulthood).

Two properties this position depends on, both of which the system itself tracks:

- **Tenure** is the variable `cos-boring-reliability` measures cumulatively across sessions, incidents, recovery drills, and false-positive ledger drift. It is bounded by wall-clock, not by velocity.
- **Bilateral external validation** is the variable that does not yet have a primitive in the repository. It would look like a third-party project running `core` for 30+ days and reporting prevented-incident counts, false-positive ratios, and cognitive-cost qualitative feedback. Building the receiving primitive for that data is itself a future cycle.

That receiving primitive now exists as a truth surface:
[`scripts/cos-claim-signature-audit`](../../scripts/cos-claim-signature-audit)
and [`claim-signature-audit.md`](../architecture/claim-signature-audit.md). It
does not sign the claims by itself. It records exactly what evidence would sign
them, and currently reports the three remaining gaps as warnings.

The position is intentionally falsifiable. Re-read this snapshot when:

- `cos_demotion_loop_audit` reports `status: pass` with `roi_signed_demotion_count >= 1` (the open warn budget closes 2026-06-02).
- The lifecycle manifest holds three or more `lifecycle_state: demoted` entries.
- A non-maintainer project posts a 30+ day adoption report with measurable findings.

When all three are true, *"post-adolescent"* is no longer the right word. Until then, it is.

The reviewer's signature on this characterisation is the act of writing it into the case-study commit, not a separate sign-off field. The maintainer's acceptance of this characterisation is the act of merging it. Both are obligations under the bilateral-pressure section above.

## How to read this document over time

This is a snapshot of one cycle. The reproducible value is the structure of the cycle, not its specific findings. If a later review produces a different reframing or a different set of artefacts, that is expected and welcome. The point of preserving this is so the *shape* of the response — capture, reframe, enforce, test, document — has a worked example to compare against, not a procedure to comply with.
