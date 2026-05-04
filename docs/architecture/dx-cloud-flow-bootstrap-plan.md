# DX-First Cloud Flow Bootstrap Plan

> **Status**: ready-for-step-3 (trajectory ADR-137 + flow contract schema ADR-138 committed; cloud premises ADR-139..142 committed; first flow lab entry pending)
> **Date**: 2026-05-03 (updated 2026-05-04: ADR-139..142 landed)
> **Audience**: maintainer + future contributors evaluating the next operational direction
> **Companion docs**: [`cognitive-prosthesis.md`](cognitive-prosthesis.md), [`boring-reliability-control-plane.md`](boring-reliability-control-plane.md), [ADR-137](../adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md), [ADR-138](../adrs/ADR-138-flow-contract-schema.md), [ADR-139](../adrs/ADR-139-account-agnostic-multi-provider-runtime.md), [ADR-140](../adrs/ADR-140-cross-os-containerized-deployment.md), [ADR-141](../adrs/ADR-141-engram-cloud-cross-instance-replication.md), [ADR-142](../adrs/ADR-142-compliance-audit-air-gapped-surface.md), [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md), [ADR-136](../adrs/ADR-136-cross-instance-learning-runway.md), [ADR-064](../adrs/ADR-064-harness-agnostic-cognitive-os.md)

This document captures a strategic direction surfaced in conversation and converts it into a concrete, bounded bootstrap plan. It is **not** an ADR (no decision is being committed) and **not** a roadmap (no dates beyond the first flow). It is a plan in the same sense as [`expansion-hardening-plan.md`](expansion-hardening-plan.md): a named direction with explicit non-goals and falsifiable conditions.

## Strategic intent

Cognitive OS is **not** positioned as a product to consume. It is positioned as a **runtime of cognitive prosthesis** for AI agents that execute maintenance flows in cloud instances under human audit. The flows in scope:

- Vulnerability remediation
- Bug fixing
- Feature construction
- Documentation generation
- Expansion of agent primitives covering the codebase intelligently

The non-negotiable property of every flow: a human signs the final landing. Agents propose; humans approve. The same contract that ADR-134 (`headless-self-improvement-proposer`) and ADR-135 (`self-evolving-doctrine-proposals`) already enforce internally is generalised to all agent work.

## What already aligns (no construction needed)

The repository contains the primitives this direction requires. They were built for Shape A maintenance, but their shape happens to be the right shape for Shape B agent flows under human audit:

| Capability | Mechanism | Why it maps |
|---|---|---|
| Per-event audit trail | `agent-audit-trail.jsonl`, `hook-timing.jsonl`, `blast-radius.jsonl`, `clarification-events.jsonl`, `cost-events.jsonl` | "Human audits" reduces to consuming JSONL in a UI or alert pipeline. |
| Propose-only as enforced default | ADR-134 / ADR-135 | The contract "agent proposes, human approves" is already wired and tested against real audit data. |
| Lifecycle with `demotion_evidence` | ADR-126 | Required to "expand primitives covering the codebase" without re-inflating to 200+ unused skills. |
| Anti-self-validation | `manifests/external-adoption-evidence.yaml`, commit `d4535df` | Trust contract when a cloud worker reports its own work — schema rejects self-reported, maintainer-owned, or same-machine evidence as adoption signal. |
| Hard governance gates | `secret-detector`, `destructive-git-blocker`, `lethal-trifecta-gate`, `safe-worktree-remove`, `concurrent-write-guard` | A cloud agent without these is a loaded gun. Already real, already blocking. |
| Cross-instance learning runway | ADR-136 (`cos-engram-bundle`, `cos-engram-import-propose`, registry locks, `cos-cross-instance-drill`) | The literal primitive set for "cloud worker does work, sends evidence bundle, maintainer machine imports propose-only, human signs." |
| Boring-reliability dashboard | `cos-boring-reliability` aggregator + 9 sub-tools | Operator-readable state per flow, per gate, per cost. |

## What does not exist yet (the actual gaps)

| Gap | Why it blocks the direction | Cheapest fill |
|---|---|---|
| Shape B runway is dormant | All six counters in `manifests/federation-triggers.yaml` are zero. The runway has been rehearsed via `cos-cross-instance-drill` but no real cross-instance work has run. | Run **one** real flow end-to-end; fire the first trigger. Do not activate Shape B yet. |
| No "spawn cloud worker bootstrapped with COS context" primitive | Skills `e2b-integration` and `gpu-sandbox` exist but are not wired into a deployable flow. There is no `cos-cloud-worker-bootstrap.sh`. | One thin script per first flow. Promote to skill only after second flow reuses it. |
| `llm-dispatch.jsonl` is empty | Per the 2026-05-02 DX assessment, the multi-provider dispatch code is real but production data is zero. Cloud agents without per-task cost are an unaccountable bill. | Wire **one** flow's dispatch to actually log. Use that data to validate the cost predictor. |
| Cross-harness adapters partial | Claude Code is canonical, Codex has gaps (per ADR-064 implementation status), CI runners / ephemeral VMs / containers have no adapter. | Pick the harness that matches the first flow's deploy target. Build only that adapter. |
| No human-review UX | Reviewers read JSONL and `docs/proposals/*.md` by hand. There is no surface for "N propose-only evidence bundles, sign or reject." | First flow uses GitHub PR + `cos-engram-import-propose` output as the review surface. New UX is deferred until the JSONL-on-PR pattern measurably fails. |
| No flow contract schema | Each flow needs a falsifiable success condition, a sandboxed write path, blocked-actions list, and required-evidence shape. The proposers (ADR-134/135) defined this contract for themselves; it is not yet generalised. | First flow ships its own contract; the second flow promotes the shared shape into a manifest. |

## The tradeoff that matters

The repository is calibrated for Shape A: one maintainer, sustained attention, low surface area. The use case described is Shape B: multiple instances reporting, human reviewer in the loop, ephemeral cloud workers. The hardened doctrine — `cognitive-prosthesis.md`, the boring-reliability control plane, the recent demotion-with-evidence work — explicitly **penalises adding surface before demoting**.

The risk is straightforward and concrete: build "cloud adapter," "review UI," "flow templates," "agent dispatcher" as new skills without first demoting unused surface. This reverses the subtraction work that absorbed the 2026-05-02 SR review and returns the project to the pre-v0.23 surface inflation.

The forcing function against that risk is already in the repo: `scripts/lab_first_promotion_gate.py`. Every new primitive in the bootstrap path **must** start in `lab` / `sandbox` and earn promotion through evidence. The plan below is shaped to satisfy that gate.

## Recommended bootstrap path

**Do not activate Shape B as a posture.** Instead, pick one flow and build it end-to-end on top of existing primitives. Activation of Shape B is then an observable consequence of a real flow firing real triggers, not a decision.

The candidate first flow: **vulnerability remediation in a sandbox**. Selection rationale:

1. Deterministic input — CVE feed / `semgrep` output / `dependabot` alert is structured and dated.
2. Verifiable output — tests pass, scan re-run is clean, PR is mergeable. The flow can prove its own success without human judgement on the fix's quality.
3. Existing sandbox primitive — `e2b-integration` skill exists; first flow consumes it instead of inventing one.
4. Natural fit for propose-only — output is a PR; human reviews via GitHub UI; landing goes through `scripts/merge-to-main.sh` (ADR-116 merge queue).
5. Importable evidence — flow result is sent back via `cos-engram-import-propose` without inventing a new evidence channel.
6. Survives anti-self-validation — the flow's signature is "agent proposed, human approved, tests passed, scan re-ran clean." None of those signals are self-reported by the agent.

### Bootstrap budget

What the first flow ships, and what it explicitly does not ship:

| Artefact | Status after first flow |
|---|---|
| `skills/vuln-remediation-flow/` | New skill, `lifecycle_state: lab`, `criticality: standard` |
| `scripts/cos-cloud-worker-bootstrap.sh` | New script, **not promoted to skill**; reused-or-die |
| `manifests/flow-contract-schema.yaml` | New manifest with the first flow's contract; promoted to shared shape only after second flow reuses it |
| `llm-dispatch.jsonl` instrumentation | Wired for the first flow only; populates real data for the cost predictor |
| `manifests/federation-triggers.yaml` | First counter (`external_consumer_reports_30d` or `concurrent_remote_writers`) becomes non-zero |
| `docs/architecture/vuln-remediation-flow.md` | Flow documentation with explicit `falsifiable_when` block |
| `docs/proposals/vuln-remediation-flow-results-<date>.md` | First propose-only evidence bundle, reviewed and signed (or rejected) by maintainer |
| New default-visible primitives | **Zero**. The `active_primitive_index` thresholds (`VISIBLE_WARN=12`, `VISIBLE_FAIL=25`) must not be crossed. |
| New rules added to `rules/RULES-COMPACT.md` | **Zero**. Flow-specific rules live in the skill's SKILL.md, not in the shared rule index. |
| Shape B activation | **No**. The runway primitives are exercised, not promoted. |

### Falsifiable conditions for this plan

The plan is **broken** if any of the following is observed:

- The first flow ships and `llm-dispatch.jsonl` is still empty after a week of operation.
- The first flow ships and the `external_consumer_reports_30d` counter remains zero after the flow has run on a non-maintainer codebase.
- A second flow lands without reusing `scripts/cos-cloud-worker-bootstrap.sh` or without promoting `manifests/flow-contract-schema.yaml` to shared shape.
- The default-visible primitive count crosses `VISIBLE_WARN=12` at any point during bootstrap. If it does, the plan is producing the surface inflation it was designed to prevent.
- The first cross-instance evidence bundle is signed despite carrying `maintainer_owned: true` or `same_machine: true` — i.e., the anti-self-validation schema (`d4535df`) is bypassed for convenience.
- Any flow primitive is promoted to `core` / `team` without a `demotion_evidence` block on something it replaces.

The plan is **healthy** if:

- Each new flow ships with its own falsifiable success condition in markdown and its own block in `manifests/flow-contract-schema.yaml`.
- The boring-reliability dashboard surfaces flow-level cost, latency, and propose-vs-rejected ratio per flow.
- After three flows, at least one shared primitive (sandbox bootstrap, evidence schema, dispatch-instrumentation pattern) has been promoted out of `lab`, with evidence.
- After three flows, at least one demoted flow exists (a flow whose propose-vs-reject ratio or cost made it not worth keeping in default-on).

## Direction (answered 2026-05-03): governance layer → runtime

The maintainer has explicitly named the trajectory: today COS operates as **Framing B** (governance layer over agents that already exist — Claude Code, Codex, etc.); the target is **Framing A** (runtime that travels with the agent — cloud worker boots with `cos-init` and operates *inside* the COS environment using Engram, hooks, and dispatch natively).

This is a directional decision, not a bridge-burning. Framing B is the current operational reality and is not deprecated; Framing A is the destination the bootstrap path converges toward. Flows shipped during the transition are evaluated by **how much of Framing A they exercise**, not by whether they fully embody it on day one.

Priority shifts that follow from the trajectory:

| Surface | Why it moves up | Where it lives today |
|---|---|---|
| ADR-064 (harness-agnostic COS) implementation completion | Runtime that travels needs portable hooks, portable session lifecycle, portable Engram client across harnesses. Codex coverage is partial. | `docs/adrs/ADR-064-harness-agnostic-cognitive-os.md`, `docs/architecture/bootstrap-portability.md` |
| `bootstrap-portability.md` enforced as gate, not aspiration | Cloud worker boot path is the test of portability. Aspirational portability dies the first time `cos-init` assumes `~/.claude/`. | `docs/architecture/bootstrap-portability.md` |
| Cross-machine `engram` daemon discovery | Runtime-side memory that survives cloud worker tear-down requires Engram to be addressable from outside the maintainer's machine, not just `127.0.0.1:7437`. | `mcp-server/cos_mcp.py`, `lib/engram_client.py` |
| Cloud-worker-specific session lifecycle | SessionStart / SessionEnd / Stop hooks need to behave correctly when the "session" is an ephemeral container, not a developer terminal. The session-start runtime diet (v0.23) is the right scaffold. | `docs/architecture/session-start-runtime-diet.md`, `hooks/session-start*.sh` |
| `cos-cloud-worker-bootstrap.sh` | The single entry point a cloud instance runs to become a COS-native runtime: install harness, fetch context, register with central instance, start session. Does not exist yet. | new — first flow ships it |

What does **not** move up (deliberately):

- Building a "central COS instance" UI for the governance layer. Framing B persists during transition; the existing JSONL + GitHub PR surface remains the audit substrate. A custom UI is still gated behind "JSONL + PR measurably fails."
- Generalising harness adapters across the full Cursor / Aider / Continue matrix. The trajectory toward Framing A means thin adapters are needed only for harnesses where a flow actually runs. Pre-built adapters for harnesses with no flow are surface inflation.
- Replacing the propose-only contract from ADR-134 / ADR-135 with a richer transaction model. The contract is correct for both framings; only its *transport* changes (PR comment vs. cloud worker evidence bundle).

The first flow's deploy target — `e2b-integration` sandbox — is **already** closer to Framing A than to Framing B. That is convenient, not coincidental: the cheapest first flow to build is also the one most aligned with the destination. This means the bootstrap path does not need a separate "transition" sub-plan; the first flow is the transition, evaluated by how much native runtime behaviour it exposes.

A trajectory ADR codifying this direction (B → A) and the priority shifts above is the **first** required artefact and gates the rest of the plan.

## Non-goals (explicit)

- Activating Shape B as a posture. Shape B activation is a consequence of trigger conditions firing in `manifests/federation-triggers.yaml`, not a roadmap milestone.
- Adding a "flow framework" abstraction before three flows have shipped and revealed the actual shared shape. ADR-133 (`expansion-without-monsterization`) prohibits speculative scaffolding; this plan is bound by it.
- Building a custom human-review UI before the GitHub-PR-plus-`cos-engram-import-propose` pattern measurably fails. The cost of the existing surface is reading a JSONL and a markdown file; the cost of a UI is maintaining a UI.
- Promoting any flow primitive to `core` or `team` tier in the first cycle. All flow primitives start in `lab`.
- Generalising the dispatch instrumentation across all flows before the first flow has produced a week of real data.

## How this plan relates to existing doctrine

This plan does not introduce new doctrine. It is a **sequencing document** for applying existing doctrine to a new operational class:

- `cognitive-prosthesis.md` §"Two maturity stages" — every new flow primitive must answer "how do I know mechanically when it stops working?"
- ADR-126 — flow primitives have lifecycle states; demotion is expected, not exceptional.
- ADR-133 — flow primitives start in `lab`; no shortcut to default-visible.
- ADR-134 / ADR-135 — propose-only is the contract for flow output; human approval is structural, not optional.
- ADR-136 — Shape B runway is exercised by real flows, not by drills alone.

If a flow proposes something that violates one of the above, the violation is the signal — either the flow does not belong, or the doctrine is wrong on that point. The plan deliberately does not preempt that resolution.

## Next concrete steps (ordered)

1. **Trajectory ADR — Framing B → A.** Landed as [ADR-137](../adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md). Codifies the directional answer above, names ADR-064 completion and `bootstrap-portability.md` enforcement as the runtime-side prerequisites, introduces the **framing-exercise statement** required in flow skill metadata. Does **not** schedule the priority shifts.
2. **Flow contract schema ADR.** Landed as [ADR-138](../adrs/ADR-138-flow-contract-schema.md). Commits the shape of `manifests/flow-contract-schema.yaml`: required fields per flow (input source, success condition, sandboxed write paths, blocked actions, evidence shape, framing-exercise statement per ADR-137), and the rule that the schema is promoted to shared form only after the second flow reuses it.
3. **Cloud premises ADRs.** Landed as ADR-139..142. These four ADRs are required before flow #1 is promoted beyond `lab`. They close the structural gaps that would otherwise be discovered mid-construction:
   - [ADR-139](../adrs/ADR-139-account-agnostic-multi-provider-runtime.md) — credential isolation and billing attribution; adds `credential_source`, `billing_identity`, `provider_capabilities` to the flow contract.
   - [ADR-140](../adrs/ADR-140-cross-os-containerized-deployment.md) — Docker Compose worker stack; satisfies `bootstrap-portability.md` for container surfaces; required before promoting flow #1 to `advisory` on CI targets.
   - [ADR-141](../adrs/ADR-141-engram-cloud-cross-instance-replication.md) — Engram cloud replication; satisfies the cross-machine Engram discovery prerequisite named in ADR-137 §Priority shifts; adds `engram_project_scope`, `air_gapped_compatible` to the flow contract.
   - [ADR-142](../adrs/ADR-142-compliance-audit-air-gapped-surface.md) — compliance audit surface; formalises `agent-audit-trail.jsonl` as the compliance evidence file, adds `tenant_id`, `audit_class` to the flow contract. Required before flow #1 is promoted beyond `advisory`.
4. **First flow lab entry.** `skills/vuln-remediation-flow/` registered with `lifecycle_state: lab` and the full contract from ADR-138 (including ADR-139..142 fields) wired in. Construction begins now.

With ADR-137..142 all committed, this plan moves from `ready-for-step-3` to **`ready-for-first-flow-lab`**. The first flow may be built against the canonical schema in ADR-138 (as extended by ADR-139/141/142) even before `manifests/flow-contract-schema.yaml` lands physically.
