# Cognitive Prosthesis — Why the System Has This Shape

> Companion to [boring-reliability-control-plane.md](boring-reliability-control-plane.md).
> The control-plane document is the **operational doctrine**: real / measurable
> / reversible / honest / evidence-backed. This document is the **rationale**:
> why those five properties became the contract, why the architecture looks
> the way it looks, and what readers should infer when something feels
> idiosyncratic.

## Audience

A new contributor, an external auditor, or a future-self of the maintainer
asking: *why does this system have these shapes? Why these particular
gates, this particular memory layer, this particular doctrine?* The
intent is not to defend the choices, but to make the underlying logic
explicit so subsequent decisions stay coherent with it.

Not in scope here: biographical or behavioural detail about the
maintainer. That belongs in personal documents, not in the repository
of an OSS-shaped governance system.

## The system is a mirror, not a metaphor

The doctrine *real / measurable / reversible / honest / evidence-backed*
is the same filter the maintainer applies, in practice, when evaluating
his own technical decisions. The taxonomy `REAL / DORMANT / ASPIRATIONAL`
in `scripts/aspirational_audit.py` is the same taxonomy used (informally,
in the maintainer's own head) to classify whether a given decision has
landed or is still wishful thinking.

This is not adoption of an external framework. It is **externalisation
of an internal one**. The implication for contributors:

- Doctrine that looks idiosyncratic usually has a one-line internal
  rationale that is consistent across the system. If a decision
  surprises you, the question to ask is *what filter is being applied
  here?*, not *is this arbitrary?*
- Inconsistencies, when they exist, are signals that the maintainer's
  filter has not yet been applied to that surface. They are real bugs
  to fix, not deliberate design.

## Cognitive prosthesis

The system contains three components whose function is to externalise
the maintainer's ongoing thinking, not to ship features:

1. **Engram** — persists what was learned, decided, or discovered, with
   decay and reinforcement. Survives session compaction and machine
   sleep. Operates as the long-term memory layer.
2. **ADRs** — preserve decisions in version control with cross-links
   to implementation files, reports, and other ADRs. Operate as the
   medium-term reasoning layer.
3. **`cos-boring-reliability` dashboard** — surfaces the current
   operational state of the system (false-positive counts, runtime
   coverage, WIP safety, recovery drill pass rate) so a single look
   reveals whether judgement is sound or has drifted.

These exist because **a single maintainer's sustained attention has
limits**. Building them is a precondition for sustaining the project,
not a luxury layer. Treat them as load-bearing.

## Guardrails against tired-self

A non-trivial fraction of the hooks (`destructive-git-blocker`,
`secret-detector`, `concurrent-write-guard`, `orchestrator-claim-gate`,
`safe-worktree-remove`, `lethal-trifecta-gate`) exist because the
maintainer assumed his future-self might, in a moment of fatigue,
push to `main` without thinking, leak a credential into a commit
body, destroy in-flight work, or merge an unverified claim.

The hooks are not bureaucracy. They are explicit fences against
known failure modes of human attention under cost. If a contributor
finds them in the way, the question is *which mode is this fence
guarding against?*, not *can I bypass it?*. The bypass mechanism
exists for documented exceptions (`COS_ALLOW_DESTRUCTIVE_GIT=1`,
`--no-verify`, `--allow-destructive` token). It is intentional that
bypass requires a deliberate keystroke; that is the design.

## Dogfood, not consumable

There is no `dev`/`staging`/`prod` separation. The maintainer is
simultaneously the first user, the last QA, and the adversary
against whom the gates are tested. Hooks bring blockers in real
sessions; they fail closed on real commits; their false-positive
rate is measured by `cos-false-positive-ledger`.

The implication: the system is not a polished product to consume.
It is an environment to operate inside. New contributors should
expect to be blocked by their own gates and should treat that as
the expected experience, not as friction to remove.

The corollary: simplifying the system to make it "easier to consume"
typically removes the part that gives it value. The boring-reliability
doctrine names the route to disciplined simplification — demote
gates that are not real / measurable / reversible / honest /
evidence-backed, do not delete them globally.

## Subtraction + maturity-driven, not addition-driven

Most open-source projects increase in features over time. This one
explicitly does not. `rules/phase-aware-agents.md` declares the
current phase as `reconstruction`: rewrite code that does not meet
standards, demote primitives that do not satisfy the contract, do
not defer fixes as "future work".

That is a posture, not a label. The signals that this is the
direction:

- ADR-130 + ADR-131 removed eleven workflows by renaming them to
  `.disabled`, not by adding two new ones.
- The boring-reliability control plane is built around
  `cos-default-visible-reducer` (which proposes demotions) and
  `cos-silent-failure-audit` (which prevents silent growth), not
  around adding new visible primitives.
- The maturity manifest (`manifests/governance-maturity.yaml`)
  labels gates as `advisory` / `observe` rather than re-classifying
  them as `blocking` without evidence.

If a proposed feature looks like net-new surface area without
demoting something existing, it probably does not belong in the
default profile. It belongs in `lab` until it earns promotion.

## Single-maintainer calibration

The system today is calibrated to fit one maintainer's working
style and cognitive bandwidth. 162 skills, 116 hooks, and 1,580
classified silent-failure occurrences are quantities one attentive
brain can hold over time, given the externalisation infrastructure
above. For any other person, those quantities are pure overload.

This is not a defect; it is a deliberate scope. The cost — that
the system fits like a glove made to measure — is named explicitly
in [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md).
That ADR also names the trigger conditions that would warrant
re-shaping the system for a wider audience: a sustained second
contributor, or a specific external organisation requesting
unmediated consumption. Until those triggers fire, the present
shape is correct.

The five provisional constraints in ADR-132 (hook portability
declaration, evidence-blocks for tier claims, topic-key
namespacing in Engram, no hard-coded filesystem assumptions,
progressive externalisation of the maintainer's mental cache) are
the discipline that keeps the door open to multi-maintainer at
low cost without committing to it now.

A property worth naming explicitly: the system's response velocity
— feedback → ADR → implementation → audit, often inside a single
working day — is not separable from the single-maintainer shape.
The same absence of review quorum, code-owners file, and shared
mental cache that ADR-132 catalogues as risk is what makes the
iteration loop sub-daily. Multi-maintainer adoption is therefore
not only an onboarding cost; it is a deliberate trade of iteration
speed for durability. The trigger conditions in ADR-132 should be
read with this in mind: the question is not *when does a second
maintainer appear*, it is *when is the durability gain worth the
velocity loss*. The two framings produce different decisions.

## How to read this document over time

This is not a manifesto and it is not a contract. It is a
**snapshot of the rationale** at a moment when the system reached
operational maturity. As the maintainer's filter evolves — and it
will — this document should evolve with it, or be marked stale.

The companion documents to read alongside, in order:

1. [`boring-reliability-control-plane.md`](boring-reliability-control-plane.md)
   — what the doctrine says.
2. This document — why the doctrine looks the way it does.
3. [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md)
   — the next strategic decision the system faces.

If, while reading the codebase, something seems opinionated without
explanation, the explanation is most likely one of the five sections
above. If none of them fit, that is signal: either the maintainer's
filter has not been applied to that surface yet, or the section
above is missing a case the new evidence reveals. Both are useful
discoveries; both deserve a follow-up.
