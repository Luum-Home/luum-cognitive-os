---

adr: 137
title: Operational Trajectory — From Governance Layer Over Agents to Embedded Runtime
status: accepted
implementation_status: planned
date: 2026-05-03
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: [strategy, trajectory, runtime, harness-agnostic, dx, cloud-flows]
---

# ADR-137: Operational Trajectory — From Governance Layer Over Agents to Embedded Runtime

## Status

**Accepted** for the trajectory itself. The directional commitment (B → A, defined below) is firm.

The individual priority shifts that follow from the trajectory are **not scheduled** by this ADR. They become required artefacts only when a flow under the [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) needs them. This ADR fixes the destination, not the calendar.

## Context

Today Cognitive OS operates as **Framing B**: a governance layer over agents that already exist (Claude Code, Codex, Cursor, etc.). The harness runs the agent; COS provides the audit trail, the hooks, the Engram memory layer, the dispatch policy, and the propose-only contract. The agent is not aware it is inside COS — COS is wrapped around the harness.

This shape is operationally sound for the maintainer's day-to-day workflow and for absorption of external agent capabilities as they ship. It is also a **dead end** for the use case named in [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md): cloud-instance agents executing maintenance flows (vulnerability remediation, bug fixing, feature construction, documentation, primitive expansion) under human audit. That use case requires the agent to behave as a COS-native runtime: Engram-aware, hook-aware, dispatch-aware, lifecycle-aware. A wrapper that lives only on the maintainer's machine cannot fulfil it.

The target is **Framing A**: COS as a runtime that travels with the agent. A cloud worker boots with `cos-init`, registers with a central Engram, runs hooks natively, dispatches through the configured providers, and returns evidence via the [ADR-136](ADR-136-cross-instance-learning-runway.md) runway. The agent operates *inside* COS, not next to it.

This trajectory is **not** a fork. It is a directional commitment that the present Framing B operation is the starting point, not the destination.

## Decision

Commit Cognitive OS to the trajectory **Framing B → Framing A**. Specifically:

1. Framing B remains the operational reality during transition. No deprecation, no removal of governance-layer behaviour. The maintainer's workflow continues unchanged.
2. Every new flow shipped under [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) is evaluated by **how much of Framing A it exercises**. A flow that runs entirely in Framing B is acceptable for `lab` but cannot be promoted to `default-on` or `core`.
3. The [ADR-136](ADR-136-cross-instance-learning-runway.md) runway primitives (`cos-engram-bundle`, `cos-engram-import-propose`, registry locks, `cos-cross-instance-drill`) are the transport layer for the transition. They were built as runway; this ADR commits to using them as runtime infrastructure.
4. Framing A is **not** Shape B in the sense of [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md). Shape B is a *maintainer-topology* fork (one human → multiple humans). Framing A is a *runtime-topology* shift (governance layer → embedded runtime). They are orthogonal axes. Framing A under Shape A — embedded runtime, single maintainer signing — is the explicit near-term shape and is the configuration this ADR commits to.

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) | **Orthogonal axis.** ADR-132 governs *who* operates the system (one maintainer vs. multi-maintainer). This ADR governs *where the runtime lives* (in the wrapper vs. in the agent). The two combine: present configuration is `(Shape A, Framing B)`; near-term target is `(Shape A, Framing A)`; Shape B remains `exploration`. |
| [ADR-064](ADR-064-harness-agnostic-cognitive-os.md) | **Becomes prerequisite, not aspiration.** Framing A requires hooks, session lifecycle, and Engram client to behave consistently regardless of harness. ADR-064 implementation completion is now gated by the first flow that requires it, not by a separate roadmap. |
| [ADR-136](ADR-136-cross-instance-learning-runway.md) | **Runway becomes runtime.** The four primitive families introduced as Shape B runway (consumer evidence exchange, deterministic registry locks, portable Engram bundle, federation trigger audit) are repurposed as the transport layer for Framing A flows. The federation triggers become flow-activation observability. |
| [ADR-126](ADR-126-agentic-primitive-lifecycle-governor.md) | **Applies unchanged.** Flow primitives use the same eight-state lifecycle. Demotion-with-evidence is the discipline that prevents Framing A flows from re-inflating the surface. |
| [ADR-133](ADR-133-expansion-without-monsterization.md) | **Applies unchanged.** Every Framing A primitive starts in `lab`. Promotion requires evidence. The bootstrap plan is bound by this. |
| [ADR-134](ADR-134-headless-self-improvement-proposer.md) / [ADR-135](ADR-135-self-evolving-doctrine-proposals.md) | **Contract pattern generalises.** The propose-only-with-human-approval contract these ADRs enforce for self-improvement is the same contract Framing A flows use for their output. The transport changes (PR comment vs. cloud-worker evidence bundle); the contract does not. |

## Priority shifts

The trajectory implies the following priority changes. These are **not scheduled** here; they become required when a flow needs them.

**Moves up:**

| Surface | Why |
|---|---|
| ADR-064 implementation completion | Embedded runtime must run on every harness a flow targets, not just Claude Code. Codex coverage is currently partial; cloud-worker harnesses (CI runners, ephemeral containers) have no adapter. |
| `docs/04-Concepts/architecture/bootstrap-portability.md` enforced as gate | Cloud-worker boot is the test of portability. A `cos-init` that assumes `~/.claude/` fails the first time a worker runs in a vanilla container. |
| Cross-machine Engram daemon discovery | Embedded runtime needs Engram addressable beyond `127.0.0.1:7437`. Today this is a maintainer-machine assumption. |
| Cloud-worker session lifecycle | SessionStart / SessionEnd / Stop hooks must behave correctly when the "session" is an ephemeral container, not a developer terminal. The session-start runtime diet (v0.23) is the right scaffold. |
| `cos-cloud-worker-bootstrap.sh` | The single entry point a cloud instance runs to become COS-native. Does not exist yet. The first flow ships it; reuse-or-die governs whether it becomes a skill. |

**Stays the same:**

| Surface | Why |
|---|---|
| Hard governance gates (`secret-detector`, `destructive-git-blocker`, `lethal-trifecta-gate`, `safe-worktree-remove`, `concurrent-write-guard`) | Already correct shape for both framings. |
| Propose-only contract from ADR-134 / ADR-135 | Already correct shape for both framings; only the transport changes. |
| Boring-reliability dashboard, lifecycle manifest, demotion-with-evidence | Already correct shape; gains new flow-level signals over time without restructure. |
| Anti-self-validation (`manifests/external-adoption-evidence.yaml`) | Schema applies identically to evidence produced by an embedded runtime. |

**Does not move up (deliberately):**

| Surface | Why excluded |
|---|---|
| Custom human-review UI | Framing B persists during transition; GitHub PR + `cos-engram-import-propose` output remains the audit substrate. UI is gated behind "JSONL + PR measurably fails," not behind the trajectory itself. |
| Pre-built adapters for Cursor / Aider / Continue / other harnesses with no flow | The trajectory means thin adapters are needed only where a flow runs. Pre-building adapters is surface inflation toward Framing B, not toward A. |
| Replacement of the propose-only contract with a richer transaction model | The contract is correct for both framings. Modifying it speculatively before a flow demands it would be over-engineering. |
| Activation of Shape B (multi-maintainer) | Independent decision under [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) triggers. Framing A under Shape A is fully coherent and is what this ADR commits to. |

## Acceptance Criteria

This ADR is satisfied when the following are observable:

1. The next flow shipped under [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) carries an explicit **framing-exercise statement** in its skill metadata: how much of Framing A it exercises (e.g., "boots cos-init in sandbox: yes; uses native Engram client: no; dispatches through configured providers: yes"). Flows without this statement cannot be promoted out of `lab`.
2. ADR-064 implementation status is reflected in [`docs/04-Concepts/architecture/bootstrap-portability.md`](../architecture/bootstrap-portability.md) and the gaps blocking the first cloud-worker flow are named there as backlog with owners.
3. `manifests/federation-triggers.yaml` (introduced in ADR-136 as runway observability) gains a `framing_a_flows_active` counter or equivalent. The counter increments when a flow runs end-to-end in Framing A. Zero counter after three flows is signal that the trajectory is being talked about, not lived.
4. No flow primitive promoted to `core` or `team` tier before at least one flow has shipped end-to-end in Framing A. This is the structural protection against the trajectory becoming aspirational.

## Border Cases

- **A flow that runs entirely in Framing B.** Acceptable for `lab` and `sandbox`; not promotable beyond `advisory`. The trajectory does not forbid B-only flows; it forbids treating them as the destination.
- **A flow that runs partially in Framing A** (e.g., COS hooks fire but Engram is read-only from outside). Acceptable for `default-on`. The framing-exercise statement makes the partial coverage explicit.
- **A flow whose deploy target makes Framing A impossible** (e.g., a third-party SaaS agent with a closed runtime). Acceptable as Framing B integration, classified as such, and not used as evidence for the trajectory.
- **Shape B (multi-maintainer) trigger fires before Framing A is fully reached.** The two trajectories proceed independently. Shape B implementation re-evaluates this ADR's priority shifts in its own context but does not block them.
- **The trajectory stalls** (three flows ship, none exercises Framing A). The ADR's acceptance criteria fail, surfacing the stall as auditable signal. Response: re-evaluate whether the bootstrap plan's first flow choice was correct, not whether the trajectory was correct.

## Consequences

**Positive.**

- The strategic intent in [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) has a directional anchor that future flows can be evaluated against.
- ADR-064 stops being aspirational and becomes flow-gated. Its completion is paid for by the flows that need it, not by a separate roadmap.
- The runway primitives from ADR-136 acquire a second purpose (runtime transport layer), justifying their continued existence beyond the cross-instance drill.
- The orthogonality of Framing and Shape is named explicitly. Future contributors do not conflate "embedded runtime" with "multi-maintainer," which are distinct concerns.

**Negative / risk.**

- Naming a trajectory creates pressure to demonstrate progress on it. The acceptance criteria above are designed to convert that pressure into observable signal rather than into surface inflation.
- The trajectory may be partially read as deprecation of Framing B. The decision text explicitly preserves Framing B; future communications must not let "trajectory toward A" become "B is going away."
- ADR-064 completion is no longer paced by a separate roadmap. If no flow ever needs full ADR-064 coverage, ADR-064 stays partial. That is acceptable under the trajectory's logic but may be uncomfortable for readers expecting a roadmap.

**Of not making this commitment.**

- The bootstrap plan's first flow ships and `e2b-integration` is treated as a one-off integration rather than as the first artefact of a directional shift. The cycle ends without producing reusable trajectory evidence.
- ADR-064 remains aspirational indefinitely. Each new harness adapter is justified case-by-case rather than against a directional anchor.
- The runway primitives from ADR-136 stay decorative — exercised by drills, never load-bearing for real flows.

## Recommendation

Open the ADR (this document). Begin the bootstrap plan's step 2 (flow contract schema ADR) only after this ADR is committed and the framing-exercise statement requirement is reflected in the skill metadata schema.

Re-read this ADR before promoting any flow primitive out of `lab`. The promotion test is: *does this primitive move us measurably toward Framing A, and is the framing-exercise statement honest?*

## Cross-references

- [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) — the operational plan this ADR's trajectory anchors.
- [ADR-064](ADR-064-harness-agnostic-cognitive-os.md) — harness-agnostic implementation, now flow-gated rather than roadmap-gated.
- [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — orthogonal axis (maintainer topology); this ADR commits to `(Shape A, Framing A)`.
- [ADR-136](ADR-136-cross-instance-learning-runway.md) — runway primitives, now repurposed as runtime transport layer.
- [ADR-126](ADR-126-agentic-primitive-lifecycle-governor.md) — lifecycle discipline that prevents trajectory from inflating surface.
- [ADR-133](ADR-133-expansion-without-monsterization.md) — `lab`-first promotion gate, applies to all flow primitives.
- [ADR-134](ADR-134-headless-self-improvement-proposer.md) / [ADR-135](ADR-135-self-evolving-doctrine-proposals.md) — propose-only contract pattern, transport-agnostic.
- [`bootstrap-portability.md`](../architecture/bootstrap-portability.md) — gate that becomes load-bearing under Framing A.
- [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md) — rationale layer; the "knows-when-it-doesn't-work" property applies to flows under this trajectory.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

